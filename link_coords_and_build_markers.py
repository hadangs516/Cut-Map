# -*- coding: utf-8 -*-
"""1단계: university_master_list.json의 좌표미확보 행을 권역 일치 캠퍼스로 재연결.
   2단계: 좌표가 연결된 학부 조사 대상 행만 phase1_markers.json 마커로 만든다.

1단계가 끝나야 2단계로 넘어간다 (같은 스크립트 안에서 순서대로 실행).

캠퍼스 재연결 규칙:
  - 대학명에서 괄호 캠퍼스 표기를 뗀 "본명"이 같은 coords 행들을 후보로 삼는다.
    (표기가 달라도 - WISE/경주처럼 - 본명만 같으면 후보에 넣는다)
  - 그 후보들의 주소가 가리키는 권역이, 이 행의 권역(ctpvNm 기준으로 이미 확정된 값)과
    같은 것만 남긴다.
  - 남은 후보가 정확히 1개일 때만 연결한다. 0개나 2개 이상이면 연결하지 않는다.
  - 권역출처불일치 플래그가 있던 행(가톨릭대 등)은 먼저 기존 좌표를 지우고 좌표미확보로
    되돌린 다음 같은 규칙으로 다시 시도한다.
  - 지역분산으로 나뉜 행도 각자의 권역 기준으로 독립적으로 시도한다.
  - 좌표를 추정하지 않는다 (후보가 애매하면 그냥 미확보로 남긴다).
"""
import io
import json
import os
import re
from collections import defaultdict

from build_university_master_list import REGIONS, UNKNOWN_REGION, region_of

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_PATH = os.path.join(HERE, "university_master_list.json")
COORDS_PATH = os.path.join(HERE, "univ_coords.json")
CATALOG_PATH = os.path.join(HERE, "catalog.json")
MARKERS_OUT = os.path.join(HERE, "phase1_markers.json")
MISSING_OUT = os.path.join(HERE, "marker_missing_coords.json")

FOCUS_UNIS = ["고려대학교", "연세대학교", "한양대학교", "건국대학교", "동국대학교", "가톨릭대학교"]


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def strip_campus(name):
    return re.sub(r"\s*\([^)]*\)\s*$", "", name or "").strip()


def all_row_lists(master):
    lists = []
    for region in REGIONS + [UNKNOWN_REGION]:
        lists.append(master["byRegion"].get(region, []))
    for key in ("제외_grad_only", "제외_cyber", "제외_college"):
        lists.append(master[key]["items"])
    return lists


def phase1_link(master, coords):
    # coords 후보 인덱스: 본명 -> [(권역, coords_entry), ...]
    base_index = defaultdict(list)
    for c in coords:
        base = strip_campus(c["대학이름"])
        region, _basis = region_of(c.get("주소", ""))
        base_index[base].append((region, c))

    newly_linked = 0
    reset_then_relinked = 0
    reset_then_unresolved = 0

    for rows in all_row_lists(master):
        for row in rows:
            was_mismatch = row.get("권역출처불일치", False)
            if was_mismatch:
                row["좌표미확보"] = True
                row["연결캠퍼스명"] = None
                row["매칭방식"] = None
                row["위도"] = None
                row["경도"] = None
                row["주소"] = None

            if not row.get("좌표미확보"):
                continue

            target_region = row.get("권역")
            if not target_region or target_region == UNKNOWN_REGION:
                if was_mismatch:
                    reset_then_unresolved += 1
                continue

            base = strip_campus(row["대학명"])
            matches = [c for (r, c) in base_index.get(base, []) if r == target_region]

            if len(matches) == 1:
                c = matches[0]
                row.update({
                    "연결캠퍼스명": c["대학이름"],
                    "매칭방식": "region_matched",
                    "좌표미확보": False,
                    "위도": c["위도"],
                    "경도": c["경도"],
                    "주소": c["주소"],
                })
                newly_linked += 1
                if was_mismatch:
                    reset_then_relinked += 1
            else:
                if was_mismatch:
                    reset_then_unresolved += 1

    return {
        "newly_linked": newly_linked,
        "reset_then_relinked": reset_then_relinked,
        "reset_then_unresolved": reset_then_unresolved,
    }


def recompute_summary(master):
    undergrad_rows = []
    for region in REGIONS + [UNKNOWN_REGION]:
        undergrad_rows.extend(master["byRegion"].get(region, []))
    linked = sum(1 for r in undergrad_rows if not r["좌표미확보"])
    unlinked = sum(1 for r in undergrad_rows if r["좌표미확보"])
    master["linkedCampusCount"] = linked
    master["unlinkedCampusCount"] = unlinked
    return undergrad_rows


def region_coverage(undergrad_rows):
    cov = {}
    for region in REGIONS + [UNKNOWN_REGION]:
        rows = [r for r in undergrad_rows if r["권역"] == region]
        linked = sum(1 for r in rows if not r["좌표미확보"])
        cov[region] = {"총": len(rows), "연결됨": linked, "미확보": len(rows) - linked}
    return cov


def focus_results(undergrad_rows):
    out = {}
    for name in FOCUS_UNIS:
        matches = [r for r in undergrad_rows if r["대학명"] == name or strip_campus(r["대학명"]) == name]
        out[name] = [
            {
                "대학명": r["대학명"], "권역": r["권역"], "좌표미확보": r["좌표미확보"],
                "연결캠퍼스명": r.get("연결캠퍼스명"), "위도": r.get("위도"), "경도": r.get("경도"),
            }
            for r in matches
        ]
    return out


def check_dedup_address_fields():
    dedup = load_json(os.path.join(HERE, "univ_major_dedup.json"))
    items = dedup["items"]
    fields = list(items[0].keys()) if items else []
    location_fields = [f for f in fields if f in ("ctpvCd", "ctpvNm", "sggCd", "sggNm")]
    samples = []
    for it in items[:3]:
        samples.append({f: it.get(f) for f in location_fields})
    return {
        "전체필드": fields,
        "위치관련필드": location_fields,
        "샘플3개": samples,
        "결론": "도로명/지번 주소 필드는 없음. 시도명(ctpvNm)/시군구명(sggNm)과 그 코드값만 있음.",
    }


def build_markers(master, catalog_fields_note):
    undergrad_rows = []
    for region in REGIONS + [UNKNOWN_REGION]:
        undergrad_rows.extend(master["byRegion"].get(region, []))

    linked_rows = [r for r in undergrad_rows if not r["좌표미확보"]]
    missing_rows = [r for r in undergrad_rows if r["좌표미확보"]]

    markers = []
    for r in linked_rows:
        markers.append({
            "univ": r["대학명"],
            "campus": r.get("연결캠퍼스명"),
            "region": r["권역"],
            "lat": r.get("위도"),
            "lon": r.get("경도"),
            "hasITDept": len(r.get("보유IT계열학과명목록", [])) > 0,
            "itDepts": r.get("보유IT계열학과명목록", []),
        })

    missing = []
    for r in missing_rows:
        reason = "캠퍼스 연결 안 됨"
        if r.get("복수캠퍼스후보"):
            reason = "후보 캠퍼스 2개 이상 또는 권역 불일치로 자동 연결 안 함"
        elif r.get("권역출처불일치"):
            reason = "권역출처불일치로 기존 연결 해제 후 재연결 실패"
        missing.append({
            "univ": r["대학명"],
            "region": r["권역"],
            "hasITDept": len(r.get("보유IT계열학과명목록", [])) > 0,
            "itDepts": r.get("보유IT계열학과명목록", []),
            "reason": reason,
        })

    region_counts = defaultdict(int)
    for m in markers:
        region_counts[m["region"]] += 1

    markers_out = {
        "version": 1,
        "note": [
            "university_master_list.json에서 좌표가 연결된 학부 조사 대상 행만 담았다.",
            "필드 구조는 catalog.json의 univs/depts 배열 관례(univ/region/name 스타일 영문 키)를 따랐다: %s"
            % catalog_fields_note,
        ],
        "source": "university_master_list.json + univ_coords.json",
        "stats": {"totalMarkers": len(markers), "regionCounts": dict(region_counts)},
        "markers": markers,
    }
    missing_out = {
        "version": 1,
        "note": "좌표가 연결되지 않아 마커로 만들지 못한 학부 조사 대상 행.",
        "count": len(missing),
        "items": missing,
    }
    return markers_out, missing_out


def main():
    master = load_json(MASTER_PATH)
    coords = load_json(COORDS_PATH)
    catalog = load_json(CATALOG_PATH)
    catalog_fields_note = "univs=%s / depts=%s" % (
        list(catalog["univs"][0].keys()), list(catalog["depts"][0].keys())
    )

    # ===== 1단계 =====
    link_stats = phase1_link(master, coords)
    undergrad_rows = recompute_summary(master)
    coverage = region_coverage(undergrad_rows)
    focus = focus_results(undergrad_rows)
    addr_field_check = check_dedup_address_fields()

    with io.open(MASTER_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    # ===== 2단계 =====
    markers_out, missing_out = build_markers(master, catalog_fields_note)
    with io.open(MARKERS_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(markers_out, f, ensure_ascii=False, indent=2)
    with io.open(MISSING_OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(missing_out, f, ensure_ascii=False, indent=2)

    lines = []
    lines.append("=== 1단계: 좌표 재연결 ===")
    lines.append("새로 연결된 행 수: %d" % link_stats["newly_linked"])
    lines.append("  (그중 권역출처불일치로 해제 후 재연결된 행: %d)" % link_stats["reset_then_relinked"])
    lines.append("권역출처불일치 해제 후 끝내 미확보로 남은 행: %d" % link_stats["reset_then_unresolved"])
    lines.append("")
    lines.append("권역별 좌표 커버리지:")
    for region in REGIONS + [UNKNOWN_REGION]:
        c = coverage[region]
        lines.append("  %s: 총 %d / 연결 %d / 미확보 %d" % (region, c["총"], c["연결됨"], c["미확보"]))
    lines.append("")
    lines.append("dedup 주소 관련 필드 확인:")
    lines.append("  위치관련필드: %s" % addr_field_check["위치관련필드"])
    for s in addr_field_check["샘플3개"]:
        lines.append("   샘플: %s" % s)
    lines.append("  결론: %s" % addr_field_check["결론"])
    lines.append("")
    lines.append("=== 2단계: 마커 생성 ===")
    lines.append("생성된 마커 수: %d" % len(markers_out["markers"]))
    lines.append("좌표 없어 빠진 행 수: %d" % missing_out["count"])
    lines.append("")
    lines.append("주요 대학 최종 좌표 연결 결과:")
    for name in FOCUS_UNIS:
        lines.append(" [%s]" % name)
        for r in focus[name]:
            lines.append("   - %s | 권역=%s | 좌표미확보=%s | 캠퍼스=%s | 위도=%s 경도=%s" % (
                r["대학명"], r["권역"], r["좌표미확보"], r["연결캠퍼스명"], r["위도"], r["경도"]))

    with io.open(os.path.join(HERE, "phase1_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
