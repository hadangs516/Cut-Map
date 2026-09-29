# -*- coding: utf-8 -*-
"""지도 데이터(data.py의 UNIS)와 카탈로그(catalog.json)를 이름으로 연결한다.

공백·괄호 차이처럼 기계적으로 1:1로 맞는 것만 연결한다.
안 맞는 것은 추측으로 잇지 않고 후보와 함께 보고한다.
결과: univ_map.json (연결표), 그리고 표준출력에 실패 목록.
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")

from data import UNIS  # noqa: E402

CAT = json.load(io.open(os.path.join(HERE, "catalog.json"), encoding="utf-8"))
CAT_NAMES = [u["name"] for u in CAT["univs"]]


def norm(s):
    """공백과 괄호만 지운다. 글자는 바꾸지 않는다."""
    return re.sub(r"[\s()（）·]", "", s or "")


by_norm = {}
for n in CAT_NAMES:
    by_norm.setdefault(norm(n), []).append(n)

pairs, fails = [], []
for u in UNIS:
    full = u["nm"]
    hit = by_norm.get(norm(full), [])
    if len(hit) == 1:
        pairs.append({"mapId": u["id"], "mapName": full, "catalogName": hit[0],
                      "how": "exact" if hit[0] == full else "공백·괄호만 다름"})
        continue
    # 실패. 원인을 나눈다.
    stem = re.sub(r"(대학교|대학)$", "", full)
    cands = [n for n in CAT_NAMES if stem and stem in n]
    if hit:
        reason = "같은 이름이 여러 개"
    elif cands:
        reason = "표기가 달라서 안 맞음"
    else:
        reason = "파일에 학교 자체가 없음"
    fails.append({"mapId": u["id"], "mapName": full, "reason": reason, "candidates": cands[:5]})

out = {
    "version": 1,
    "note": [
        "지도 데이터(data.py)와 catalog.json을 학교 이름으로 연결한 표.",
        "공백·괄호 차이만 허용했다. 이름이 다르면 추측으로 잇지 않고 실패로 남긴다.",
        "카탈로그 CSV가 잘린 파일이라 '파일에 학교 자체가 없음'이 나올 수 있다.",
    ],
    "pairs": pairs,
    "fails": fails,
}
with io.open(os.path.join(HERE, "univ_map.json"), "w", encoding="utf-8", newline="\n") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("지도 대학 %d개 중 연결 %d, 실패 %d" % (len(UNIS), len(pairs), len(fails)))
print("\n[공백·괄호만 달라서 맞춘 것]")
for p in pairs:
    if p["how"] != "exact":
        print("  %s  ->  %s" % (p["mapName"], p["catalogName"]))
print("\n[실패]")
for reason in ["파일에 학교 자체가 없음", "표기가 달라서 안 맞음", "같은 이름이 여러 개"]:
    got = [f for f in fails if f["reason"] == reason]
    if not got:
        continue
    print("  * %s (%d개)" % (reason, len(got)))
    for f in got:
        print("     - %s  후보: %s" % (f["mapName"], ", ".join(f["candidates"]) or "없음"))
