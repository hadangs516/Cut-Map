# -*- coding: utf-8 -*-
"""경상남도교육청_대학정보_20250918.csv의 대학이름/주소를 VWorld Geocoder로 좌표 변환.

CSV 인코딩은 CP949. type=road로 먼저 시도하고 실패하면 type=parcel로 재시도한다.
둘 다 실패하면 좌표를 추정하지 않고 geocode_failed.json에 사유와 함께 남긴다.

인증키는 .env의 VWORLD_KEY에서 읽는다. 코드에 직접 쓰지 않는다.
"""
import csv
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
CSV_PATH = os.path.join(HERE, "경상남도교육청_대학정보_20250918.csv")
OUT_OK = os.path.join(HERE, "univ_coords.json")
OUT_FAIL = os.path.join(HERE, "geocode_failed.json")

ENDPOINT = "http://api.vworld.kr/req/address"
SLEEP_SEC = 0.2
MAX_RETRY = 3


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


def load_rows():
    with io.open(CSV_PATH, encoding="cp949", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


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


def geocode_one(key, univ_name, address):
    for addr_type in ("road", "parcel"):
        data = call_geocoder(key, address, addr_type)
        time.sleep(SLEEP_SEC)
        status = data.get("response", {}).get("status")
        if status == "OK":
            point = data["response"]["result"]["point"]
            return {
                "ok": True,
                "matchType": addr_type,
                "lat": float(point["y"]),
                "lon": float(point["x"]),
            }
        # NOT_FOUND면 다음 type으로, ERROR면 사유를 남기고 계속 다음 type 시도
        last_status = status
        last_error = data.get("response", {}).get("error", {}).get("text", "")
    reason = last_status or "UNKNOWN"
    if last_error:
        reason += ": " + last_error
    return {"ok": False, "reason": "road/parcel 모두 실패 (%s)" % reason}


def main():
    env = load_env(ENV_PATH)
    key = env.get("VWORLD_KEY")
    if not key:
        raise SystemExit(".env에 VWORLD_KEY가 없음")

    rows = load_rows()
    print("입력 행 수:", len(rows))

    success = []
    failed = []
    road_count = 0
    parcel_count = 0

    for i, r in enumerate(rows, 1):
        univ_name = r.get("대학이름", "")
        address = r.get("주소", "")
        if not address:
            failed.append({"대학이름": univ_name, "주소": address, "실패사유": "주소 컬럼이 비어있음"})
            continue

        result = geocode_one(key, univ_name, address)
        if result["ok"]:
            success.append({
                "대학이름": univ_name,
                "주소": address,
                "위도": result["lat"],
                "경도": result["lon"],
                "매칭방식": result["matchType"],
            })
            if result["matchType"] == "road":
                road_count += 1
            else:
                parcel_count += 1
        else:
            failed.append({"대학이름": univ_name, "주소": address, "실패사유": result["reason"]})

        print("[%d/%d] %s -> %s" % (i, len(rows), univ_name, "성공(%s)" % result.get("matchType") if result["ok"] else "실패"))

    with io.open(OUT_OK, "w", encoding="utf-8", newline="\n") as f:
        json.dump(success, f, ensure_ascii=False, indent=2)
    with io.open(OUT_FAIL, "w", encoding="utf-8", newline="\n") as f:
        json.dump(failed, f, ensure_ascii=False, indent=2)

    print()
    print("전체 %d건 중 성공 %d건, 실패 %d건" % (len(rows), len(success), len(failed)))
    print("road 성공 %d건, parcel 성공 %d건" % (road_count, parcel_count))
    if failed:
        print("실패 목록:")
        for f_ in failed:
            print(" -", f_["대학이름"], "|", f_["실패사유"])


if __name__ == "__main__":
    main()
