# -*- coding: utf-8 -*-
"""IT확정반영_신규후보대학과 연세대 인천(국제캠퍼스) 미배정 학과를 마스터 목록에 반영한다.

- 신규 후보 대학: ctpvNm 기준으로 권역을 판정하고, IT 학과가 여러 권역에 걸치면 기존 지역분산
  규칙대로 권역별 행으로 나눈다. 학부 대상은 byRegion에, 나머지는 grad_only/cyber/college 제외 섹션에 넣는다.
- 연세대 인천 학과: 원래 속한 학교(schlNm) 기준으로 인천 권역 행을 새로 만든다.
  연세대학교 학과는 byRegion 인천 행으로, 연세대학교 대학원 학과는 제외_grad_only의 인천 행으로 간다.
- 좌표는 기존 재연결 규칙(본명 같음 + 캠퍼스 주소 권역 일치 + 후보 정확히 1개)만 쓴다. 추정하지 않는다.
"""
import io
import json
import os
from collections import defaultdict

from build_university_master_list import (
    REGIONS, UNKNOWN_REGION, campus_token_of, classify_track, region_of, resolve_region_by_ctpv,
)
from link_coords_and_build_markers import strip_campus

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_PATH = os.path.join(HERE, "university_master_list.json")
MARKERS_PATH = os.path.join(HERE, "phase1_markers.json")
MISSING_PATH = os.path.join(HERE, "marker_missing_coords.json")
DEDUP_PATH = os.path.join(HERE, "univ_major_dedup.json")
IT_PATH = os.path.join(HERE, "it_track_candidates.json")
INCLUDE_PATH = os.path.join(HERE, "final_include_list.json")
COORDS_PATH = os.path.join(HERE, "univ_coords.json")

TRACK_SECTION = {"grad_only": "제외_grad_only", "cyber": "제외_cyber", "college": "제외_college"}
ADDED_TAG = "IT확정반영 신규후보"


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    master = load_json(MASTER_PATH)
    markers = load_json(MARKERS_PATH)
    missing = load_json(MISSING_PATH)
    dedup = load_json(DEDUP_PATH)
    it_data = load_json(IT_PATH)
    include = load_json(INCLUDE_PATH)
    coords = load_json(COORDS_PATH)

    if master["IT확정반영_신규후보대학"].get("반영상태"):
        raise SystemExit("이미 반영된 상태입니다. 백업본으로 되돌린 뒤 다시 실행하세요.")

    confirmed_new = set(n for names in include.values() for n in names)
    keyword_it = set(n for g in it_data["groups"].values() for n in g["names"])
    final_it = keyword_it | confirmed_new
    remaining_uncl = set(it_data["unclassifiedItCandidates"]["names"]) - confirmed_new

    uni_depts = defaultdict(set)
    uni_degrees = defaultdict(set)
    dept_ctpv = defaultdict(set)
    for it in dedup["items"]:
        schl = it.get("schlNm", "")
        dept = it.get("scsbjtNm", "")
        if not schl:
            continue
        uni_degrees[schl].add(it.get("degCrseCrsNm", ""))
        if dept:
            uni_depts[schl].add(dept)
            if it.get("ctpvNm"):
                dept_ctpv[(schl, dept)].add(it["ctpvNm"])

    base_index = defaultdict(list)
    for c in coords:
        base_index[strip_campus(c["대학이름"])].append((region_of(c.get("주소", ""))[0], c))

    def link_coords(row):
        row.update({"연결캠퍼스명": None, "매칭방식": None, "좌표미확보": True,
                    "위도": None, "경도": None, "주소": None})
        cands = base_index.get(strip_campus(row["대학명"]), [])
        matches = [c for (r, c) in cands if r == row["권역"]]
        if len(matches) == 1:
            c = matches[0]
            row.update({"연결캠퍼스명": c["대학이름"], "매칭방식": "region_matched", "좌표미확보": False,
                        "위도": c["위도"], "경도": c["경도"], "주소": c["주소"]})
            return None
        if not cands:
            return "coords에 해당 대학 캠퍼스 없음"
        if not matches:
            return "coords에 %s 권역 캠퍼스 없음" % row["권역"]
        return "%s 권역 캠퍼스 후보 %d개라 자동 연결 안 함" % (row["권역"], len(matches))

    def new_row(schl, region, basis, it_depts, track, split_regions=None):
        row = {
            "대학명": schl,
            "캠퍼스구분": campus_token_of(schl),
            "보유IT계열학과명목록": sorted(it_depts),
            "미분류IT후보학과명목록": sorted(d for d in uni_depts[schl] if d in remaining_uncl),
            "학부구분": track,
            "권역": region,
            "권역판정근거": basis,
            "복수캠퍼스후보": None,
            "추가경위": ADDED_TAG,
        }
        if split_regions:
            row["지역분산분리"] = True
            row["분산된전체권역"] = split_regions
        return row

    added_rows = []  # (section, row, missing_reason)

    def place(row):
        reason = link_coords(row)
        if row["학부구분"] == "undergrad":
            master["byRegion"].setdefault(row["권역"], []).append(row)
            section = "byRegion"
        else:
            section = TRACK_SECTION[row["학부구분"]]
            master[section]["items"].append(row)
        added_rows.append((section, row, reason))

    # ===== 1. 신규 후보 대학 =====
    cand_names = [u["대학명"] for u in master["IT확정반영_신규후보대학"]["items"]]
    for schl in cand_names:
        it_depts = sorted(d for d in uni_depts[schl] if d in final_it)
        track = classify_track(schl, uni_degrees[schl])
        result = resolve_region_by_ctpv(schl, it_depts, dept_ctpv)
        if result is None:
            place(new_row(schl, UNKNOWN_REGION, "ctpvNm 없음", it_depts, track))
        elif result["mode"] == "single":
            region = result["region"]
            place(new_row(schl, region,
                          "ctpvNm 기준(단일): IT 계열 학과의 ctpvNm이 모두 %s에 해당" % region,
                          it_depts, track))
        else:
            split_regions = sorted(result["byRegion"].keys())
            for region in split_regions:
                place(new_row(schl, region,
                              "ctpvNm 기준(지역분산): 이 대학의 IT 계열 학과가 여러 권역에 걸쳐 있어 분리함",
                              result["byRegion"][region], track, split_regions))

    # ===== 2. 연세대 인천(국제캠퍼스) 미배정 학과 =====
    def all_existing_rows():
        for region in REGIONS + [UNKNOWN_REGION]:
            for r in master["byRegion"].get(region, []):
                yield r
        for sec in TRACK_SECTION.values():
            for r in master[sec]["items"]:
                yield r

    yonsei_log = []
    for entry in master.get("IT확정반영_타권역학과", []):
        schl = entry["대학명"]
        by_region = defaultdict(list)
        for d in entry["학과"]:
            for region in d["권역"]:
                by_region[region].append(d["학과명"])
        existing = [r for r in all_existing_rows() if r["대학명"] == schl and not r.get("추가경위")]
        if not existing:
            raise SystemExit("기존 행을 찾지 못함: %s" % schl)
        track = existing[0]["학부구분"]
        all_regions = sorted(set(r["권역"] for r in existing) | set(by_region.keys()))
        for r in existing:
            r.pop("확정IT_타권역학과", None)
            r["지역분산분리"] = True
            r["분산된전체권역"] = all_regions
        for region, depts in sorted(by_region.items()):
            row = new_row(schl, region,
                          "ctpvNm 기준(지역분산): IT확정반영으로 확정된 %s 학과를 위해 %s 행 신설" % (region, region),
                          depts, track, all_regions)
            row["추가경위"] = "IT확정반영 타권역학과(%s 행 신설)" % region
            place(row)
            yonsei_log.append({"대학명": schl, "권역": region, "학과": sorted(depts), "학부구분": track})
        entry["반영상태"] = "%s 행 신설로 반영됨" % "/".join(sorted(by_region.keys()))

    # ===== 3. 요약 필드 재계산 =====
    for region in master["byRegion"]:
        master["byRegion"][region].sort(key=lambda x: (x["대학명"], x["권역"]))
    for sec in TRACK_SECTION.values():
        master[sec]["items"].sort(key=lambda x: (x["대학명"], x["권역"]))
        master[sec]["count"] = len(master[sec]["items"])

    undergrad = [r for region in REGIONS + [UNKNOWN_REGION] for r in master["byRegion"].get(region, [])]
    master["학부조사대상_전체"] = len(undergrad)
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])
    master["regionUnknownCount"] = sum(1 for r in undergrad if r["권역"] == UNKNOWN_REGION)
    master["regionCounts"] = {r: len(master["byRegion"].get(r, [])) for r in REGIONS + [UNKNOWN_REGION]}
    master["IT확정반영_신규후보대학"]["반영상태"] = "학부 대상은 byRegion, 나머지는 제외 섹션에 행으로 추가됨"

    # ===== 4. 마커 / 좌표 누락 파일 =====
    new_markers = 0
    new_missing = 0
    for section, row, reason in added_rows:
        if section != "byRegion":
            continue
        if not row["좌표미확보"]:
            markers["markers"].append({
                "univ": row["대학명"], "campus": row["연결캠퍼스명"], "region": row["권역"],
                "lat": row["위도"], "lon": row["경도"],
                "hasITDept": len(row["보유IT계열학과명목록"]) > 0,
                "itDepts": row["보유IT계열학과명목록"],
            })
            new_markers += 1
        else:
            missing["items"].append({
                "univ": row["대학명"], "region": row["권역"],
                "hasITDept": len(row["보유IT계열학과명목록"]) > 0,
                "itDepts": row["보유IT계열학과명목록"],
                "reason": reason,
            })
            new_missing += 1

    region_counts = defaultdict(int)
    for m in markers["markers"]:
        region_counts[m["region"]] += 1
    markers["stats"] = {"totalMarkers": len(markers["markers"]), "regionCounts": dict(region_counts)}
    markers["note"].append("IT확정반영 신규후보 대학과 연세대 인천 행 중 좌표가 연결된 행을 추가함.")
    missing["count"] = len(missing["items"])

    save_json(MASTER_PATH, master)
    save_json(MARKERS_PATH, markers)
    save_json(MISSING_PATH, missing)

    # ===== 보고 =====
    undergrad_added = [(r, why) for (s, r, why) in added_rows if s == "byRegion"]
    excl_added = defaultdict(list)
    for s, r, _ in added_rows:
        if s != "byRegion":
            excl_added[s].append(r)

    lines = []
    lines.append("추가된 행 총: %d" % len(added_rows))
    lines.append("학부 대상(byRegion) 추가 행: %d (대학 %d곳)" % (
        len(undergrad_added), len(set(r["대학명"] for r, _ in undergrad_added))))
    lines.append("  마커 생성: %d / 좌표 누락: %d" % (new_markers, new_missing))
    for r, why in undergrad_added:
        lines.append("   - %s | %s | %s | %s" % (
            r["대학명"], r["권역"], r["연결캠퍼스명"] if not r["좌표미확보"] else "좌표없음", why or ""))
    lines.append("제외 섹션 추가:")
    for sec in TRACK_SECTION.values():
        rows = excl_added.get(sec, [])
        lines.append("  %s: %d행 (대학 %d곳)" % (sec, len(rows), len(set(r["대학명"] for r in rows))))
    lines.append("연세대 인천 행:")
    for y in yonsei_log:
        lines.append("  - %s | %s | %s | %s" % (y["대학명"], y["학부구분"], y["권역"], y["학과"]))
    lines.append("전체 마커 수: %d / 좌표 누락 파일 전체: %d" % (len(markers["markers"]), missing["count"]))
    lines.append("권역별 학부 대상 행: %s" % master["regionCounts"])
    with io.open(os.path.join(HERE, "new_candidates_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
