# -*- coding: utf-8 -*-
"""data.json(처음 버전의 학과별 상세 자료)를 지금 대상 마커와 맞춰 docs/data/legacy_detail.json 으로 만든다.

입력: data.json, docs/data/targets.json, docs/data/markers.json, docs/data/ipgyeol.json
출력: docs/data/legacy_detail.json  (--write 가 있을 때만 쓴다. 없으면 보고만 한다)

학교 대응: 학교 이름(띄어쓰기·괄호 무시)이 같고, data.json 좌표와 마커 좌표가 5km 안일 때만 맞춘다.
  이름이 같아도 5km 밖이거나, 이름이 같은 data.json 학교가 둘 이상이면 넣지 않고 보고한다.
학과 대응: ipgyeol.json 의 그 마커 학과명과 같은 규칙(공백, 괄호, 붙임표, 끝말 학과·학부·전공 무시 후 같을 때만).
  대응되지 않는 data.json 학과는 그 학교의 별도 학과(match 없음)로 넣는다.
restricted: 전형명에 scripts/extract_ipgyeol.py 의 판정 규칙(말 목록과 사용자 결정 목록)을 그대로 적용한다.

data.json 필드 뜻(루트 index.html 코드가 쓰는 방식)
  학교: id, nm(학교명), sh(짧은 이름), rg(권역), loc(소재), ty(설립 구분), lat/lng, url(학교 홈페이지), cp(캠퍼스 이름), w(여대)
        tier(마커 크기·이름표 우선순위, 화면 배치용)와 cum9(성적 관리의 9등급 누적비율)는 이 화면에 필요 없어 넣지 않는다.
  학과: id, nm, f(계열 cs/sw/ai/ds/broad), rows(학종 전형별 행), gy(교과 입결 참고 {cut, y, s}), mt(전형 방식 {t, s}),
        xs(추가 출처 목록), note(학과 설명), sm(숙명여대 수학/컴퓨터 권장 과목 상자를 붙이는 표시)
  행:   t(전형명), cy(입결 학년도), cut(그 학년도 70% 컷), pc(2025학년도 입결), n(모집인원, cy 가 2024 면 2026 계획),
        comp(경쟁률)와 compY(그 학년도), add(추가합격)와 addY(그 학년도), sp(지원 자격이나 평가 방식이 다른 특별전형 표시),
        note(행 설명), s(출처 키)
"""
import io
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from extract_ipgyeol import is_restricted, norm_dept, exact_key, RESTRICT_OVERRIDE  # noqa: E402

DATA_JSON = os.path.join(ROOT, "data.json")
TARGETS = os.path.join(ROOT, "docs", "data", "targets.json")
MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
IPGYEOL = os.path.join(ROOT, "docs", "data", "ipgyeol.json")
OUT = os.path.join(ROOT, "docs", "data", "legacy_detail.json")
MAX_KM = 5.0
FIELD_NAME = {"cs": "컴퓨터", "sw": "소프트웨어", "ai": "인공지능", "ds": "데이터·AI", "broad": "광역 모집"}
PREP_SRC = ["snu28", "ys28", "va608317", "adiga"]   # 권장 과목 안내에 쓰는 출처(루트 화면 pSrc 와 같음)


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def nk(s):
    return re.sub(r"[\s()\[\]·\-]", "", s or "")


def core_name(adm):
    """전형명에서 앞의 '학생부종합', '[학생부종합]', '학종'과 끝의 '전형'을 떼고 띄어쓰기·괄호를 없앤 이름."""
    return re.sub(r"전형$", "", nk(re.sub(r"^\s*(\[?학생부종합\]?|학종)\s*", "", adm or "")))


def legacy_restricted(admission, marker):
    """ipgyeol 과 같은 규칙. 사용자 결정 목록은 전형 이름(앞의 학종 표기를 뗀 것)이 같은 data.json 전형에도 적용한다."""
    for (mk, adm), val in RESTRICT_OVERRIDE.items():
        if mk == marker and core_name(adm) and core_name(adm) == core_name(admission):
            return val
    return is_restricted(admission, marker)


def km(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(x))


def src_obj(SRC, key):
    s = SRC.get(key)
    if not s:
        return {"src": key, "src_title": None, "src_url": None, "src_desc": None}
    return {"src": key, "src_title": s.get("t"), "src_url": s.get("u"), "src_desc": s.get("d")}


def main():
    write = "--write" in sys.argv
    D = load(DATA_JSON)
    SRC = D["src"]
    markers = {m["campus"]: m for m in load(MARKERS)["markers"]}
    targets = [t["marker"] for t in load(TARGETS)["targets"]]
    ipg = load(IPGYEOL)

    schools = {}
    rep = {"matched": [], "target_no_data": [], "target_unmatched": [], "data_only": [], "dept": [], "warn": []}
    used_uni = {}
    used_src = set()
    for marker in targets:
        m = markers[marker]
        cands = [u for u in D["unis"] if nk(u["nm"]) == nk(m["univ"])]
        if not cands:
            rep["target_no_data"].append((marker, "data.json 에 같은 이름의 학교 없음"))
            continue
        near = [(u, km(m["lat"], m["lon"], u["lat"], u["lng"])) for u in cands]
        near = [(u, k) for u, k in near if k <= MAX_KM]
        if len(near) != 1:
            why = "이름이 같은 data.json 학교 %d개, 5km 안 %d개(%s)" % (
                len(cands), len(near), ", ".join("%s %.1fkm" % (u["id"], km(m["lat"], m["lon"], u["lat"], u["lng"])) for u in cands))
            rep["target_unmatched"].append((marker, why))
            continue
        u, dist = near[0]
        if u["id"] in used_uni:
            rep["target_unmatched"].append((marker, "data.json 학교 %s 가 이미 %s 에 대응됨" % (u["id"], used_uni[u["id"]])))
            continue
        used_uni[u["id"]] = marker
        rep["matched"].append((marker, u["id"], u["nm"], u.get("cp") or "-", round(dist, 2), len(u["ds"]), sum(len(d["rows"]) for d in u["ds"])))

        ipg_names = sorted({e["department"] for e in ipg.get(marker, []) if e.get("department")})
        by_norm = {}
        for n in ipg_names:
            by_norm.setdefault(norm_dept(n), []).append(n)
        taken = {}
        depts = []
        for d in u["ds"]:
            cs = by_norm.get(norm_dept(d["nm"]), [])
            match, how = None, "별도 학과"
            if len(cs) == 1:
                match, how = cs[0], "대응"
            elif len(cs) > 1:
                ex = [n for n in cs if exact_key(n) == exact_key(d["nm"])]
                if len(ex) == 1:
                    match, how = ex[0], "대응(이름 전체 일치)"
                else:
                    how = "애매(ipgyeol 학과 %d개: %s) -> 별도 학과" % (len(cs), " / ".join(cs))
            if match and match in taken:
                rep["warn"].append("%s: ipgyeol 학과 '%s' 에 data.json 학과가 둘 이상(%s, %s) -> 뒤의 것은 별도 학과" % (marker, match, taken[match], d["nm"]))
                match, how = None, "별도 학과(ipgyeol 학과 중복 대응)"
            if match:
                taken[match] = d["nm"]
            rep["dept"].append((marker, d["nm"], match or "-", how, len(d["rows"])))
            rows = []
            for r in d["rows"]:
                used_src.add(r["s"])
                row = {"admission": r["t"], "year": r["cy"], "cut70": r["cut"], "cut70_2025": r.get("pc"),
                       "recruit": r.get("n"), "recruit_basis": "2026 계획" if r["cy"] == 2024 else "2026",
                       "comp": r.get("comp"), "comp_year": r.get("compY"), "add": r.get("add"), "add_year": r.get("addY"),
                       "special": bool(r.get("sp")), "note": r.get("note"), "restricted": legacy_restricted(r["t"], marker)}
                row.update(src_obj(SRC, r["s"]))
                rows.append(row)
                if r.get("sp") and not row["restricted"]:
                    rep["warn"].append("%s %s '%s': 특별전형 표시(sp)가 있으나 restricted 규칙에는 안 걸림(false)" % (marker, d["nm"], r["t"]))
            ent = {"id": d["id"], "name": d["nm"], "field": d["f"], "field_name": FIELD_NAME.get(d["f"]),
                   "match": match, "match_note": how, "note": d.get("note"), "sm": bool(d.get("sm")), "rows": rows}
            if d.get("gy"):
                used_src.add(d["gy"]["s"])
                ent["gyo"] = dict({"cut": d["gy"]["cut"], "year": d["gy"]["y"]}, **src_obj(SRC, d["gy"]["s"]))
            if d.get("mt"):
                used_src.add(d["mt"]["s"])
                ent["method"] = dict({"text": d["mt"]["t"]}, **src_obj(SRC, d["mt"]["s"]))
            if d.get("xs"):
                for x in d["xs"]:
                    used_src.add(x)
                ent["extra_src"] = [src_obj(SRC, x) for x in d["xs"]]
            depts.append(ent)
        schools[marker] = {"legacy_id": u["id"], "name": u["nm"], "short": u.get("sh"), "campus_label": u.get("cp"),
                           "region": u.get("rg"), "loc": u.get("loc"), "type": u.get("ty"), "homepage": u.get("url"),
                           "women": bool(u.get("w")), "match": {"by": "이름과 좌표", "distance_km": round(dist, 2)}, "depts": depts}
    rep["data_only"] = [(u["id"], u["nm"], u.get("cp") or "-") for u in D["unis"] if u["id"] not in used_uni]
    for k in PREP_SRC:
        used_src.add(k)
    out = {"meta": {"built_from": "data.json", "asof": D.get("asof"), "generator": "scripts/build_legacy_detail.py",
                    "note": "처음 버전(루트 index.html)의 학과별 상세 자료. 입결은 에듀진 등 기사 표에서 옮긴 값이고 대학 원문이 아니다.",
                    "prep_src": PREP_SRC},
           "src": {k: SRC[k] for k in sorted(used_src) if k in SRC},
           "schools": schools}
    if write:
        with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print("학교 대응: 맞춤 %d, 대상인데 data.json 에 없음 %d, 대상인데 못 맞춤 %d, data.json 에만 있어 뺌 %d" % (
        len(rep["matched"]), len(rep["target_no_data"]), len(rep["target_unmatched"]), len(rep["data_only"])))
    print("\n[맞춘 학교] 마커 | data.json id | 이름 | 캠퍼스 | 거리 km | 학과 수 | 행 수")
    for r in rep["matched"]:
        print("  " + " | ".join(str(x) for x in r))
    print("\n[대상인데 못 맞춘 학교]")
    for r in rep["target_unmatched"]:
        print("  %s | %s" % r)
    print("\n[대상인데 data.json 에 없는 학교]")
    for r in rep["target_no_data"]:
        print("  %s | %s" % r)
    print("\n[data.json 에만 있어 뺀 학교]")
    for r in rep["data_only"]:
        print("  %s | %s | %s" % r)
    print("\n[학과 대응] 마커 | data.json 학과 | ipgyeol 학과 | 결과 | 행 수")
    for r in rep["dept"]:
        print("  " + " | ".join(str(x) for x in r))
    print("\n[경고]")
    for w in rep["warn"]:
        print("  " + w)
    print("\n쓴 파일: " + OUT if write else "\n(--write 없음: 파일을 쓰지 않음)")
    return out, rep


if __name__ == "__main__":
    main()
