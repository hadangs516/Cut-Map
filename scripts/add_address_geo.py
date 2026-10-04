# -*- coding: utf-8 -*-
"""주소가 없는 마커에, 마커 좌표와 가까운 KEDI 후보 주소를 붙인다 (#1005-04 작업 58).

입력: docs/data/markers.json(주소가 없는 마커), KEDI 2026 고등교육통계 xlsx, .env 의 VWORLD_KEY
출력: docs/data/markers.json 갱신(address 만 추가), address_review.md(붙이지 못한 마커 목록)

규칙
  1. 주소가 없는 마커마다, KEDI 2026 고등교육통계의 같은 학교(학교명에서 공백·괄호 표기를 뺀 이름이 같은 운영 중 학부 행) 후보 주소를 모두 모은다.
  2. 후보 주소를 VWorld 로 좌표 변환한다(도로명 -> 지번 순서).
  3. 후보 하나라도 좌표 변환에 실패하면 그 마커는 주소를 붙이지 않는다.
  4. 마커 좌표에서 1km 안에 있는 후보가 딱 하나이고, 나머지 후보가 모두 5km 보다 멀 때만 그 후보의 KEDI 주소를 붙인다.
  5. 그 밖의 마커는 address_review.md 에 마커 이름, 마커 좌표, 후보 주소, 후보별 거리, 붙이지 않은 이유를 적는다.
이미 address 가 있는 마커는 건드리지 않는다. 주소 값은 xlsx 에서 그대로 읽어 옮긴다(사람·LLM 이 옮기지 않는다).

키: .env 의 VWORLD_KEY 를 읽어 요청에만 쓴다. 화면·로그·파일 어디에도 키 값을 출력하지 않는다
(오류 문구에 키가 섞일 수 있어 출력 전에 가린다).

사용: python scripts/add_address_geo.py [--dry-run]
"""
import io
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from add_address import find_xlsx, is_candidate, load_kedi, norm_addr  # noqa: E402

MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
ENV_PATH = os.path.join(ROOT, ".env")
REVIEW = os.path.join(ROOT, "address_review.md")
ENDPOINT = "http://api.vworld.kr/req/address"
NEAR_KM = 1.0
FAR_KM = 5.0
SLEEP_SEC = 0.2
MAX_RETRY = 3
_KEY = None


def load_key():
    with io.open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("VWORLD_KEY="):
                v = line.split("=", 1)[1].strip()
                if v:
                    return v
    raise SystemExit(".env 에 VWORLD_KEY 가 없음")


def redact(s):
    s = str(s)
    return s.replace(_KEY, "***") if _KEY else s


def nrm(s):
    return re.sub(r"\([^)]*\)", "", re.sub(r"\s+", "", s or ""))


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def call(address, addr_type):
    params = {"service": "address", "request": "getcoord", "version": "2.0", "crs": "epsg:4326",
              "address": address, "type": addr_type, "format": "json", "key": _KEY}
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last = redact(e)
            time.sleep(1.0 * attempt)
    return {"response": {"status": "ERROR", "error": {"text": "요청 실패: %s" % last}}}


def geocode(address):
    """(lat, lon, 방식) 또는 (None, None, 실패 사유)"""
    reason = ""
    for t in ("road", "parcel"):
        d = call(address, t)
        time.sleep(SLEEP_SEC)
        resp = d.get("response", {})
        if resp.get("status") == "OK":
            p = resp["result"]["point"]
            return float(p["y"]), float(p["x"]), t
        reason = "%s: %s" % (resp.get("status"), redact(resp.get("error", {}).get("text", "")))
    return None, None, "road/parcel 모두 실패 (%s)" % reason


def main():
    global _KEY
    dry = "--dry-run" in sys.argv
    _KEY = load_key()
    kedi = load_kedi(find_xlsx())
    by_norm = {}
    for k in kedi:
        if is_candidate(k):
            by_norm.setdefault(nrm(k["학교명"]), []).append(k)
    with io.open(MARKERS, encoding="utf-8") as f:
        data = json.load(f)
    markers = data["markers"]
    targets = [m for m in markers if not m.get("address")]
    cache = {}
    attached, review = [], []
    for m in targets:
        cands, seen = [], set()
        for k in by_norm.get(nrm(m["univ"]), []):
            a = k["주소"]
            if not a or norm_addr(a) in seen:
                continue
            seen.add(norm_addr(a))
            cands.append(k)
        rows = []
        failed = False
        for k in cands:
            key = norm_addr(k["주소"])
            if key not in cache:
                cache[key] = geocode(key)
            lat, lon, info = cache[key]
            if lat is None:
                failed = True
                rows.append((k, None, info))
            else:
                rows.append((k, haversine_km(m["lat"], m["lon"], lat, lon), info))
        if not cands:
            review.append((m, rows, "KEDI에 같은 학교 후보 주소가 없음"))
            continue
        if failed:
            review.append((m, rows, "후보 중 좌표 변환에 실패한 것이 있음"))
            continue
        near = [r for r in rows if r[1] <= NEAR_KM]
        far_ok = all(r[1] > FAR_KM for r in rows if r not in near)
        if len(near) == 1 and far_ok:
            m["address"] = near[0][0]["주소"]
            attached.append((m, near[0]))
        elif len(near) == 0:
            review.append((m, rows, "마커 좌표 %gkm 안에 후보가 없음" % NEAR_KM))
        elif len(near) > 1:
            review.append((m, rows, "마커 좌표 %gkm 안에 후보가 %d개" % (NEAR_KM, len(near))))
        else:
            review.append((m, rows, "1km 안 후보는 1개지만 다른 후보 중 %gkm 이내가 있음" % FAR_KM))
    if not dry and attached:
        with io.open(MARKERS, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
    out = ["# 주소를 붙이지 못한 마커 (scripts/add_address_geo.py, 2026-10-05)", "",
           "규칙: 마커 좌표 %gkm 안의 후보가 딱 하나이고 나머지 후보가 모두 %gkm 보다 멀 때만 붙인다. 후보 주소는 KEDI 2026 고등교육통계의 같은 학교 운영 중 학부 행이다." % (NEAR_KM, FAR_KM), "",
           "주소가 없던 마커 %d개 중 붙인 것 %d개, 못 붙인 것 %d개.%s" % (len(targets), len(attached), len(review), " (--dry-run: 파일을 쓰지 않음)" if dry else ""), "",
           "| 마커 이름 | 마커 좌표 | 후보 주소 | 후보별 거리(km) | 붙이지 않은 이유 |", "|---|---|---|---|---|"]
    for m, rows, reason in review:
        addr = "<br>".join("%s %s" % (r[0]["본분교"], r[0]["주소"].replace("|", "\\|")) for r in rows) or "없음"
        dist = "<br>".join(("%.2f" % r[1]) if r[1] is not None else "좌표 변환 실패" for r in rows) or "-"
        out.append("| %s (%s) | %.5f, %.5f | %s | %s | %s |" % (m["campus"], m["univ"], m["lat"], m["lon"], addr, dist, reason))
    with io.open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("주소 없는 마커: %d, 붙임: %d, 못 붙임: %d" % (len(targets), len(attached), len(review)))
    print("후보 주소 좌표 변환 호출 대상(중복 제거): %d, 실패: %d" % (len(cache), sum(1 for v in cache.values() if v[0] is None)))
    for m, (k, d, how) in attached:
        print("  붙임: %s | %s | %.2fkm" % (m["campus"], k["주소"], d))
    print("review: %s" % os.path.basename(REVIEW))


if __name__ == "__main__":
    main()
