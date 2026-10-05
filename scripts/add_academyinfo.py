# -*- coding: utf-8 -*-
"""대학알리미 등록금·기숙사 공시 xlsx 를 docs/data/markers.json 의 마커와 이름으로 맞춰 docs/data/academyinfo.json 에 저장한다.
(#1005-06 작업 67에서 만들고, #1005-20 작업 83에서 매칭 규칙을 바꿨다.)

입력(저장소 루트, 원본 xlsx 는 커밋하지 않는다)
  등록금 현황 (2026_대학).xlsx    - 열 "등록금 (D=B)" 을 학부 연평균 등록금(원)으로 쓴다
  기숙사 수용 현황 (2025_대학).xlsx - 열 "기숙사수용률 (C=B/A×100)" 을 기숙사 수용률(%)로 쓴다
  university_master_list_v2.json  - 마커의 캠퍼스 구분을 연결캠퍼스명으로 정한다
출력
  docs/data/academyinfo.json  - 마커별 "연평균 등록금(학부)"(원), 기숙사 수용률(%), 항목별 공시년도, 출처, 라이선스
  academyinfo_review.md       - 매칭되지 않은 마커와 xlsx 행, 4년제 미매칭 마커의 이름·사유
화면 코드(docs/index.html 등)는 건드리지 않는다.

열 선택: 머리글(4행)에 "등록금"이 들어간 열이 하나일 때만, "기숙사수용률"이 들어간 열이 하나일 때만 값을 쓴다.

매칭 규칙 (이름이 정확히 같을 때만, 비슷한 이름으로 맞추지 않는다)
  xlsx 학교 칸은 "학교명", "학교명 _제N캠퍼스", "학교명_제N캠퍼스", "학교명 _분교" 형식이다(접미사 앞 공백 유무는 무시한다).
  마커의 캠퍼스 구분은 master(university_master_list_v2.json)의 연결캠퍼스명으로 정한다.
  1) 그 학교(연결캠퍼스명의 "학교명", 표기가 없으면 마커 univ)의 xlsx 행이 접미사 없는 행 하나뿐이면,
     그 학교의 모든 마커에 그 값을 붙이고 "scope": "학교 단위 공시값"을 넣는다.
  2) 그렇지 않으면 연결캠퍼스명이 "학교명 (본교(제1캠퍼스))" -> 접미사 없는 행, "(본교(제N캠퍼스))" -> "_제N캠퍼스" 행,
     "(분교(…))" -> "_분교" 행과 정확히 대응하는 행이 1개일 때만 붙인다.
  3) 정확히 대응하는 행이 없으면(연결캠퍼스명에 본분교 표기가 없는 마커 포함) 비워 둔다.
  4) master 에 마커 행이 없으면(연결캠퍼스명을 알 수 없으면) 비워 둔다.
  값이 학교(행) 안에서 하나로 정해지지 않으면(기숙사 수용률이 건물 행마다 다름) 값을 넣지 않는다.
  원자료 이상값은 값을 바꾸지 않고 "flag": "원자료 값(확인 필요)"를 붙인다(FLAGS).
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
sys.path.insert(0, HERE)
from add_address import find_xlsx as find_kedi, is_candidate, load_kedi  # noqa: E402

MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
OUT = os.path.join(ROOT, "docs", "data", "academyinfo.json")
REVIEW = os.path.join(ROOT, "academyinfo_review.md")
MASTER = os.path.join(ROOT, "university_master_list_v2.json")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
TAG_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<kind>본교|분교)\(제(?P<n>\d+)캠퍼스\)\)$")
SRC_TUITION = "대학알리미 8-차-1. 등록금 현황 (2026 공시, 학교별평균값)"
SRC_DORM = "대학알리미 14-마-1. 기숙사 수용 현황 (2025 공시, 학교별평균값)"
LICENSE = "공공누리 제1유형"
NAME_TUITION = "연평균 등록금(학부)"
NAME_DORM = "기숙사 수용률"
SCOPE_SCHOOL = "학교 단위 공시값"
FLAG = "원자료 값(확인 필요)"
# 기존 flag 2개를 유지한다: (마커 campus 시작 문자열, 항목 키)
FLAGS = [("정석대학", "tuitionUndergradAnnual"), ("금강대학교(논산)", "dormCapacityRate")]


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
    cand = [(col, clean(v)) for col, v in header.items() if needle in re.sub(r"\s+", "", v)]
    return (cand[0], cand) if len(cand) == 1 else (None, cand)


def load_entries(sheet, first_data_row, name_col, value_col, year_col):
    ents = OrderedDict()
    for rn, c in sheet:
        if rn < first_data_row or not clean(c.get(name_col)):
            continue
        nm = clean(c[name_col])
        e = ents.setdefault(nm, {"name": nm, "values": set(), "years": set(), "kind": clean(c.get("B"))})
        v = c.get(value_col, "")
        if v != "":
            e["values"].add(v)
        e["years"].add(c.get(year_col, ""))
    return ents


def split_name(nm):
    m = re.match(r"^(.*?)\s*_\s*(.+)$", nm)
    return (m.group(1).strip(), m.group(2).strip()) if m else (nm, None)


def index_entries(ents):
    idx = defaultdict(list)
    for nm in ents:
        base, suffix = split_name(nm)
        idx[base].append((suffix, nm))
    return idx


def want_suffix(tag):
    if tag.group("kind") == "분교":
        return "분교"
    return None if tag.group("n") == "1" else "제%s캠퍼스" % tag.group("n")


def match_marker(link, univ, idx):
    """(xlsx 학교 칸 이름, scope 또는 None, 설명) 또는 (None, None, 사유)"""
    if link is None:
        return None, None, "연결캠퍼스명을 알 수 없음(master에 마커 행이 없음)"
    tag = TAG_RE.match(link.strip())
    base = tag.group("name") if tag else univ.strip()
    rows = idx.get(base, [])
    if not rows:
        return None, None, "xlsx에 학교명 없음"
    if len(rows) == 1 and rows[0][0] is None:
        return rows[0][1], SCOPE_SCHOOL, "학교의 xlsx 행이 접미사 없는 행 하나뿐"
    if not tag:
        return None, None, "연결캠퍼스명에 본분교 표기가 없어 캠퍼스 구분 불가(xlsx 행: %s)" % " / ".join(nm for _, nm in rows)
    want = want_suffix(tag)
    hit = [nm for suf, nm in rows if suf == want]
    if len(hit) == 1:
        return hit[0], None, "연결캠퍼스명 본분교 표기와 접미사 일치(%s)" % (want or "접미사 없음")
    return None, None, "대응하는 접미사 행 없음(필요: %s, xlsx 행: %s)" % (want or "접미사 없음", " / ".join(nm for _, nm in rows))


def kedi_types(master_row, kedi):
    nm_ = lambda s: re.sub(r"\s+", "", s or "")
    link = master_row.get("연결캠퍼스명") or ""
    m = re.match(r"^(.*?)\s*\((본교\(제\d캠퍼스\)|분교.*?)\)$", link)
    hit = []
    if m:
        hit = [k for k in kedi if nm_(k["학교명"]) == nm_(m.group(1)) and k["본분교"] == m.group(2)]
    if not hit:
        hit = [k for k in kedi if nm_(k["학교명"]) == nm_(master_row["대학명"])]
    return sorted({k["학제"] for k in hit})


def main():
    p_t = find_one("등록금 현황 (2026_대학)")
    p_d = find_one("기숙사 수용 현황 (2025_대학)")
    st, sd = read_sheet(p_t), read_sheet(p_d)
    s_t, s_d = list(st.values())[0], list(sd.values())[0]
    ht, hd = dict(s_t)[4], dict(s_d)[4]
    col_t, cand_t = pick_column(ht, "등록금")
    col_d, cand_d = pick_column(hd, "기숙사수용률")
    print("등록금 열: %s" % (("%s열 '%s'" % col_t) if col_t else "하나로 정해지지 않음 %s" % cand_t))
    print("기숙사수용률 열: %s" % (("%s열 '%s'" % col_d) if col_d else "하나로 정해지지 않음 %s" % cand_d))
    assert clean(ht["F"]) == "학교" and clean(hd["F"]) == "학교"
    ent_t = load_entries(s_t, 6, "F", col_t[0] if col_t else "G", "A")
    ent_d = load_entries(s_d, 7, "F", col_d[0] if col_d else "M", "A")
    idx_t, idx_d = index_entries(ent_t), index_entries(ent_d)
    markers = json.load(io.open(MARKERS, encoding="utf-8"))["markers"]
    master = json.load(io.open(MASTER, encoding="utf-8"))["byRegion"]
    mrow = {}
    for rg in master.values():
        for r in rg:
            if isinstance(r, dict):
                mrow[(r["대학명"], r.get("연결캠퍼스명"))] = r
    prev = None
    if os.path.exists(OUT):
        prev = json.load(io.open(OUT, encoding="utf-8")).get("stats")

    out_markers, rows = [], []
    used_t, used_d = set(), set()
    n_t = n_d = n_none = 0
    for m in markers:
        row = mrow.get((m["univ"], m["campus"]))
        link = row["연결캠퍼스명"] if row else None
        rec = OrderedDict([("univ", m["univ"]), ("campus", m["campus"]), ("region", m["region"])])
        info = {}
        for key, ents, idx, col, name, unit, src, conv in (
                ("tuitionUndergradAnnual", ent_t, idx_t, col_t, NAME_TUITION, "원", SRC_TUITION, None),
                ("dormCapacityRate", ent_d, idx_d, col_d, NAME_DORM, "%", SRC_DORM, None)):
            if not col:
                info[key] = "열이 하나로 정해지지 않음"
                continue
            nm, scope, why = match_marker(link, m["univ"], idx)
            if nm is None:
                info[key] = why
                continue
            vals = ents[nm]["values"]
            if len(vals) != 1:
                info[key] = "xlsx 값이 하나로 정해지지 않음(%s)" % sorted(vals)
                continue
            v = float(next(iter(vals)))
            item = OrderedDict([("name", name), ("value", (int(v) if (key == "tuitionUndergradAnnual" and v == int(v)) else v)), ("unit", unit),
                                ("year", int(float(next(iter(ents[nm]["years"]))))), ("xlsxName", nm), ("match", why), ("source", src)])
            if scope:
                item["scope"] = scope
            for prefix, fkey in FLAGS:
                if m["campus"].startswith(prefix) and fkey == key:
                    item["flag"] = FLAG
            rec[key] = item
            info[key] = "매칭"
            (used_t if key == "tuitionUndergradAnnual" else used_d).add(nm)
        has_t = "tuitionUndergradAnnual" in rec
        has_d = "dormCapacityRate" in rec
        n_t += has_t
        n_d += has_d
        if not (has_t or has_d):
            n_none += 1
        else:
            rec["license"] = LICENSE
            out_markers.append(rec)
        rows.append((m, row, link, info, has_t, has_d))
    doc = OrderedDict([
        ("version", 2),
        ("note", ["대학알리미 공시 xlsx 두 개를 scripts/add_academyinfo.py 가 읽어 마커 이름과 정확히 일치하는 항목에만 값을 붙였다.",
                  "마커의 캠퍼스 구분은 university_master_list_v2.json 의 연결캠퍼스명으로 정했다. 학교의 xlsx 행이 접미사 없는 행 하나뿐이면 그 학교의 모든 마커에 붙이고 scope 를 \"학교 단위 공시값\"으로 적었다.",
                  "정확히 대응하는 행이 없거나 값이 하나로 정해지지 않으면 값을 넣지 않았다. 매칭 못 한 목록은 academyinfo_review.md.",
                  "원자료 이상값은 값을 바꾸지 않고 flag 로 표시했다."]),
        ("sources", OrderedDict([("tuition", SRC_TUITION), ("dorm", SRC_DORM)])),
        ("years", OrderedDict([("tuition", 2026), ("dorm", 2025)])),
        ("license", LICENSE),
        ("stats", OrderedDict([("markers", len(markers)), ("tuitionMatched", n_t), ("dormMatched", n_d), ("noneMatched", n_none)])),
        ("markers", out_markers),
    ])
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")

    kedi = [k for k in load_kedi(find_kedi())]
    def typ(row):
        if row is None:
            return None
        t = kedi_types(row, kedi)
        return "/".join(t) if t else "찾지 못함"
    rv = ["# 대학알리미 공시 매칭 결과 (scripts/add_academyinfo.py, 2026-10-05, 규칙 변경판)", "",
          "마커 %d개, 등록금 매칭 %d개, 기숙사 매칭 %d개, 둘 다 매칭 안 된 마커 %d개." % (len(markers), n_t, n_d, n_none)]
    if prev:
        rv.append("이전 규칙(#1005-06)의 결과: 등록금 %d, 기숙사 %d, 둘 다 미매칭 %d." % (prev["tuitionMatched"], prev["dormMatched"], prev["noneMatched"]))
    rv.append("")
    four = [(m, row, link, info) for m, row, link, info, ht_, hd_ in rows if not (ht_ and hd_) and typ(row) in ("대학교", "산업대학")]
    rv += ["## 4년제(대학교, 산업대학) 중 등록금 또는 기숙사가 매칭되지 않은 마커 (%d)" % len(four), "",
           "| 마커 이름 | KEDI 학교 종류 | 연결캠퍼스명 | 등록금 | 기숙사 |", "|---|---|---|---|---|"]
    for m, row, link, info in four:
        rv.append("| %s | %s | %s | %s | %s |" % (m["campus"], typ(row), link, info["tuitionUndergradAnnual"].replace("|", "/"), info["dormCapacityRate"].replace("|", "/")))
    rv += [""]
    unk = [m for m, row, link, info, a, b in rows if row is None]
    rv += ["## master에 마커 행이 없어 연결캠퍼스명·학교 종류를 알 수 없는 마커 (%d)" % len(unk), ""] + ["- %s (%s)" % (m["campus"], m["univ"]) for m in unk] + [""]
    both = [(m, row, info) for m, row, link, info, a, b in rows if not a and not b]
    rv += ["## 둘 다 매칭되지 않은 마커 (%d)" % len(both), "", "| 마커 이름 | KEDI 학교 종류 | 사유 |", "|---|---|---|"]
    for m, row, info in both:
        rv.append("| %s | %s | %s |" % (m["campus"], typ(row) or "master 행 없음", info["tuitionUndergradAnnual"].replace("|", "/")))
    rv += [""]
    left_t = [nm for nm in ent_t if nm not in used_t]
    left_d = [nm for nm in ent_d if nm not in used_d]
    rv += ["## 매칭되지 않은 등록금 xlsx 항목 (%d / %d)" % (len(left_t), len(ent_t)), ""] + ["- %s (%s)" % (nm, ent_t[nm]["kind"]) for nm in left_t] + [""]
    rv += ["## 매칭되지 않은 기숙사 xlsx 항목 (%d / %d, 학교 단위)" % (len(left_d), len(ent_d)), ""] + ["- %s (%s)" % (nm, ent_d[nm]["kind"]) for nm in left_d] + [""]
    with io.open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rv) + "\n")
    school = sum(1 for r in out_markers for k in ("tuitionUndergradAnnual", "dormCapacityRate") if r.get(k, {}).get("scope"))
    print("이전: %s" % prev)
    print("마커 %d, 등록금 매칭 %d, 기숙사 매칭 %d, 둘 다 미매칭 %d (학교 단위 공시값 항목 %d개)" % (len(markers), n_t, n_d, n_none, school))
    print("4년제 중 등록금/기숙사 미매칭 마커 %d, master 행 없는 마커 %d" % (len(four), len(unk)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
