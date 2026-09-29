# -*- coding: utf-8 -*-
"""#0929-09 답 5: univ_major_dedup.json에서 master 조사 대상 행에 해당하는 학과 행만 뽑아 univ_major_scope.json 작성.

매칭: 학교명 완전일치 + 시도(ctpvNm)의 권역이 master 행 권역과 같음. 완전일치가 없으면 괄호 뺀 학교명 일치.
같은 학교·권역에 master 행이 둘 이상이면(예: 영산대 해운대·양산) 학과 행은 한 번만 넣고 matchedRows에 모두 적는다.
"""
import io
import json
import os
import re
from collections import defaultdict

from build_university_master_list import SIDO_ALIASES

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)


def nm(s):
    return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", s or ""))


def main():
    ms = json.load(io.open(P("university_master_list_v2.json"), encoding="utf-8"))
    rows = [r for reg in ms["byRegion"] for r in ms["byRegion"][reg]]
    dd = json.load(io.open(P("univ_major_dedup.json"), encoding="utf-8"))
    items = dd["items"]
    by_exact = defaultdict(list)
    by_norm = defaultdict(list)
    for i, x in enumerate(items):
        reg = SIDO_ALIASES.get(x["ctpvNm"])
        by_exact[(x["schlNm"], reg)].append(i)
        by_norm[(nm(x["schlNm"]), reg)].append(i)
    picked = defaultdict(list)
    unmatched, how = [], {}
    for r in rows:
        key = (r["대학명"], r["권역"])
        idx = by_exact.get(key)
        how[key] = "학교명 완전일치"
        if not idx:
            idx = by_norm.get((nm(r["대학명"]), r["권역"]))
            how[key] = "괄호 뺀 학교명 일치"
        if not idx:
            unmatched.append(key)
            continue
        for i in idx:
            picked[i].append("%s|%s" % key)
    out_items = []
    for i in sorted(picked):
        x = dict(items[i])
        x["matchedRows"] = picked[i]
        out_items.append(x)
    out = {"source": "univ_major_dedup.json (%s)" % dd["source"]["title"],
           "scope": "university_master_list_v2.json 학부 조사 대상 %d행" % len(rows),
           "rule": "학교명 완전일치(없으면 괄호 뺀 학교명) + 시도 권역이 master 행 권역과 같음. 비IT 학과도 포함",
           "created": "2026-09-29", "masterRows": len(rows),
           "matchedMasterRows": len(rows) - len(unmatched), "unmatchedMasterRows": ["%s|%s" % k for k in unmatched],
           "rowsSharingDeptRows": sorted(set(v for vs in picked.values() if len(vs) > 1 for v in vs)),
           "count": len(out_items), "items": out_items}
    with io.open(P("univ_major_scope.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(P("univ_major_scope.json"))
    print("rows", len(out_items), "size MB %.2f" % (size / 1048576), "unmatched", unmatched,
          "shared", out["rowsSharingDeptRows"], "normMatched", [k for k, v in how.items() if v != "학교명 완전일치" and k not in unmatched])


if __name__ == "__main__":
    main()
