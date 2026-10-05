# -*- coding: utf-8 -*-
"""#1005-36 작업 108·109: 사용자가 줄인 조사 대상 목록을 docs/data/markers.json 의 마커와 맞춰 target_univ.md, data/target_univ.json 을 만든다.

- 지도 마커와 기존 조사 기록은 바꾸지 않는다(읽기만 한다).
- 학교 이름이 마커와 하나로 맞지 않거나 IT 학과가 없는 마커는 자동으로 고르지 않고 "보고" 목록에 둔다.
- 그룹 A(지역거점국립대)는 KEDI 2026 고등교육통계의 본분교 값이 본교(제1캠퍼스)인 마커만 대상이고, 같은 학교의 다른 마커는 "다른 캠퍼스(대상 아님)"로 목록 끝에 적는다.
- 상태 값은 컷맵_입결위치조사_20260930_v8.md(1장 표, 7장 표), 2027_정시모집요강_URL_누적.md(조사 완료 대학 표), docs/data/academyinfo.json 에서 읽는다.
사용: python scripts/build_target_univ.py
"""
import io
import json
import os
import re
import sys
from collections import OrderedDict, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from add_address import find_xlsx, load_kedi  # noqa: E402

MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
V8 = os.path.join(ROOT, "컷맵_입결위치조사_20260930_v8.md")
JS = os.path.join(ROOT, "2027_정시모집요강_URL_누적.md")
ACAD = os.path.join(ROOT, "docs", "data", "academyinfo.json")
OUT_MD = os.path.join(ROOT, "target_univ.md")
OUT_JSON = os.path.join(ROOT, "data", "target_univ.json")
SPL = re.compile(r"(?<!\\)\|")

# (그룹, 목록에 적힌 이름, 마커 univ 값, 마커 고르는 규칙 이름)
# 규칙: None = 그 univ 의 마커가 정확히 하나여야 함, 문자열 = 규칙 함수 이름
TARGETS = [
    ("A", "강원대학교", "강원대학교", "A"), ("A", "경북대학교", "경북대학교", "A"), ("A", "경상국립대학교", "경상국립대학교", "A"),
    ("A", "부산대학교", "부산대학교", "A"), ("A", "전남대학교", "전남대학교", "A"), ("A", "전북대학교", "전북대학교", "A"),
    ("A", "제주대학교", "제주대학교", "A"), ("A", "충남대학교", "충남대학교", "A"), ("A", "충북대학교", "충북대학교", "A"),
    ("B", "포항공과대학교", "포항공과대학교", None), ("B", "한동대학교", "한동대학교", None),
    ("C", "경북대학교(그룹 A와 겹침)", "경북대학교", None), ("C", "계명대학교", "계명대학교", None), ("C", "대구경북과학기술원", "대구경북과학기술원", None),
    ("C", "영남대학교", "영남대학교", None), ("C", "대구대학교", "대구대학교", None), ("C", "대구가톨릭대학교", "대구가톨릭대학교", None), ("C", "대구한의대학교", "대구한의대학교", None),
    ("D", "서울대학교", "서울대학교", None), ("D", "연세대학교(서울)", "연세대학교", "서울"), ("D", "고려대학교(서울)", "고려대학교", None),
    ("D", "서강대학교", "서강대학교", None), ("D", "성균관대학교(수원)", "성균관대학교", "수원시"), ("D", "한양대학교(서울)", "한양대학교", None),
    ("D", "한양대학교(ERICA)", "한양대학교(ERICA)", None), ("D", "서울시립대학교", "서울시립대학교", None), ("D", "중앙대학교(서울)", "중앙대학교", "서울"),
    ("D", "경희대학교(국제캠퍼스)", "경희대학교", "기흥구"), ("D", "건국대학교(서울)", "건국대학교", None), ("D", "동국대학교(서울)", "동국대학교", None),
    ("D", "홍익대학교(서울)", "홍익대학교", "서울"), ("D", "국민대학교", "국민대학교", None), ("D", "숭실대학교", "숭실대학교", None),
    ("D", "세종대학교", "세종대학교", None), ("D", "광운대학교", "광운대학교", None), ("D", "서울과학기술대학교", "서울과학기술대학교", None),
    ("D", "가톨릭대학교(성심)", "가톨릭대학교", "부천시"),
    ("E", "상명대학교(서울)", "상명대학교", "서울"), ("E", "명지대학교", "명지대학교", "전체"), ("E", "한성대학교", "한성대학교", None),
    ("E", "삼육대학교", "삼육대학교", None), ("E", "서경대학교", "서경대학교", None), ("E", "한국외국어대학교(글로벌캠퍼스)", "한국외국어대학교", "용인시"),
]
GROUP_NAME = OrderedDict([("A", "지역거점국립대"), ("B", "포항"), ("C", "대구·경산"), ("D", "서울·수도권 대상"), ("E", "서울·수도권 보류")])
E_MEMO = "교과전형 IT 학과 70% 컷을 확인한 뒤 9등급제 4.0보다 나쁘면 대상에서 뺀다."


def cells(line):
    return [x.strip() for x in SPL.split(line.strip().strip("|"))]


def base(name):
    return re.sub(r"\s*\(.*$", "", name).strip()


def load_v8_rows():
    t = io.open(V8, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    sec = None
    rows = []
    plan = {}
    hold = {}
    for l in t:
        m = re.match(r"^#{2,3} (\d(?:-\d+)?)\.", l)
        if m:
            sec = m.group(1)
            continue
        if not l.startswith("|") or l.startswith("|---") or l.startswith("| 대학명") or l.startswith("| 대학 |"):
            continue
        c = cells(l)
        if sec and sec.startswith("1-"):
            status = c[-1] if sec in ("1-1", "1-2", "1-3", "1-4") else c[-1]
            rows.append(OrderedDict([("sec", sec), ("name", c[0]), ("col2", c[1]), ("status", status)]))
        elif sec == "7":
            plan[c[0]] = c[4]
        elif sec in ("3-1", "3-2"):
            hold[base(c[0])] = (sec, c[1])
    return rows, plan, hold


def classify(text):
    s = text.strip()
    s = re.sub(r"^\d{4}-\d{2}-\d{2}\s*/\s*", "", s)   # 앞의 확인일 표기
    for key, label in (("미확인", "미확인"), ("미공개", "미공개"), ("미조사", "미조사"), ("보류", "보류"), ("제외", "제외"), ("부분확인", "부분확인"), ("확인", "확인")):
        if s.startswith(key):
            return label
    return "기타"


def load_js():
    t = io.open(JS, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
    i0 = t.index("## 조사 완료 대학")
    j = i0 + 4
    rows = {}
    while t[j].startswith("|"):
        c = cells(t[j])
        if c[6] != "-":
            st = classify(c[6])
        else:
            v = c[2:5]
            st = "미조사" if all(x == "미조사" for x in v) else ("해당없음" if "해당없음" in v else ("미확인" if any("미확인" in x for x in v) else "확인"))
        rows[(c[0], c[1])] = (st, c[6][:60])
        j += 1
    return rows


def main():
    data = json.load(io.open(MARKERS, encoding="utf-8"))["markers"]
    acad = {m["campus"]: m for m in json.load(io.open(ACAD, encoding="utf-8"))["markers"]}
    kedi = [k for k in load_kedi(find_xlsx()) if not k["대학원구분"] and "대학원" not in k["학제"]]
    by_addr = defaultdict(list)
    for k in kedi:
        by_addr[k["주소"].strip()].append(k)
    v8rows, plan, hold = load_v8_rows()
    js = load_js()

    def kedi_kind(m):
        rs = [k for k in by_addr.get((m.get("address") or "").strip(), []) if k["학교명"] == m["univ"] or k["학교명"].startswith(base(m["univ"]))]
        kinds = sorted({k["본분교"] for k in rs})
        return kinds[0] if len(kinds) == 1 else ("KEDI 구분 불명(%s)" % ",".join(kinds) if kinds else "KEDI 행 없음")

    def v8_status(m, hint):
        b = base(m["univ"])
        cand = [r for r in v8rows if base(r["name"]) == b]
        if not cand:
            if b in hold:
                return "보류", "v8 %s장 %s: %s" % (hold[b][0], b, hold[b][1][:60]), hold[b][1]
            return "행 없음", "v8 1장·3장에 행 없음", None
        paren = re.search(r"\(([^()]*)", m["campus"])
        city = re.search(r"([가-힣]+)시", m.get("address") or "")
        specific = set()
        for t_ in (paren.group(1) if paren else "", city.group(1) if city else "", m["campus"], hint or ""):
            if t_ and not re.match(r"^(본교|분교)", t_):
                specific.add(t_)
        def hit(r, toks):
            return any(t_ and (t_ == r["col2"] or t_ in r["col2"] or t_ in r["name"]) for t_ in toks)
        if len(cand) == 1:
            pick = cand
        else:
            pick = [r for r in cand if hit(r, specific)]
            if len(pick) != 1:
                pick = [r for r in cand if hit(r, specific | {m["region"]})] if not pick else pick
        if len(pick) != 1:
            return None, "v8 행이 하나로 정해지지 않음(%s)" % " / ".join("%s %s|%s" % (r["sec"], r["name"], r["col2"]) for r in pick or cand), None
        r = pick[0]
        return classify(r["status"]), "%s %s | %s" % (r["sec"], r["name"], r["col2"]), r["status"]

    def js_status(m):
        v = js.get((m["univ"], m["campus"]))
        if v is None:
            return "행 없음", ""
        return v

    def plan_status(m):
        # v8 7장 표의 행 이름과 마커 이름이 같을 때만 읽는다
        for nm, st in plan.items():
            if nm == m["campus"] or nm == m["univ"] or nm.replace("학교", "대") == m["campus"]:
                pass
        keymap = {"고려대학교(서울)": "고려대학교(서울)", "충남대학교(대전)": "충남대학교", "전남대학교 (본교(제1캠퍼스))": "전남대학교", "한양대학교(에리카)": "한양대학교(ERICA)", "동아대학교(부산)": "동아대학교"}
        key = keymap.get(m["campus"])
        if key and key in plan:
            return classify(plan[key]) if not plan[key].startswith("서울 통합") else "부분확인", plan[key][:70]
        return "행 없음", ""

    out = []
    reports = []
    others = []
    used_markers = set()
    for grp, tname, univ, rule in TARGETS:
        cand = [m for m in data if m["univ"] == univ]
        if not cand:
            reports.append(OrderedDict([("group", grp), ("target", tname), ("reason", "지도 마커에 '%s' 마커가 없음" % univ)]))
            continue
        if rule == "A":
            tgt = []
            for m in cand:
                kk = kedi_kind(m)
                if kk == "본교(제1캠퍼스)":
                    tgt.append(m)
                else:
                    others.append(OrderedDict([("group", "A"), ("target", tname), ("marker", m["campus"]), ("kedi", kk), ("address", m.get("address"))]))
            if len(tgt) != 1:
                reports.append(OrderedDict([("group", grp), ("target", tname), ("reason", "KEDI 본교(제1캠퍼스) 마커가 하나로 정해지지 않음(%d개)" % len(tgt))]))
                continue
            picks = tgt
        elif rule is None:
            if len(cand) != 1:
                reports.append(OrderedDict([("group", grp), ("target", tname), ("reason", "마커가 하나로 정해지지 않음: " + " / ".join(m["campus"] for m in cand))]))
                continue
            picks = cand
        elif rule == "전체":
            picks = cand
        else:
            picks = [m for m in cand if (rule in (m.get("address") or "")) or (rule == "서울" and m["region"] == "서울")]
            if len(picks) != 1:
                reports.append(OrderedDict([("group", grp), ("target", tname), ("reason", "'%s' 조건에 맞는 마커가 하나로 정해지지 않음: %s" % (rule, " / ".join(m["campus"] for m in cand)))]))
                continue
        for m in picks:
            it = m["itStatus"]
            if it != "IT있음":
                reports.append(OrderedDict([("group", grp), ("target", tname), ("marker", m["campus"]), ("reason", "IT 학과 유무가 '%s'라 자동으로 넣지 않음(IT 학과명 %d개, 개설 중 0개, 폐지 %d개)" % (it, len(m.get("itDepts", [])), (m.get("itDeptCounts") or {}).get("closed", 0)))]))
                continue
            hint = re.search(r"\(([^()]*)\)$", tname)
            hint = re.sub("캠퍼스$", "", hint.group(1)) if hint and not hint.group(1).startswith("그룹") else ""
            st8, row8, raw8 = v8_status(m, hint)
            sj, rawj = js_status(m)
            sp, rawp = plan_status(m)
            a = acad.get(m["campus"], {})
            out.append(OrderedDict([
                ("group", grp), ("target", tname), ("marker", m["campus"]), ("univ", m["univ"]), ("region", m["region"]), ("address", m.get("address")),
                ("itStatus", it), ("ipgyeol", st8 or "행 확정 못함"), ("ipgyeolRow", row8), ("ipgyeolRaw", raw8),
                ("jeongsi2027", sj), ("jeongsiRaw", rawj), ("plan2028", sp), ("planRaw", rawp),
                ("tuition", "있음" if "tuitionUndergradAnnual" in a else "없음"), ("dorm", "있음" if "dormCapacityRate" in a else "없음"),
                ("kedi", kedi_kind(m))]))
    doc = OrderedDict([("note", ["scripts/build_target_univ.py 가 만든다. 마커와 기존 조사 기록은 바꾸지 않았다.",
                                 "상태는 v8(1장 입결 위치, 7장 시행계획), 2027 정시 요강 누적 파일(조사 완료 대학 표), docs/data/academyinfo.json 에서 읽었다."]),
                       ("groups", GROUP_NAME), ("groupE", E_MEMO), ("targets", out), ("otherCampus", others), ("reports", reports)])
    with io.open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")

    # ---------------- md
    def cnt(rows, key):
        c = OrderedDict()
        for r in rows:
            c[r[key]] = c.get(r[key], 0) + 1
        return ", ".join("%s %d" % (k, v) for k, v in c.items()) or "-"

    rv = ["# 조사 대상 목록 (target_univ.md)", "",
          "scripts/build_target_univ.py 가 data/target_univ.json 과 함께 만들었다. 지도 마커 306개와 기존 조사 기록은 그대로 두고, 앞으로의 입결·요구사항 조사만 이 목록으로 한정한다.",
          "상태는 컷맵_입결위치조사_20260930_v8.md(1장 입결 위치, 7장 시행계획), 2027_정시모집요강_URL_누적.md(조사 완료 대학 표), docs/data/academyinfo.json에서 읽었다.", "",
          "## 요약 (그룹별 상태 값 개수)", "",
          "| 그룹 | 대상 마커 수 | IT 학과 유무 | 입결 위치 상태 | 2027 정시 요강 상태 | 2028 시행계획 위치 상태 | 등록금 값 | 기숙사 값 |", "|---|---|---|---|---|---|---|---|"]
    for g, gn in GROUP_NAME.items():
        rows = [r for r in out if r["group"] == g]
        rv.append("| %s %s | %d | %s | %s | %s | %s | %s | %s |" % (g, gn, len(rows), cnt(rows, "itStatus"), cnt(rows, "ipgyeol"), cnt(rows, "jeongsi2027"), cnt(rows, "plan2028"), cnt(rows, "tuition"), cnt(rows, "dorm")))
    uniq = OrderedDict()
    for r in out:
        uniq[r["marker"]] = r
    rows = list(uniq.values())
    rv.append("| 전체(중복 제외) | %d | %s | %s | %s | %s | %s | %s |" % (len(rows), cnt(rows, "itStatus"), cnt(rows, "ipgyeol"), cnt(rows, "jeongsi2027"), cnt(rows, "plan2028"), cnt(rows, "tuition"), cnt(rows, "dorm")))
    rv += ["", "그룹 C의 경북대학교는 그룹 A와 같은 마커라 두 그룹에 모두 적었고, 전체 줄에서는 한 번만 센다.", ""]
    for g, gn in GROUP_NAME.items():
        rows = [r for r in out if r["group"] == g]
        rv += ["## 그룹 %s %s (%d)" % (g, gn, len(rows)), ""]
        if g == "E":
            rv += ["메모: " + E_MEMO, ""]
        if g == "A":
            rv += ["그룹 A는 KEDI 2026 고등교육통계에서 본분교 값이 본교(제1캠퍼스)인 마커만 대상이다. 같은 학교의 다른 마커는 목록 끝의 \"다른 캠퍼스(대상 아님)\"에 있다.", ""]
        rv += ["| 그룹 | 마커 이름 | IT 학과 유무 | 입결 위치 상태 | 2027 정시 요강 상태 | 2028 시행계획 위치 상태 | 등록금 값 유무 | 기숙사 값 유무 |", "|---|---|---|---|---|---|---|---|"]
        for r in rows:
            nm = r["marker"] + (" (그룹 A와 겹침)" if r["target"].endswith("겹침)") else "")
            rv.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (g, nm, r["itStatus"], r["ipgyeol"], r["jeongsi2027"], r["plan2028"], r["tuition"], r["dorm"]))
        rv.append("")
    rv += ["## 다른 캠퍼스(대상 아님)", "", "그룹 A 학교 중 KEDI 본분교 값이 본교(제1캠퍼스)가 아닌 마커다.", "", "| 그룹 | 마커 이름 | KEDI 본분교 값 | 주소 |", "|---|---|---|---|"]
    for o in others:
        rv.append("| %s | %s | %s | %s |" % (o["group"], o["marker"], o["kedi"], o["address"]))
    if not others:
        rv.append("| - | 없음 | - | - |")
    rv += ["", "## 보고 (자동으로 고르지 않음)", "", "학교 이름이 마커와 하나로 맞지 않거나 IT 학과가 없는 마커라 목록에 넣지 않았다.", "", "| 그룹 | 목록의 이름 | 마커 | 이유 |", "|---|---|---|---|"]
    for r in reports:
        rv.append("| %s | %s | %s | %s |" % (r["group"], r["target"], r.get("marker", "-"), r["reason"]))
    if not reports:
        rv.append("| - | 없음 | - | - |")
    rv += ["", "## 상태 원문 참고", "", "입결 위치 상태가 \"기타\"이거나 행을 고른 근거를 아래에 둔다(v8 표의 행 위치와 상태 원문 앞부분).", "", "| 마커 이름 | v8 행 | 입결 상태 원문 |", "|---|---|---|"]
    for r in out:
        if r["ipgyeol"] in ("기타", "행 확정 못함", "행 없음", "보류") or r["ipgyeolRow"] is None:
            rv.append("| %s | %s | %s |" % (r["marker"], r["ipgyeolRow"], (r["ipgyeolRaw"] or "")[:80].replace("|", "/")))
    rv.append("")
    with io.open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rv))
    print("대상 마커:", {g: len([r for r in out if r["group"] == g]) for g in GROUP_NAME}, "전체(중복 제외)", len(uniq))
    print("다른 캠퍼스:", len(others), "보고:", len(reports))
    for r in reports:
        print("보고:", r["group"], r["target"], r.get("marker", ""), r["reason"])
    for o in others:
        print("다른 캠퍼스:", o["marker"], o["kedi"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
