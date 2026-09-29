# -*- coding: utf-8 -*-
"""작업 9 (읽기 전용, 초안): 학과명 IT 분류 초안.
입력: it_track_candidates.json, univ_major_dedup.json (+ 참고: final_include_list.json, final_exclude_list.json)
출력: it_classification_draft_20260924.json, it_classification_draft_20260924.md
이 초안은 확정이 아니며 master list, 마커, 삭제 작업에 쓰지 않는다.
"""
import io
import json
import os
import re
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)

AUTO = ["AI", "컴퓨터", "소프트웨어"]                       # SPEC 1: 이름에 있으면 성격과 관계없이 포함
CORE = ["인공지능", "데이터", "정보보안", "정보보호", "정보통신", "전자", "전기"]   # SPEC 1: IT·ICT 인접 키워드
HINT = ["IT", "ICT", "SW", "네트워크", "모바일", "임베디드", "사물인터넷", "IoT", "로봇", "게임", "정보시스템", "정보공학",
        "웹", "지능형", "스마트", "반도체", "디지털", "사이버", "보안", "통신", "메타버스", "드론", "클라우드", "블록체인",
        "정보", "미디어", "자동화", "메카트로닉스"]
# CORE 키워드가 있어도 이름만으로는 IT 여부가 갈리는 표현 -> 경계
AMBIG = [("전자상거래", "전자"), ("전자무역", "전자"), ("전자출판", "전자"), ("전기차", "전기"), ("전기자동차", "전기"),
         ("전기설비", "전기"), ("전기소방", "전기"), ("소방·전기", "전기"), ("전기·소방", "전기"), ("전기에너지", "전기"),
         ("전기철도", "전기"), ("철도전기", "전기"), ("데이터경영", "데이터"), ("데이터마케팅", "데이터")]
ACTIVE = {"기존", "신설", "변경"}
RULES = [
    "1. 자동포함: 학과명에 %s 중 하나가 들어가면 학과 성격과 관계없이 포함 (SPEC 1번 5·6번째 줄). "
    "AI는 영문 단어 안에 끼어 있지 않은 대문자 'AI'만 인정" % ", ".join(AUTO),
    "2. 키워드포함: 1에 해당하지 않고 %s 중 하나가 들어가면 포함 (SPEC 1번 3·4번째 줄: 데이터·정보보안·정보통신·전자전기 등)" % ", ".join(CORE),
    "3. 경계: (a) 2의 키워드가 있어도 %s 처럼 이름만으로 IT 여부가 갈리는 표현이 있는 학과, "
    "(b) 1·2의 키워드는 없고 IT 힌트 키워드(%s)가 있는 학과, (c) it_track_candidates.json의 미분류 IT 후보(unclassifiedItCandidates)" % (
        ", ".join(sorted(set(a for a, _ in AMBIG))), ", ".join(HINT)),
    "4. 해당없음: 위 키워드가 하나도 없는 학과 (univ_major_dedup.json 학과명 중 나머지)",
    "5. 규칙 적용 순서는 1 → 2(→3a) → 3b·3c → 4. 한 학과명은 한 분류에만 들어감",
    "6. 참고 표시: final_include_list.json(확정 포함), final_exclude_list.json(확정 제외)에 있는 학과명은 existingDecision에 적음. "
    "분류에는 쓰지 않고 충돌만 표시",
    "7. 학과 상태: univ_major_dedup.json의 학과상태(scsbjtSttsNm) 행 수와, 기존·신설·변경이 하나라도 있으면 active=true",
]


def flat(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from flat(v)
    elif isinstance(o, list):
        for v in o:
            yield from flat(v)
    elif isinstance(o, str):
        yield o


def has_ai(name):
    return re.search(r"(?<![A-Za-z])AI(?![A-Za-z])", name) is not None


def classify(name, unclassified):
    auto = [k for k in AUTO if (has_ai(name) if k == "AI" else k in name)]
    if auto:
        return "자동포함", "1", auto
    core = [k for k in CORE if k in name]
    if core:
        amb = [a for a, k in AMBIG if a in name and k in core]
        if amb:
            return "경계", "3a", core + ["모호:" + a for a in amb]
        return "키워드포함", "2", core
    hint = [k for k in HINT if k in name]
    if hint:
        return "경계", "3b", hint
    if name in unclassified:
        return "경계", "3c", ["미분류IT후보"]
    return "해당없음", "4", []


def main():
    cand = json.load(io.open(P("it_track_candidates.json"), encoding="utf-8"))
    dedup = json.load(io.open(P("univ_major_dedup.json"), encoding="utf-8"))["items"]
    inc = set(flat(json.load(io.open(P("final_include_list.json"), encoding="utf-8"))))
    exc = set(flat(json.load(io.open(P("final_exclude_list.json"), encoding="utf-8"))))
    unclassified = set(cand["unclassifiedItCandidates"]["names"])
    grouped = set(n for g in cand["groups"].values() for n in g["names"])

    st = defaultdict(Counter)
    schools = defaultdict(set)
    for r in dedup:
        st[r["scsbjtNm"]][r["scsbjtSttsNm"]] += 1
        schools[r["scsbjtNm"]].add(r["schlNm"])
    names = sorted(set(st) | grouped | unclassified)

    items = []
    for n in names:
        cat, rule, matched = classify(n, unclassified)
        ed = "include" if n in inc else "exclude" if n in exc else None
        items.append({"name": n, "category": cat, "rule": rule, "matched": matched,
                      "statuses": dict(st.get(n, {})), "active": bool(set(st.get(n, {})) & ACTIVE),
                      "schools": len(schools.get(n, ())), "existingDecision": ed,
                      "inCandidates": "group" if n in grouped else "unclassified" if n in unclassified else None})
    cnt = Counter(i["category"] for i in items)
    rule_cnt = Counter(i["rule"] for i in items)
    conflicts = [i for i in items if (i["category"] in ("자동포함", "키워드포함") and i["existingDecision"] == "exclude")
                 or (i["category"] == "해당없음" and i["existingDecision"] == "include")]
    ai_in_word = sorted(n for n in names if "AI" in n and not has_ai(n))

    out = {"rules": RULES,
           "keywords": {"자동포함": AUTO, "키워드포함": CORE, "경계_모호표현": [a for a, _ in AMBIG], "경계_힌트": HINT},
           "note": "초안. 확정이 아니며 master list, 마커, 삭제 작업에 쓰지 않는다. 2차 단계 IT 판정 준비용",
           "sources": ["it_track_candidates.json", "univ_major_dedup.json (학과명·학과상태)",
                       "final_include_list.json / final_exclude_list.json (참고 표시만)"],
           "created": "2026-09-28", "counts": dict(cnt), "ruleCounts": dict(rule_cnt),
           "items": items}
    with io.open(P("it_classification_draft_20260924.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    def active_split(cat):
        xs = [i for i in items if i["category"] == cat]
        return len(xs), sum(1 for i in xs if i["active"]), sum(1 for i in xs if i["statuses"] and not i["active"]), \
            sum(1 for i in xs if not i["statuses"])

    L = ["# IT 판정 분류 초안 (작업 9, 초안)", "",
         "> 이 초안은 확정이 아니며 master list, 마커, 삭제 작업에 쓰지 않는다. 전체 목록은 `it_classification_draft_20260924.json`.", "",
         "## 분류 규칙", ""] + ["- " + r for r in RULES] + [
         "", "## 키워드 목록", "",
         "- 자동포함: " + ", ".join(AUTO),
         "- 키워드포함: " + ", ".join(CORE),
         "- 경계(모호 표현): " + ", ".join(a for a, _ in AMBIG),
         "- 경계(IT 힌트): " + ", ".join(HINT), "",
         "## 분류 결과 (학과명 %d개)" % len(items), "",
         "| 분류 | 학과명 수 | 모집 중(기존·신설·변경 있음) | 폐지만 | 상태 정보 없음 |", "|---|---|---|---|---|"]
    for cat in ("자동포함", "키워드포함", "경계", "해당없음"):
        L.append("| %s | %d | %d | %d | %d |" % ((cat,) + active_split(cat)))
    ed_cnt = Counter((i["category"], i["existingDecision"] or "-") for i in items)
    L += ["", "규칙별: " + ", ".join("%s=%d" % kv for kv in sorted(rule_cnt.items())), "",
          "기존 확정 목록 표시(분류별): " + ", ".join("%s/%s=%d" % (c, e, n) for (c, e), n in sorted(ed_cnt.items()) if e != "-"), "",
          "## 기존 확정 목록과 충돌 (%d)" % len(conflicts), "",
          "자동포함·키워드포함인데 final_exclude_list에 있거나, 해당없음인데 final_include_list에 있는 학과명.", "",
          "| 학과명 | 초안 분류 | 기존 결정 | 매칭 키워드 | 모집 중 |", "|---|---|---|---|---|"]
    L += ["| %s | %s | %s | %s | %s |" % (i["name"], i["category"], i["existingDecision"], ", ".join(i["matched"]) or "-",
                                         "예" if i["active"] else "아니오") for i in conflicts]
    L += ["", "## 'AI'가 영문 단어 안에만 있어 자동포함에서 뺀 학과명 (%d)" % len(ai_in_word), ""]
    L += ["- " + n for n in ai_in_word] or ["- 없음"]
    L += ["", "## 경계 학과명 (모집 중인 것만, 규칙별 앞 30개)", ""]
    for rule, title in (("3a", "3a. 키워드 있으나 모호 표현"), ("3b", "3b. IT 힌트 키워드만"), ("3c", "3c. 미분류 IT 후보")):
        xs = sorted((i for i in items if i["rule"] == rule and i["active"]), key=lambda i: -i["schools"])
        L += ["### %s (모집 중 %d)" % (title, len(xs)), ""]
        L += ["- %s (%s, %d개교)" % (i["name"], ", ".join(i["matched"]), i["schools"]) for i in xs[:30]]
        L.append("")
    with io.open(P("it_classification_draft_20260924.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")
    print(dict(cnt), dict(rule_cnt), "conflicts", len(conflicts), "ai_in_word", len(ai_in_word))
    for cat in ("자동포함", "키워드포함", "경계", "해당없음"):
        print(cat, active_split(cat))


if __name__ == "__main__":
    main()
