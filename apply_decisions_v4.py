# -*- coding: utf-8 -*-
"""컷맵 작업 지시(2026-09-24, v4) 반영.

작업 1: 서울·충청·강원·제주·호남 4년제 목록 (KEDI 학제 기준)
작업 2: 좌표 3건 확정 (coords_review_v2.json 장소 검색 후보, 사용자 지정 주소)
작업 3: 한국복지대 후속 캠퍼스 = 한경국립대학교 평택캠퍼스 (사용자 확정)
작업 4: 확인만 (수정 없음) -> decisions_v4_report.txt

수정 파일(백업: backup_20260924_decisions_v4/): university_master_list_v2.json, phase1_markers_v3.json,
coords_review_v2.json, merged_schools.json
새 파일: 4yr_list_seoul_chungcheong_gangwon_jeju_honam.md, decisions_v4_report.txt
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

from fill_coords_from_kedi import load_kedi
from geocode_gyeongnam_univ import load_env
from resolve_coords22 import P, SIDO_ALIASES, geocode_variants, is_grad, km, load_json, save_json

TODAY = "2026-09-24"
APPROVAL = "사용자 확정 (%s 작업 지시)" % TODAY
BACKUP = "backup_20260924_decisions_v4"
FOUR_YEAR = ("대학교", "산업대학")
REGIONS_T1 = ("서울", "충청", "강원", "제주", "호남")

# 작업 2: 대학명 -> (권역, 확정 도로명주소(검색 결과 road 값), KEDI 본분교)
CONFIRM = {
    "재능대학교": ("인천", "인천광역시 동구 재능로 178", "본교(제1캠퍼스)"),
    "포항대학교": ("영남", "경상북도 포항시 북구 흥해읍 신덕로 60", "본교(제1캠퍼스)"),
    "예원예술대학교": ("경기", "경기도 양주시 은현면 예원대학로 56-0", "본교(제2캠퍼스)"),
}
HK_SOURCE = {"url": "https://www.hknu.ac.kr/sanhak/3034/subview.do", "위치": "페이지 하단 주소",
             "주소": "경기도 평택시 삼남로 283", "확인일": TODAY,
             "확인자": "사용자 (Claude는 이 페이지에 접근하지 않음)"}
ACTIVE = {"기존", "신설", "변경"}


def nm(s):
    return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", s or ""))


def main():
    for f in ("university_master_list_v2.json", "phase1_markers_v3.json", "coords_review_v2.json",
              "merged_schools.json", "SPEC_대학맵.md"):
        assert os.path.exists(P(os.path.join(BACKUP, f))), "백업 없음: %s" % f
    master = load_json("university_master_list_v2.json")
    markers = load_json("phase1_markers_v3.json")
    review = load_json("coords_review_v2.json")
    merged = load_json("merged_schools.json")
    kedi = load_kedi()
    only_task1 = len(sys.argv) > 1 and sys.argv[1] == "task1"
    dedup = load_json("univ_major_dedup.json")["items"]
    key = load_env(P(".env"))["VWORLD_KEY"]
    rows = {(r["대학명"], r["권역"]): r for reg in master["byRegion"] for r in master["byRegion"][reg]}
    rep = []

    # ------------------------------------------------ 작업 1
    kedi_nongrad = [k for k in kedi if not is_grad(k)]

    def kedi_type(r):
        link = r.get("연결캠퍼스명") or ""
        m = re.match(r"^(.*?)\s*\((본교\(제\d캠퍼스\)|분교.*?)\)$", link)
        if m:
            hit = [k for k in kedi_nongrad if nm(k["학교명"]) == nm(m.group(1)) and k["본분교"] == m.group(2)]
            if hit:
                return sorted(set(k["학제"] for k in hit))
        for name in (r["대학명"], link.split("(")[0]):
            hit = [k for k in kedi_nongrad if nm(k["학교명"]) == nm(name)]
            if hit:
                return sorted(set(k["학제"] for k in hit))
        return []

    md = ["# 4년제 목록: 서울·충청·강원·제주·호남", "",
          "- 기준: university_master_list_v2.json 학부 조사 대상 행 (%s 정리본)" % TODAY,
          "- 4년제 판정: KEDI 2026 학교별 현황의 **학제** 열 값만 사용 (KEDI 파일에 '학교종류'라는 이름의 열은 없고, "
          "학교 종류는 '학제' 열에 있음). 4년제로 본 값: %s. 교육대학은 SPEC 12번 조사 순서(4년제 다음)에 따라 "
          "아래 참고 표로 분리" % ", ".join(FOUR_YEAR),
          "- KEDI 매칭: 연결캠퍼스명(학교명+본분교) 우선, 없으면 학교명 일치. 대학원 학제 행은 매칭에서 뺌.", ""]
    no_type, other = [], []
    counts = {}
    for reg in REGIONS_T1:
        four = []
        for r in sorted(master["byRegion"][reg], key=lambda x: x["대학명"]):
            t = kedi_type(r)
            if not t:
                no_type.append((reg, r))
            elif all(x in FOUR_YEAR for x in t):
                four.append((r, "/".join(t)))
            elif any(x in FOUR_YEAR for x in t):
                other.append((reg, r, "/".join(t) + " (값이 여러 개)"))
            else:
                other.append((reg, r, "/".join(t)))
        counts[reg] = len(four)
        md += ["## %s (%d)" % (reg, len(four)), "", "| # | 대학명 | 연결 캠퍼스 | KEDI 학제 | 좌표 |", "|---|---|---|---|---|"]
        md += ["| %d | %s | %s | %s | %s |" % (i, r["대학명"], r.get("연결캠퍼스명") or "-", t,
                                            "미확보" if r["좌표미확보"] else "있음") for i, (r, t) in enumerate(four, 1)]
        md.append("")
    md += ["## 학제 값이 없는 행 (%d)" % len(no_type), "", "KEDI에서 학교명을 찾지 못해 4년제 여부를 판정하지 않은 행.", "",
           "| 권역 | 대학명 | 연결 캠퍼스 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], r.get("연결캠퍼스명") or "-") for reg, r in no_type]
    md += ["", "## 참고: 4년제가 아닌 학제 (%d)" % len(other), "", "| 권역 | 대학명 | KEDI 학제 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], t) for reg, r, t in other]
    with io.open(P("4yr_list_seoul_chungcheong_gangwon_jeju_honam.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    other_types = defaultdict(int)
    for _, _, t in other:
        other_types[t] += 1
    rep.append("[작업 1] 4년제 %d행 %s / 학제 값 없음 %d / 비4년제 %d %s" % (
        sum(counts.values()), counts, len(no_type), len(other), dict(other_types)))

    if only_task1:
        print("\n".join(rep))
        return
    assert len(markers["markers"]) == 305 and review["count"] == 4 and merged["count"] == 7

    # ------------------------------------------------ 작업 2
    rev_by = {it["univ"]: it for it in review["items"]}
    for univ, (region, road, campus) in CONFIRM.items():
        cands = [c for c in rev_by[univ]["candidates"] if c["road"] == road]
        assert cands, "%s: 지정 주소 후보 없음" % univ
        c = cands[0]
        extra = [x for x in cands[1:]]
        r = rows[(univ, region)]
        assert r["좌표미확보"]
        kr = [k for k in kedi_nongrad if k["학교명"] == univ and k["본분교"] == campus]
        assert len(kr) == 1
        label = "%s (%s)" % (univ, campus)
        prev = {k: r.get(k) for k in ("연결캠퍼스명", "위도", "경도", "주소")}
        r.update({"연결캠퍼스명": label, "매칭방식": "vworld_place_search_user_confirmed", "좌표미확보": False,
                  "위도": c["lat"], "경도": c["lon"], "주소": road.replace("56-0", "56"),
                  "좌표출처": "VWorld 장소 검색(검색어: 학교명) 결과 중 사용자 확정 후보",
                  "지오코딩방식": "place_search",
                  "source": {"지정": APPROVAL, "검색결과제목": c["title"], "분류": c["category"],
                             "지번": c["parcel"], "KEDI주소": kr[0]["주소"]}})
        markers["markers"].append({
            "univ": univ, "campus": label, "region": region, "lat": c["lat"], "lon": c["lon"],
            "hasITDept": len(r["보유IT계열학과명목록"]) > 0, "itDepts": r["보유IT계열학과명목록"],
            "coordSource": "v4 VWorld 장소 검색 후보 사용자 확정", "address": r["주소"]})
        line = "[작업 2] %s -> %s (%.6f, %.6f) 지번 %s | 이전 %s" % (univ, road, c["lat"], c["lon"], c["parcel"], prev)
        for x in extra:
            line += " | 같은 주소 다른 검색결과 %.6f,%.6f (%.0fm 차이, 미사용)" % (
                x["lat"], x["lon"], km((c["lat"], c["lon"]), (x["lat"], x["lon"])) * 1000)
        if univ == "예원예술대학교":
            line += " | KEDI 주소(화합로1134번길 110)와 도로명이 다름. 마스터 주소는 예원대학로 56으로 기록"
        rep.append(line)
    review["items"] = [it for it in review["items"] if it["univ"] not in CONFIRM]

    # ------------------------------------------------ 작업 3
    hk_kedi = [k for k in kedi_nongrad if k["학교명"] == "한경국립대학교"]
    hk_pt = [k for k in hk_kedi if "평택" in k["주소"]]
    g = geocode_variants(key, HK_SOURCE["주소"])
    g35 = geocode_variants(key, hk_pt[0]["주소"]) if hk_pt else {}
    hk_rows = [r for r in rows.values() if r["대학명"].startswith("한경")]
    pt_rows = [r for r in hk_rows if "평택" in (r.get("주소") or "") or "평택" in (r.get("연결캠퍼스명") or "")]
    hk_it = [r for r in hk_rows][0]["보유IT계열학과명목록"] if hk_rows else []
    pt_it = defaultdict(set)
    for x in dedup:
        if x["schlNm"] == "한경국립대학교" and x["sggNm"] == "평택시" and x["scsbjtNm"] in set(hk_it):
            pt_it[x["scsbjtNm"]].add(x["scsbjtSttsNm"])
    ent = next(e for e in merged["items"] if e["구학교명"] == "한국복지대학교")
    ent["이전_후속캠퍼스후보"] = ent.pop("후속캠퍼스후보", None)
    ent["이전_근거"] = ent.pop("근거", None)
    succ = {"후속학교": "한경국립대학교", "후속캠퍼스": "한경국립대학교 평택캠퍼스",
            "대응근거": APPROVAL, "주소": HK_SOURCE["주소"], "주소출처": HK_SOURCE,
            "KEDI행": [{"본분교": k["본분교"], "상태": k["상태"], "주소": k["주소"]} for k in hk_pt],
            "평택_IT학과_표준데이터": {n: sorted(s) for n, s in sorted(pt_it.items())}}
    if "lat" in g:
        succ.update({"lat": g["lat"], "lon": g["lon"], "좌표출처": "공식 홈페이지 주소 -> VWorld Geocoder"})
    else:
        succ.update({"lat": None, "lon": None,
                     "좌표상태": "미확보: '%s'는 VWorld Geocoder 변형 %d가지 x 도로명/지번 모두 NOT_FOUND. 추정하지 않음" % (
                         HK_SOURCE["주소"], len(set(t["address"] for t in g["tries"]))),
                     "좌표참고_판단필요": {
                         "주소": hk_pt[0]["주소"] if hk_pt else None,
                         "lat": g35.get("lat"), "lon": g35.get("lon"),
                         "근거": ["VWorld 주소 검색: 한경대학로 35 = 경기도 평택시 한경대학로 35 (장안동), 지번 장안동 5-3",
                                "VWorld 장소 검색: 한국복지대학교 건물(본관·창의관·생활관 등)이 도로명 '삼남로 283', 지번 "
                                "장안동 5-3·5-36·5-39 등으로 등록돼 있음",
                                "VWorld 장소 검색: '한경국립대학교(버스정류장)' 도로명 삼남로 283, "
                                "'한경국립대학교평택캠퍼스' 도로명 한경대학로 35",
                                "VWorld 역지오코딩(한경대학로 35 좌표): 도로명 한경대학로 35 (장안동)",
                                "Geocoder DB에는 삼남로 283이 없고 한경대학로 35만 있음 -> 도로명이 바뀐 같은 캠퍼스일 "
                                "가능성이 크지만 도로명 변경 공고 등으로 확인한 사실은 아님"]}})
    succ["마커"] = ("없음: 마스터에 한경국립대 평택 행 없음 (한경국립대 경기 행 1개, 좌표는 %s)" % (
        hk_rows[0].get("연결캠퍼스명") if hk_rows else "-")) if not pt_rows else "평택 행 있음"
    ent["후속캠퍼스"] = [succ]
    ent["확인상태"] = "확인(사용자 확정, 공식 홈페이지 주소). 좌표는 %s" % ("확보" if "lat" in g else "미확보")
    for e in master["제외_지도대상"]["items"]:
        if e["대학명"] == "한국복지대학교":
            e["후속캠퍼스"] = ["한경국립대학교 평택캠퍼스"]
            e["후속캠퍼스확정"] = APPROVAL
    rv = next((it for it in review["items"] if it["univ"] == "한국복지대학교"), None)
    if rv is not None:
        if "lat" in g:
            review["items"].remove(rv)
        else:
            rv.update({"result": "검토", "type": "통합·폐교 후속 캠퍼스 좌표",
                       "decisionNeeded": "후속 캠퍼스는 확정됨. 삼남로 283이 VWorld에서 변환되지 않아, KEDI 평택 행 주소 "
                                         "한경대학로 35 좌표를 쓸지 결정 필요 (현재 마커 대상 행이 없어 지도에는 영향 없음)",
                       "candidates": [succ["좌표참고_판단필요"]], "evidence": succ["좌표참고_판단필요"]["근거"]})
    rep.append("[작업 3] 삼남로 283 VWorld: %s | KEDI 평택 행: %s | 한경대학로 35 좌표: %s,%s | 마스터 한경 행: %s | 평택 행: %s" % (
        "성공" if "lat" in g else "NOT_FOUND(%s)" % [t["status"] for t in g["tries"]],
        [(k["본분교"], k["주소"]) for k in hk_pt], g35.get("lat"), g35.get("lon"),
        [(r["대학명"], r["권역"], r.get("연결캠퍼스명"), r.get("위도"), r.get("경도")) for r in hk_rows],
        "없음 -> 좌표 반영·행 추가 안 함" if not pt_rows else pt_rows))
    rep.append("[작업 3] 평택시 IT 학과(한경 경기 행 IT 목록 중 표준데이터 평택시 소재): %s" % dict(pt_it))

    # ------------------------------------------------ 저장 (작업 2·3)
    undergrad = [r for reg in master["byRegion"] for r in master["byRegion"][reg]]
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])
    master.setdefault("변경이력", []).append(
        "%s apply_decisions_v4.py: 좌표 3건 확정(재능대·포항대·예원예대 양주), 한국복지대 후속 캠퍼스 확정" % TODAY)
    rc = defaultdict(int)
    for m in markers["markers"]:
        rc[m["region"]] += 1
    markers["stats"].update({"totalMarkers": len(markers["markers"]), "regionCounts": dict(rc), "prevMarkers": 305,
                             "added": 3, "removed": 0})
    markers["note"].append("%s apply_decisions_v4.py: 장소 검색 후보 사용자 확정 3건 추가." % TODAY)
    review["count"] = len(review["items"])
    review["version"] = 3
    merged["updated"] = TODAY
    linked = {(r["대학명"], r["권역"]) for r in undergrad if not r["좌표미확보"]}
    mk = {(m["univ"], m["region"]) for m in markers["markers"] if "mergedFrom" not in m}
    assert linked == mk, "마스터-마커 불일치: %s" % (linked ^ mk)
    save_json("university_master_list_v2.json", master)
    save_json("phase1_markers_v3.json", markers)
    save_json("coords_review_v2.json", review)
    save_json("merged_schools.json", merged)
    rep.append("[저장] 마스터 학부 %d행 (좌표 %d / 미확보 %d) | 마커 305 -> %d | 검토 4 -> %d %s" % (
        len(undergrad), master["linkedCampusCount"], master["unlinkedCampusCount"], len(markers["markers"]),
        review["count"], [it["univ"] for it in review["items"]]))

    # ------------------------------------------------ 작업 4 (확인만)
    for name in ("경남과학기술대학교", "한국골프과학기술대학교"):
        ks = [k for k in kedi_nongrad if k["학교명"] == name]
        mr = [(r["대학명"], r["권역"], r.get("연결캠퍼스명"), "마커있음" if not r["좌표미확보"] else "좌표없음")
              for r in undergrad if nm(r["대학명"]) == nm(name)]
        rep.append("[작업 4] %s KEDI: %s | 마스터: %s" % (name, [(k["학제"], k["상태"], k["본분교"], k["주소"]) for k in ks], mr))
    gn = [k for k in kedi_nongrad if k["학교명"] == "경상국립대학교"]
    rep.append("[작업 4] 경상국립대 KEDI 운영 행: %s (동진로 33 행 없음)" % [(k["본분교"], k["주소"]) for k in gn])

    # 폐지 학과만 있는 마커
    status = defaultdict(set)
    for x in dedup:
        status[(nm(x["schlNm"]), SIDO_ALIASES.get(x["ctpvNm"]), x["scsbjtNm"])].add(x["scsbjtSttsNm"])
    only_closed, unknown = [], []
    for m in markers["markers"]:
        src = m.get("mergedFrom") or m["univ"]
        a = c = u = 0
        for d in m["itDepts"]:
            s = status.get((nm(src), m["region"], d))
            if not s:
                u += 1
            elif s & ACTIVE:
                a += 1
            else:
                c += 1
        if m["itDepts"] and a == 0 and c > 0:
            only_closed.append((m["univ"], m["campus"], m["region"], c, u, m["hasITDept"], m.get("mergedFrom")))
        if u:
            unknown.append((m["univ"], m["region"], u, len(m["itDepts"])))
    rep.append("[작업 4] 폐지 IT 학과만 있는 마커 %d개 (운영 학과 0, 폐과 1 이상). hasITDept=True %d개" % (
        len(only_closed), sum(1 for x in only_closed if x[5])))
    for x in only_closed:
        rep.append("    - %s | %s | %s | 폐과 %d, 상태불명 %d | hasITDept=%s%s" % (
            x[0], x[1], x[2], x[3], x[4], x[5], " | 구 학교 %s" % x[6] if x[6] else ""))
    rep.append("[작업 4] 학과 상태를 표준데이터에서 찾지 못한 학과가 있는 마커 %d개: %s" % (len(unknown), unknown))

    # 영산대 두 행
    ys = [r for r in undergrad if r["대학명"].startswith("영산대")]
    for r in ys:
        rep.append("[작업 4] %s | 연결 %s | %s | %.5f,%.5f | IT %d개" % (
            r["대학명"], r.get("연결캠퍼스명"), r.get("주소"), r["위도"], r["경도"], len(r["보유IT계열학과명목록"])))
    if len(ys) == 2:
        rep.append("[작업 4] 영산대 두 행 거리 %.1fkm" % km((ys[0]["위도"], ys[0]["경도"]), (ys[1]["위도"], ys[1]["경도"])))
    ysk = [(k["본분교"], k["주소"]) for k in kedi_nongrad if k["학교명"] == "영산대학교"]
    rep.append("[작업 4] KEDI 영산대학교: %s" % ysk)

    with io.open(P("decisions_v4_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print("\n".join(rep))


if __name__ == "__main__":
    main()
