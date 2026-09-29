# -*- coding: utf-8 -*-
"""좌표 22행 처리 결과에 대한 사용자 결정(2026-09-24)을 반영한다.

입력(읽기만): phase1_markers_v2.json, coords_review.json, coords_unresolved.json,
             university_master_list.json, kedi_multi_address_review.json, univ_major_dedup.json, KEDI xlsx
출력(새 파일): phase1_markers_v3.json, university_master_list_v2.json, merged_schools.json,
             coords_review_v2.json, coords_unresolved_v2.json, 4yr_list_gyeonggi_incheon_yeongnam.md,
             decisions_v3_report.txt
원칙: 좌표 추정 안 함 / 후보 2개 이상 자동 선택 안 함 / 학과 데이터 수정 안 함.
"""
import copy
import io
import json
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict

from fill_coords_from_kedi import load_kedi
from geocode_gyeongnam_univ import load_env
from resolve_coords22 import (P, SIDO_ALIASES, addr_core, addr_key, geocode_variants, km, load_json, save_json,
                              sha, is_grad)

TODAY = "2026-09-24"
APPROVAL = "사용자 승인 (%s 작업 지시)" % TODAY
INPUTS = ["phase1_markers_v2.json", "coords_review.json", "coords_unresolved.json", "university_master_list.json",
          "kedi_multi_address_review.json", "univ_major_dedup.json"]
KEDI_SRC = "KEDI 2026 고등교육통계 학교별 주요 현황(xlsx)"

# 1. 캠퍼스 확정 (사용자 승인): 대학명 -> (권역, 본분교, 주소에 들어 있어야 하는 시군)
CAMPUS_CONFIRM = {
    "경동대학교": ("강원", "본교(제1캠퍼스)", "고성군"),
    "유원대학교": ("충청", "본교(제2캠퍼스)", "아산시"),
    "국립한국교통대학교": ("충청", "본교(제1캠퍼스)", "충주시"),
}
# 2. 대학원 행
GRAD_ROWS = [("서울과학기술대학교 나노IT디자인융합대", "서울"), ("한국외국어대학교 글로벌미디어커뮤니케이", "서울"),
             ("한국공학대학교 지식기반기술·에너지대학", "경기"), ("한국기술교육대학교 IT융합과학경영산업", "충청")]
# 3. 통합·폐교 학교: 구 학교명 -> 권역
MERGED = {"서라벌대학교": "영남", "성심외국어대학": "영남", "전남도립대학교": "호남", "경남도립거창대학": "영남",
          "경북도립대학교": "영남", "국립강릉원주대학교": "강원", "한국복지대학교": "경기"}
# 4. 원격대학
REMOTE_ROWS = [("한국방송통신대학교", "서울"), ("서울디지털대학교", "서울"), ("부산디지털대학교", "영남")]
# 5. 장소 검색 재시도 대상: 대학명 -> (권역, 기존 주소)
SEARCH_TARGETS = ["재능대학교", "포항대학교", "예원예술대학교"]
ACTIVE_STATUS = ("기존", "신설", "변경")
FOUR_YEAR = ("대학교", "산업대학")  # 교육대학은 SPEC 12번 조사 순서에 따라 4년제 목록에서 분리


def sgg_of(addr):
    """주소에서 '시 구' 또는 '시/군'까지의 시군구 표기를 뽑는다."""
    a = re.sub(r"\([^)]*\)", "", addr or "")
    m = re.search(r"(\S+시)\s+(\S+구)\s", a + " ")
    if m:
        return m.group(1) + " " + m.group(2)
    m = re.search(r"(\S+[시군구])\s", a + " ")
    return m.group(1) if m else None


def place_search(key, query):
    p = {"service": "search", "request": "search", "version": "2.0", "query": query, "type": "place",
         "format": "json", "size": "100", "page": "1", "crs": "EPSG:4326", "key": key}
    url = "https://api.vworld.kr/req/search?" + urllib.parse.urlencode(p)
    for attempt in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                         timeout=30).read()
            return json.loads(raw.decode("utf-8"))["response"]
        except Exception as e:  # noqa
            last = e
            time.sleep(1 + attempt)
    return {"status": "ERROR", "error": repr(last)}


def dept_status(dedup, univ, it_names, sgg=None):
    """구 학교 IT 학과를 운영(기존·신설·변경 중 하나라도 있음)/폐지(폐과만)로 나눈다."""
    st = defaultdict(set)
    for r in dedup:
        if r["schlNm"] == univ and r["scsbjtNm"] in it_names and (sgg is None or r["sggNm"] == sgg):
            st[r["scsbjtNm"]].add(r["scsbjtSttsNm"])
    active = sorted(n for n, s in st.items() if s & set(ACTIVE_STATUS))
    closed = sorted(n for n, s in st.items() if not (s & set(ACTIVE_STATUS)))
    return active, closed


def main():
    before = {n: sha(n) for n in INPUTS}
    markers = load_json("phase1_markers_v2.json")
    review = load_json("coords_review.json")
    unresolved = load_json("coords_unresolved.json")
    master_src = load_json("university_master_list.json")
    kmr = load_json("kedi_multi_address_review.json")
    assert len(markers["markers"]) == 305 and review["count"] == 9 and unresolved["count"] == 3
    dedup = load_json("univ_major_dedup.json")["items"]
    kedi = load_kedi()
    key = load_env(P(".env"))["VWORLD_KEY"]

    master = copy.deepcopy(master_src)
    by_region = master["byRegion"]
    rows = {(r["대학명"], r["권역"]): r for reg in by_region for r in by_region[reg]}
    new_markers = [m for m in markers["markers"]]
    log = []
    removed_markers, added_markers = [], []

    def take_row(univ, region):
        r = rows.pop((univ, region))
        by_region[region].remove(r)
        return r

    def drop_markers(univ, region):
        hit = [m for m in new_markers if m["univ"] == univ and m["region"] == region]
        for m in hit:
            new_markers.remove(m)
            removed_markers.append((univ, m["campus"]))
        return hit

    exclude = []

    # ---------------- 0) 지난번(coords22) 해결 행 중 이번 결정과 무관하게 남는 행을 마스터에 반영
    kept_prev = [m for m in markers["markers"][295:] if m["univ"] not in MERGED]
    for m in kept_prev:
        r = rows[(m["univ"], m["region"])]
        r.update({"연결캠퍼스명": m["campus"], "매칭방식": "coords22_kedi_rematch", "좌표미확보": False,
                  "위도": m["lat"], "경도": m["lon"], "주소": m["address"],
                  "좌표출처": "resolve_coords22.py (KEDI 재매칭 주소 -> VWorld)"})
    log.append("0) 지난번 해결 행 마스터 반영: %s" % [m["univ"] for m in kept_prev])

    # ---------------- 1) 캠퍼스 확정 3건
    confirmed = []
    for univ, (region, campus, city) in CAMPUS_CONFIRM.items():
        item = next(it for it in kmr["items"] if it["univ"] == univ and it["region"] == region)
        cand = [c for c in item["candidates"] if c["본분교"] == campus]
        assert len(cand) == 1 and city in cand[0]["주소"], "%s: 지정 캠퍼스 후보 불일치" % univ
        c = cand[0]
        g = geocode_variants(key, c["주소"])
        assert "lat" in g, "%s: 지오코딩 실패" % univ
        r = rows[(univ, region)]
        assert r["좌표미확보"]
        label = "%s (%s)" % (c["학교명"], campus)
        r.update({"연결캠퍼스명": label, "매칭방식": "kedi_manual_designation", "좌표미확보": False,
                  "위도": g["lat"], "경도": g["lon"], "주소": c["주소"],
                  "좌표출처": "KEDI 후보 주소 사용자 수동 지정 -> VWorld", "지오코딩방식": g["type"],
                  "source": {"지정": APPROVAL, "근거": "운영 중 IT 학과 소재지(univ_major_dedup.json)"}})
        r.pop("KEDI주소후보", None)
        mk = {"univ": univ, "campus": label, "region": region, "lat": g["lat"], "lon": g["lon"],
              "hasITDept": len(r["보유IT계열학과명목록"]) > 0, "itDepts": r["보유IT계열학과명목록"],
              "coordSource": "v3 캠퍼스 확정(사용자 승인)", "address": c["주소"]}
        new_markers.append(mk)
        added_markers.append((univ, label))
        confirmed.append({"univ": univ, "region": region, "campus": label, "address": c["주소"],
                          "lat": g["lat"], "lon": g["lon"], "refined": g["refined"]})
    log.append("1) 캠퍼스 확정: %s" % [(c["univ"], c["campus"], round(c["lat"], 5), round(c["lon"], 5))
                                    for c in confirmed])
    # 교통대 의왕(경기) 행이 그대로인지 확인
    uiwang = rows[("국립한국교통대학교", "경기")]
    assert uiwang == next(r for r in master_src["byRegion"]["경기"] if r["대학명"] == "국립한국교통대학교")

    # ---------------- 2) 대학원 4행 제외
    for univ, region in GRAD_ROWS:
        r = take_row(univ, region)
        assert not drop_markers(univ, region)
        exclude.append(dict(r, 제외사유="대학원", 제외근거="표준데이터 학교구분이 전문대학원/특수대학원, KEDI에 같은 이름의 대학원 행",
                            제외승인=APPROVAL))

    # ---------------- 3) 통합·폐교 7곳
    merged_out = []
    extra_review = []
    for old, region in MERGED.items():
        r = take_row(old, region)
        dropped = drop_markers(old, region)
        it_names = set(r["보유IT계열학과명목록"])
        active, closed = dept_status(dedup, old, it_names)
        old_rows = [k for k in kedi if not is_grad(k) and k["학교명"] == old]
        entry = {"구학교명": old, "권역": region,
                 "KEDI구학교행": [{"본분교": k["본분교"], "학제": k["학제"], "상태": k["상태"], "주소": k["주소"]}
                               for k in old_rows],
                 "IT학과수": {"전체": len(active) + len(closed), "운영중": len(active), "폐지": len(closed)},
                 "IT학과_운영중": active, "IT학과_폐지": closed,
                 "IT학과수_기준": "univ_major_dedup.json. 같은 학과명에 기존·신설·변경 상태가 하나라도 있으면 운영중, "
                              "폐과만 있으면 폐지",
                 "후속캠퍼스": [], "별도마커": "없음(%s)" % APPROVAL,
                 "삭제한_v2마커": [m["campus"] for m in dropped]}
        succ_rows = []
        for k0 in old_rows:
            for k in kedi:
                if not is_grad(k) and k["상태"] != "폐교" and addr_key(k["주소"]) == addr_key(k0["주소"]):
                    succ_rows.append((k0, k))
        if not succ_rows:
            # 한국복지대학교: 같은 주소의 운영 중 행이 없음 -> 한경국립대 평택 소재 행만 찾아 검토로 남긴다
            hk = [k for k in kedi if not is_grad(k) and k["학교명"].startswith("한경") and "평택" in k["주소"]]
            hk_dedup = sorted(set(x["scsbjtNm"] for x in dedup if x["schlNm"] == "한경국립대학교"
                                  and x["sggNm"] == "평택시"))
            old_depts = sorted(set(x["scsbjtNm"] for x in dedup if x["schlNm"] == old))
            ev = ["KEDI %s 행은 폐교이고, 같은 주소(%s)의 운영 중 행이 없음" % (old, addr_core(old_rows[0]["주소"])),
                  "KEDI 한경국립대 평택 소재 행: %s" % ("; ".join("%s %s [%s] %s" % (k["학교명"], k["본분교"], k["상태"],
                                                                             k["주소"]) for k in hk) or "없음"),
                  "주소가 서로 달라(삼남로 283 vs %s) 같은 캠퍼스인지 자료로 확인되지 않음" % (
                      addr_core(hk[0]["주소"]).split(" ", 2)[-1] if hk else "-"),
                  "표준데이터 한경국립대 평택시 학과 %d개, 한국복지대 학과 %d개, 학과명 완전일치 %s" % (
                      len(hk_dedup), len(old_depts), sorted(set(hk_dedup) & set(old_depts)) or "없음"),
                  "보유 파일 안에 두 학교의 통합 관계를 적은 자료는 없음"]
            cands = []
            for k in hk:
                g = geocode_variants(key, k["주소"])
                c = {"학교명": k["학교명"], "본분교": k["본분교"], "상태": k["상태"], "주소": k["주소"], "출처": KEDI_SRC}
                if "lat" in g:
                    c.update({"lat": g["lat"], "lon": g["lon"]})
                    ex = [m for m in new_markers if km((g["lat"], g["lon"]), (m["lat"], m["lon"])) < 0.3]
                    c["기존마커"] = [m["campus"] for m in ex] or "없음"
                cands.append(c)
            entry.update({"확인상태": "미확인(한경국립대 평택 행은 있으나 대응 관계 미확인)", "후속캠퍼스후보": cands,
                          "근거": ev})
            result = "검토" if hk else "미확인"
            extra_review.append({"univ": old, "region": region, "type": "통합·폐교 후속 캠퍼스", "result": result,
                                 "candidates": cands, "evidence": ev,
                                 "decisionNeeded": "한국복지대 → 한경국립대 평택캠퍼스 대응 여부, 대응 시 평택 마커 추가 여부",
                                 "needed": ["한국복지대 통합(승계) 관계와 평택 캠퍼스 현재 주소를 적은 자료 "
                                            "(예: 교육부 통합 승인 공고, 한경국립대 캠퍼스 안내)"]})
        else:
            for k0, k in succ_rows:
                g = geocode_variants(key, k["주소"])
                assert "lat" in g, "%s 후속 주소 지오코딩 실패" % k["학교명"]
                label = "%s (%s)" % (k["학교명"], k["본분교"])
                near = [m for m in new_markers if km((g["lat"], g["lon"]), (m["lat"], m["lon"])) < 0.3]
                same_univ = [m for m in near if m["univ"].split("(")[0] == k["학교명"]]
                sgg = re.search(r"(\S+[시군구])\s", re.sub(r"^\S+\s", "", addr_core(k0["주소"])) + " ").group(1)
                a2, c2 = dept_status(dedup, old, it_names, sgg=sgg)
                s = {"후속학교": k["학교명"], "후속캠퍼스": label, "학제": k["학제"], "주소": k["주소"],
                     "구학교캠퍼스": k0["본분교"], "대응근거": "KEDI 폐교 행 주소 = 운영 중 행 주소 (%s)" % addr_core(k["주소"]),
                     "lat": g["lat"], "lon": g["lon"], "이캠퍼스_구학교IT학과": {"운영중": a2, "폐지": c2}}
                if same_univ:
                    s["마커"] = "기존 마커 유지: %s" % same_univ[0]["campus"]
                else:
                    if near:
                        s["주의"] = "300m 이내 다른 마커: %s" % [m["campus"] for m in near]
                    depts = a2 + c2
                    mk = {"univ": k["학교명"], "campus": label, "region": region, "lat": g["lat"], "lon": g["lon"],
                          "hasITDept": len(depts) > 0, "itDepts": depts,
                          "coordSource": "v3 통합·폐교 후속 캠퍼스 (KEDI 운영 중 행 주소 -> VWorld)",
                          "address": k["주소"], "mergedFrom": old,
                          "itDeptsSource": "구 학교(%s) IT 학과 중 이 시군(%s) 소재분. 후속 학교 명의의 학과 자료는 "
                                           "표준데이터에 이 시군 행이 없음" % (old, sgg)}
                    new_markers.append(mk)
                    added_markers.append((k["학교명"], label))
                    s["마커"] = "이번에 추가"
                entry["후속캠퍼스"].append(s)
            entry["확인상태"] = "확인(주소 일치)"
        merged_out.append(entry)
        exclude.append(dict(r, 제외사유="통합·폐교", 후속캠퍼스=[s["후속캠퍼스"] for s in entry["후속캠퍼스"]] or "미확인",
                            제외승인=APPROVAL))

    # ---------------- 4) 원격대학 3곳
    for univ, region in REMOTE_ROWS:
        r = take_row(univ, region)
        d = drop_markers(univ, region)
        exclude.append(dict(r, 제외사유="원격대학", 삭제한마커=[m["campus"] for m in d], 제외승인=APPROVAL))

    # ---------------- 5) 장소 검색 재시도
    old_items = {it["univ"]: it for it in review["items"] + unresolved["items"]}
    review_v2, unresolved_v2 = [], []
    for univ in SEARCH_TARGETS:
        it = old_items[univ]
        region = it["region"]
        r = rows[(univ, region)]
        base_addr = (re.search(r"KEDI 주소:\s*(.+)$", it["evidence"][0]) or [None, ""])[1]
        want = sgg_of(base_addr)
        resp = place_search(key, univ)
        items = (resp.get("result") or {}).get("items", [])
        total = int((resp.get("record") or {}).get("total", len(items)))
        uniq = {}
        for x in items:
            if univ not in x["title"].replace(" ", ""):
                continue
            road, parcel = x["address"].get("road", ""), x["address"].get("parcel", "")
            k = (x["title"], x.get("category"), road, parcel)
            if k not in uniq:
                uniq[k] = {"title": x["title"], "category": x.get("category"), "road": road, "parcel": parcel,
                           "lat": float(x["point"]["y"]), "lon": float(x["point"]["x"]),
                           "sameSgg": bool(want) and want in (road + " " + parcel)}
        school_like = [v for v in uniq.values() if (v["category"] or "").endswith("대학교")]
        ev = ["기존 주소: %s (시군구 %s)" % (base_addr, want),
              "VWorld 장소 검색 '%s': 전체 %d건 (API 응답 %d건 확인)" % (univ, total, len(items)),
              "제목에 학교명이 들어간 결과 %d건, 그중 분류가 '교육부 > 대학교'인 결과 %d건" % (len(uniq), len(school_like)),
              "결과가 1건이 아니라 규칙에 따라 자동 확정 안 함"]
        entry = {"univ": univ, "region": region, "type": "A(장소 검색 재시도)", "itDepts": r["보유IT계열학과명목록"],
                 "searchTotal": total, "candidates": school_like, "otherTitleMatches": len(uniq) - len(school_like),
                 "evidence": ev, "prevEvidence": it["evidence"]}
        if total == 1 and school_like and school_like[0]["sameSgg"]:
            raise SystemExit("검색 결과 1건 — 해결 처리 로직 필요: %s" % univ)
        elif total >= 1:
            entry["result"] = "검토"
            entry["decisionNeeded"] = "후보 중 캠퍼스 좌표 선택 (같은 시군구 후보: %d건)" % sum(1 for v in school_like if v["sameSgg"])
            review_v2.append(entry)
        else:
            entry.update({"result": "미확인", "needed": it.get("needed", ["캠퍼스 지번주소 또는 공식 좌표"])})
            unresolved_v2.append(entry)
    for e in extra_review:
        (review_v2 if e["result"] == "검토" else unresolved_v2).append(e)

    # ---------------- 마스터 v2 정리
    master["제외_지도대상"] = {"note": "지도에서 제외한 학부 조사 대상 행 (%s). 행은 삭제하지 않고 여기로 옮김." % APPROVAL,
                           "count": len(exclude), "사유별": {s: sum(1 for e in exclude if e["제외사유"] == s)
                                                          for s in ("대학원", "통합·폐교", "원격대학")},
                           "items": exclude}
    undergrad = [r for reg in by_region for r in by_region[reg]]
    master["학부조사대상_전체"] = len(undergrad)
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])
    master["regionCounts"] = {reg: len(by_region[reg]) for reg in by_region}
    master.setdefault("변경이력", []).append(
        "%s apply_decisions_v3.py: 캠퍼스 확정 3, 지난번 재매칭 5행 좌표 반영, 제외 %d행(대학원 4/통합·폐교 7/원격 3)"
        % (TODAY, len(exclude)))

    # ---------------- 마커 v3
    out_markers = copy.deepcopy(markers)
    out_markers["markers"] = new_markers
    rc = defaultdict(int)
    for m in new_markers:
        rc[m["region"]] += 1
    out_markers["stats"] = {"totalMarkers": len(new_markers), "regionCounts": dict(rc), "prevMarkers": 305,
                            "removed": len(removed_markers), "added": len(added_markers)}
    out_markers["note"].append("%s apply_decisions_v3.py: 캠퍼스 확정 3 추가, 통합·폐교 구 학교 마커 5 삭제 후 후속 캠퍼스 "
                               "마커 추가, 원격대학 마커 삭제. 추가 행에만 coordSource/address(/mergedFrom) 필드가 있음."
                               % TODAY)
    # 마스터 좌표 연결 행 == 마커(후속 캠퍼스 마커 제외) 대응 확인
    linked = {(r["대학명"], r["권역"]) for r in undergrad if not r["좌표미확보"]}
    mk_keys = {(m["univ"], m["region"]) for m in new_markers if "mergedFrom" not in m}
    diff = linked ^ mk_keys
    log.append("마스터 좌표연결 행 vs 마커 대응 차이: %s" % (sorted(diff) or "없음"))

    save_json("phase1_markers_v3.json", out_markers)
    save_json("university_master_list_v2.json", master)
    save_json("merged_schools.json", {"version": 1, "date": TODAY, "generatedBy": "apply_decisions_v3.py",
                                      "note": "통합·폐교된 구 학교와 후속 학교 캠퍼스의 대응. 구 학교는 별도 마커를 두지 않음.",
                                      "count": len(merged_out), "items": merged_out})
    save_json("coords_review_v2.json", {"version": 2, "date": TODAY, "generatedBy": "apply_decisions_v3.py",
                                        "note": "후보가 여러 개라 자동 확정하지 않은 행. 후보 좌표는 판단용이며 마커에 넣지 않음.",
                                        "count": len(review_v2), "items": review_v2})
    save_json("coords_unresolved_v2.json", {"version": 2, "date": TODAY, "generatedBy": "apply_decisions_v3.py",
                                            "note": "보유 자료와 VWorld로 확인하지 못한 행.",
                                            "count": len(unresolved_v2), "items": unresolved_v2})

    # ---------------- 6) DGIST 확인 (보고만)
    dg_name = "대구경북과학기술원"
    dg_dedup = defaultdict(list)
    for x in dedup:
        if x["schlNm"].startswith(dg_name):
            dg_dedup[(x["schlNm"], x["schlSeNm"])].append("%s(%s,%s)" % (x["scsbjtNm"], x["degCrseCrsNm"],
                                                                        x["scsbjtSttsNm"]))
    dg_kedi = [k for k in kedi if k["학교명"].startswith(dg_name)]
    raw = open(P("경상남도교육청_대학정보_20250918.csv"), "rb").read().decode("cp949")
    dg_csv = [l for l in raw.splitlines() if re.search("DGIST|대구경북과학|디지스트", l)]
    dg_master = [e["대학명"] for sec in ("제외_grad_only",) for e in master_src[sec]["items"] if e["대학명"].startswith(dg_name)]
    log.append("6) DGIST: dedup=%s | KEDI=%s | 경남CSV=%d건 | 마스터 제외_grad_only=%s" % (
        dict(dg_dedup), [(k["학교명"], k["학제"], k["상태"], k["주소"]) for k in dg_kedi], len(dg_csv), dg_master))

    # ---------------- 7) 4년제 목록 (경기·인천·영남)
    kedi_nongrad = [k for k in kedi if not is_grad(k)]

    def nm(s):
        return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", s or ""))

    def kedi_type(r):
        link = r.get("연결캠퍼스명") or ""
        m = re.match(r"^(.*?)\s*\((본교\(제\d캠퍼스\)|분교.*?)\)$", link)
        if m:
            hit = [k for k in kedi_nongrad if nm(k["학교명"]) == nm(m.group(1)) and k["본분교"] == m.group(2)]
            if hit:
                return sorted(set(k["학제"] for k in hit)), "연결캠퍼스(학교명+본분교)"
        for name in (r["대학명"], link.split("(")[0]):
            hit = [k for k in kedi_nongrad if nm(k["학교명"]) == nm(name)]
            if hit:
                return sorted(set(k["학제"] for k in hit)), "학교명"
        return [], "매칭 없음"

    md = ["# 4년제 목록: 경기·인천·영남", "",
          "- 기준: university_master_list_v2.json 학부 조사 대상 행 (%s 정리본)" % TODAY,
          "- 4년제 판정: KEDI 2026 학교별 현황의 **학제** 열 값만 사용 (KEDI 파일에 '학교종류'라는 이름의 열은 없고, "
          "학교 종류는 '학제' 열에 있음). 4년제로 본 값: %s. 교육대학은 SPEC 12번 조사 순서(4년제 다음)에 따라 아래 참고 표로 분리" % ", ".join(FOUR_YEAR),
          "- KEDI 매칭: 연결캠퍼스명(학교명+본분교) 우선, 없으면 학교명 일치. 대학원 학제 행은 매칭에서 뺌.", ""]
    no_type, other_type = [], []
    total4 = 0
    for reg in ("경기", "인천", "영남"):
        four = []
        for r in sorted(by_region[reg], key=lambda x: x["대학명"]):
            types, how = kedi_type(r)
            if not types:
                no_type.append((reg, r, how))
            elif len(types) == 1 and types[0] in FOUR_YEAR:
                four.append((r, types[0], how))
            elif any(t in FOUR_YEAR for t in types):
                other_type.append((reg, r, "/".join(types) + " (값이 여러 개)"))
            else:
                other_type.append((reg, r, "/".join(types)))
        total4 += len(four)
        md += ["## %s (%d)" % (reg, len(four)), "", "| # | 대학명 | 연결 캠퍼스 | KEDI 학제 | 좌표 |", "|---|---|---|---|---|"]
        for i, (r, t, how) in enumerate(four, 1):
            md.append("| %d | %s | %s | %s | %s |" % (i, r["대학명"], r.get("연결캠퍼스명") or "-", t,
                                                   "미확보" if r["좌표미확보"] else "있음"))
        md.append("")
    md += ["## 학제 값이 없는 행 (%d)" % len(no_type), "", "KEDI에서 학교명을 찾지 못해 4년제 여부를 판정하지 않은 행.", "",
           "| 권역 | 대학명 | 연결 캠퍼스 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], r.get("연결캠퍼스명") or "-") for reg, r, _ in no_type]
    md += ["", "## 참고: 4년제가 아닌 학제 (%d)" % len(other_type), "", "| 권역 | 대학명 | KEDI 학제 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], t) for reg, r, t in other_type]
    with io.open(P("4yr_list_gyeonggi_incheon_yeongnam.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    log.append("7) 4년제 %d행, 학제 값 없음 %d행, 비4년제 %d행" % (total4, len(no_type), len(other_type)))

    after = {n: sha(n) for n in INPUTS}
    assert before == after, "입력 파일이 바뀌었음"
    log.append("입력 파일 해시 변동 없음")
    log.append("마커 305 -> %d (삭제 %d: %s / 추가 %d: %s)" % (len(new_markers), len(removed_markers), removed_markers,
                                                         len(added_markers), added_markers))
    log.append("마스터 학부 행 %d (좌표 %d / 미확보 %d), 제외_지도대상 %d" % (
        len(undergrad), master["linkedCampusCount"], master["unlinkedCampusCount"], len(exclude)))
    log.append("검토 %d: %s / 미확인 %d: %s" % (len(review_v2), [e["univ"] for e in review_v2],
                                           len(unresolved_v2), [e["univ"] for e in unresolved_v2]))
    for e in merged_out:
        log.append("  통합: %s -> %s | IT 운영 %d / 폐지 %d | %s" % (
            e["구학교명"], [(s["후속캠퍼스"], s["마커"]) for s in e["후속캠퍼스"]] or e.get("후속캠퍼스후보"),
            e["IT학과수"]["운영중"], e["IT학과수"]["폐지"], e["확인상태"]))
    for e in review_v2:
        log.append("  검토: %s | %s | 같은 시군구 후보 %d" % (e["univ"], e["evidence"][1] if len(e["evidence"]) > 1 else "",
                                                     sum(1 for c in e["candidates"] if c.get("sameSgg"))))
    with io.open(P("decisions_v3_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log))
    print("\n".join(log))


if __name__ == "__main__":
    main()
