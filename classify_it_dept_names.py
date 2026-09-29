# -*- coding: utf-8 -*-
"""univ_major_dedup.json의 학과명(scsbjtNm)을 IT 계열 키워드로 분류.

IT 여부를 자동 확정하지 않는다. 사람이 검토할 후보 목록만 만든다.
학과명에 track 값을 써넣지 않는다.
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "univ_major_dedup.json")
OUT = os.path.join(HERE, "it_track_candidates.json")

KEYWORDS = ["컴퓨터", "소프트웨어", "AI", "인공지능", "데이터", "정보보호", "정보보안", "정보통신", "전자", "전기"]

# 위 10개 키워드에는 안 걸리지만 이름만 보면 IT와 관련 있어 보이는 학과를 걸러내기 위한 힌트.
# 확정 기준이 아니라 후보를 넓게 잡기 위한 것이며, 사람이 다시 검토해야 한다.
IT_HINT_KEYWORDS = [
    "IT", "네트워크", "모바일", "임베디드", "사물인터넷", "IoT", "빅데이터",
    "로봇", "게임", "정보시스템", "정보공학", "웹", "지능형", "스마트",
]
# "IT"/"IoT"는 대소문자 구분 없이 부분일치시키면 Digital, Hospitality, Politics처럼
# 영단어 속에 우연히 들어간 it까지 잡힌다. 이 둘만 앞뒤가 영문자가 아닐 때만(토큰 경계) 매칭한다.
ASCII_TOKEN_HINTS = {"IT", "IoT"}
TEXT_HINT_KEYWORDS = [h for h in IT_HINT_KEYWORDS if h not in ASCII_TOKEN_HINTS]


def name_has_hint(name):
    if any(hint in name for hint in TEXT_HINT_KEYWORDS):
        return True
    for tok in ASCII_TOKEN_HINTS:
        if re.search(r"(?<![A-Za-z])" + re.escape(tok) + r"(?![A-Za-z])", name, re.IGNORECASE):
            return True
    return False


def main():
    if not os.path.exists(SRC):
        raise SystemExit("입력 파일 없음: %s" % SRC)

    with io.open(SRC, encoding="utf-8") as f:
        data = json.load(f)

    names = sorted(set(it.get("scsbjtNm", "") for it in data["items"] if it.get("scsbjtNm")))

    groups = {kw: [] for kw in KEYWORDS}
    matched_any = set()
    for name in names:
        for kw in KEYWORDS:
            if kw.lower() in name.lower():
                groups[kw].append(name)
                matched_any.add(name)

    unclassified = []
    for name in names:
        if name in matched_any:
            continue
        if name_has_hint(name):
            unclassified.append(name)

    out = {
        "source": "univ_major_dedup.json",
        "totalUniqueDeptNames": len(names),
        "keywordsUsed": KEYWORDS,
        "itHintKeywordsUsed": IT_HINT_KEYWORDS,
        "groups": {
            kw: {"count": len(v), "names": v} for kw, v in groups.items()
        },
        "unclassifiedItCandidates": {
            "count": len(unclassified),
            "names": unclassified,
            "note": "위 10개 키워드에는 안 걸렸지만 IT_HINT_KEYWORDS로 걸러낸 후보. IT 여부 확정 아님, 사람 검토 필요.",
        },
    }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("고유 학과명 수: %d" % len(names))
    for kw in KEYWORDS:
        lines.append("  %s: %d건" % (kw, len(groups[kw])))
    lines.append("미분류 IT 후보: %d건" % len(unclassified))
    with io.open(os.path.join(HERE, "classify_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
