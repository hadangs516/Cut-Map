# -*- coding: utf-8 -*-
"""IT 계열 학과를 가진 대학의 마스터 목록을 만든다 (권역별 그룹핑).

IT 계열 판정 기준: it_track_candidates.json의 키워드 그룹 매칭 결과만 사용한다.
미분류 후보(1,187건)는 대학이 이미 포함된 경우에 한해 참고용으로 별도 표시하며,
그 자체로 대학을 목록에 넣거나 빼는 근거로 쓰지 않는다.

캠퍼스 연결: dedup의 대학명(schlNm)을 univ_coords.json의 대학이름과 연결한다.
  1. 완전히 같은 문자열이면 그대로 사용.
  2. dedup 이름에 괄호 캠퍼스 표기가 있고 name_normalization_candidates.json의
     별칭 매칭(ERICA/WISE/GLOCAL)에 있으면 그 대응 이름을 사용.
  3. dedup 이름이 캠퍼스 표기 없는 이름이면 접미사 매칭 결과를 본다.
     후보가 정확히 1개면 그것을 쓰고, 0개거나 2개 이상이면(어느 캠퍼스인지 자동으로
     판단하지 않으므로) 연결하지 않는다.
연결이 안 되면 "좌표미확보"로 표시하고 좌표를 추정하지 않는다.

권역 판정 (2단계):
  1차: 주소 맨 앞의 잔여 우편번호(예: [51767])를 제거한 뒤, 첫 토큰이 광역시도명이면 그걸로 판정.
  2차: 1차가 실패하면 첫 토큰이 시군구명인 경우 시군구->광역시도 매핑 테이블로 판정.
       두 도에 동시에 있는 시군구명(예: 고성군)은 중의적이라 판정하지 않는다.
  둘 다 실패하면 "미확인"으로 남기고 임의로 추정하지 않는다.

학부 조사 대상 필터링:
  대학명에 "대학원"이 있으면 grad_only, "사이버대학교"/"사이버대"가 있으면 cyber로 분리한다.
  그 외에는 dedup의 학위과정명(degCrseCrsNm) 집합을 본다. "학사"가 하나도 없고
  "전문학사"만 있으면 college로 분리한다. 학사도 전문학사도 전혀 없으면(대학원 수준
  프로그램만 있는 경우) grad_only로 취급한다.
  세 카테고리는 삭제하지 않고 별도 섹션으로 남기며, 최종 권역별 집계에서는 제외한다.

권역 판정 우선순위 (ctpvNm 전면 재판정):
  가톨릭대 재확인 작업에서 dedup 각 행에 ctpvNm(시도명)/sggNm(시군구명)이 실제로
  들어있음을 확인했다. 이제 이 필드를 권역 판정의 1차 기준으로 쓴다.
  대학별로 "IT 계열로 분류된 학과들"의 ctpvNm만 모아서 그 대학의 IT 프로그램이
  실제로 어느 지역에 있는지 본다 (전체 학과 기준이 아니라 IT 학과 기준).
    - ctpvNm이 가리키는 권역이 하나면 그 권역으로 확정한다.
    - 여러 권역에 걸쳐 있으면 자동으로 합치지 않고 권역별로 별도 행(entry)으로 분리한다.
    - ctpvNm 값 자체가 없거나 비어있는 학과만 기존 주소 파싱 방식(캠퍼스 좌표 기반)을
      보조로 사용한다. (실제로는 모든 행에 ctpvNm이 채워져 있어 거의 발생하지 않는다.)
  캠퍼스 좌표(연결캠퍼스명/위도/경도)는 참고용으로 계속 유지하지만, 그 캠퍼스의 주소가
  가리키는 권역과 ctpvNm 기준 권역이 다르면(예: 가톨릭대학교 - 연결된 좌표는 서울 캠퍼스지만
  IT 학과는 경기도 부천시 소속) "권역출처불일치" 플래그와 비고를 남기고 ctpvNm 쪽을 최종
  권역으로 채택한다.
"""
import io
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEDUP_PATH = os.path.join(HERE, "univ_major_dedup.json")
IT_PATH = os.path.join(HERE, "it_track_candidates.json")
NORM_PATH = os.path.join(HERE, "name_normalization_candidates.json")
COORDS_PATH = os.path.join(HERE, "univ_coords.json")
OUT = os.path.join(HERE, "university_master_list.json")

REGIONS = ["서울", "경기", "인천", "강원", "충청", "호남", "영남", "제주"]
UNKNOWN_REGION = "미확인"

SIDO_ALIASES = {
    "서울특별시": "서울", "서울시": "서울", "서울": "서울",
    "인천광역시": "인천", "인천시": "인천", "인천": "인천",
    "경기도": "경기", "경기": "경기",
    "강원특별자치도": "강원", "강원도": "강원", "강원": "강원",
    "대전광역시": "충청", "대전시": "충청", "대전": "충청",
    "세종특별자치시": "충청", "세종시": "충청", "세종": "충청",
    "충청남도": "충청", "충남": "충청",
    "충청북도": "충청", "충북": "충청",
    "광주광역시": "호남", "광주시": "호남", "광주": "호남",
    "전라남도": "호남", "전남": "호남",
    "전북특별자치도": "호남", "전라북도": "호남", "전북": "호남",
    "부산광역시": "영남", "부산시": "영남", "부산": "영남",
    "대구광역시": "영남", "대구시": "영남", "대구": "영남",
    "울산광역시": "영남", "울산시": "영남", "울산": "영남",
    "경상남도": "영남", "경남": "영남",
    "경상북도": "영남", "경북": "영남",
    "제주특별자치도": "제주", "제주도": "제주", "제주시": "제주", "제주": "제주",
}

# 시군구명 -> 권역 (2차 매핑). 광역시도 접두어 없이 시/군 이름만 적힌 주소 대응.
# 구(區) 이름은 도시마다 겹쳐서(중구, 서구 등) 뺐다 - 도시 맥락 없이는 판정 불가.
_GANGWON = ["춘천시", "원주시", "강릉시", "동해시", "태백시", "속초시", "삼척시",
            "홍천군", "횡성군", "영월군", "평창군", "정선군", "철원군", "화천군",
            "양구군", "인제군", "양양군"]
_GYEONGGI = ["수원시", "성남시", "의정부시", "안양시", "부천시", "광명시", "평택시",
             "동두천시", "안산시", "고양시", "과천시", "구리시", "남양주시", "오산시",
             "시흥시", "군포시", "의왕시", "하남시", "용인시", "파주시", "이천시",
             "안성시", "김포시", "화성시", "양주시", "포천시", "여주시", "연천군",
             "가평군", "양평군"]
_CHUNGBUK = ["청주시", "충주시", "제천시", "보은군", "옥천군", "영동군", "증평군",
             "진천군", "괴산군", "음성군", "단양군"]
_CHUNGNAM = ["천안시", "공주시", "보령시", "아산시", "서산시", "논산시", "계룡시",
             "당진시", "금산군", "부여군", "서천군", "청양군", "홍성군", "예산군", "태안군"]
_JEONBUK = ["전주시", "군산시", "익산시", "정읍시", "남원시", "김제시", "완주군",
            "진안군", "무주군", "장수군", "임실군", "순창군", "고창군", "부안군"]
_JEONNAM = ["목포시", "여수시", "순천시", "나주시", "광양시", "담양군", "곡성군",
            "구례군", "고흥군", "보성군", "화순군", "장흥군", "강진군", "해남군",
            "영암군", "무안군", "함평군", "영광군", "장성군", "완도군", "진도군", "신안군"]
_GYEONGBUK = ["포항시", "경주시", "김천시", "안동시", "구미시", "영주시", "영천시",
              "상주시", "문경시", "경산시", "군위군", "의성군", "청송군", "영양군",
              "영덕군", "청도군", "고령군", "성주군", "칠곡군", "예천군", "봉화군",
              "울진군", "울릉군"]
_GYEONGNAM = ["창원시", "진주시", "통영시", "사천시", "김해시", "밀양시", "거제시",
              "양산시", "의령군", "함안군", "창녕군", "남해군", "하동군", "산청군",
              "함양군", "거창군", "합천군"]
_JEJU = ["제주시", "서귀포시"]

SGG_TO_REGION = {}
for names, region in [
    (_GANGWON, "강원"), (_GYEONGGI, "경기"), (_CHUNGBUK, "충청"), (_CHUNGNAM, "충청"),
    (_JEONBUK, "호남"), (_JEONNAM, "호남"), (_GYEONGBUK, "영남"), (_GYEONGNAM, "영남"),
    (_JEJU, "제주"),
]:
    for n in names:
        SGG_TO_REGION[n] = region

# 강원도와 경상남도에 동시에 있는 시군구명 - 중의적이라 매핑에서 뺀다.
AMBIGUOUS_SGG = {"고성군"}
for name in AMBIGUOUS_SGG:
    SGG_TO_REGION.pop(name, None)

LEADING_ZIP_RE = re.compile(
    r"^\s*[\(\[]?\s*(?:우\)?\s*)?[\(\[]?\s*(\d{3}-\d{3}|\d{5,6}|\d{3})\s*[\)\]]?\s*"
)

GRAD_ONLY_MARKERS = ["대학원"]
CYBER_MARKERS = ["사이버대학교", "사이버대"]


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def strip_leading_zip(address):
    m = LEADING_ZIP_RE.match(address)
    if m:
        return address[m.end():].strip()
    return address


def region_of(address):
    if not address:
        return UNKNOWN_REGION, "주소 없음"

    cleaned = strip_leading_zip(address)
    tokens = cleaned.strip().split()
    token = tokens[0] if tokens else ""

    region = SIDO_ALIASES.get(token)
    if region:
        basis = "1차: 시도명 인식(%s)" % token
        if cleaned != address:
            basis += " [우편번호 제거 후]"
        return region, basis

    if token in AMBIGUOUS_SGG:
        return UNKNOWN_REGION, "2차 매핑 중의적 (%s는 강원/경남에 동시 존재)" % token

    region = SGG_TO_REGION.get(token)
    if region:
        return region, "2차: 시군구 매핑(%s -> %s)" % (token, region)

    return UNKNOWN_REGION, "시도/시군구명 인식 불가 (첫 토큰=%r)" % token


def campus_token_of(name):
    m = re.match(r"^.+\(([^()]+)\)$", name)
    return m.group(1) if m else None


def classify_track(schl_name, deg_set):
    if any(marker in schl_name for marker in GRAD_ONLY_MARKERS):
        return "grad_only"
    if any(marker in schl_name for marker in CYBER_MARKERS):
        return "cyber"
    has_bachelor = "학사" in deg_set
    has_college = "전문학사" in deg_set
    if has_bachelor:
        return "undergrad"
    if has_college:
        return "college"
    return "grad_only"  # 학사/전문학사가 전혀 없음 -> 학부 조사 대상 아님


PREVIOUS_AMBIGUOUS_13 = [
    "고려대학교", "중앙대학교", "경기대학교", "연세대학교", "을지대학교", "전남대학교",
    "건국대학교", "홍익대학교", "상명대학교", "동국대학교", "명지대학교",
    "한국외국어대학교", "한양대학교",
]


def resolve_region_by_ctpv(schl, it_depts, dept_ctpv):
    dept_regions = {}
    all_regions = set()
    for dept in it_depts:
        ctpvs = dept_ctpv.get((schl, dept), set())
        regions = set(SIDO_ALIASES.get(c) for c in ctpvs if c)
        regions.discard(None)
        if regions:
            dept_regions[dept] = regions
            all_regions |= regions
    if not all_regions:
        return None
    if len(all_regions) == 1:
        return {"mode": "single", "region": next(iter(all_regions))}
    by_region = defaultdict(set)
    for dept, regs in dept_regions.items():
        for r in regs:
            by_region[r].add(dept)
    return {"mode": "split", "byRegion": {r: sorted(ds) for r, ds in by_region.items()}}


def main():
    dedup = load_json(DEDUP_PATH)
    it_data = load_json(IT_PATH)
    norm_data = load_json(NORM_PATH)
    coords = load_json(COORDS_PATH)

    it_names = set()
    for g in it_data["groups"].values():
        it_names.update(g["names"])
    unclassified_names = set(it_data["unclassifiedItCandidates"]["names"])

    coords_by_name = {}
    for c in coords:
        coords_by_name.setdefault(c["대학이름"], c)

    suffix_map = {}
    for g in norm_data["suffixMatchCandidates"]:
        suffix_map[g["대학명"]] = [m["표기"] for m in g["매칭캠퍼스들"]]

    alias_map = {}
    for c in norm_data["aliasMatchCandidates"]:
        alias_map[c["표기1"]] = c["표기2"]
        alias_map[c["표기2"]] = c["표기1"]

    uni_depts = defaultdict(set)
    uni_degrees = defaultdict(set)
    dept_ctpv = defaultdict(set)
    for it in dedup["items"]:
        schl = it.get("schlNm", "")
        dept = it.get("scsbjtNm", "")
        if schl and dept:
            uni_depts[schl].add(dept)
            ctpv = it.get("ctpvNm", "")
            if ctpv:
                dept_ctpv[(schl, dept)].add(ctpv)
        if schl:
            uni_degrees[schl].add(it.get("degCrseCrsNm", ""))

    entries = []
    newly_resolved_total = []
    resolved_among_13 = []
    split_universities = []
    catholic_note = None

    for schl, depts in uni_depts.items():
        it_depts = sorted(d for d in depts if d in it_names)
        if not it_depts:
            continue
        unclassified_depts = sorted(d for d in depts if d in unclassified_names)
        track = classify_track(schl, uni_degrees[schl])

        # 캠퍼스 좌표 연결 (참고용) - 이전과 동일한 방식
        campus_token = campus_token_of(schl)
        coords_name = None
        match_type = None
        suffix_candidates = None
        if schl in coords_by_name:
            coords_name, match_type = schl, "exact"
        elif schl in alias_map and alias_map[schl] in coords_by_name:
            coords_name, match_type = alias_map[schl], "alias"
        elif campus_token is None and schl in suffix_map:
            cands = suffix_map[schl]
            if len(cands) == 1:
                coords_name, match_type = cands[0], "suffix_single"
            else:
                suffix_candidates = cands

        campus_info = {"연결캠퍼스명": None, "매칭방식": None, "좌표미확보": True,
                        "위도": None, "경도": None, "주소": None,
                        "복수캠퍼스후보": suffix_candidates}
        addr_region, addr_basis = UNKNOWN_REGION, "캠퍼스 연결 안 됨"
        if coords_name and coords_name in coords_by_name:
            c = coords_by_name[coords_name]
            addr_region, addr_basis = region_of(c.get("주소", ""))
            campus_info.update({
                "연결캠퍼스명": coords_name, "매칭방식": match_type, "좌표미확보": False,
                "위도": c.get("위도"), "경도": c.get("경도"), "주소": c.get("주소"),
            })

        # ctpvNm 기준 1차 판정 (IT 계열 학과만)
        ctpv_result = resolve_region_by_ctpv(schl, it_depts, dept_ctpv)

        was_unknown_before = (addr_region == UNKNOWN_REGION)

        def make_entry(region, region_basis, depts_for_region, mismatch_note=None, split_info=None):
            e = {
                "대학명": schl,
                "캠퍼스구분": campus_token,
                "보유IT계열학과명목록": depts_for_region,
                "미분류IT후보학과명목록": unclassified_depts,
                "학부구분": track,
                "권역": region,
                "권역판정근거": region_basis,
            }
            e.update(campus_info)
            if mismatch_note:
                e["권역출처불일치"] = True
                e["비고"] = mismatch_note
            if split_info:
                e["지역분산분리"] = True
                e["분산된전체권역"] = split_info
            return e

        if ctpv_result is None:
            # ctpvNm 데이터가 전혀 없는 경우만 기존 주소 파싱 방식을 보조로 사용
            entry = make_entry(addr_region, addr_basis + " (ctpvNm 없음, 주소 파싱으로 보조 판정)", it_depts)
            entries.append(entry)
            if catholic_note is None and schl == "가톨릭대학교":
                catholic_note = {"대학명": schl, "결과": "ctpvNm 데이터 없음 - 주소 파싱으로 보조 판정",
                                  "권역": addr_region}
        elif ctpv_result["mode"] == "single":
            region = ctpv_result["region"]
            basis = "ctpvNm 기준(단일): IT 계열 학과의 ctpvNm이 모두 %s에 해당" % region
            mismatch_note = None
            if addr_region != UNKNOWN_REGION and addr_region != region:
                mismatch_note = (
                    "연결된 캠퍼스 좌표(%s, %s)는 %s 권역이지만, IT 계열 학과의 ctpvNm은 "
                    "%s로 확인됨. ctpvNm 기준을 최종 권역으로 채택함." % (
                        campus_info.get("연결캠퍼스명"), campus_info.get("주소"), addr_region, region)
                )
            entry = make_entry(region, basis, it_depts, mismatch_note=mismatch_note)
            entries.append(entry)
            if was_unknown_before:
                newly_resolved_total.append({"대학명": schl, "권역": region, "근거": basis})
            if schl in PREVIOUS_AMBIGUOUS_13:
                resolved_among_13.append({"대학명": schl, "권역": region})
            if schl == "가톨릭대학교":
                catholic_note = {
                    "대학명": schl,
                    "IT학과_ctpvNm_기준_권역": region,
                    "연결된_캠퍼스_좌표_기준_권역": addr_region,
                    "연결된_캠퍼스명": campus_info.get("연결캠퍼스명"),
                    "권역출처불일치": mismatch_note is not None,
                    "최종채택": "ctpvNm 기준 (%s)" % region,
                }
        else:  # split
            by_region = ctpv_result["byRegion"]
            basis_template = "ctpvNm 기준(지역분산): 이 대학의 IT 계열 학과가 여러 권역에 걸쳐 있어 분리함"
            for region, region_depts in sorted(by_region.items()):
                entry = make_entry(
                    region, basis_template, region_depts,
                    split_info=sorted(by_region.keys()),
                )
                # 지역분산 대학은 특정 캠퍼스 좌표를 대표로 쓸 수 없으므로 참고 표시만 남긴다
                entry["좌표미확보"] = True
                entries.append(entry)
            split_universities.append({"대학명": schl, "권역별학과": {r: ds for r, ds in sorted(by_region.items())}})
            if was_unknown_before:
                newly_resolved_total.append({"대학명": schl, "권역": "분산(%s)" % "/".join(sorted(by_region.keys())),
                                              "근거": basis_template})
            if schl in PREVIOUS_AMBIGUOUS_13:
                resolved_among_13.append({"대학명": schl, "권역": "분산(%s)" % "/".join(sorted(by_region.keys()))})
            if schl == "가톨릭대학교":
                catholic_note = {
                    "대학명": schl,
                    "IT학과_ctpvNm_기준": "여러 권역에 분산됨: %s" % by_region,
                    "결론": "지역별로 분리함",
                }

    # 카테고리 분리
    undergrad = [e for e in entries if e["학부구분"] == "undergrad"]
    grad_only = [e for e in entries if e["학부구분"] == "grad_only"]
    cyber = [e for e in entries if e["학부구분"] == "cyber"]
    college = [e for e in entries if e["학부구분"] == "college"]

    linked_count = sum(1 for e in undergrad if not e["좌표미확보"])
    unlinked_count = sum(1 for e in undergrad if e["좌표미확보"])
    region_unknown_count = sum(1 for e in undergrad if e["권역"] == UNKNOWN_REGION)

    grouped = defaultdict(list)
    for e in undergrad:
        grouped[e["권역"]].append(e)
    for region in grouped:
        grouped[region].sort(key=lambda x: x["대학명"])

    region_counts = {r: len(grouped.get(r, [])) for r in REGIONS + [UNKNOWN_REGION]}

    still_unknown = sorted(
        (e["대학명"] for e in undergrad if e["권역"] == UNKNOWN_REGION)
    )

    out = {
        "기준": {
            "itKeywordGroups": sorted(it_data["groups"].keys()),
            "unclassifiedCandidateTotal": len(unclassified_names),
            "note": "IT 계열 포함 여부는 키워드 그룹 매칭 결과만 기준으로 함. 미분류 후보는 참고 표시만.",
            "학부구분기준": "이름에 '대학원' 포함->grad_only, '사이버대학교/사이버대' 포함->cyber, "
                        "그 외 degCrseCrsNm에 '학사' 없고 '전문학사'만 있으면 college, "
                        "학사/전문학사 모두 없으면 grad_only, 그 외는 undergrad(학부 조사 대상)",
        },
        "학부조사대상_전체": len(undergrad),
        "linkedCampusCount": linked_count,
        "unlinkedCampusCount": unlinked_count,
        "regionUnknownCount": region_unknown_count,
        "regionCounts": region_counts,
        "byRegion": {r: grouped.get(r, []) for r in REGIONS + [UNKNOWN_REGION]},
        "제외_grad_only": {"count": len(grad_only), "items": sorted(grad_only, key=lambda x: x["대학명"])},
        "제외_cyber": {"count": len(cyber), "items": sorted(cyber, key=lambda x: x["대학명"])},
        "제외_college": {"count": len(college), "items": sorted(college, key=lambda x: x["대학명"])},
        "가톨릭대_재확인": catholic_note,
        "ctpvNm_기준_새로확정된_목록": newly_resolved_total,
        "ctpvNm_기준_기존13건중_해결": resolved_among_13,
        "지역분산으로_분리된_대학": split_universities,
    }

    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=== 학부 조사 대상 (grad_only/cyber/college 제외) ===")
    lines.append("총 %d개 대학" % len(undergrad))
    lines.append("캠퍼스 연결됨: %d / 연결 안 됨(좌표미확보): %d" % (linked_count, unlinked_count))
    lines.append("권역 미확인: %d" % region_unknown_count)
    lines.append("")
    lines.append("권역별 대학 수:")
    for r in REGIONS + [UNKNOWN_REGION]:
        lines.append("  %s: %d" % (r, region_counts[r]))
    lines.append("")
    lines.append("ctpvNm 기준 재판정으로 새로 권역 확정된 건수: %d" % len(newly_resolved_total))
    for r in newly_resolved_total:
        lines.append(" - %s -> %s (%s)" % (r["대학명"], r["권역"], r["근거"]))
    lines.append("")
    lines.append("그중 기존 13건 복수캠퍼스후보에서 해결된 건수: %d / 13" % len(resolved_among_13))
    for r in resolved_among_13:
        lines.append(" - %s -> %s" % (r["대학명"], r["권역"]))
    unresolved_13 = [n for n in PREVIOUS_AMBIGUOUS_13 if n not in [r["대학명"] for r in resolved_among_13]]
    if unresolved_13:
        lines.append("  (13건 중 아직 미해결: %s)" % ", ".join(unresolved_13))
    lines.append("")
    lines.append("IT 학과가 실제로 여러 권역에 걸쳐 분리된 대학 (%d건):" % len(split_universities))
    for s in split_universities:
        lines.append(" - %s: %s" % (s["대학명"], s["권역별학과"]))
    lines.append("")
    lines.append("제외 카테고리: grad_only %d건 / cyber %d건 / college %d건" % (
        len(grad_only), len(cyber), len(college)))
    lines.append("")
    lines.append("그래도 남은 미확인 대학 목록 (%d건):" % len(still_unknown))
    for name in still_unknown:
        lines.append(" - %s" % name)
    lines.append("")
    lines.append("가톨릭대학교 재판정 결과:")
    if catholic_note:
        for k, v in catholic_note.items():
            lines.append("  %s: %s" % (k, v))

    with io.open(os.path.join(HERE, "master_list_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
