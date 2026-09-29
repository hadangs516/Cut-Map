# -*- coding: utf-8 -*-
"""kedi_multi_address_review.json 중 사용자가 캠퍼스를 지정한 14건을 좌표로 확정한다.

지정 주소는 검토 목록의 KEDI 후보(주소 + 본분교)와 일치해야 한다. 일치하지 않으면 중단한다.
지정하지 않은 건은 검토 목록에 그대로 남긴다.
"""
import io
import json
import os
import re
import time
from collections import defaultdict

from build_university_master_list import region_of
from geocode_gyeongnam_univ import call_geocoder, load_env

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER_PATH = os.path.join(HERE, "university_master_list.json")
MARKERS_PATH = os.path.join(HERE, "phase1_markers.json")
MISSING_PATH = os.path.join(HERE, "marker_missing_coords.json")
REVIEW_PATH = os.path.join(HERE, "kedi_multi_address_review.json")

DESIGNATED = {
    "두원공과대학교": ("본교(제1캠퍼스)", "경기도 안성시 죽산면 관음당길 51"),
    "수원여자대학교": ("본교(제1캠퍼스)", "경기도 수원시 권선구 온정로 72"),
    "한경국립대학교": ("본교(제1캠퍼스)", "경기도 안성시 중앙로 327"),
    "재능대학교": ("본교(제1캠퍼스)", "인천광역시 동구 재능로 178"),
    "국립공주대학교": ("본교(제2캠퍼스)", "충남 천안시 서북구 천안대로 1223-24"),
    "국립한밭대학교": ("본교(제1캠퍼스)", "대전광역시 유성구 동서대로 125"),
    "국립목포대학교": ("본교(제1캠퍼스)", "전라남도 무안군 청계면 영산로 1666"),
    "전남대학교": ("본교(제1캠퍼스)", "광주광역시 북구 용봉로 77"),
    "경남정보대학교": ("본교(제1캠퍼스)", "부산광역시 사상구 주례로 45"),
    "경상국립대학교": ("본교(제1캠퍼스)", "경상남도 진주시 진주대로 501"),
    "국립경국대학교": ("본교(제1캠퍼스)", "경상북도 안동시 경동로 1375"),
    "국립창원대학교": ("본교(제1캠퍼스)", "경상남도 창원시 의창구 창원대학로 20"),
    "영산대학교(해운대)": ("본교(제1캠퍼스)", "부산 해운대구 반송순환로 142"),
    "울산과학대학교": ("본교(제1캠퍼스)", "울산광역시 동구 봉수로 101"),
}
KONGJU = "국립공주대학교"
KONGJU_EXCEPTION_DEPT = "컴퓨터교육과"
SOURCE = {
    "지정": "사용자 수동 지정 (2026-09-24 작업 지시: KEDI 복수주소 검토 목록 수동 확정)",
    "주소출처": "KEDI 2026 고등교육통계 학교별 주요 현황의 후보 주소 중 선택",
    "좌표": "지정 주소를 VWorld Geocoder로 변환",
    "검증": "지정 근거(검색 확인/일반 지식)는 작업 지시에 명시되지 않았고, Claude가 별도 검색으로 확인하지 않음",
}


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def addr_key(a):
    return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", a or ""))


def geocode(key, address):
    for typ in ("road", "parcel"):
        data = call_geocoder(key, address, typ)
        time.sleep(0.2)
        resp = data.get("response", {})
        if resp.get("status") == "OK":
            p = resp["result"]["point"]
            return float(p["y"]), float(p["x"]), typ
    return None


def main():
    master = load_json(MASTER_PATH)
    markers = load_json(MARKERS_PATH)
    missing = load_json(MISSING_PATH)
    review = load_json(REVIEW_PATH)
    key = load_env(os.path.join(HERE, ".env")).get("VWORLD_KEY")
    if not key:
        raise SystemExit(".env에 VWORLD_KEY가 없음")

    rows_by_key = {(r["대학명"], r["권역"]): r for reg in master["byRegion"] for r in master["byRegion"][reg]}

    # 1) 지정값 검증: 검토 목록에 있고, 지정 주소·본분교가 후보와 일치하고, 권역이 맞아야 함
    plan = []
    review_names = [it["univ"] for it in review["items"]]
    for univ, (campus, addr) in DESIGNATED.items():
        matches = [it for it in review["items"] if it["univ"] == univ]
        if len(matches) != 1:
            raise SystemExit("검토 목록에서 %s 행이 %d개" % (univ, len(matches)))
        item = matches[0]
        cand = [c for c in item["candidates"] if addr_key(c["주소"]) == addr_key(addr)]
        if not cand:
            raise SystemExit("%s: 지정 주소가 KEDI 후보에 없음: %s" % (univ, addr))
        if cand[0]["본분교"] != campus:
            raise SystemExit("%s: 본분교 불일치 (지정 %s / KEDI %s)" % (univ, campus, cand[0]["본분교"]))
        if region_of(addr)[0] != item["region"]:
            raise SystemExit("%s: 지정 주소 권역(%s)이 행 권역(%s)과 다름" % (univ, region_of(addr)[0], item["region"]))
        row = rows_by_key.get((univ, item["region"]))
        if row is None or not row["좌표미확보"]:
            raise SystemExit("%s: 좌표미확보 마스터 행이 없음" % univ)
        plan.append((univ, campus, addr, cand[0], item, row))

    # 2) 지오코딩. 실패한 건은 좌표를 추정하지 않고, 지정 캠퍼스만 기록한 채 누락으로 남긴다.
    results = {}
    failed = []
    for univ, campus, addr, cand, item, row in plan:
        g = geocode(key, addr)
        if g is None:
            g = geocode(key, cand["주소"])  # KEDI 원문(괄호 부가정보 포함)으로 한 번 더
        if g is None:
            failed.append(univ)
        else:
            results[univ] = g

    # 3) 반영
    confirmed_keys = set()
    designated_keys = set()
    for univ, campus, addr, cand, item, row in plan:
        designated_keys.add((item["univ"], item["region"]))
        if univ in failed:
            row.pop("KEDI주소후보", None)
            row["지정캠퍼스"] = {"캠퍼스": "%s (%s)" % (cand["학교명"], campus), "주소": addr, "source": SOURCE}
            row["비고"] = ((row["비고"] + " / ") if row.get("비고") else "") + \
                "지정 주소가 VWorld에서 도로명/지번 모두 NOT_FOUND라 좌표 미확보로 남김(추정 안 함)."
            for it in missing["items"]:
                if (it["univ"], it["region"]) == (item["univ"], item["region"]):
                    it["reason"] = "캠퍼스 지정됨(%s)이나 VWorld 변환 실패: %s" % (campus, addr)
                    it.pop("kediCandidates", None)
            continue
        lat, lon, typ = results[univ]
        row.update({
            "연결캠퍼스명": "%s (%s)" % (cand["학교명"], campus),
            "매칭방식": "kedi_manual_designation",
            "좌표미확보": False,
            "위도": lat, "경도": lon, "주소": addr,
            "좌표출처": "KEDI 후보 주소 사용자 수동 지정 -> VWorld",
            "지오코딩방식": typ,
            "source": SOURCE,
        })
        row.pop("KEDI주소후보", None)
        if univ == KONGJU:
            in_list = KONGJU_EXCEPTION_DEPT in row["보유IT계열학과명목록"]
            row["좌표예외학과"] = [KONGJU_EXCEPTION_DEPT]
            note = ("%s는 천안캠퍼스(본교 제2캠퍼스) 좌표를 쓰지만, 이 행의 %s는 다른 캠퍼스(예: 공주 신관동 "
                    "본캠퍼스) 소속일 가능성이 있어 예외로 표시만 함. 좌표는 변경하지 않음.%s" % (
                        univ, KONGJU_EXCEPTION_DEPT,
                        "" if in_list else " (주의: 현재 보유IT계열학과명목록에 이 학과가 없음)"))
            row["비고"] = (row["비고"] + " / " + note) if row.get("비고") else note
        markers["markers"].append({
            "univ": row["대학명"], "campus": row["연결캠퍼스명"], "region": row["권역"],
            "lat": lat, "lon": lon,
            "hasITDept": len(row["보유IT계열학과명목록"]) > 0,
            "itDepts": row["보유IT계열학과명목록"],
        })
        confirmed_keys.add((item["univ"], item["region"]))

    missing["items"] = [it for it in missing["items"] if (it["univ"], it["region"]) not in confirmed_keys]
    missing["count"] = len(missing["items"])
    review["items"] = [it for it in review["items"] if (it["univ"], it["region"]) not in designated_keys]
    review["count"] = len(review["items"])

    region_counts = defaultdict(int)
    for m in markers["markers"]:
        region_counts[m["region"]] += 1
    markers["stats"] = {"totalMarkers": len(markers["markers"]), "regionCounts": dict(region_counts)}
    markers["note"].append("KEDI 복수주소 검토 목록 중 사용자가 캠퍼스를 지정한 %d건을 추가함." % len(results))

    undergrad = [r for reg in master["byRegion"] for r in master["byRegion"][reg]]
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])

    save_json(MASTER_PATH, master)
    save_json(MARKERS_PATH, markers)
    save_json(MISSING_PATH, missing)
    save_json(REVIEW_PATH, review)

    lines = ["지정 %d건 / 마커 생성 %d곳 / 변환 실패 %s" % (len(plan), len(results), failed),
             "전체 마커 %d / 좌표 누락 %d / 검토 목록 남은 건 %s" % (
                 len(markers["markers"]), missing["count"], [it["univ"] for it in review["items"]]),
             "검토목록 원래 대학: %s" % review_names]
    for univ, campus, addr, cand, item, row in plan:
        if univ in results:
            lines.append("  %s | %s | %s | %.5f, %.5f (%s)" % (univ, item["region"], addr, results[univ][0],
                                                              results[univ][1], results[univ][2]))
    kongju = rows_by_key.get((KONGJU, next(p[4]["region"] for p in plan if p[0] == KONGJU)))
    lines.append("공주대 비고: %s" % kongju.get("비고"))
    with io.open(os.path.join(HERE, "kedi_confirm_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
