# -*- coding: utf-8 -*-
"""대학알리미 등록금·기숙사 공시 xlsx 를 docs/data/markers.json 의 마커와 이름으로 맞춰 docs/data/academyinfo.json 에 저장한다 (#1005-06 작업 67).

입력(저장소 루트, 원본 xlsx 는 커밋하지 않는다)
  등록금 현황 (2026_대학).xlsx   - 열 "등록금 (D=B)" 을 학부 연평균 등록금(원)으로 쓴다
  기숙사 수용 현황 (2025_대학).xlsx - 열 "기숙사수용률 (C=B/A×100)" 을 기숙사 수용률(%)로 쓴다
출력
  docs/data/academyinfo.json  - 마커별 연평균 등록금(학부), 기숙사 수용률, 항목별 공시년도, 출처, 라이선스
  academyinfo_review.md       - 매칭되지 않은 마커와 매칭되지 않은 xlsx 행
화면 코드(docs/index.html 등)는 건드리지 않는다.

열 선택: 머리글(4행)에 "등록금"이 들어간 열이 하나일 때만, "기숙사수용률"이 들어간 열이 하나일 때만 값을 쓴다.
         조건에 맞는 열이 하나로 정해지지 않으면 값을 넣지 않고 후보 열 이름만 출력한다.

매칭(이름이 정확히 같을 때만, 비슷한 이름으로 맞추지 않는다)
  xlsx 학교 칸은 "학교명", "학교명 _제2캠퍼스", "학교명 _분교" 형식이다(KEDI 학교명 + 본분교).
  - 마커 campus 가 "학교명 (본교(제N캠퍼스))" / "학교명 (분교(제N캠퍼스))" 형식이면
      본교 제1캠퍼스 -> 접미사 없는 "학교명", 본교 제N(N>=2) -> "학교명 _제N캠퍼스", 분교 -> "학교명 _분교" 와 같은 항목 1개일 때만.
  - 그 형식이 아니면 마커 univ 와 학교명이 같은 xlsx 항목이 1개일 때만.
  - 한 xlsx 항목에 마커가 둘 이상 대응하면(중복) 모두 매칭하지 않는다.
  - 값이 학교 안에서 하나로 정해지지 않으면(기숙사 수용률이 건물 행마다 다름) 값을 넣지 않는다.
값은 xlsx 에서 그대로 읽어 옮긴다(사람·LLM 이 옮기지 않는다).

사용: python scripts/add_academyinfo.py
"""
import io
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
OUT = os.path.join(ROOT, "docs", "data", "academyinfo.json")
REVIEW = os.path.join(ROOT, "academyinfo_review.md")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
TAG_RE = re.compile(r"^(?P<name>.+?) \((?P<kind>본교|분교)\(제(?P<n>\d+)캠퍼스\)\)$")
SRC_TUITION = "대학알리미 8-차-1. 등록금 현황 (2026 공시, 학교별평균값)"
SRC_DORM = "대학알리미 14-마-1. 기숙사 수용 현황 (2025 공시, 학교별평균값)"
LICENSE = "공공누리 제1유형"


def find_one(prefix):
    hits = sorted(f for f in os.listdir(ROOT) if f.startswith(prefix) and f.lower().endswith(".xlsx"))
    if len(hits) != 1:
        raise SystemExit("%s 로 시작하는 xlsx 를 정확히 1개 찾지 못함: %s" % (prefix, hits))
    return os.path.join(ROOT, hits[0])


def read_sheet(path):
    """{시트 이름: [(행 번호, {열 문자: 값})]}"""
    z = zipfile.ZipFile(path)
    try:
        shared = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
                  for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    except KeyError:
        shared = []
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall("p:Relationship", NS)}
    out = OrderedDict()
    for s in wb.findall(".//m:sheet", NS):
        t = rels[s.get("{%s}id" % NS["r"])].lstrip("/")
        t = t if t.startswith("xl/") else "xl/" + t
        data = []
        for row in ET.fromstring(z.read(t)).findall(".//m:sheetData/m:row", NS):
            c = {}
            for cell in row.findall("m:c", NS):
                col = re.sub(r"\d+", "", cell.get("r"))
                v = cell.find("m:v", NS)
                if cell.get("t") == "inlineStr":
                    node = cell.find("m:is", NS)
                    val = "".join(x.text or "" for x in node.iter("{%s}t" % NS["m"])) if node is not None else ""
                elif v is None:
                    continue
                elif cell.get("t") == "s":
                    val = shared[int(v.text)]
                else:
                    val = v.text
                c[col] = val
            data.append((int(row.get("r")), c))
        out[s.get("name")] = data
    return out


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def pick_column(header, needle):
    """머리글 칸 중 needle 이 들어간 열. 하나일 때만 (열 문자, 머리글) 반환, 아니면 (None, 후보 목록)"""
    cand = [(col, clean(v)) for col, v in header.items() if needle in re.sub(r"\s+", "", v)]
    return (cand[0], cand) if len(cand) == 1 else (None, cand)


def load_entries(sheet, header_row, first_data_row, name_col, value_col, year_col):
    """학교 칸 -> {'rows': 행 수, 'values': {값...}, 'year': 기준연도, 'name': 원본 학교명}"""
    header = dict(sheet)[header_row]
    ents = OrderedDict()
    for rn, c in sheet:
        if rn < first_data_row or not clean(c.get(name_col)):
            continue
        nm = clean(c[name_col])
        e = ents.setdefault(nm, {"name": nm, "rows": 0, "values": set(), "years": set(), "kind": clean(c.get("B"))})
        e["rows"] += 1
        v = c.get(value_col, "")
        if v != "":
            e["values"].add(v)
        e["years"].add(c.get(year_col, ""))
    return header, ents


def split_name(nm):
    m = re.match(r"^(.*?)\s*_\s*(.+)$", nm)
    return (m.group(1).strip(), m.group(2).strip()) if m else (nm, None)


def index_entries(ents):
    idx = defaultdict(list)
    for nm in ents:
        base, suffix = split_name(nm)
        idx[base].append((suffix, nm))
    return idx


def match_marker(m, idx):
    """(xlsx 학교 칸 이름, 방식) 또는 (None, 이유)"""
    t = TAG_RE.match(m["campus"].strip())
    if t:
        if t.group("kind") == "분교":
            want = "분교"
        else:
            want = None if t.group("n") == "1" else "제%s캠퍼스" % t.group("n")
        hit = [nm for suffix, nm in idx.get(t.group("name"), []) if suffix == want]
        how = "학교명+본분교 표기 일치(%s)" % (want or "접미사 없음")
    else:
        hit = [nm for suffix, nm in idx.get(m["univ"].strip(), [])]
        how = "마커 univ 와 학교명 일치"
    if len(hit) == 1:
        return hit[0], how
    return None, ("xlsx 에 같은 이름의 항목이 없음" if not hit else "같은 이름의 xlsx 항목이 %d개" % len(hit))


def main():
    p_t = find_one("등록금 현황 (2026_대학)")
    p_d = find_one("기숙사 수용 현황 (2025_대학)")
    st, sd = read_sheet(p_t), read_sheet(p_d)
    print("[등록금 xlsx] %s" % os.path.basename(p_t))
    for name, data in st.items():
        print("  시트: %s (행 %d)  열 이름(4행): %s" % (name, len(data), [clean(v) for v in dict(data)[4].values()]))
    print("[기숙사 xlsx] %s" % os.path.basename(p_d))
    for name, data in sd.items():
        h4 = dict(data)[4]
        print("  시트: %s (행 %d)  열 이름(4행): %s" % (name, len(data), [clean(v) for v in h4.values()]))
    s_t = list(st.values())[0]
    s_d = list(sd.values())[0]
    ht, hd = dict(s_t)[4], dict(s_d)[4]
    col_t, cand_t = pick_column(ht, "등록금")
    col_d, cand_d = pick_column(hd, "기숙사수용률")
    name_col = "F"
    assert clean(ht[name_col]) == "학교" and clean(hd[name_col]) == "학교"
    if col_t is None:
        print("등록금 열이 하나로 정해지지 않음. 후보:", cand_t)
    else:
        print("등록금 열 선택: %s열 '%s'" % (col_t[0], col_t[1]))
    if col_d is None:
        print("기숙사수용률 열이 하나로 정해지지 않음. 후보:", cand_d)
    else:
        print("기숙사수용률 열 선택: %s열 '%s'" % (col_d[0], col_d[1]))
    # 항목별 xlsx 항목 만들기. 값 열이 없으면 매칭만 하지 않고 값은 넣지 않는다
    _, ent_t = load_entries(s_t, 4, 6, name_col, col_t[0] if col_t else "G", "A")
    _, ent_d = load_entries(s_d, 4, 7, name_col, col_d[0] if col_d else "M", "A")
    idx_t, idx_d = index_entries(ent_t), index_entries(ent_d)
    markers = json.load(io.open(MARKERS, encoding="utf-8"))["markers"]

    claim_t, claim_d = defaultdict(list), defaultdict(list)
    res = []
    for m in markers:
        nt, how_t = match_marker(m, idx_t)
        nd, how_d = match_marker(m, idx_d)
        res.append([m, nt, how_t, nd, how_d])
        if nt:
            claim_t[nt].append(m["campus"])
        if nd:
            claim_d[nd].append(m["campus"])
    out_markers = []
    unm_t, unm_d = [], []
    n_t = n_d = n_none = 0
    used_t, used_d = set(), set()
    for m, nt, how_t, nd, how_d in res:
        rec = OrderedDict([("univ", m["univ"]), ("campus", m["campus"]), ("region", m["region"])])
        has_t = has_d = False
        # 등록금
        if col_t and nt and len(claim_t[nt]) == 1:
            vals = ent_t[nt]["values"]
            if len(vals) == 1:
                v = float(next(iter(vals)))
                rec["tuitionUndergradAnnual"] = {"value": int(v) if v == int(v) else v, "unit": "원", "year": int(float(next(iter(ent_t[nt]["years"])))),
                                                 "xlsxName": nt, "match": how_t, "source": SRC_TUITION}
                has_t = True
                used_t.add(nt)
            else:
                unm_t.append((m["campus"], "값이 하나로 정해지지 않음 (%s)" % sorted(vals)))
        else:
            unm_t.append((m["campus"], how_t if not nt else "한 xlsx 항목에 마커 %d개 대응(%s)" % (len(claim_t[nt]), ", ".join(claim_t[nt])) if col_t else "등록금 열이 하나로 정해지지 않음"))
        # 기숙사
        if col_d and nd and len(claim_d[nd]) == 1:
            vals = ent_d[nd]["values"]
            if len(vals) == 1:
                rec["dormCapacityRate"] = {"value": float(next(iter(vals))), "unit": "%", "year": int(float(next(iter(ent_d[nd]["years"])))),
                                           "xlsxName": nd, "match": how_d, "source": SRC_DORM}
                has_d = True
                used_d.add(nd)
            else:
                unm_d.append((m["campus"], "값이 하나로 정해지지 않음 (%s)" % sorted(vals)))
        else:
            unm_d.append((m["campus"], how_d if not nd else "한 xlsx 항목에 마커 %d개 대응(%s)" % (len(claim_d[nd]), ", ".join(claim_d[nd])) if col_d else "기숙사수용률 열이 하나로 정해지지 않음"))
        n_t += has_t
        n_d += has_d
        if not (has_t or has_d):
            n_none += 1
        if has_t or has_d:
            rec["license"] = LICENSE
            out_markers.append(rec)
    doc = OrderedDict([
        ("version", 1),
        ("note", ["대학알리미 공시 xlsx 두 개를 scripts/add_academyinfo.py 가 읽어 마커 이름과 정확히 일치하는 항목에만 값을 붙였다.",
                  "이름이 정확히 같은 항목이 1개로 정해지지 않거나 값이 하나로 정해지지 않으면 값을 넣지 않았다. 매칭 못 한 목록은 academyinfo_review.md."]),
        ("sources", OrderedDict([("tuition", SRC_TUITION), ("dorm", SRC_DORM)])),
        ("years", OrderedDict([("tuition", 2026), ("dorm", 2025)])),
        ("license", LICENSE),
        ("stats", OrderedDict([("markers", len(markers)), ("tuitionMatched", n_t), ("dormMatched", n_d), ("noneMatched", n_none)])),
        ("markers", out_markers),
    ])
    if col_t or col_d:
        with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
            f.write("\n")
    # review
    rv = ["# 대학알리미 공시 매칭 결과 (scripts/add_academyinfo.py, 2026-10-05)", "",
          "마커 %d개, 등록금 매칭 %d개, 기숙사 매칭 %d개, 둘 다 매칭 안 된 마커 %d개." % (len(markers), n_t, n_d, n_none), ""]
    both = [m["campus"] for m, nt, ht_, nd, hd_ in res if m["campus"] in {c for c, _ in unm_t} and m["campus"] in {c for c, _ in unm_d}]
    rv += ["## 둘 다 매칭되지 않은 마커 (%d)" % len(both), ""] + ["- %s" % c for c in both] + [""]
    rv += ["## 등록금만 매칭되지 않은 마커 (%d)" % len([c for c, _ in unm_t if c not in both]), ""]
    rv += ["- %s | %s" % (c, r) for c, r in unm_t if c not in both] + [""]
    rv += ["## 기숙사만 매칭되지 않은 마커 (%d)" % len([c for c, _ in unm_d if c not in both]), ""]
    rv += ["- %s | %s" % (c, r) for c, r in unm_d if c not in both] + [""]
    left_t = [nm for nm in ent_t if nm not in used_t]
    left_d = [nm for nm in ent_d if nm not in used_d]
    rv += ["## 매칭되지 않은 등록금 xlsx 항목 (%d / %d)" % (len(left_t), len(ent_t)), ""]
    rv += ["- %s (%s)" % (nm, ent_t[nm]["kind"]) for nm in left_t] + [""]
    rv += ["## 매칭되지 않은 기숙사 xlsx 항목 (%d / %d, 학교 단위)" % (len(left_d), len(ent_d)), ""]
    rv += ["- %s (%s)" % (nm, ent_d[nm]["kind"]) for nm in left_d] + [""]
    with io.open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rv) + "\n")
    print("마커 %d, 등록금 매칭 %d, 기숙사 매칭 %d, 둘 다 미매칭 %d" % (len(markers), n_t, n_d, n_none))
    print("마커 중 등록금 미매칭 %d, 기숙사 미매칭 %d" % (len(markers) - n_t, len(markers) - n_d))
    print("xlsx 항목 중 미매칭: 등록금 %d/%d, 기숙사 %d/%d" % (len(left_t), len(ent_t), len(left_d), len(ent_d)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
