# -*- coding: utf-8 -*-
"""작업 7 (읽기 전용): 공공데이터포털 CSV(잘린 파일)와 API 수집본(univ_major_full/dedup) 비교.
출력: api_csv_coverage_20260924.md
"""
import csv
import io
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)
CSV = "전국대학별학과정보표준데이터.csv"
TARGETS = ["고려대학교", "경희대학교", "동국대학교", "국민대학교", "광운대학교", "경기대학교", "가톨릭대학교"]


def load_csv():
    raw = open(P(CSV), "rb").read()
    txt = raw.decode("cp949")
    rd = list(csv.reader(io.StringIO(txt)))
    hdr = rd[0]
    ix = {h: i for i, h in enumerate(hdr)}
    out = []
    for r in rd[1:]:
        if len(r) < len(hdr):
            out.append({"_short": True, "학교명": r[ix["학교명"]] if len(r) > ix["학교명"] else ""})
            continue
        out.append({"yr": r[ix["연도"]], "ctpvNm": r[ix["시도명"]], "sggNm": r[ix["시군구명"]], "schlNm": r[ix["학교명"]],
                    "schlSeNm": r[ix["학교구분명"]], "degCrseCrsNm": r[ix["학위과정명"]], "danCrsNm": r[ix["주야과정명"]],
                    "scsbjtSttsNm": r[ix["학과상태명"]], "scsbjtNm": r[ix["학과명"]]})
    return hdr, out, len(raw), raw[-200:]


def summarize(rows):
    univ = Counter(r["schlNm"] for r in rows)
    camp = Counter((r["schlNm"], r["ctpvNm"], r["sggNm"]) for r in rows)
    dept = defaultdict(set)
    for r in rows:
        dept[r["schlNm"]].add(r["scsbjtNm"])
    return univ, camp, dept


def main():
    hdr, csv_rows, size, tail = load_csv()
    short = [r for r in csv_rows if r.get("_short")]
    csv_rows = [r for r in csv_rows if not r.get("_short")]
    full = json.load(open(P("univ_major_full.json"), encoding="utf-8"))["items"]
    dd = json.load(open(P("univ_major_dedup.json"), encoding="utf-8"))
    dedup, dmeta = dd["items"], dd["dedup"]

    sets = {"CSV": csv_rows, "API full": full, "API dedup": dedup}
    summ = {k: summarize(v) for k, v in sets.items()}
    L = ["# API 수집본 vs 공공데이터포털 CSV 커버리지 (작업 7, 읽기 전용)", "",
         "- 작성: 2026-09-28 / check_api_csv_coverage.py",
         "- CSV: `%s` (%d바이트, 헤더 제외 %d행, 열 수가 모자란 행 %d개)" % (CSV, size, len(csv_rows) + len(short), len(short)),
         "- API full: `univ_major_full.json` (data.go.kr API, totalCount 101,238, 수집 101,238행)",
         "- API dedup: `univ_major_dedup.json` (full에서 완전 중복 제거: %s)" % dmeta,
         "- 캠퍼스 정의: (학교명, 시도명, 시군구명) 조합. 데이터에 캠퍼스 이름 열이 없어 소재지로 구분함",
         "- 학과 수: 학교별 서로 다른 학과명 수 (학위과정·주야 구분 없이)",
         "- 이 문서는 근거 정리만 하며, API 수집본이 CSV 완전본을 대신할 수 있는지는 판단하지 않음", ""]

    L += ["## 1. 누락 7개 대학 포함 여부", "",
          "| 대학 | CSV 행 | API full 행 | API dedup 행 | 캠퍼스 표기 (dedup: 시도 시군구 / 학교구분) | dedup 학과 수 | dedup 학과상태 |",
          "|---|---|---|---|---|---|---|"]
    for t in TARGETS:
        c = [r for r in csv_rows if r["schlNm"] == t]
        f = [r for r in full if r["schlNm"] == t]
        d = [r for r in dedup if r["schlNm"] == t]
        camps = Counter((r["ctpvNm"], r["sggNm"], r["schlSeNm"]) for r in d)
        camp_txt = "; ".join("%s %s / %s (%d행)" % (a, b, s, n) for (a, b, s), n in sorted(camps.items()))
        st = Counter(r["scsbjtSttsNm"] for r in d)
        L.append("| %s | %d | %d | %d | %s | %d | %s |" % (t, len(c), len(f), len(d), camp_txt or "-",
                                                         len(set(r["scsbjtNm"] for r in d)), dict(st)))
    L += ["", "같은 이름으로 시작하는 다른 학교명(대학원 등, dedup 기준):", ""]
    for t in TARGETS:
        rel = Counter(r["schlNm"] for r in dedup if r["schlNm"].startswith(t.replace("대학교", "")) and r["schlNm"] != t)
        L.append("- %s: %s" % (t, ", ".join("%s(%d)" % kv for kv in sorted(rel.items())) or "없음"))
    L.append("")

    L += ["## 2. 전체 규모 비교", "", "| 구분 | 행 | 대학(학교명) | 캠퍼스(학교명+시도+시군구) | 학과(학교명+학과명) | 연도 값 |",
          "|---|---|---|---|---|---|"]
    for k, rows in sets.items():
        u, c, d = summ[k]
        L.append("| %s | %d | %d | %d | %d | %s |" % (k, len(rows), len(u), len(c), sum(len(v) for v in d.values()),
                                                  dict(Counter(r["yr"] for r in rows))))
    L.append("")
    last = csv_rows[-1]
    L += ["CSV 마지막 행: %s / %s / %s (잘린 위치 참고)" % (last["schlNm"], last["scsbjtNm"], last["yr"]), ""]

    cu, cc, cd = summ["CSV"]
    au, ac, ad = summ["API dedup"]
    only_csv_u = sorted(set(cu) - set(au))
    only_api_u = sorted(set(au) - set(cu))
    only_csv_c = sorted(set(cc) - set(ac))
    only_api_c = sorted(set(ac) - set(cc))
    both = set(cu) & set(au)
    dept_diff = [(u, len(cd[u]), len(ad[u])) for u in sorted(both) if cd[u] != ad[u]]
    L += ["## 3. 한쪽에만 있는 대학·캠퍼스 (CSV vs API dedup)", "",
          "- CSV에만 있는 대학 %d개 / API에만 있는 대학 %d개" % (len(only_csv_u), len(only_api_u)),
          "- CSV에만 있는 캠퍼스 %d개 / API에만 있는 캠퍼스 %d개" % (len(only_csv_c), len(only_api_c)),
          "- 양쪽에 다 있는 대학 %d개 중 학과명 집합이 다른 대학 %d개" % (len(both), len(dept_diff)), ""]
    L += ["### 3-1. CSV에만 있는 대학 (%d)" % len(only_csv_u), ""] + ["- %s (%d행)" % (u, cu[u]) for u in only_csv_u] + [""]
    L += ["### 3-2. API에만 있는 대학 (%d)" % len(only_api_u), ""]
    L += ["- %s (%d행)%s" % (u, au[u], " ← 누락 7개" if u in TARGETS else "") for u in only_api_u] + [""]
    L += ["### 3-3. CSV에만 있는 캠퍼스 (%d)" % len(only_csv_c), ""]
    L += ["- %s / %s %s (%d행)" % (a, b, c, cc[(a, b, c)]) for a, b, c in only_csv_c] + [""]
    L += ["### 3-4. API에만 있는 캠퍼스 중 양쪽에 다 있는 대학의 것 (%d)" % sum(1 for x in only_api_c if x[0] in both), ""]
    L += ["- %s / %s %s (%d행)" % (a, b, c, ac[(a, b, c)]) for a, b, c in only_api_c if a in both] + [""]
    L += ["### 3-5. 양쪽에 있으나 학과명 집합이 다른 대학 (%d)" % len(dept_diff), "",
          "| 대학 | CSV 학과 수 | API dedup 학과 수 | CSV에만 | API에만 |", "|---|---|---|---|---|"]
    for u, a, b in dept_diff:
        L.append("| %s | %d | %d | %d | %d |" % (u, a, b, len(cd[u] - ad[u]), len(ad[u] - cd[u])))
    L.append("")
    with io.open(P("api_csv_coverage_20260924.md"), "w", encoding="utf-8", newline="\n") as fo:
        fo.write("\n".join(L) + "\n")
    print("\n".join(L[:40]))
    print("only_csv_u", len(only_csv_u), "only_api_u", len(only_api_u), "only_csv_c", len(only_csv_c),
          "only_api_c", len(only_api_c), "dept_diff", len(dept_diff))


if __name__ == "__main__":
    main()
