# -*- coding: utf-8 -*-
"""geocode_failed.json의 실패 건을 주소 정리 후 재시도.

순서대로 누적 적용한다 (이전 단계가 안 걸리면 건너뛰고, 걸리면 그 결과를 다음 단계의 입력으로 쓴다):
  1. 맨 앞 구주소 우편번호 제거
  2. 대학명 뒤에 붙은 부서명 제거 (대학명이 나온 지점부터 끝까지 자른다)
  3. 콤마/슬래시로 여러 캠퍼스가 같이 적힌 경우 첫 번째만 분리

각 단계마다 type=road -> type=parcel 순으로 재시도한다.
끝까지 실패하면 geocode_failed.json에 원래 내용 그대로 남기고 좌표를 추정하지 않는다.
성공하면 univ_coords.json에 추가하고, 원본 주소와 적용된 규칙(cleaned_by)을 같이 남긴다.
"""
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
COORDS_PATH = os.path.join(HERE, "univ_coords.json")
FAILED_PATH = os.path.join(HERE, "geocode_failed.json")

ENDPOINT = "http://api.vworld.kr/req/address"
SLEEP_SEC = 0.2
MAX_RETRY = 3

OLD_ZIP_RE = re.compile(
    r"^\s*[\(\[]?\s*(?:우\)?\s*)?[\(\[]?\s*(\d{3}-\d{3}|\d{5,6}|\d{3})\s*[\)\]]?\s*"
)


def load_env(path):
    env = {}
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def call_geocoder(key, address, addr_type):
    params = {
        "service": "address",
        "request": "getcoord",
        "version": "2.0",
        "crs": "epsg:4326",
        "address": address,
        "type": addr_type,
        "format": "json",
        "key": key,
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1.0 * attempt)
    return {"response": {"status": "ERROR", "error": {"text": "요청 실패: %r" % last_err}}}


def try_geocode(key, address):
    for addr_type in ("road", "parcel"):
        data = call_geocoder(key, address, addr_type)
        time.sleep(SLEEP_SEC)
        status = data.get("response", {}).get("status")
        if status == "OK":
            point = data["response"]["result"]["point"]
            return {"ok": True, "matchType": addr_type, "lat": float(point["y"]), "lon": float(point["x"])}
    return {"ok": False}


def strip_old_zip(addr):
    m = OLD_ZIP_RE.match(addr)
    if not m:
        return None
    new_addr = addr[m.end():].strip()
    return new_addr if new_addr and new_addr != addr else None


def strip_trailing_univ_dept(addr, univ_name):
    core = re.sub(r"\([^)]*\)\s*$", "", univ_name).strip()
    if not core:
        return None
    idx = addr.rfind(core)
    if idx <= 0:
        return None
    new_addr = addr[:idx].strip()
    return new_addr if new_addr and new_addr != addr else None


def split_multi_campus(addr):
    positions = [p for p in (addr.find(","), addr.find("/")) if p != -1]
    if not positions:
        return None
    cut = min(positions)
    first = addr[:cut].strip()
    return first if first and first != addr else None


def clean_and_retry(key, univ_name, original_addr):
    current = original_addr
    applied = []

    for rule_name, rule_fn in (
        ("strip_old_zip", lambda a: strip_old_zip(a)),
        ("strip_trailing_dept", lambda a: strip_trailing_univ_dept(a, univ_name)),
        ("split_multi_campus", lambda a: split_multi_campus(a)),
    ):
        candidate = rule_fn(current)
        if candidate is None:
            continue
        result = try_geocode(key, candidate)
        if result["ok"]:
            return {
                "ok": True,
                "cleanedAddress": candidate,
                "cleanedBy": applied + [rule_name],
                "matchType": result["matchType"],
                "lat": result["lat"],
                "lon": result["lon"],
            }
        current = candidate
        applied.append(rule_name)

    return {"ok": False, "cleanedBy": applied, "finalAddress": current}


def main():
    env = load_env(ENV_PATH)
    key = env.get("VWORLD_KEY")
    if not key:
        raise SystemExit(".env에 VWORLD_KEY가 없음")

    if not os.path.exists(FAILED_PATH):
        raise SystemExit("입력 파일 없음: %s" % FAILED_PATH)
    if not os.path.exists(COORDS_PATH):
        raise SystemExit("입력 파일 없음: %s" % COORDS_PATH)

    with io.open(FAILED_PATH, encoding="utf-8") as f:
        failed = json.load(f)
    with io.open(COORDS_PATH, encoding="utf-8") as f:
        coords = json.load(f)

    still_failed = []
    revived = []

    for item in failed:
        univ_name = item.get("대학이름", "")
        addr = item.get("주소", "")
        r = clean_and_retry(key, univ_name, addr)
        if r["ok"]:
            entry = {
                "대학이름": univ_name,
                "주소": r["cleanedAddress"],
                "원본주소": addr,
                "위도": r["lat"],
                "경도": r["lon"],
                "매칭방식": r["matchType"],
                "cleaned_by": r["cleanedBy"],
            }
            coords.append(entry)
            revived.append(entry)
        else:
            still_failed.append(item)

    with io.open(COORDS_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(coords, f, ensure_ascii=False, indent=2)
    with io.open(FAILED_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(still_failed, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("재시도 대상: %d건" % len(failed))
    lines.append("살아난 건: %d건" % len(revived))
    lines.append("끝까지 실패: %d건" % len(still_failed))
    lines.append("")
    lines.append("살아난 건 상세:")
    for e in revived:
        lines.append(" - %s | 규칙=%s | 매칭=%s | 정리주소=%s" % (e["대학이름"], "+".join(e["cleaned_by"]), e["매칭방식"], e["주소"]))
    lines.append("")
    lines.append("끝까지 실패한 대학 목록:")
    for it in still_failed:
        lines.append(" - %s" % it.get("대학이름", ""))

    with io.open(os.path.join(HERE, "retry_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
