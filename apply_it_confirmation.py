# -*- coding: utf-8 -*-
"""final_include_list.json의 학과명을 IT 계열 확정으로 반영한다.

최종 확정 IT 학과명 = it_track_candidates.json 키워드 그룹 학과명 + final_include_list.json 전체.
final_exclude_list.json 학과명과 두 목록 어디에도 없는 미분류 후보는 미분류로 그대로 둔다.

권역/좌표 연결 로직은 건드리지 않는다. 기존 행의 권역·좌표는 그대로 두고 학과 목록만 다시 계산한다.
새 확정 학과는 dedup ctpvNm 기준 권역이 그 행의 권역과 같을 때만 그 행의 보유IT계열학과명목록에 넣는다.
권역이 다르면(해당 권역 행이 없으면) 보유 목록에 넣지 않고 "확정IT_타권역학과"에 따로 남긴다.
마스터 목록에 없는 대학(키워드 IT 학과가 0개였던 대학)은 행을 새로 만들지 않고 후보로만 기록한다.
"""
import io
import json
import os
from collections import defaultdict

from build_university_master_list import REGIONS, UNKNOWN_REGION, SIDO_ALIASES, classify_track

HERE = os.path.dirname(os.path.abspath(__file__))
INCLUDE_PATH = os.path.join(HERE, "final_include_list.json")
EXCLUDE_PATH = os.path.join(HERE, "final_exclude_list.json")
IT_PATH = os.path.join(HERE, "it_track_candidates.json")
DEDUP_PATH = os.path.join(HERE, "univ_major_dedup.json")
MASTER_PATH = os.path.join(HERE, "university_master_list.json")
MARKERS_PATH = os.path.join(HERE, "phase1_markers.json")
MISSING_PATH = os.path.join(HERE, "marker_missing_coords.json")


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def all_rows(master):
    for region in REGIONS + [UNKNOWN_REGION]:
        for row in master["byRegion"].get(region, []):
            yield row
    for key in ("제외_grad_only", "제외_cyber", "제외_college"):
        for row in master[key]["items"]:
            yield row


def main():
    include = load_json(INCLUDE_PATH)
    exclude = load_json(EXCLUDE_PATH)
    it_data = load_json(IT_PATH)
    dedup = load_json(DEDUP_PATH)
    master = load_json(MASTER_PATH)
    markers = load_json(MARKERS_PATH)
    missing = load_json(MISSING_PATH)

    confirmed_new = set(n for names in include.values() for n in names)
    excluded = set(n for names in exclude.values() for n in names)
    overlap = confirmed_new & excluded
    if overlap:
        raise SystemExit("include/exclude 양쪽에 있는 학과명: %s" % sorted(overlap))

    keyword_it = set(n for g in it_data["groups"].values() for n in g["names"])
    final_it = keyword_it | confirmed_new

    uni_depts = defaultdict(set)
    uni_degrees = defaultdict(set)
    dept_regions = defaultdict(set)
    for it in dedup["items"]:
        schl = it.get("schlNm", "")
        dept = it.get("scsbjtNm", "")
        if not schl:
            continue
        uni_degrees[schl].add(it.get("degCrseCrsNm", ""))
        if dept:
            uni_depts[schl].add(dept)
            region = SIDO_ALIASES.get(it.get("ctpvNm", ""))
            if region:
                dept_regions[(schl, dept)].add(region)

    # ===== 마스터 목록 행 갱신 =====
    # 대학별로 존재하는 행 권역. 지역분산 대학은 다른 권역 학과가 형제 행에 들어가므로
    # 그 대학에 해당 권역 행이 아예 없을 때만 "타권역(미배정)"으로 본다.
    univ_row_regions = defaultdict(set)
    for row in all_rows(master):
        univ_row_regions[row["대학명"]].add(row["권역"])

    master_univs = set()
    rows_changed = 0
    moved_total = 0
    other_region_log = []
    became_true = []

    for row in all_rows(master):
        schl = row["대학명"]
        region = row["권역"]
        master_univs.add(schl)

        old_it = list(row.get("보유IT계열학과명목록", []))
        had_it_before = len(old_it) > 0
        new_here = sorted(
            d for d in uni_depts.get(schl, ())
            if d in confirmed_new and region in dept_regions.get((schl, d), set())
        )
        new_it = sorted(set(old_it) | set(new_here))

        old_uncl = list(row.get("미분류IT후보학과명목록", []))
        remaining_uncl = sorted(d for d in old_uncl if d not in confirmed_new)
        confirmed_in_uncl = [d for d in old_uncl if d in confirmed_new]
        other_region = sorted(
            d for d in confirmed_in_uncl
            if not (dept_regions.get((schl, d), set()) & univ_row_regions[schl])
        )

        row["보유IT계열학과명목록"] = new_it
        row["미분류IT후보학과명목록"] = remaining_uncl
        if new_here:
            row["IT확정추가학과"] = new_here
        if other_region:
            row["확정IT_타권역학과"] = [
                {"학과명": d, "권역": sorted(dept_regions.get((schl, d), set()))} for d in other_region
            ]
            if not any(o["대학명"] == schl for o in other_region_log):
                other_region_log.append({
                    "대학명": schl,
                    "존재하는행권역": sorted(univ_row_regions[schl]),
                    "학과": row["확정IT_타권역학과"],
                })

        added = len(new_it) - len(old_it)
        if added:
            rows_changed += 1
            moved_total += added
        if not had_it_before and new_it:
            became_true.append({"대학명": schl, "권역": region})
            row["hasITDept변경"] = "false->true"

    # 마스터 목록에 없는 대학 중 이번 확정으로 IT 학과가 생긴 대학 (행은 만들지 않고 후보로만 기록)
    new_candidate_univs = []
    for schl, depts in uni_depts.items():
        if schl in master_univs:
            continue
        confirmed_depts = sorted(d for d in depts if d in confirmed_new)
        if not confirmed_depts:
            continue
        regions = sorted(set(r for d in confirmed_depts for r in dept_regions.get((schl, d), set())))
        new_candidate_univs.append({
            "대학명": schl,
            "학부구분": classify_track(schl, uni_degrees[schl]),
            "IT확정학과": confirmed_depts,
            "ctpvNm기준권역": regions,
        })
    new_candidate_univs.sort(key=lambda x: x["대학명"])
    new_candidate_undergrad = [u for u in new_candidate_univs if u["학부구분"] == "undergrad"]

    master["기준"]["IT확정반영"] = {
        "source": ["final_include_list.json", "final_exclude_list.json"],
        "키워드그룹학과수": len(keyword_it),
        "include확정학과수": len(confirmed_new),
        "exclude학과수": len(excluded),
        "최종확정IT학과수": len(final_it),
        "note": "include 학과는 해당 행의 권역(ctpvNm 기준)과 같은 권역일 때만 보유 목록에 넣음. "
                "권역이 다르면 확정IT_타권역학과에 따로 남김. 권역/좌표는 변경하지 않음.",
    }
    master["IT확정반영_타권역학과"] = other_region_log
    master["IT확정반영_신규후보대학"] = {
        "note": "키워드 IT 학과가 없어 마스터 목록에 없던 대학 중 이번 확정으로 IT 학과가 생긴 대학. "
                "권역/좌표 로직을 돌리지 않았으므로 행으로 추가하지 않고 후보로만 기록함.",
        "count": len(new_candidate_univs),
        "undergradCount": len(new_candidate_undergrad),
        "items": new_candidate_univs,
    }
    save_json(MASTER_PATH, master)

    # ===== 마커 갱신 (행 = 대학명+권역) =====
    row_by_key = {}
    for region in REGIONS + [UNKNOWN_REGION]:
        for row in master["byRegion"].get(region, []):
            row_by_key[(row["대학명"], row["권역"])] = row

    markers_changed = 0
    marker_became_true = []
    for m in markers["markers"]:
        row = row_by_key.get((m["univ"], m["region"]))
        if row is None:
            raise SystemExit("마커에 대응하는 마스터 행 없음: %s / %s" % (m["univ"], m["region"]))
        before_has = m["hasITDept"]
        new_depts = row["보유IT계열학과명목록"]
        if new_depts != m["itDepts"]:
            markers_changed += 1
        m["itDepts"] = new_depts
        m["hasITDept"] = len(new_depts) > 0
        if not before_has and m["hasITDept"]:
            m["hasITDeptChanged"] = "false->true"
            marker_became_true.append(m["univ"])
    markers["note"].append(
        "itDepts는 키워드 그룹 + final_include_list.json 확정 학과 기준으로 갱신됨 (권역 일치 학과만)."
    )
    save_json(MARKERS_PATH, markers)

    for item in missing["items"]:
        row = row_by_key.get((item["univ"], item["region"]))
        if row is not None:
            item["itDepts"] = row["보유IT계열학과명목록"]
            item["hasITDept"] = len(item["itDepts"]) > 0
    save_json(MISSING_PATH, missing)

    lines = []
    lines.append("새로 IT로 확정된 학과명 총 건수: %d" % len(confirmed_new))
    lines.append("최종 확정 IT 학과명 전체: %d (키워드 %d + 확정 %d)" % (len(final_it), len(keyword_it), len(confirmed_new)))
    lines.append("마스터 목록에서 보유 목록이 늘어난 행: %d (추가된 학과 항목 %d)" % (rows_changed, moved_total))
    lines.append("hasITDept false->true 행(마스터): %d" % len(became_true))
    lines.append("hasITDept false->true 마커: %d" % len(marker_became_true))
    lines.append("itDepts가 바뀐 마커 수: %d / %d" % (markers_changed, len(markers["markers"])))
    orphan_depts = sum(len(o["학과"]) for o in other_region_log)
    lines.append("확정됐지만 그 권역 행이 없어 미배정된 학과: %d건 (%d개 대학)" % (orphan_depts, len(other_region_log)))
    lines.append("마스터 목록 밖 신규 후보 대학: %d (그중 학부 대상 %d)" % (
        len(new_candidate_univs), len(new_candidate_undergrad)))
    for u in new_candidate_undergrad:
        lines.append("  - %s %s %s" % (u["대학명"], u["ctpvNm기준권역"], u["IT확정학과"]))
    lines.append("")
    lines.append("미배정(타권역) 학과 상세:")
    for o in other_region_log:
        lines.append("  - %s (행 권역 %s): %s" % (o["대학명"], o["존재하는행권역"], o["학과"]))
    with io.open(os.path.join(HERE, "it_confirm_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
