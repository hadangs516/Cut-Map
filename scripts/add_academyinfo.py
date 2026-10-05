# -*- coding: utf-8 -*-
"""대학알리미 등록금·기숙사 공시 xlsx 를 docs/data/markers.json 의 마커와 이름으로 맞춰 docs/data/academyinfo.json 에 저장한다.
(#1005-06 작업 67에서 만들고, #1005-20 작업 83, #1005-22 작업 87·88에서 규칙을 바꿨다.)

입력(저장소 루트, 원본 xlsx 는 커밋하지 않는다)
  등록금 현황 (2026_대학).xlsx    - 열 "등록금 (D=B)" 을 학부 연평균 등록금(원)으로 쓴다
  기숙사 수용 현황 (2025_대학).xlsx - 열 "기숙사수용률 (C=B/A×100)" 을 기숙사 수용률(%)로 쓴다
  KEDI 2026 고등교육통계 xlsx      - 마커 주소와 정확히 같은 주소의 행으로 캠퍼스 구분을 정한다
  university_master_list_v2.json  - KEDI 로 정하지 못한 마커의 캠퍼스 구분은 연결캠퍼스명으로 정한다
출력
  docs/data/academyinfo.json  - 마커별 "연평균 등록금(학부)"(원), 기숙사 수용률(%), 항목별 공시년도, 출처, 라이선스
  academyinfo_review.md       - 매칭되지 않은 마커와 xlsx 행, 4년제 미매칭 마커의 이름·사유
화면 코드(docs/index.html 등)는 건드리지 않는다.

열 선택: 머리글(4행)에 "등록금"이 들어간 열이 하나일 때만, "기숙사수용률"이 들어간 열이 하나일 때만 값을 쓴다.

마커의 캠퍼스 구분(본교(제1캠퍼스), 본교(제N캠퍼스), 분교)
  1) markers.json 마커 주소와 정확히 같은 주소를 가진 KEDI 행(대학원 제외, 학교명이 마커 univ 와 같은 행만)이 정확히 하나이면 그 행의 본분교 값을 쓴다.
  2) 같은 주소 행이 없거나 둘 이상이면 master 의 연결캠퍼스명("학교명 (본교(제N캠퍼스))" 등)에서 정한다.
  3) 그래도 알 수 없으면 캠퍼스 구분 없음.
xlsx 행과 맞추는 규칙(이름이 정확히 같을 때만, 비슷한 이름으로 맞추지 않는다)
  xlsx 학교 칸은 "학교명", "학교명 _제N캠퍼스", "학교명_제N캠퍼스", "학교명 _분교" 형식이다(접미사 앞 공백 유무는 무시한다).
  학교명은 연결캠퍼스명의 "학교명"(표기가 없으면 마커 univ)이다.
  a) 그 학교의 xlsx 행이 접미사 없는 행 하나뿐이면 그 학교의 모든 마커에 그 값을 붙인다.
  b) 그렇지 않으면 본교(제1캠퍼스) -> 접미사 없는 행, 본교(제N캠퍼스) -> "_제N캠퍼스" 행, 분교 -> "_분교" 행과 정확히 1개 대응할 때만 붙인다.
  c) 정확히 대응하는 행이 없으면 비워 둔다.
  값이 행 안에서 하나로 정해지지 않으면(기숙사 수용률이 건물 행마다 다름) 값을 넣지 않는다.
scope: a) 로 붙은 값이고 그 학교의 마커가 2개 이상일 때만 "scope": "학교 단위 공시값"을 넣는다(마커 1개뿐인 학교는 뺀다).
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
from add_address import find_xlsx as find_kedi, load_kedi  # noqa: E402

MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
OUT = os.path.join(ROOT, "docs", "data", "academyinfo.json")
REVIEW = os.path.join(ROOT, "academyinfo_review.md")
MASTER = os.path.join(ROOT, "university_master_list_v2.json")
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
TAG_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<kind>본교|분교)\(제(?P<n>\d+)캠퍼스\)\)$")
KEDI_TAG_RE = re.compile(r"^(?P<kind>본교|분교)\(제(?P<n>\d+)캠퍼스\)$")
SRC_TUITION = "대학알리미 8-차-1. 등록금 현황 (2026 공시, 학교별평균값)"
SRC_DORM = "대학알리미 14-마-1. 기숙사 수용 현황 (2025 공시, 학교별평균값)"
LICENSE = "공공누리 제1유형"
NAME_TUITION = "연평균 등록금(학부)"
NAME_DORM = "기숙사 수용률"
SCOPE_SCHOOL = "학교 단위 공시값"
FLAG = "원자료 값(확인 필요)"
FLAGS = [("정석대학", "tuitionUndergradAnnual"), ("금강대학교(논산)", "dormCapacityRate")]   # 기존 flag 2개 유지


def find_one(prefix):
    hits = sorted(f for f in os.listdir(ROOT) if f.startswith(prefix) and f.lower().endswith(".xlsx"))
    if len(hits) != 1:
        raise SystemExit("%s 로 시작하는 xlsx 를 정확히 1개 찾지 못함: %s" % (prefix, hits))
    return os.path.join(ROOT, hits[0])


def read_sheet(path):
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


def gubun_from(kind, n):
    """(본교|분교, 번호) -> xlsx 접미사"""
    if kind == "분교":
        return "분교"
    return None if str(n) == "1" else "제%s캠퍼스" % n


def match_marker(base, gub, idx):
    """(xlsx 학교 칸 이름, 학교 단위 여부, 설명) 또는 (None, False, 사유). gub = (kind, n) 또는 None"""
    rows = idx.get(base, [])
    if not rows:
        return None, False, "xlsx에 학교명 없음"
    if len(rows) == 1 and rows[0][0] is None:
        return rows[0][1], True, "학교의 xlsx 행이 접미사 없는 행 하나뿐"
    if gub is None:
        return None, False, "캠퍼스 구분을 알 수 없음(xlsx 행: %s)" % " / ".join(nm for _, nm in rows)
    want = gubun_from(*gub)
    hit = [nm for suf, nm in rows if suf == want]
    if len(hit) == 1:
        return hit[0], False, "캠퍼스 구분(%s)과 접미사 일치(%s)" % ("%s 제%s캠퍼스" % gub if gub[0] == "본교" else "분교", want or "접미사 없음")
    return None, False, "대응하는 접미사 행 없음(필요: %s, xlsx 행: %s)" % (want or "접미사 없음", " / ".join(nm for _, nm in rows))


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
    kedi_all = load_kedi(find_kedi())
    kedi_ug = [k for k in kedi_all if not k["대학원구분"] and "대학원" not in k["학제"]]
    by_addr = defaultdict(list)
    for k in kedi_ug:
        if k["주소"]:
            by_addr[k["주소"].strip()].append(k)
    prev = None
    if os.path.exists(OUT):
        prev = json.load(io.open(OUT, encoding="utf-8")).get("stats")

    # 1단계: 마커별 캠퍼스 구분, 학교명, 매칭 결과
    infos = []
    for m in markers:
        row = mrow.get((m["univ"], m["campus"]))
        link = row["연결캠퍼스명"] if row else None
        tag = TAG_RE.match(link.strip()) if link else None
        base = tag.group("name") if tag else m["univ"].strip()
        k_rows = [k for k in by_addr.get((m.get("address") or "").strip(), []) if k["학교명"] == m["univ"]] if m.get("address") else []
        if len(k_rows) == 1 and KEDI_TAG_RE.match(k_rows[0]["본분교"]):
            kt = KEDI_TAG_RE.match(k_rows[0]["본분교"])
            gub, gsrc = (kt.group("kind"), kt.group("n")), "KEDI 주소 일치"
        elif tag:
            gub, gsrc = (tag.group("kind"), tag.group("n")), "master 연결캠퍼스명"
        else:
            gub, gsrc = None, "구분 불가"
        infos.append(dict(m=m, row=row, link=link, base=base, gub=gub, gsrc=gsrc, n_addr=len(k_rows)))
    school_count = defaultdict(int)
    for i in infos:
        school_count[i["base"]] += 1

    out_markers, rows_out = [], []
    used_t, used_d = set(), set()
    n_t = n_d = n_none = 0
    for i in infos:
        m = i["m"]
        rec = OrderedDict([("univ", m["univ"]), ("campus", m["campus"]), ("region", m["region"])])
        info = {}
        for key, ents, idx, col, name, unit, src in (
                ("tuitionUndergradAnnual", ent_t, idx_t, col_t, NAME_TUITION, "원", SRC_TUITION),
                ("dormCapacityRate", ent_d, idx_d, col_d, NAME_DORM, "%", SRC_DORM)):
            if not col:
                info[key] = "열이 하나로 정해지지 않음"
                continue
            nm, school_level, why = match_marker(i["base"], i["gub"], idx)
            if nm is None:
                info[key] = why
                continue
            vals = ents[nm]["values"]
            if len(vals) != 1:
                info[key] = "xlsx 값이 하나로 정해지지 않음(%s)" % sorted(vals)
                continue
            v = float(next(iter(vals)))
            item = OrderedDict([("name", name), ("value", (int(v) if (key == "tuitionUndergradAnnual" and v == int(v)) else v)), ("unit", unit),
                                ("year", int(float(next(iter(ents[nm]["years"]))))), ("xlsxName", nm),
                                ("match", why + ("" if school_level else " [캠퍼스 구분 출처: %s]" % i["gsrc"])), ("source", src)])
            if school_level and school_count[i["base"]] >= 2:
                item["scope"] = SCOPE_SCHOOL
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
        rows_out.append((i, info, has_t, has_d))
    n_scope = sum(1 for r in out_markers for k in ("tuitionUndergradAnnual", "dormCapacityRate") if r.get(k, {}).get("scope"))
    doc = OrderedDict([
        ("version", 3),
        ("note", ["대학알리미 공시 xlsx 두 개를 scripts/add_academyinfo.py 가 읽어 마커 이름과 정확히 일치하는 항목에만 값을 붙였다.",
                  "마커의 캠퍼스 구분은 마커 주소와 정확히 같은 주소의 KEDI 행(정확히 하나일 때)으로 정하고, 못 정하면 master 연결캠퍼스명으로 정했다.",
                  "학교의 xlsx 행이 접미사 없는 행 하나뿐이면 그 학교의 모든 마커에 붙이고, 그 학교의 마커가 2개 이상일 때만 scope 를 \"학교 단위 공시값\"으로 적었다.",
                  "정확히 대응하는 행이 없거나 값이 하나로 정해지지 않으면 값을 넣지 않았다. 매칭 못 한 목록은 academyinfo_review.md.",
                  "원자료 이상값은 값을 바꾸지 않고 flag 로 표시했다."]),
        ("sources", OrderedDict([("tuition", SRC_TUITION), ("dorm", SRC_DORM)])),
        ("years", OrderedDict([("tuition", 2026), ("dorm", 2025)])),
        ("license", LICENSE),
        ("stats", OrderedDict([("markers", len(markers)), ("tuitionMatched", n_t), ("dormMatched", n_d), ("noneMatched", n_none), ("scopeItems", n_scope)])),
        ("markers", out_markers),
    ])
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")

    def typ(row, m=None):
        if row is None:   # master 행이 없으면 마커 주소와 같은 KEDI 행(학교명이 마커 univ 와 같은 것)의 학제를 쓴다
            t = sorted({k["학제"] for k in by_addr.get((m.get("address") or "").strip(), []) if k["학교명"] == m["univ"]}) if m else []
            return "/".join(t) if t else None
        t = kedi_types(row, kedi_ug)
        return "/".join(t) if t else "찾지 못함"
    gs = defaultdict(int)
    for i, *_ in rows_out:
        gs[i["gsrc"]] += 1
    rv = ["# 대학알리미 공시 매칭 결과 (scripts/add_academyinfo.py, 2026-10-05, #1005-22 규칙)", "",
          "마커 %d개, 등록금 매칭 %d개, 기숙사 매칭 %d개, 둘 다 매칭 안 된 마커 %d개, scope(학교 단위 공시값) 항목 %d개." % (len(markers), n_t, n_d, n_none, n_scope),
          "이전 실행(파일에 있던 값): %s" % (dict(prev) if prev else "없음"),
          "캠퍼스 구분 출처: %s" % ", ".join("%s %d개" % (k, v) for k, v in sorted(gs.items())), ""]
    four = [(i, info) for i, info, ht_, hd_ in rows_out if not (ht_ and hd_) and typ(i["row"], i["m"]) in ("대학교", "산업대학")]
    rv += ["## 4년제(대학교, 산업대학) 중 등록금 또는 기숙사가 매칭되지 않은 마커 (%d)" % len(four), "",
           "| 마커 이름 | KEDI 학교 종류 | 캠퍼스 구분(출처) | 등록금 | 기숙사 |", "|---|---|---|---|---|"]
    for i, info in four:
        g = ("%s 제%s캠퍼스" % i["gub"] if i["gub"] and i["gub"][0] == "본교" else (i["gub"][0] if i["gub"] else "없음"))
        rv.append("| %s | %s | %s(%s) | %s | %s |" % (i["m"]["campus"], typ(i["row"], i["m"]), g, i["gsrc"],
                                                        info["tuitionUndergradAnnual"].replace("|", "/"), info["dormCapacityRate"].replace("|", "/")))
    rv += [""]
    unk = [i for i, *_ in rows_out if i["row"] is None]
    rv += ["## master에 마커 행이 없는 마커 (%d)" % len(unk), ""] + ["- %s (%s) 캠퍼스 구분 출처: %s" % (i["m"]["campus"], i["m"]["univ"], i["gsrc"]) for i in unk] + [""]
    both = [(i, info) for i, info, a, b in rows_out if not a and not b]
    rv += ["## 둘 다 매칭되지 않은 마커 (%d)" % len(both), "", "| 마커 이름 | KEDI 학교 종류 | 사유 |", "|---|---|---|"]
    for i, info in both:
        rv.append("| %s | %s | %s |" % (i["m"]["campus"], typ(i["row"], i["m"]) or "master 행 없음", info["tuitionUndergradAnnual"].replace("|", "/")))
    rv += [""]
    left_t = [nm for nm in ent_t if nm not in used_t]
    left_d = [nm for nm in ent_d if nm not in used_d]
    rv += ["## 매칭되지 않은 등록금 xlsx 항목 (%d / %d)" % (len(left_t), len(ent_t)), ""] + ["- %s (%s)" % (nm, ent_t[nm]["kind"]) for nm in left_t] + [""]
    rv += ["## 매칭되지 않은 기숙사 xlsx 항목 (%d / %d, 학교 단위)" % (len(left_d), len(ent_d)), ""] + ["- %s (%s)" % (nm, ent_d[nm]["kind"]) for nm in left_d] + [""]
    with io.open(REVIEW, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rv) + "\n")
    print("이전: %s" % prev)
    print("마커 %d, 등록금 매칭 %d, 기숙사 매칭 %d, 둘 다 미매칭 %d, scope 항목 %d" % (len(markers), n_t, n_d, n_none, n_scope))
    print("캠퍼스 구분 출처:", dict(gs))
    return rows_out, out_markers


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
