# -*- coding: utf-8 -*-
"""#1005-20 작업 77~80: 주소를 붙이지 못했던 마커 10개를 처리한다.

77. 서울대(서울), 우석대(완주), 성신여대(서울), 경북대(대구), 고신대(부산), 청주대(청주), 예원예술대(임실)
    -> KEDI 2026 고등교육통계의 같은 학교 본교(제1캠퍼스) 학부 행 주소를 xlsx 에서 그대로 읽어 붙인다(address_review.md 후보와 같은지 확인).
78. 연세대학교(원주), 고려대학교(세종)
    -> KEDI 에서 같은 학교(학교명이 "학교명 …"으로 시작)의 분교 학부 행이 정확히 하나이고 주소가 강원 원주시 / 세종특별자치시일 때만 붙인다.
       조건에 맞지 않으면 붙이지 않고 찾은 행을 출력한다.
79. 동아대학교(부산) 마커를 승학캠퍼스로 옮긴다(IT 계열 학과는 승학캠퍼스에만 있음, 사용자 확인 2026-10-05).
    -> 주소는 KEDI 본교(제1캠퍼스) 주소, 좌표는 그 주소를 VWorld(.env VWORLD_KEY)로 변환한 값. 변환 실패면 바꾸지 않는다.
80. address_review.md 를 이번 결과로 다시 만든다(주소가 아직 없는 마커가 있으면 그 목록만 남긴다).
마커의 다른 좌표는 바꾸지 않는다(79의 동아대만 예외). 주소 값은 xlsx 에서 그대로 읽어 옮긴다. 키 값은 출력하지 않는다.
사용: python scripts/apply_address_fixes.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import add_address_geo as G  # noqa: E402
from add_address import find_xlsx, is_candidate, load_kedi, norm_addr  # noqa: E402

TARGET77 = ["서울대학교(서울)", "우석대학교(완주)", "성신여자대학교(서울)", "경북대학교(대구)", "고신대학교(부산)", "청주대학교(청주)", "예원예술대학교(임실)"]
TARGET78 = {"연세대학교(원주)": ("연세대학교", "원주시"), "고려대학교(세종)": ("고려대학교", "세종특별자치시")}
CAMPUS79 = "동아대학교(부산)"
BASIS79 = "IT 계열 학과는 승학캠퍼스에만 있음(사용자 확인, 2026-10-05)"


def main():
    kedi = [k for k in load_kedi(find_xlsx()) if is_candidate(k)]
    review_old = io.open(G.REVIEW, encoding="utf-8").read()
    data = json.load(io.open(G.MARKERS, encoding="utf-8"))
    ms = {m["campus"]: m for m in data["markers"]}
    log = []
    # ---- 77
    for camp in TARGET77:
        m = ms[camp]
        assert not m.get("address"), camp
        rows = [k for k in kedi if k["학교명"] == m["univ"] and k["본분교"] == "본교(제1캠퍼스)"]
        assert len(rows) == 1, (camp, len(rows))
        addr = rows[0]["주소"]
        assert addr in review_old, ("address_review.md 후보와 다름", camp, addr)
        m["address"] = addr
        log.append(("77", camp, "붙임", addr))
    # ---- 78
    for camp, (base, need) in TARGET78.items():
        m = ms[camp]
        assert not m.get("address"), camp
        rows = [k for k in kedi if (k["학교명"] == base or k["학교명"].startswith(base + " ")) and k["본분교"].startswith("분교")]
        found = ["%s | %s | %s | %s" % (k["학교명"], k["본분교"], k["시도"], k["주소"]) for k in rows]
        if len(rows) == 1 and need in rows[0]["주소"] and (rows[0]["시도"] == "강원" or need == "세종특별자치시"):
            m["address"] = rows[0]["주소"]
            log.append(("78", camp, "붙임", rows[0]["주소"]))
        else:
            log.append(("78", camp, "붙이지 않음(조건 불일치)", " / ".join(found) or "분교 학부 행 없음"))
    # ---- 79
    m = ms[CAMPUS79]
    rows = [k for k in kedi if k["학교명"] == m["univ"] and k["본분교"] == "본교(제1캠퍼스)"]
    assert len(rows) == 1 and "낙동대로550번길 37" in rows[0]["주소"], rows
    addr = rows[0]["주소"]
    G._KEY = G.load_key()
    lat, lon, how = G.geocode(norm_addr(addr))
    old = (m["lat"], m["lon"])
    if lat is None:
        log.append(("79", CAMPUS79, "바꾸지 않음(좌표 변환 실패)", how))
    else:
        m["lat"], m["lon"] = lat, lon
        m["address"] = addr
        m["coordSource"] = "KEDI 본교(제1캠퍼스) 주소 VWorld 변환(%s), 승학캠퍼스로 이동. 근거: %s" % (how, BASIS79)
        log.append(("79", CAMPUS79, "승학캠퍼스로 이동", "좌표 %.6f, %.6f → %.6f, %.6f / 주소 %s" % (old[0], old[1], lat, lon, addr)))
    with io.open(G.MARKERS, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")
    # ---- 80
    left = [m for m in data["markers"] if not m.get("address")]
    out = ["# 주소가 아직 없는 마커 (scripts/apply_address_fixes.py, 2026-10-05)", "",
           "docs/data/markers.json 마커 %d개 중 주소가 없는 마커 %d개." % (len(data["markers"]), len(left)), ""]
    if left:
        out += ["| 마커 이름 | 마커 좌표 |", "|---|---|"] + ["| %s (%s) | %.5f, %.5f |" % (m["campus"], m["univ"], m["lat"], m["lon"]) for m in left]
    else:
        out += ["없음. 모든 마커에 주소가 있다."]
    with io.open(G.REVIEW, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    for t in log:
        print(" | ".join(t))
    print("주소 없는 마커: %d" % len(left))


if __name__ == "__main__":
    main()
