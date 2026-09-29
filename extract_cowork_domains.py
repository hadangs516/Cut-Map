# -*- coding: utf-8 -*-
"""작업 14 (읽기 전용): KEDI 학교별 현황 '홈페이지' 열에서 master list 조사 대상 행의 공식 홈페이지·허용 도메인 추출.
출력: cowork_allowed_domains.md
"""
import io
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict

from build_university_master_list import SIDO_ALIASES

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)
XLSX = "2026년 고등 학교별 학과수 입학정원 지원 입학 학생 외국학생 졸업 교직원_260826H.xlsx"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
VALID_TLD = ("kr", "com", "net", "org", "edu", "ac")
# KEDI 홈페이지가 빈 행 보충 (#0929-01-A 사용자 결정). KEDI 값이 아니므로 출처를 함께 적는다
SUPPLEMENT = {
    ("연세대학교", "인천"): {"url": "www.yonsei.ac.kr", "출처": "KEDI 같은 학교 행(연세대학교 본교(제1캠퍼스), 서울)의 홈페이지 값",
                         "결정": "사용자 결정 #0929-01-A: 같은 학교의 KEDI 도메인 yonsei.ac.kr 사용"},
    ("국립목포해양대학교", "호남"): {"url": "http://www.mmu.ac.kr/",
                            "출처": "경상남도교육청_대학정보_20250918.csv '목포해양대학교(목포)' 행 홈페이지 열 (학교명에 '국립' 없음)",
                            "결정": "사용자 결정 #0929-01-A: 폴더 안 다른 공식 자료 값 사용"},
    ("정석대학", "서울"): {"url": None, "출처": "KEDI·경남교육청 CSV·API 수집본(홈페이지 필드 없음)·univ_coords.json 어디에도 값 없음",
                       "결정": "보류 (사용자 결정 #0929-01-A: 없으면 비워 두고 보류)"},
}
TWO_LEVEL = ("ac.kr", "co.kr", "or.kr", "re.kr", "go.kr", "ne.kr", "pe.kr", "hs.kr")


def load_kedi_full():
    z = zipfile.ZipFile(P(XLSX))
    sh = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
          for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    rows = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:sheetData/m:row", NS)

    def cells(r):
        c = {}
        for cell in r.findall("m:c", NS):
            v = cell.find("m:v", NS)
            if v is not None:
                c[re.sub(r"\d+", "", cell.get("r"))] = sh[int(v.text)] if cell.get("t") == "s" else v.text
        return c
    hi = next(i for i, r in enumerate(rows) if cells(r).get("E") == "학교명")
    header = cells(rows[hi])
    col = {v: k for k, v in header.items()}
    if "홈페이지" not in col:
        raise SystemExit("KEDI 파일에 홈페이지 열이 없음: %s" % header)
    out = []
    for r in rows[hi + 1:]:
        c = cells(r)
        if c.get("E"):
            out.append({"학제": c.get("B", ""), "학교명": c["E"], "상태": c.get("F", ""), "본분교": c.get("G", ""), "시도": c.get("H", ""),
                        "주소": c.get(col["주소"], ""), "홈페이지": (c.get(col["홈페이지"]) or "").strip()})
    return out, header


def nm(s):
    return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", s or ""))


def domain_of(url):
    if not url:
        return ""
    u = re.sub(r"^[a-z]+://", "", url.strip().lower())
    host = re.split(r"[/:?#]", u)[0].strip(".")
    labels = host.split(".")
    n = 3 if any(host.endswith("." + t) or host == t for t in TWO_LEVEL) else 2
    return ".".join(labels[-n:])


def main():
    kedi, header = load_kedi_full()
    ng = [k for k in kedi if "대학원" not in k["학제"]]
    ms = json.load(io.open(P("university_master_list_v2.json"), encoding="utf-8"))
    rows = [r for reg in ms["byRegion"] for r in ms["byRegion"][reg]]
    out, empty, multi = [], [], []
    for r in rows:
        link = r.get("연결캠퍼스명") or ""
        m = re.match(r"^(.*?)\s*\((본교\(제\d캠퍼스\)|분교.*?)\)$", link)
        hit, how = [], ""
        if m:
            hit = [k for k in ng if nm(k["학교명"]) == nm(m.group(1)) and k["본분교"] == m.group(2)]
            how = "연결캠퍼스(학교명+본분교)"
        if not hit:
            for name in (r["대학명"], link.split("(")[0]):
                hit = [k for k in ng if nm(k["학교명"]) == nm(name)]
                if hit:
                    how = "학교명"
                    break
        live = [k for k in hit if k["상태"] != "폐교"] or hit
        if len(live) > 1:
            same_reg = [k for k in live if SIDO_ALIASES.get(k["시도"]) == r["권역"]]
            if same_reg:
                live = same_reg
                how += "+권역"
        urls = sorted(set(k["홈페이지"] for k in live if k["홈페이지"]))
        doms = sorted(set(domain_of(u) for u in urls))
        bad = [d for d in doms if d.split(".")[-1] not in VALID_TLD]
        doms = [d for d in doms if d not in bad]
        rec = {"권역": r["권역"], "대학명": r["대학명"], "캠퍼스": link or "-", "urls": urls, "domains": doms, "how": how,
               "kedi": len(live), "bad": bad}
        out.append(rec)
        if not urls:
            sup = SUPPLEMENT.get((r["대학명"], r["권역"]))
            rec["supplement"] = sup
            if sup and sup["url"]:
                rec["domains"] = [domain_of(sup["url"])]
            empty.append(rec)
        elif len(doms) > 1:
            multi.append(rec)

    by_univ = defaultdict(set)
    for rec in out:
        by_univ[re.sub(r"\(.*$", "", rec["대학명"]).strip()].update(rec["domains"])
    diff_campus = {u: sorted(d) for u, d in by_univ.items() if len(d) > 1}
    all_domains = sorted(set(d for rec in out for d in rec["domains"]))

    L = ["# Cowork 허용 도메인 목록", "",
         "- 작성: 2026-09-28 / extract_cowork_domains.py (읽기 전용 추출)",
         "- 출처: `%s` 학교별 교육통계 시트의 '홈페이지' 열 (KEDI 2026 고등교육통계)" % XLSX,
         "- 대상: `university_master_list_v2.json` 학부 조사 대상 %d행" % len(rows),
         "- KEDI 행 연결: 연결캠퍼스명(학교명+본분교) 우선, 없으면 학교명 일치. 대학원 학제 행은 쓰지 않음. 운영 중 행이 있으면 폐교 행은 뺌",
         "- 허용 도메인: 홈페이지 주소의 호스트에서 등록 도메인만 남김 (ac.kr·or.kr 등은 끝 3단계, 그 외는 끝 2단계). "
         "SPEC 13번에 따라 이 도메인과 그 하위 도메인을 허용",
         "- 학교명으로만 연결돼 KEDI 행이 여러 개면 KEDI 시도가 같은 권역인 행으로 좁힘. 그래도 여러 개면 홈페이지를 모두 적음", "",
         "## 1. 행별 목록 (%d행)" % len(out), "",
         "| # | 권역 | 대학명 | 캠퍼스 | KEDI 홈페이지 URL | 허용 도메인 |", "|---|---|---|---|---|---|"]
    order = ["서울", "경기", "인천", "강원", "충청", "호남", "영남", "제주"]
    for i, rec in enumerate(sorted(out, key=lambda x: (order.index(x["권역"]), x["대학명"])), 1):
        sup = rec.get("supplement")
        L.append("| %d | %s | %s | %s | %s | %s |" % (i, rec["권역"], rec["대학명"], rec["캠퍼스"],
                                                    "<br>".join(rec["urls"]) or ("(비어 있음, 보충: %s)" % sup["url"]
                                                                                 if sup and sup["url"] else "(비어 있음, 보류)"),
                                                    (", ".join(rec["domains"]) or "-") +
                                                    (" (제외: %s — KEDI 표기 오타 의심)" % ", ".join(rec["bad"]) if rec["bad"] else "")))
    L += ["", "## 2. KEDI 홈페이지 주소가 비어 있는 행 (%d)" % len(empty), "",
          "KEDI 값이 없어 다른 자료로 보충한 행과 보류한 행. 보충 도메인은 5장 전체 목록에 포함됨.", ""]
    L += ["- %s / %s / %s: %s — 출처: %s / %s" % (
        x["권역"], x["대학명"], x["캠퍼스"],
        ("보충 도메인 " + ", ".join(x["domains"])) if x["domains"] else "보류(허용 도메인 없음)",
        (x.get("supplement") or {}).get("출처", "-"), (x.get("supplement") or {}).get("결정", "-"))
          for x in empty] or ["- 없음"]
    L += ["", "## 3. 한 행에 도메인이 둘 이상인 행 (%d)" % len(multi), ""]
    L += ["- %s / %s: %s" % (x["권역"], x["대학명"], ", ".join(x["urls"])) for x in multi] or ["- 없음"]
    L += ["", "## 4. 같은 대학인데 캠퍼스(행)별 도메인이 다른 경우 (%d)" % len(diff_campus), ""]
    L += ["- %s: %s" % (u, ", ".join(d)) for u, d in sorted(diff_campus.items())] or ["- 없음"]
    badrows = [x for x in out if x["bad"]]
    L += ["", "## 4-1. 허용 목록에서 뺀 도메인 (%d행)" % len(badrows), "",
          "최상위 도메인이 kr·com·net·org·edu가 아닌 값. KEDI 원본 표기 그대로 두고 허용 목록에만 넣지 않음.", ""]
    L += ["- %s / %s: %s -> %s" % (x["권역"], x["대학명"], ", ".join(x["urls"]), ", ".join(x["bad"])) for x in badrows] or ["- 없음"]
    L += ["", "## 5. 허용 도메인 전체 (중복 제거, %d개)" % len(all_domains), ""]
    L += ["- " + d for d in all_domains]
    with io.open(P("cowork_allowed_domains.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print("rows", len(out), "empty", len(empty), [x["대학명"] for x in empty], "multi", len(multi),
          "diff_campus", diff_campus, "domains", len(all_domains))


if __name__ == "__main__":
    main()
