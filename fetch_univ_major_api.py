# -*- coding: utf-8 -*-
"""공공데이터포털 '전국대학별학과정보표준데이터' 오픈API 전체 수집.

기존 CSV(전국대학별학과정보표준데이터.csv)는 포털의 5만 건 다운로드 제한 때문에
잘려 있었다. 이 API는 pageNo를 넘겨가며 호출하면 전체 데이터를 받을 수 있다.

인증키는 .env의 SERVICE_KEY에서 읽는다. 코드에 직접 쓰지 않는다.
"""
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(HERE, ".env")
OUT = os.path.join(HERE, "univ_major_full.json")

ENDPOINT = "https://api.data.go.kr/openapi/tn_pubr_public_univ_major_api"
NUM_OF_ROWS = 1000
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


def decode(raw, content_type):
    """응답 인코딩을 헤더에서 먼저 보고, 없으면 utf-8 -> cp949 순서로 시도한다."""
    charset = None
    if content_type and "charset=" in content_type:
        charset = content_type.split("charset=")[-1].split(";")[0].strip().strip('"')
    candidates = [c for c in [charset, "utf-8", "cp949"] if c]
    seen = set()
    for enc in candidates:
        if enc.lower() in seen:
            continue
        seen.add(enc.lower())
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8(replace)"


def fetch_page(service_key, page_no):
    params = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": NUM_OF_ROWS,
        "type": "json",
    }
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                content_type = resp.headers.get("Content-Type", "")
            return raw, content_type
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            time.sleep(1.0 * attempt)
    raise SystemExit("페이지 %d 요청 실패 (재시도 %d회): %r" % (page_no, MAX_RETRY, last_err))


def main():
    env = load_env(ENV_PATH)
    service_key = env.get("SERVICE_KEY")
    if not service_key:
        raise SystemExit(".env에 SERVICE_KEY가 없음")

    all_items = []
    total_count = None
    page_no = 1
    encodings_seen = set()
    content_types_seen = set()

    while True:
        raw, content_type = fetch_page(service_key, page_no)
        content_types_seen.add(content_type)
        text, enc = decode(raw, content_type)
        encodings_seen.add(enc)

        data = json.loads(text)
        header = data.get("header") or data.get("response", {}).get("header", {})
        result_code = header.get("resultCode")
        if result_code not in (None, "00", "0"):
            raise SystemExit("API 오류 %r: %r (page %d)" % (result_code, header.get("resultMsg"), page_no))

        body = data.get("body") or data.get("response", {}).get("body", {})
        if total_count is None:
            total_count = int(body.get("totalCount", 0))
            print("totalCount =", total_count)

        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]

        if not items:
            break

        all_items.extend(items)
        print("page %d: +%d행 (누적 %d / %d)" % (page_no, len(items), len(all_items), total_count))

        if len(all_items) >= total_count:
            break
        page_no += 1
        time.sleep(SLEEP_SEC)

    out = {
        "source": {
            "title": "전국대학별학과정보표준데이터",
            "endpoint": ENDPOINT,
            "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "totalCount": total_count,
        "collected": len(all_items),
        "responseEncodings": sorted(encodings_seen),
        "responseContentTypes": sorted(content_types_seen),
        "items": all_items,
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print("저장 완료:", OUT)
    print("전체 %d행 저장 (totalCount=%d)" % (len(all_items), total_count))
    print("응답 인코딩:", sorted(encodings_seen))
    print("응답 Content-Type:", sorted(content_types_seen))


if __name__ == "__main__":
    main()
