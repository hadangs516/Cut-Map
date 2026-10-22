# -*- coding: utf-8 -*-
"""대학어디가 학생부종합전형 2026학년도 전형 결과 화면(html)에서 IT 학과 행을 읽어 docs/data/adiga.json 을 만든다.

입력
  data/ipgyeol_sources.json   학교별 어디가 파일 이름과 마커 이름
  docs/data/targets.json      지도에 보이는 대상 마커
  docs/data/markers.json      마커별 IT 학과명(itDepts)
  docs/data/ipgyeol.json      (학과 이름 연결에만 쓴다. 값은 쓰지 않는다)
  docs/data/legacy_detail.json (학과 이름 연결에만 쓴다. 값은 쓰지 않는다)
  sources/ipgyeol/*_어디가.html   받은 원본(수정하지 않는다)
출력
  docs/data/adiga.json        { meta, schools: { 마커 이름: { source_file, source_url, rows: [ ... ] } } }
  adiga_extract_review.md     학교별 맞춘 학과 수, 못 맞춘 IT 학과명, 애매해서 뺀 행, 학교마다 값 하나와 원문 글자 3줄

원칙
  - 값은 표의 머리 글자(열 이름)와 행 글자(모집단위)로 코드가 찾은 것만 쓴다. 사람이나 AI가 숫자를 옮겨 적지 않는다.
  - 표 머리 글자가 알려진 모양(구분, 모집단위, 모집인원 최초·이월·최종, 경쟁률, 충원인원, 학생부 환산점수·환산등급 50%·70%, 총점)과
    다르면 그 표는 읽지 않고 보고한다.
  - 표마다 전형명(표 제목)이 있다. 구분이 '수시'인 행만 읽는다(정시 구분 행은 읽지 않고 개수만 보고한다).
  - IT 학과 대응은 ipgyeol.json 과 같은 규칙: markers.json 의 itDepts 와 모집단위 이름이 띄어쓰기, 괄호, 붙임표, 끝말(학과, 학부, 전공)만 빼고 같을 때만 맞춘다.
    같은 전형에 끝말만 다른 이름이 여럿이면 이름 전체가 IT 학과명과 같은 행만 맞추고, 같은 이름이 값이 다르게 둘 이상이면 뺀다.
  - 숫자가 아닌 칸('-', 빈칸, 미제출 사유 등)은 null 로 두고 원문 글자를 note 에 적는다.
  - restricted: ipgyeol.json 과 같은 말 목록과 사용자 결정 목록(scripts/extract_ipgyeol.py)을 쓴다.
    전형명에 '지역'이 들어 있는데 사용자 결정 목록의 전형과 이름이 같지 않고 말 목록에도 안 걸리면 판정이 애매해서 그 행을 넣지 않고 보고한다.

사용: python scripts/extract_adiga.py [--write]   (--write 없으면 파일을 쓰지 않고 요약만 출력)
"""
import io
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from extract_ipgyeol import is_restricted, norm_dept, exact_key, RESTRICT_OVERRIDE, RESTRICT_REASON, RESTRICT_WORDS, NOSPACE_WORDS  # noqa: E402
from build_legacy_detail import core_name  # noqa: E402

SRC_DIR = os.path.join(ROOT, "sources", "ipgyeol")
SOURCES_JSON = os.path.join(ROOT, "data", "ipgyeol_sources.json")
TARGETS_JSON = os.path.join(ROOT, "docs", "data", "targets.json")
MARKERS_JSON = os.path.join(ROOT, "docs", "data", "markers.json")
IPGYEOL_JSON = os.path.join(ROOT, "docs", "data", "ipgyeol.json")
LEGACY_JSON = os.path.join(ROOT, "docs", "data", "legacy_detail.json")
OUT_JSON = os.path.join(ROOT, "docs", "data", "adiga.json")
OUT_MD = os.path.join(ROOT, "adiga_extract_review.md")

YEAR = 2026
SOURCE_TITLE = "대학어디가 평가기준 및 입시결과 > 학생부종합전형 > 2026학년도 전형 결과"
# 알려진 표 머리(행 순서대로 이어 붙인 글자). 이것과 다르면 읽지 않는다.
KNOWN_HEAD = "구분|모집단위|모집인원|경쟁률|충원인원|학생부|최초(A)|이월(B)|최종(A)+(B)|환산점수|환산등급|총점(학생부)|50%|70%|50%|70%"
# 머리에서 확인한 열 순서(열 번호 -> 이름). 머리가 KNOWN_HEAD 와 같은 표에서만 쓴다.
COLS = ["division", "department", "recruit_first", "recruit_carry", "recruit_final", "competition", "fill",
        "score50", "score70", "grade50", "grade70", "total"]
COL_NAME = {"recruit_first": "모집인원 최초", "recruit_carry": "모집인원 이월", "recruit_final": "모집인원 최종", "competition": "경쟁률",
            "fill": "충원인원", "score50": "환산점수 50%", "score70": "환산점수 70%", "grade50": "환산등급 50%", "grade70": "환산등급 70%",
            "total": "총점(학생부)"}
NUM_RE = re.compile(r"^-?\d+(?:,\d{3})*(?:\.\d+)?$")
SUSPECT_WORDS = ["지역", "서해", "배려", "기여", "추천", "SW", "sw", "소프트웨어", "불교"]


def load_json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


# ---------------------------------------------------------------- html 표 읽기
class TableParser(HTMLParser):
    """표마다 caption, 바로 앞 제목(h1~h6), 행(셀 글자, colspan, 원문 줄 번호)을 모은다."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.tables = [], []
        self.last_h, self.inh, self.hh = None, None, []
        self.incap, self.captxt = False, []

    @property
    def cur(self):
        return self.stack[-1] if self.stack else None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        c = self.cur
        if tag == "table":
            t = {"cap": None, "title": self.last_h, "rows": [], "row": None, "cell": None}
            self.tables.append(t)
            self.stack.append(t)
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.inh, self.hh = tag, []
        if c is None:
            return
        if tag == "tr":
            c["row"] = []
        elif tag in ("th", "td"):
            if c["row"] is None:
                c["row"] = []
            c["cell"] = {"tag": tag, "txt": [], "attr": a, "line": self.getpos()[0]}
        elif tag == "br" and c["cell"] is not None:
            c["cell"]["txt"].append("\n")
        elif tag == "caption":
            self.incap, self.captxt = True, []

    def handle_endtag(self, tag):
        c = self.cur
        if tag == "table" and c is not None:
            self.stack.pop()
        elif c is not None and tag in ("th", "td") and c["cell"] is not None:
            cell = c["cell"]
            c["cell"] = None
            if c["row"] is None:
                c["row"] = []
            text = re.sub(r"[ \t\r\f\v]+", " ", "".join(cell["txt"])).replace(" \n", "\n").replace("\n ", "\n").strip()
            c["row"].append({"tag": cell["tag"], "text": text, "colspan": int(cell["attr"].get("colspan") or 1),
                             "rowspan": int(cell["attr"].get("rowspan") or 1), "line": cell["line"]})
        elif c is not None and tag == "tr" and c["row"] is not None:
            c["rows"].append(c["row"])
            c["row"] = None
        elif tag == "caption" and c is not None:
            c["cap"] = re.sub(r"\s+", " ", "".join(self.captxt)).strip()
            self.incap = False
        elif tag == self.inh:
            self.last_h = re.sub(r"\s+", " ", "".join(self.hh)).strip()
            self.inh = None

    def handle_data(self, d):
        c = self.cur
        if c is not None and c["cell"] is not None:
            c["cell"]["txt"].append(d)
        if self.incap:
            self.captxt.append(d)
        if self.inh:
            self.hh.append(d)


def parse_file(path):
    with io.open(path, encoding="utf-8") as f:
        txt = f.read()
    p = TableParser()
    p.feed(txt)
    m = re.search(r"saved from (\S+)", txt[:600])
    return p.tables, (m.group(1) if m else None), txt.split("\n")


def head_text(t):
    rows = [r for r in t["rows"] if r and all(c["tag"] == "th" for c in r)]
    return "|".join(re.sub(r"\s+", "", c["text"]) for r in rows for c in r)


def to_num(t):
    t = (t or "").strip().replace(",", "")
    if NUM_RE.match(t):
        v = float(t)
        return int(v) if v == int(v) and "." not in t else v
    return None


# ---------------------------------------------------------------- restricted
def title_restricted(title, marker):
    """(restricted 또는 None, 이유). None 은 판정이 애매해서 넣지 않는다는 뜻.
    1) 사용자 결정 목록에서 전형 이름(앞의 학생부종합 표기와 끝의 '전형'을 뗀 것)이 같으면 그 값
    2) 말 목록에 걸리면 true
    3) '지역'이 들어 있으면 애매
    4) 그 밖에는 false"""
    for (mk, adm), val in RESTRICT_OVERRIDE.items():
        if mk == marker and core_name(adm) and core_name(adm) == core_name(title):
            return val, "사용자 결정 목록"
    if is_restricted(title, marker) and not any(mk == marker and adm == title for (mk, adm) in RESTRICT_OVERRIDE):
        return True, "말 목록"
    if "지역" in title:
        return None, "전형명에 '지역'이 있으나 사용자 결정 목록과 이름이 같지 않음"
    return False, "해당 없음"


def suspect_hits(title):
    return [w for w in SUSPECT_WORDS if w in title]


# ---------------------------------------------------------------- 학교 한 곳
def read_school(marker, fname, it_names, ipg_names, leg_depts):
    path = os.path.join(SRC_DIR, fname)
    tables, saved_from, lines = parse_file(path)
    res = {"marker": marker, "file": fname, "source_url": saved_from, "tables": 0, "bad_tables": [], "rows_total": 0, "rows_jeongsi": 0,
           "rows": [], "dropped": [], "matched_depts": OrderedDict(), "unmatched_it": [], "near": [], "excluded_restrict": [], "suspects": [],
           "sample": None, "mismatch": []}
    exact_set = {exact_key(n) for n in it_names}
    itmap = defaultdict(list)
    for n in it_names:
        itmap[norm_dept(n)].append(n)
    ipg_by = defaultdict(list)
    for n in ipg_names:
        ipg_by[norm_dept(n)].append(n)
    leg_by = defaultdict(list)
    for d in leg_depts:
        leg_by[norm_dept(d["name"])].append(d)

    def pick(cands, name):
        """이름 전체가 같은 후보가 하나면 그것, 후보가 하나뿐이면 그것, 아니면 None"""
        if len(cands) == 1:
            return cands[0]
        ex = [c for c in cands if exact_key(c if isinstance(c, str) else c["name"]) == exact_key(name)]
        return ex[0] if len(ex) == 1 else None

    cand = []   # (표 번호, 전형명, 셀 목록, 원본 줄)
    for ti, t in enumerate(tables):
        if not (t["cap"] and "전형결과" in t["cap"]):
            continue
        res["tables"] += 1
        if head_text(t) != KNOWN_HEAD:
            res["bad_tables"].append((t["title"], head_text(t)))
            continue
        for r in t["rows"]:
            if not r or r[0]["tag"] != "td":
                continue
            res["rows_total"] += 1
            if not r[0]["text"].startswith("수시"):
                res["rows_jeongsi"] += 1
                continue
            cand.append((ti, t["title"], r))

    # IT 학과 이름이 맞는 행만
    it_rows = [(ti, ti_, r) for (ti, ti_, r) in cand if norm_dept(r[1]["text"]) in itmap]
    punct = defaultdict(list)
    for n in it_names:
        punct[norm_dept(re.sub(r"[·_/,]", "", n))].append(n)
    seen_near = OrderedDict()
    for (ti, title, r) in cand:
        nm = r[1]["text"]
        if norm_dept(nm) in itmap:
            continue
        k = norm_dept(re.sub(r"[·_/,]", "", nm))
        if k in punct:
            seen_near.setdefault((nm, tuple(punct[k])), title)
    res["near"] = list(seen_near.items())

    def build(title, r):
        cells = r
        d = OrderedDict()
        notes = []
        if len(cells) == 12:
            vals = {COLS[i]: cells[i]["text"] for i in range(12)}
            for k in COLS[2:]:
                v = to_num(vals[k])
                d[k] = v
                if v is None:
                    notes.append("%s: %s" % (COL_NAME[k], vals[k] if vals[k] != "" else "(빈칸)"))
        elif len(cells) == 8 and cells[7]["colspan"] == 5:
            for i, k in enumerate(COLS[2:7]):
                v = to_num(cells[2 + i]["text"])
                d[k] = v
                if v is None:
                    notes.append("%s: %s" % (COL_NAME[k], cells[2 + i]["text"] if cells[2 + i]["text"] != "" else "(빈칸)"))
            for k in ("score50", "score70", "grade50", "grade70", "total"):
                d[k] = None
            notes.append(cells[7]["text"])
        else:
            return None, "칸 모양이 알려진 두 가지(12칸, 끝 칸이 5칸을 합친 8칸)가 아님: %d칸" % len(cells)
        return d, "; ".join(notes) if notes else None

    # 한 표(전형) 안에서 끝말을 뗀 이름이 같은 행이 둘 이상이면 이름 전체가 IT 학과명과 같은 행만
    by_key = defaultdict(list)
    for item in it_rows:
        ti, title, r = item
        by_key[(ti, norm_dept(r[1]["text"]))].append(item)
    kept = []
    for key, g in by_key.items():
        names = {exact_key(r[1]["text"]) for (_, _, r) in g}
        if len(names) > 1:
            keep = [x for x in g if exact_key(x[2][1]["text"]) in exact_set]
            drop = [x for x in g if x not in keep]
            kept += keep
            for x in drop:
                res["dropped"].append((x[1], x[2][1]["text"], "같은 전형 안에 끝말만 다른 이름이 여러 개이고 이름 전체가 IT 학과명과 같지 않음"))
        else:
            kept += g
    # 같은 (표, 이름)이 여러 번이면 값이 모두 같을 때만 하나
    final, seen = [], OrderedDict()
    for item in kept:
        seen.setdefault((item[0], exact_key(item[2][1]["text"])), []).append(item)
    for k, g in seen.items():
        built = [build(x[1], x[2]) for x in g]
        if any(b[0] is None for b in built):
            for x, b in zip(g, built):
                if b[0] is None:
                    res["dropped"].append((x[1], x[2][1]["text"], b[1]))
            g = [x for x, b in zip(g, built) if b[0] is not None]
            built = [b for b in built if b[0] is not None]
            if not g:
                continue
        if len({json.dumps(b[0], sort_keys=True) for b in built}) > 1:
            for x in g:
                res["dropped"].append((x[1], x[2][1]["text"], "같은 이름·전형에 값이 서로 다른 행이 둘 이상"))
            continue
        final.append((g[0], built[0]))
    final.sort(key=lambda x: (x[0][0], tables[x[0][0]]["rows"].index(x[0][2])))

    for (item, (vals, note)) in final:
        ti, title, r = item
        nm = r[1]["text"]
        same = [n for n in it_names if exact_key(n) == exact_key(nm)] or itmap[norm_dept(nm)]
        if len(set(same)) != 1:
            res["dropped"].append((title, nm, "IT 학과명 후보가 여럿(%s)이라 애매함" % " / ".join(sorted(set(same)))))
            continue
        rs, why = title_restricted(title, marker)
        if rs is None:
            res["excluded_restrict"].append((title, nm, why))
            continue
        hits = suspect_hits(title)
        if hits and why == "해당 없음":
            res["suspects"].append((title, hits))
        ipg_m = pick(ipg_by.get(norm_dept(nm), []), nm)
        leg_m = pick(leg_by.get(norm_dept(nm), []), nm)
        if vals["recruit_first"] is not None and vals["recruit_carry"] is not None and vals["recruit_final"] is not None \
                and vals["recruit_first"] + vals["recruit_carry"] != vals["recruit_final"]:
            res["mismatch"].append((title, nm, "모집인원 최초 %s + 이월 %s 가 최종 %s 와 다름" % (vals["recruit_first"], vals["recruit_carry"], vals["recruit_final"])))
        row = OrderedDict()
        row["department"] = nm
        row["match"] = same[0]
        row["ipg_match"] = ipg_m
        row["legacy_id"] = leg_m["id"] if leg_m else None
        row["admission"] = title
        row["year"] = YEAR
        row["recruit_first"] = vals["recruit_first"]
        row["recruit_carry"] = vals["recruit_carry"]
        row["recruit_final"] = vals["recruit_final"]
        row["competition"] = vals["competition"]
        row["fill"] = vals["fill"]
        row["score50"] = vals["score50"]
        row["score70"] = vals["score70"]
        row["grade50"] = vals["grade50"]
        row["grade70"] = vals["grade70"]
        row["note"] = note
        row["restricted"] = rs
        row["source_line"] = r[10]["line"] if len(r) == 12 else r[7]["line"]
        res["rows"].append(row)
        res["matched_depts"].setdefault(same[0], 0)
        res["matched_depts"][same[0]] += 1
        if res["sample"] is None and vals["grade70"] is not None:
            ln = r[10]["line"]
            res["sample"] = {"department": nm, "admission": title, "field": "환산등급 70%", "value": vals["grade70"], "line": ln,
                             "text": [lines[i - 1].strip() for i in (ln - 1, ln, ln + 1)]}
    res["unmatched_it"] = [n for n in it_names if n not in res["matched_depts"]]
    if res["sample"] is None and res["rows"]:
        r0 = res["rows"][0]
        ln = r0["source_line"]
        res["sample"] = {"department": r0["department"], "admission": r0["admission"], "field": "(환산등급 값 없음) 마지막 칸", "value": None, "line": ln,
                         "text": [lines[i - 1].strip() for i in (ln - 1, ln, ln + 1)]}
    return res


def main():
    write = "--write" in sys.argv
    srcs = load_json(SOURCES_JSON)
    markers = {m["campus"]: m for m in load_json(MARKERS_JSON)["markers"]}
    targets = [t["marker"] for t in load_json(TARGETS_JSON)["targets"]]
    ipg = load_json(IPGYEOL_JSON)
    leg = load_json(LEGACY_JSON)["schools"]
    file_by_marker = OrderedDict()
    for r in srcs["rows"]:
        if r.get("file", "").endswith("_어디가.html"):
            file_by_marker.setdefault(r["marker"], r["file"])
    results = OrderedDict()
    for marker in targets:
        fname = file_by_marker.get(marker)
        if not fname or not os.path.exists(os.path.join(SRC_DIR, fname)):
            results[marker] = None
            continue
        ipg_names = sorted({e["department"] for e in ipg.get(marker, []) if e.get("department")})
        results[marker] = read_school(marker, fname, markers[marker]["itDepts"], ipg_names, (leg.get(marker) or {}).get("depts", []))

    out = OrderedDict()
    out["meta"] = OrderedDict([
        ("built_from", "sources/ipgyeol/*_어디가.html"), ("generator", "scripts/extract_adiga.py"), ("year", YEAR),
        ("source_title", SOURCE_TITLE),
        ("note", "대학어디가 학생부종합전형 2026학년도 전형 결과 화면의 표에서 코드가 열 이름으로 읽은 값. 환산등급은 대학별 환산 방식에 따른 값이라 대학 원문 등급과 기준이 다를 수 있다."),
        ("fields", "department=표의 모집단위 이름, match=markers.json itDepts 이름, ipg_match=ipgyeol.json 학과 이름(없으면 null), legacy_id=legacy_detail.json 학과 id(없으면 null), "
                   "admission=표 제목(전형명), recruit_first/carry/final=모집인원 최초·이월·최종, competition=경쟁률, fill=충원인원, score50/70=환산점수, grade50/70=환산등급, "
                   "note=숫자가 아닌 칸의 원문 글자, restricted=지원 자격 제한 전형, source_line=원본 html 줄 번호")])
    schools = OrderedDict()
    for marker, r in results.items():
        if not r or not r["rows"]:
            continue
        schools[marker] = OrderedDict([("source_file", r["file"]), ("source_url", r["source_url"]), ("source_title", SOURCE_TITLE), ("rows", r["rows"])])
    out["schools"] = schools
    if write:
        with io.open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
            f.write("\n")
        with io.open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
            f.write(review(results))
    summary(results)
    print("\n쓴 파일: %s %s" % (OUT_JSON, OUT_MD) if write else "\n(--write 없음: 파일을 쓰지 않음)")
    return out, results


def summary(results):
    print("%-34s %5s %5s %6s %6s %6s %6s" % ("마커", "표", "정시", "맞춘학과", "행", "못맞춤IT", "뺀행"))
    tot = [0, 0, 0]
    for m, r in results.items():
        if not r:
            print("%-34s 어디가 파일 없음" % m)
            continue
        ex = len(r["dropped"]) + len(r["excluded_restrict"])
        print("%-34s %5d %5d %6d %6d %6d %6d" % (m, r["tables"], r["rows_jeongsi"], len(r["matched_depts"]), len(r["rows"]), len(r["unmatched_it"]), ex))
        tot[0] += len(r["rows"])
        tot[1] += len(r["matched_depts"])
        tot[2] += ex
    print("합계: 행 %d, 맞춘 학과 %d, 뺀 행 %d" % tuple(tot))


def fmt(v):
    return "-" if v is None else str(v)


def review(results):
    L = []
    L.append("# 대학어디가 학종 2026 추출 검토 (adiga_extract_review.md)\n")
    L.append("scripts/extract_adiga.py 가 만들었다. 값은 표의 머리 글자(열 이름)와 행 글자(모집단위)로 코드가 찾은 것만 쓴다. 사람이나 AI가 화면을 보고 옮긴 숫자는 없다.\n")
    L.append("- 읽은 표: 각 파일에서 caption 이 '전년도 전형결과'인 표(표 제목이 전형명). 표 머리가 알려진 모양과 다르면 읽지 않는다.")
    L.append("- 읽은 행: 구분이 '수시'인 행만. 구분이 정시(가·나·다)인 행은 읽지 않았다(아래 표에 개수).")
    L.append("- IT 학과 대응: markers.json 의 itDepts 와 모집단위 이름이 띄어쓰기, 괄호, 붙임표, 끝말(학과, 학부, 전공)만 빼고 같을 때만 맞춘다.")
    L.append("- restricted: 전형명에 다음 말 중 하나가 그대로 들어 있으면 true: " + ", ".join(RESTRICT_WORDS) + " (서해5도는 공백 무시). 사용자 결정 목록은 전형 이름(앞의 학생부종합 표기와 끝의 '전형'을 뗀 것)이 같은 표에 적용한다.")
    L.append("- 사용자 결정 목록에 '가톨릭지도자추천 = true'를 추가했다(100).")
    L.append("- 사용자 결정(101)으로 다음 전형을 정했다. 근거: 사용자 고교 소재지 경북, 101 결정.")
    for (mk_, adm_), val in RESTRICT_OVERRIDE.items():
        if (mk_, adm_) in RESTRICT_REASON:
            L.append("  - %s: %s = %s (근거: %s)" % (mk_, adm_, "true" if val else "false", RESTRICT_REASON[(mk_, adm_)]))
    L.append("- 전형명에 '지역'이 있는데 사용자 결정 목록과 이름이 같지 않고 말 목록에도 안 걸리는 행은 판정이 애매해서 넣지 않는다(101 결정 이후 해당 행 없음이면 아래 표가 비어 있다).\n")
    L.append("## 학교별 요약\n")
    L.append("| 학교(마커) | 어디가 파일 | 읽은 표 | 정시 구분 행(읽지 않음) | 맞춘 학과 수 | 넣은 행 수 | 맞추지 못한 IT 학과 수 | 애매해서 뺀 행 수 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m, r in results.items():
        if not r:
            L.append("| %s | 없음 | - | - | - | - | - | - |" % m)
            continue
        L.append("| %s | %s | %d | %d | %d | %d | %d | %d |" % (m, r["file"], r["tables"], r["rows_jeongsi"], len(r["matched_depts"]), len(r["rows"]),
                                                          len(r["unmatched_it"]), len(r["dropped"]) + len(r["excluded_restrict"])))
    L.append("\n## 맞추지 못한 IT 학과명\n")
    L.append("markers.json 의 IT 학과명 중 어디가 표(수시 행)에서 규칙으로 맞는 모집단위가 하나도 없는 것.\n")
    L.append("| 학교(마커) | 맞추지 못한 IT 학과명 |")
    L.append("|---|---|")
    for m, r in results.items():
        if r and r["unmatched_it"]:
            L.append("| %s | %s |" % (m, ", ".join(r["unmatched_it"])))
    L.append("\n### 규칙으로는 안 맞았지만 가운뎃점·밑줄 등을 무시하면 같아지는 이름(넣지 않음)\n")
    L.append("| 학교(마커) | 어디가 모집단위 | IT 학과명 | 전형 |")
    L.append("|---|---|---|---|")
    any_near = False
    for m, r in results.items():
        for (nm, its), title in (r["near"] if r else []):
            L.append("| %s | %s | %s | %s |" % (m, nm, " / ".join(its), title))
            any_near = True
    if not any_near:
        L.append("| (없음) | | | |")
    L.append("\n## 애매해서 뺀 행\n")
    L.append("| 학교(마커) | 전형 | 모집단위 | 이유 |")
    L.append("|---|---|---|---|")
    anyd = False
    for m, r in results.items():
        if not r:
            continue
        for (title, nm, why) in r["dropped"]:
            L.append("| %s | %s | %s | %s |" % (m, title, nm, why))
            anyd = True
        for (title, nm, why) in r["excluded_restrict"]:
            L.append("| %s | %s | %s | 지원 자격 제한 판정이 애매함: %s |" % (m, title, nm, why))
            anyd = True
    if not anyd:
        L.append("| (없음) | | | |")
    L.append("\n## 확인이 필요한 전형명(restricted=false 로 넣었지만 이름에 의심되는 말이 있음)\n")
    L.append("| 학교(마커) | 전형 | 말 |")
    L.append("|---|---|---|")
    anys = False
    seen = set()
    for m, r in results.items():
        for (title, hits) in (r["suspects"] if r else []):
            if (m, title) in seen:
                continue
            seen.add((m, title))
            L.append("| %s | %s | %s |" % (m, title, ", ".join(hits)))
            anys = True
    if not anys:
        L.append("| (없음) | | |")
    L.append("\n## 모집인원 검산(최초 + 이월 = 최종이 아닌 행, 값은 고치지 않고 그대로 넣음)\n")
    L.append("| 학교(마커) | 전형 | 모집단위 | 내용 |")
    L.append("|---|---|---|---|")
    anym = False
    for m, r in results.items():
        for (title, nm, why) in (r["mismatch"] if r else []):
            L.append("| %s | %s | %s | %s |" % (m, title, nm, why))
            anym = True
    if not anym:
        L.append("| (없음) | | | |")
    L.append("\n## 표 머리가 알려진 모양과 달라 읽지 않은 표\n")
    bad = [(m, b) for m, r in results.items() if r for b in r["bad_tables"]]
    if bad:
        for m, (title, h) in bad:
            L.append("- %s: %s / %s" % (m, title, h))
    else:
        L.append("없음 (읽은 모든 표의 머리가 같음: `%s`)" % KNOWN_HEAD)
    L.append("\n## 학교별 값 하나와 원문 글자\n")
    L.append("값은 원본 html 에서 그 칸이 있는 줄과 앞뒤 한 줄씩(3줄)이다.\n")
    for m, r in results.items():
        if not r or not r["sample"]:
            continue
        s = r["sample"]
        L.append("- **%s** (%s, 줄 %d): %s / %s / %s = %s" % (m, r["file"], s["line"], s["department"], s["admission"], s["field"], fmt(s["value"])))
        L.append("  ```")
        for t in s["text"]:
            L.append("  " + t)
        L.append("  ```")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
