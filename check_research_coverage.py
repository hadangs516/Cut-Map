# -*- coding: utf-8 -*-
"""작업 8 (읽기 전용): 조사 문서 2개의 대학·캠퍼스를 master list 조사 대상 행, 4yr_list 2개와 대조.
출력: research_coverage_check_20260924.md
"""
import io
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)
DOC_A = "컷맵_입결위치조사_20260924_v2.md"
DOC_B = "2027_정시모집요강_URL_누적.md"
DOC_A3 = "컷맵_입결위치조사_20260924_v3_중간.md"
FOURYR = ["4yr_list_gyeonggi_incheon_yeongnam.md", "4yr_list_seoul_chungcheong_gangwon_jeju_honam.md"]
REGIONS = ["서울", "경기", "인천", "강원", "충청", "호남", "영남", "제주"]
MAIN_A = re.compile(r"^### 1-\d")          # 입결 문서 본 조사 표 (1장)
MAIN_B = "## 조사 완료 대학"                  # 정시 문서 본 조사 표


def base(s):
    s = s or ""
    while re.search(r"\([^()]*\)", s):
        s = re.sub(r"\([^()]*\)", "", s)
    return re.sub(r"[\s()]+", "", s)


def split_top(text, seps=",/"):
    """괄호 밖의 구분자로만 나눈다."""
    out, cur, depth = [], "", 0
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch in seps and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


ALIAS = {"KAIST": "한국과학기술원", "인하공전": "인하공업전문대학"}
SUFFIX = [("과기대", "과학기술대학교"), ("예대", "예술대학교"), ("여대", "여자대학교"), ("교대", "교육대학교"), ("공대", "공과대학교"),
          ("외대", "외국어대학교"), ("대", "대학교"), ("대", "대학")]
ROMAN = {"I": "I", "II": "II", "III": "III", "IV": "IV", "V": "V", "VI": "VI", "VII": "VII"}


def expand(abbr, rows):
    """약칭 -> master 행 후보. 규칙: 별칭 사전, 접미 약칭 확장, 폴리텍 로마숫자+캠퍼스명."""
    b0 = base(abbr)
    if b0 in ALIAS:
        return [r for r in rows if base(r["대학명"]) == ALIAS[b0]]
    m = re.match(r"^폴리텍\s*([IVX]+)?\s*(\S+)$", re.sub(r"\([^)]*\)", "", abbr).strip())
    if m:
        num, camp = m.group(1), m.group(2).replace("캠퍼스", "")
        return [r for r in rows if "폴리텍" in r["대학명"] and camp in r["대학명"]
                and (num is None or re.search(r"폴리텍 %s 대학" % num, r["대학명"]))]
    for short, full in SUFFIX:
        if b0.endswith(short):
            hit = [r for r in rows if base(r["대학명"]) == b0[:-len(short)] + full]
            if hit:
                return hit
    return []


def paren(s):
    m = re.search(r"\(([^)]*)\)", s or "")
    return m.group(1) if m else ""


def link_text(s):
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)


def parse_doc(path, main_is):
    """표 행과 '- 이름 (캠퍼스)' 목록을 (절, 이름, 권역, 캠퍼스, 본조사여부)로 뽑는다."""
    out, abbrev = [], []
    sec, hdr, in_main = "", None, False
    for line in io.open(P(path), encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            sec = line.strip("# ").strip()
            in_main = main_is(line)
            hdr = None
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if hdr is None:
                hdr = cells
                continue
            if set(line.replace("|", "").strip()) <= set("-: "):
                continue
            row = dict(zip(hdr, cells))
            if hdr[:2] == ["권역", "대학"]:
                reg = row["권역"].split()[0]
                for nmx in split_top(row["대학"]):
                    nmx = nmx.strip()
                    if nmx:
                        out.append({"sec": sec, "name": nmx, "region": reg, "campus": "", "main": False,
                                    "abbrev": True})
                continue
            if "대학명" in row or "대학" in row:
                name = link_text(row.get("대학명") or row.get("대학"))
                parts = [x for x in re.split(r"·(?=[^()]*(?:\(|$))", name) if x] if re.search(r"대학교·", name) else [name]
                for nmx in parts:
                    out.append({"sec": sec, "name": nmx.strip(), "region": row.get("지역") or row.get("권역") or "",
                                "campus": row.get("캠퍼스", ""), "main": in_main})
            continue
        m = re.match(r"^- (.+?) \((.+)\)\s*$", line)
        if m and not line.startswith("- 없음"):
            out.append({"sec": sec, "name": m.group(1).strip(), "region": "", "campus": m.group(2).strip(),
                        "main": False})
    return out, abbrev


def parse_4yr():
    rows = []
    for fn in FOURYR:
        reg = None
        for line in io.open(P(fn), encoding="utf-8"):
            m = re.match(r"^## (\S+) \(\d+\)", line)
            if m:
                reg = m.group(1) if m.group(1) in REGIONS else None
                continue
            if reg and re.match(r"^\| \d+ \|", line):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                rows.append({"region": reg, "name": c[1], "campus": c[2], "type": c[3], "file": fn})
    return rows


def main():
    ms = json.load(io.open(P("university_master_list_v2.json"), encoding="utf-8"))
    rows = [r for reg in ms["byRegion"] for r in ms["byRegion"][reg]]
    excl = {(e["대학명"], e["권역"]): e["제외사유"] for e in ms["제외_지도대상"]["items"]}
    four = parse_4yr()
    four_key = {(f["name"], f["region"]): f for f in four}

    def match(ent, scope=None):
        """문서 항목 -> 마스터 행 키 목록. 여러 권역·캠퍼스를 한 칸에 쓴 표기는 해당 행 모두를 돌려준다."""
        nmx = ent["name"]
        cands = [r for r in rows if base(r["대학명"]) == base(nmx)]
        if not cands:
            cands = expand(nmx, rows)
        regs = [x for x in REGIONS if x in ent["region"]]
        sec_regs = [x for x in REGIONS if re.search(r"\d+\. %s" % x, ent["sec"])]
        if regs:
            cands = [r for r in cands if r["권역"] in regs]
        elif sec_regs:
            cands = [r for r in cands if r["권역"] in sec_regs] or cands
        elif scope and len(cands) > 1:
            cands = [r for r in cands if r["권역"] in scope] or cands
        if ent["campus"] and ent["campus"] != "-" and len(cands) > 1:
            cp = ent["campus"]
            c2 = [r for r in cands if (r.get("연결캠퍼스명") or "") == cp or cp == r["권역"]
                  or cp in (r.get("주소") or "") or cp in (r.get("연결캠퍼스명") or "")]
            if c2:
                cands = c2
        p = paren(nmx)
        if len(cands) > 1 and p:
            ps = [x for x in re.split(r"[·,]", p) if x]
            c2 = [r for r in cands if any(x == r["권역"] or x in r["대학명"] or x in (r.get("연결캠퍼스명") or "")
                                          or x in (r.get("주소") or "") for x in ps)]
            if c2:
                cands = c2
            if len(ps) > 1 and len(cands) > 1:
                return [(r["대학명"], r["권역"]) for r in cands]   # 여러 캠퍼스를 함께 적은 표기
        if len(regs) > 1:
            return [(r["대학명"], r["권역"]) for r in cands]
        if ent["campus"] and len(cands) > 1:
            c2 = [r for r in cands if (r.get("연결캠퍼스명") or "") == ent["campus"]]
            if c2:
                cands = c2
        if len(cands) > 1 and paren(ent["name"]):
            p = paren(ent["name"])
            c2 = [r for r in cands if p in r["대학명"] or p in (r.get("연결캠퍼스명") or "") or p in (r.get("주소") or "")]
            if c2:
                cands = c2
        if len(cands) > 1 and nmx in [r["대학명"] for r in cands]:
            cands = [r for r in cands if r["대학명"] == nmx]
        if len(cands) > 1:
            ent["ambiguous"] = True
        return [(r["대학명"], r["권역"]) for r in cands]

    docs = {}
    abbrevs = {}
    for label, path, main_is, scope in (("입결v2", DOC_A, lambda l: bool(MAIN_A.match(l)), None),
                                        ("정시", DOC_B, lambda l: l.strip() == MAIN_B, ("경기", "인천", "영남")),
                                        ("입결v3중간", DOC_A3, lambda l: bool(MAIN_A.match(l)), None)):
        if not os.path.exists(P(path)):
            continue
        ents, ab = parse_doc(path, main_is)
        for e in ents:
            e["match"] = match(e, scope)
        docs[label] = ents
        abbrevs[label] = ab

    seen = defaultdict(lambda: defaultdict(list))   # key -> doc -> [sec]
    unmatched = defaultdict(list)
    ambiguous = defaultdict(list)
    for label, ents in docs.items():
        for e in ents:
            if not e["match"]:
                unmatched[label].append(e)
            elif e.get("ambiguous"):
                ambiguous[label].append(e)
            else:
                for k in e["match"]:
                    seen[k][label].append(e["sec"] + (" (본조사)" if e["main"] else ""))

    L = ["# 조사 누락 점검 (작업 8, 읽기 전용)", "",
         "- 작성: 2026-09-28 / check_research_coverage.py",
         "- 기준: `university_master_list_v2.json` 학부 조사 대상 %d행 (작업 11 반영본), 4yr_list 2개 (4년제 %d행)" % (
             len(rows), len(four)),
         "- 대조 문서: `%s`(입결v2), `%s`(정시). 참고로 `%s`(입결v3중간)도 같은 방법으로 대조해 별도 열에 적음" % (
             DOC_A, DOC_B, DOC_A3),
         "- 매칭: 학교명(괄호 뺀 이름)이 같고, 문서에 권역이 있으면 권역도 같아야 함. 여러 행이면 캠퍼스(연결캠퍼스명) → "
         "괄호 안 캠퍼스 표기 → 이름 완전일치 순으로 좁힘",
         "- 대기열 표(4장)의 약칭은 '약칭+학교'가 master 학교명과 같을 때만 매칭. 폴리텍·교대 약칭 등은 2장 표에 남음",
         "- 한 칸에 여러 권역·캠퍼스를 적은 표기(예: 강원·경기, 서울·안성)는 해당 행 모두에 나온 것으로 셈",
         "- 본조사 = 입결v2의 1장(권역별 조사 결과) 표, 정시의 '조사 완료 대학' 표. 그 밖의 절(미확인·보류·대기열 목록)은 "
         "같은 대학을 다시 적는 목록이라 중복 판정에서 뺌", ""]

    # 1. master에 있는데 두 문서 어디에도 없는 행
    missing = [r for r in rows if not (seen[(r["대학명"], r["권역"])].get("입결v2") or seen[(r["대학명"], r["권역"])].get("정시"))]
    L += ["## 1. master list에 있는데 두 문서(입결v2·정시) 어디에도 없는 행 (%d)" % len(missing), "",
          "| # | 권역 | 대학명 | 연결 캠퍼스 | 4yr_list 학제 | 입결v3중간에 있음 |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(sorted(missing, key=lambda r: (REGIONS.index(r["권역"]), r["대학명"])), 1):
        f = four_key.get((r["대학명"], r["권역"]))
        L.append("| %d | %s | %s | %s | %s | %s |" % (i, r["권역"], r["대학명"], r.get("연결캠퍼스명") or "-",
                                                  f["type"] if f else "4년제 목록에 없음(비4년제 등)",
                                                  "예" if seen[(r["대학명"], r["권역"])].get("입결v3중간") else "-"))
    miss4 = [r for r in missing if (r["대학명"], r["권역"]) in four_key]
    by_reg = defaultdict(int)
    for r in miss4:
        by_reg[r["권역"]] += 1
    L += ["", "그중 4년제(4yr_list) 행: %d개 %s" % (len(miss4), dict(by_reg)), ""]

    # 2. 문서에 있는데 master에 없는 행
    L += ["## 2. 문서에 있는데 master list 조사 대상에 없는 행", "",
          "| 문서 | 절 | 문서 표기 | 권역 | 캠퍼스 표기 | master 상태 |", "|---|---|---|---|---|---|"]
    n2 = 0
    for label in ("입결v2", "정시", "입결v3중간"):
        done = set()
        for e in unmatched.get(label, []):
            k = (e["name"], e["region"], e["campus"])
            if k in done:
                continue
            done.add(k)
            ex = [v + " (" + kk[0] + ")" for kk, v in excl.items() if base(kk[0]) == base(e["name"])
                  and (not e["region"] or kk[1] == e["region"])]
            L.append("| %s | %s | %s | %s | %s | %s |" % (label, e["sec"], e["name"], e["region"] or "-", e["campus"] or "-",
                                                    "제외_지도대상: " + ", ".join(ex) if ex else "master에 없음"))
            n2 += label != "입결v3중간"
    L += ["", "매칭 후보가 여러 개라 한 행으로 정하지 못한 항목:", ""]
    for label in ("입결v2", "정시", "입결v3중간"):
        for e in ambiguous.get(label, []):
            L.append("- %s / %s: %s (권역 %s, 캠퍼스 %s) → 후보 %s" % (label, e["sec"], e["name"], e["region"] or "-",
                                                                e["campus"] or "-", e["match"]))
    L.append("")

    # 3. 같은 캠퍼스가 두 번 이상 나오는 행 (본조사 표 기준)
    L += ["## 3. 같은 캠퍼스가 본조사 표에 두 번 이상 나오는 행", "",
          "| master 행 | 권역 | 문서 | 나온 절 |", "|---|---|---|---|"]
    n3 = 0
    for k, d in sorted(seen.items()):
        for label, secs in d.items():
            mains = [s for s in secs if s.endswith("(본조사)")]
            if len(mains) >= 2:
                n3 += 1
                L.append("| %s | %s | %s | %s |" % (k[0], k[1], label, "; ".join(mains)))
    both = [(k, d) for k, d in seen.items()
            if any(s.endswith("(본조사)") for s in d.get("입결v2", [])) and any(s.endswith("(본조사)") for s in d.get("정시", []))]
    L += ["", "참고: 입결v2 본조사와 정시 본조사 양쪽에 모두 나오는 행 %d개 (문서 목적이 달라 중복으로 보지 않음)" % len(both), ""]

    # 4. 요약
    L += ["## 4. 요약", "",
          "- master 조사 대상 %d행 중 두 문서 어디에도 없는 행 %d (그중 4년제 %d)" % (len(rows), len(missing), len(miss4)),
          "- 문서에만 있고 master 조사 대상에 없는 항목(입결v2·정시, 중복 표기 제외) %d" % n2,
          "- 본조사 표 안에서 두 번 이상 나오는 캠퍼스 %d" % n3,
          "- 문서별 항목 수: %s" % {k: len(v) for k, v in docs.items()}, "",
          "## 5. 참고 (표 밖 언급·묶음 표기)", "",
          "- 경희대학교(서울 행)는 입결v2 표에는 없고 5장 결정 사항 본문에 '경희대(서울 행)는 기존 결과 공유'로만 나옴. "
          "표 기준으로 대조해 1장 목록에 남김",
          "- 강남대학교가 1-6에 두 번 나오는 것은 두 번째 행이 SPEC 7번의 '참고자료(재계산, 외부 도메인)' 행이기 때문. "
          "같은 조사 결과를 두 번 적은 중복은 아님",
          "- '이전 조사 차단 9곳', '첨부 정보 미확인 4곳'은 대학명이 아니라 묶음 표기(3-2절). 둘째 칸에 대학 약칭이 있으나 "
          "권역·캠퍼스가 없어 대조하지 않음",
          "- 입결v3중간 결과는 1장 표의 마지막 열에만 참고로 적음", ""]
    with io.open(P("research_coverage_check_20260924.md"), "w", encoding="utf-8", newline="\n") as fo:
        fo.write("\n".join(L) + "\n")
    print("\n".join(L[-7:]))
    print("ambiguous", {k: len(v) for k, v in ambiguous.items()}, "unmatched", {k: len(v) for k, v in unmatched.items()})


if __name__ == "__main__":
    main()
