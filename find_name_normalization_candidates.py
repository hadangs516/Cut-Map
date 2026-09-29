# -*- coding: utf-8 -*-
"""세 파일에 등장하는 대학명 표기가 서로 다른 후보를 찾는다 (자동 병합 아님, 사람 검토용).

비교 대상:
  univ_major_dedup.json 의 schlNm
  univ_coords.json 의 대학이름
  경상남도교육청_대학정보_20250918.csv 의 대학이름 (CP949)

정규화: 한글/영문/숫자만 남기고 괄호·공백·특수문자를 제거하고 영문은 대문자로 맞춘다.
  예) "한양대학교(ERICA)" -> "한양대학교ERICA" / "한양대학교 ERICA" -> "한양대학교ERICA" (동일 -> 후보)
정규화 결과가 같아도 원본 표기가 완전히 같으면 후보에 넣지 않는다.
같은 정규화 그룹 안의 표기라도 전부 한 파일에서만 나왔으면(다른 파일과 겹치지 않으면) 후보에 넣지 않는다.

추가 규칙 2가지 (사람 검토용 후보 제시일 뿐, 자동 병합 아님):
1. 접미사 매칭: dedup의 캠퍼스명 없는 대학명(괄호 접미사가 없는 이름)을, 같은 이름 뒤에
   "(캠퍼스명)"이 붙은 coords/CSV 항목들과 연결한다. 어느 게 본교인지는 판단하지 않는다.
2. 별칭 매칭: ERICA-에리카, WISE-와이즈, GLOCAL-글로컬 고정 목록만 사용해
   영문 캠퍼스 표기와 한글 캠퍼스 표기를 연결한다. 이 목록에 없는 영문 캠퍼스 표기는
   unresolved 목록에 남기고 임의로 짝을 만들지 않는다.
"""
import csv
import io
import itertools
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEDUP_PATH = os.path.join(HERE, "univ_major_dedup.json")
COORDS_PATH = os.path.join(HERE, "univ_coords.json")
CSV_PATH = os.path.join(HERE, "경상남도교육청_대학정보_20250918.csv")
OUT = os.path.join(HERE, "name_normalization_candidates.json")

SRC_DEDUP = "univ_major_dedup.json"
SRC_COORDS = "univ_coords.json"
SRC_CSV = "경상남도교육청_대학정보_20250918.csv"

ALIAS_PAIRS = [("ERICA", "에리카"), ("WISE", "와이즈"), ("GLOCAL", "글로컬")]
SUFFIX_RE = re.compile(r"^(.+?)\(([^()]+)\)$")
ASCII_TOKEN_RE = re.compile(r"^[A-Za-z]+$")


def normalize(name):
    cleaned = re.sub(r"[^가-힣A-Za-z0-9]", "", name or "")
    return cleaned.upper()


def load_names():
    for path in (DEDUP_PATH, COORDS_PATH, CSV_PATH):
        if not os.path.exists(path):
            raise SystemExit("입력 파일 없음: %s" % path)

    with io.open(DEDUP_PATH, encoding="utf-8") as f:
        dedup = json.load(f)
    dedup_names = set(it.get("schlNm", "") for it in dedup["items"] if it.get("schlNm"))

    with io.open(COORDS_PATH, encoding="utf-8") as f:
        coords = json.load(f)
    coords_names = set(it.get("대학이름", "") for it in coords if it.get("대학이름"))

    with io.open(CSV_PATH, encoding="cp949", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    csv_names = set(r.get("대학이름", "") for r in rows if r.get("대학이름"))

    return {SRC_DEDUP: dedup_names, SRC_COORDS: coords_names, SRC_CSV: csv_names}


def find_suffix_match_candidates(name_sources):
    """dedup의 접미사 없는 대학명을, coords/CSV의 '대학명(캠퍼스)' 항목들과 연결한다."""
    non_source_targets = {SRC_COORDS, SRC_CSV}
    dedup_plain_names = [
        n for n, srcs in name_sources.items()
        if SRC_DEDUP in srcs and not n.endswith(")")
    ]
    groups = []
    for base in dedup_plain_names:
        matched = []
        for other, srcs in name_sources.items():
            if other == base:
                continue
            if not (srcs & non_source_targets):
                continue
            m = SUFFIX_RE.match(other)
            if m and m.group(1) == base:
                matched.append({"표기": other, "등장파일": sorted(srcs)})
        if matched:
            groups.append({
                "대학명": base,
                "대학명_등장파일": sorted(name_sources[base]),
                "매칭캠퍼스들": sorted(matched, key=lambda x: x["표기"]),
                "복수후보": len(matched) > 1,
                "규칙": "suffix_matching",
            })
    return groups


def find_alias_match_candidates(name_sources):
    """ERICA-에리카 등 고정 별칭 목록으로 영문/한글 캠퍼스 표기를 연결한다."""
    alias_to_kr = {en.upper(): kr for en, kr in ALIAS_PAIRS}

    candidates = []
    unresolved = []
    seen_pairs = set()

    for name, srcs in name_sources.items():
        m = SUFFIX_RE.match(name)
        if not m:
            continue
        base, token = m.group(1), m.group(2)
        if not ASCII_TOKEN_RE.match(token):
            continue  # 영문 토큰만 별칭 매칭 대상 (한글 캠퍼스명은 별개 대학으로 취급)

        token_upper = token.upper()
        if token_upper in alias_to_kr:
            kr_token = alias_to_kr[token_upper]
            counterpart = "%s(%s)" % (base, kr_token)
            if counterpart in name_sources and counterpart != name:
                pair_key = tuple(sorted([name, counterpart]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                candidates.append({
                    "표기1": name,
                    "표기1_등장파일": sorted(srcs),
                    "표기2": counterpart,
                    "표기2_등장파일": sorted(name_sources[counterpart]),
                    "별칭쌍": [token_upper, kr_token],
                    "규칙": "alias_matching",
                })
        else:
            unresolved.append({
                "이름": name,
                "등장파일": sorted(srcs),
                "미확인토큰": token,
                "사유": "영문 캠퍼스 표기이지만 고정 별칭 목록(ERICA/WISE/GLOCAL)에 없음",
            })

    return candidates, unresolved


def main():
    names_by_source = load_names()

    # 이름 -> 등장한 파일 집합
    name_sources = defaultdict(set)
    for src, names in names_by_source.items():
        for n in names:
            name_sources[n].add(src)

    # 정규화키 -> 원본 이름 집합
    norm_groups = defaultdict(set)
    for n in name_sources:
        norm_groups[normalize(n)].add(n)

    format_candidates = []
    for norm_key, names in norm_groups.items():
        if len(names) < 2:
            continue  # 표기가 하나뿐이면 후보가 아님 (완전히 동일한 이름만 있는 경우 포함)
        names = sorted(names)
        # 이 그룹 전체가 파일 하나에만 걸쳐 있으면(다른 파일과 안 겹치면) 대상에서 제외
        involved_sources = set()
        for n in names:
            involved_sources |= name_sources[n]
        if len(involved_sources) < 2:
            continue

        for a, b in itertools.combinations(names, 2):
            if len(set(name_sources[a]) | set(name_sources[b])) < 2:
                continue  # 이 쌍 자체는 같은 파일에만 있을 수 있으니 다시 확인
            format_candidates.append({
                "표기1": a,
                "표기1_등장파일": sorted(name_sources[a]),
                "표기2": b,
                "표기2_등장파일": sorted(name_sources[b]),
                "정규화결과": norm_key,
                "판단근거": "괄호/공백/특수문자 제거 후 동일 (%s)" % norm_key,
                "규칙": "format_normalization",
            })

    suffix_groups = find_suffix_match_candidates(name_sources)
    alias_candidates, unresolved = find_alias_match_candidates(name_sources)

    combo_counter = defaultdict(int)
    for c in format_candidates + alias_candidates:
        combo = tuple(sorted(set(c["표기1_등장파일"]) | set(c["표기2_등장파일"])))
        combo_counter[combo] += 1
    for g in suffix_groups:
        for m in g["매칭캠퍼스들"]:
            combo = tuple(sorted(set(g["대학명_등장파일"]) | set(m["등장파일"])))
            combo_counter[combo] += 1

    out = {
        "sources": {
            SRC_DEDUP: len(names_by_source[SRC_DEDUP]),
            SRC_COORDS: len(names_by_source[SRC_COORDS]),
            SRC_CSV: len(names_by_source[SRC_CSV]),
        },
        "normalizeRule": "한글/영문/숫자만 남기고 괄호·공백·특수문자 제거, 영문은 대문자로 통일",
        "aliasPairsUsed": [list(p) for p in ALIAS_PAIRS],
        "counts": {
            "formatNormalization": len(format_candidates),
            "suffixMatching": len(suffix_groups),
            "aliasMatching": len(alias_candidates),
            "unresolvedAlias": len(unresolved),
        },
        "fileComboCounts": {"+".join(k): v for k, v in combo_counter.items()},
        "candidates": format_candidates,
        "suffixMatchCandidates": suffix_groups,
        "aliasMatchCandidates": alias_candidates,
        "unresolvedAliasCandidates": unresolved,
    }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("포맷 정규화(괄호/공백/특수문자) 후보: %d건" % len(format_candidates))
    lines.append("접미사 매칭 후보 그룹: %d건 (그중 복수후보 %d건)" % (
        len(suffix_groups), sum(1 for g in suffix_groups if g["복수후보"])))
    lines.append("별칭 매칭 후보: %d건" % len(alias_candidates))
    lines.append("미해결(alias 목록에 없는 영문 캠퍼스 표기): %d건" % len(unresolved))
    lines.append("")
    lines.append("파일 조합별 건수:")
    for combo, cnt in sorted(combo_counter.items(), key=lambda x: -x[1]):
        lines.append("  %s: %d건" % (" + ".join(combo), cnt))
    lines.append("")
    lines.append("접미사 매칭 상세:")
    for g in suffix_groups:
        campuses = ", ".join(m["표기"] for m in g["매칭캠퍼스들"])
        lines.append(" - %s -> [%s]%s" % (g["대학명"], campuses, " (복수후보)" if g["복수후보"] else ""))
    lines.append("")
    lines.append("별칭 매칭 상세:")
    for c in alias_candidates:
        lines.append(" - %s <-> %s (%s)" % (c["표기1"], c["표기2"], "/".join(c["별칭쌍"])))
    lines.append("")
    lines.append("미해결 목록:")
    for u in unresolved:
        lines.append(" - %s (토큰=%s, 파일=%s)" % (u["이름"], u["미확인토큰"], ",".join(u["등장파일"])))

    with io.open(os.path.join(HERE, "normalize_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
