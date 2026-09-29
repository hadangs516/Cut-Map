# -*- coding: utf-8 -*-
"""작업 18 (읽기 전용): CSV와 API dedup 양쪽에 있으나 학과명 집합이 다른 대학의 학과명 차이.
작업 9 초안(it_classification_draft_20260924.json)의 자동포함·키워드포함 학과를 표시한다.
출력: api_csv_dept_diff_20260929.md
"""
import io
import json
import os
from collections import defaultdict

from check_api_csv_coverage import load_csv

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)
MARK = {"자동포함": "★", "키워드포함": "☆"}


def main():
    _, csv_rows, _, _ = load_csv()
    dedup = json.load(io.open(P("univ_major_dedup.json"), encoding="utf-8"))["items"]
    draft = json.load(io.open(P("it_classification_draft_20260924.json"), encoding="utf-8"))
    cat = {i["name"]: i["category"] for i in draft["items"]}

    cd, ad = defaultdict(set), defaultdict(set)
    c_rows, a_rows = defaultdict(list), defaultdict(list)
    for r in csv_rows:
        cd[r["schlNm"]].add(r["scsbjtNm"])
        c_rows[r["schlNm"]].append(r)
    for r in dedup:
        ad[r["schlNm"]].add(r["scsbjtNm"])
        a_rows[r["schlNm"]].append(r)
    diff = sorted(u for u in set(cd) & set(ad) if cd[u] != ad[u])

    def tag(n):
        return n + MARK.get(cat.get(n), "")

    def it_cnt(ns):
        return sum(1 for n in ns if cat.get(n) in MARK)

    last = csv_rows[-1]["schlNm"]
    rows = []
    for u in diff:
        oc, oa = sorted(cd[u] - ad[u]), sorted(ad[u] - cd[u])
        rows.append((u, len(cd[u]), len(ad[u]), oc, oa, it_cnt(oc), it_cnt(oa)))

    L = ["# API 수집본 vs CSV 학과명 차이 (작업 18, 읽기 전용)", "",
         "- 작성: 2026-09-29 / check_api_csv_dept_diff.py",
         "- 대상: CSV(`전국대학별학과정보표준데이터.csv`, 50,000행)와 API dedup(`univ_major_dedup.json`) 양쪽에 있는 대학 중 "
         "학과명 집합이 다른 %d개 대학" % len(diff),
         "- 학과명: 학교별 서로 다른 학과명(학위과정·주야·학과상태 구분 없음)",
         "- 표시: ★ = 작업 9 초안의 자동포함(AI·컴퓨터·소프트웨어), ☆ = 키워드포함. 초안이며 확정 판정이 아님",
         "- CSV 마지막 행의 학교: %s (CSV가 50,000행에서 잘려 이 학교는 일부 행만 있을 수 있음)" % last,
         "- 판단(대체 가능 여부 등)은 하지 않고 차이만 정리함", "",
         "## 1. 요약 (%d개 대학)" % len(diff), "",
         "| # | 대학 | CSV 학과 수 | API 학과 수 | CSV에만 | API에만 | CSV에만 중 ★☆ | API에만 중 ★☆ |",
         "|---|---|---|---|---|---|---|---|"]
    for i, (u, nc, na, oc, oa, ic, ia) in enumerate(rows, 1):
        L.append("| %d | %s%s | %d | %d | %d | %d | %d | %d |" % (i, u, " (CSV 끝)" if u == last else "", nc, na,
                                                              len(oc), len(oa), ic, ia))
    tot = [sum(x[k] for x in rows) for k in (5, 6)]
    L += ["", "- CSV에만 있는 학과명 합계 %d (그중 ★☆ %d) / API에만 있는 학과명 합계 %d (그중 ★☆ %d)" % (
        sum(len(x[3]) for x in rows), tot[0], sum(len(x[4]) for x in rows), tot[1]),
          "- ★☆가 차이에 들어 있는 대학: %d개" % sum(1 for x in rows if x[5] or x[6]), ""]
    L += ["## 2. 대학별 목록", ""]
    for i, (u, nc, na, oc, oa, ic, ia) in enumerate(rows, 1):
        L += ["### %d. %s" % (i, u), "",
              "- CSV에만 (%d, ★☆ %d): %s" % (len(oc), ic, ", ".join(tag(n) for n in oc) or "없음"),
              "- API에만 (%d, ★☆ %d): %s" % (len(oa), ia, ", ".join(tag(n) for n in oa) or "없음"), ""]
    with io.open(P("api_csv_dept_diff_20260929.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("diff univ", len(diff), "csv-only total", sum(len(x[3]) for x in rows), "api-only total",
          sum(len(x[4]) for x in rows), "IT marks", tot, "last", last)
    for x in rows[:50]:
        print(x[0], x[1], x[2], len(x[3]), len(x[4]), x[5], x[6])


if __name__ == "__main__":
    main()
