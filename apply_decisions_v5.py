# -*- coding: utf-8 -*-
"""컷맵 작업 지시 2 (2026-09-24) — 작업 11·12 반영.

수정(백업: backup_20260924_decisions_v5/): university_master_list_v2.json, phase1_markers_v3.json,
  coords_review_v2.json, merged_schools.json, 4yr_list_*.md 2개
새 파일: undetermined_markers_check_20260924.md, decisions_v5_report.txt
SPEC_대학맵.md는 Edit로 따로 수정.
원칙: 좌표 추정 안 함 / 학과 데이터(univ_major_dedup.json) 수정 안 함.
"""
import copy
import io
import json
import os
import re
from collections import defaultdict

from fill_coords_from_kedi import load_kedi
from geocode_gyeongnam_univ import load_env
from resolve_coords22 import P, SIDO_ALIASES, geocode_variants, is_grad, km, load_json, save_json, sha

TODAY = "2026-09-24"
APPROVAL = "사용자 결정 (%s 작업 지시 2, 작업 11)" % TODAY
BACKUP = "backup_20260924_decisions_v5"
ACTIVE = {"기존", "신설", "변경"}
FOUR_YEAR = ("대학교", "산업대학")
IT_KEYWORDS = ["AI", "데이터", "소프트웨어", "인공지능", "전기", "전자", "정보보안", "정보보호", "정보통신", "컴퓨터"]

HK_ANSEONG = ("한경국립대학교", "경기")
HK_PT_NAME = "한경국립대학교(평택)"
HK_PT_ADDR = "경기 평택시 한경대학로 35"
HK_PT_MOVE = ["AI반도체융합전공", "AI반도체융합학부"]
HK_PT_BASIS = "공식 주소 삼남로 283은 VWorld 미조회, 한경대학로 35의 지번(장안동 5-3)이 옛 한국복지대 지번과 일치, 도로명 변경 여부 미확인"
GN = ("경남과학기술대학교", "영남")
GN_SUCC_TEXT = "KEDI 주소 비고상 칠암캠퍼스, KEDI에 해당 행 없음, 미확인"
HB_DUP = ("한밭대학교(산업대)", "충청")
HB_CUR = ("국립한밭대학교", "충청")
TAEJAE = ("태재대학교", "서울")
YEWON = ("예원예술대학교", "경기")
YEWON_KEDI = "경기도 양주시 은현면 화합로1134번길 110 (용암리, 예원예술대학교양주캠퍼스)"
UNDET_REASON = "데이터상 모집 중 IT 학과 없음(폐지만), 2차 IT 판정에서 재확인"


def nm(s):
    return re.sub(r"\s+", "", re.sub(r"\s*\([^)]*\)\s*$", "", s or ""))


def flat(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from flat(v)
    elif isinstance(o, list):
        for v in o:
            yield from flat(v)
    elif isinstance(o, str):
        yield o


def build_4yr(master, kedi_nongrad, regions, title, fname):
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

    md = ["# 4년제 목록: %s" % title, "",
          "- 기준: university_master_list_v2.json 학부 조사 대상 행 (%s 작업 11 반영본)" % TODAY,
          "- 4년제 판정: KEDI 2026 학교별 현황의 **학제** 열 값만 사용 (KEDI 파일에 '학교종류'라는 이름의 열은 없고, "
          "학교 종류는 '학제' 열에 있음). 4년제로 본 값: %s (값이 여러 개여도 모두 이 값이면 4년제). "
          "교육대학은 SPEC 12번 조사 순서(4년제 다음)에 따라 아래 참고 표로 분리" % ", ".join(FOUR_YEAR),
          "- KEDI 매칭: 연결캠퍼스명(학교명+본분교) 우선, 없으면 학교명 일치. 대학원 학제 행은 매칭에서 뺌.",
          "- IT 상태: 판정불가는 폐지 IT 학과만 있는 캠퍼스 (SPEC 3번).", ""]
    no_type, other, counts = [], [], {}
    for reg in regions:
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
        md += ["## %s (%d)" % (reg, len(four)), "",
               "| # | 대학명 | 연결 캠퍼스 | KEDI 학제 | 좌표 | IT 상태 |", "|---|---|---|---|---|---|"]
        md += ["| %d | %s | %s | %s | %s | %s |" % (i, r["대학명"], r.get("연결캠퍼스명") or "-", t,
                                                 "미확보" if r["좌표미확보"] else "있음", r.get("IT유무상태", "-"))
               for i, (r, t) in enumerate(four, 1)]
        md.append("")
    md += ["## 학제 값이 없는 행 (%d)" % len(no_type), "", "KEDI에서 학교명을 찾지 못해 4년제 여부를 판정하지 않은 행.", "",
           "| 권역 | 대학명 | 연결 캠퍼스 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], r.get("연결캠퍼스명") or "-") for reg, r in no_type]
    md += ["", "## 참고: 4년제가 아닌 학제 (%d)" % len(other), "", "| 권역 | 대학명 | KEDI 학제 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (reg, r["대학명"], t) for reg, r, t in other]
    with io.open(P(fname), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")
    types = defaultdict(int)
    for _, _, t in other:
        types[t] += 1
    return counts, len(no_type), dict(types), [r["대학명"] for _, r in no_type]


def main():
    for f in ("university_master_list_v2.json", "phase1_markers_v3.json", "coords_review_v2.json",
              "merged_schools.json", "SPEC_대학맵.md", "4yr_list_gyeonggi_incheon_yeongnam.md",
              "4yr_list_seoul_chungcheong_gangwon_jeju_honam.md"):
        assert os.path.exists(P(os.path.join(BACKUP, f))), "백업 없음: %s" % f
    dedup_sha = sha("univ_major_dedup.json")
    master = load_json("university_master_list_v2.json")
    markers = load_json("phase1_markers_v3.json")
    review = load_json("coords_review_v2.json")
    merged = load_json("merged_schools.json")
    assert len(markers["markers"]) == 308 and review["count"] == 1 and merged["count"] == 7
    kedi = load_kedi()
    kedi_nongrad = [k for k in kedi if not is_grad(k)]
    dedup = load_json("univ_major_dedup.json")["items"]
    key = load_env(P(".env"))["VWORLD_KEY"]
    by_region = master["byRegion"]
    rows = {(r["대학명"], r["권역"]): r for reg in by_region for r in by_region[reg]}
    mk = markers["markers"]
    excl = master["제외_지도대상"]
    rep = []
    removed, added = [], []

    status = defaultdict(set)
    for x in dedup:
        status[(nm(x["schlNm"]), SIDO_ALIASES.get(x["ctpvNm"]), x["scsbjtNm"])].add(x["scsbjtSttsNm"])

    def dept_split(univ, region, names):
        a, c, u = [], [], []
        for d in names:
            s = status.get((nm(univ), region, d))
            (u if not s else a if s & ACTIVE else c).append(d)
        return a, c, u

    def take(key_):
        r = rows.pop(key_)
        by_region[key_[1]].remove(r)
        return r

    def drop_marker(univ, region):
        hit = [m for m in mk if m["univ"] == univ and m["region"] == region and "mergedFrom" not in m]
        for m in hit:
            mk.remove(m)
            removed.append(m["campus"])
        return [m["campus"] for m in hit]

    # ---------------- 11-1 한경국립대 평택캠퍼스 행 + 마커
    an = rows[HK_ANSEONG]
    assert all(d in an["보유IT계열학과명목록"] for d in HK_PT_MOVE)
    g = geocode_variants(key, HK_PT_ADDR)
    assert "lat" in g
    kpt = [k for k in kedi_nongrad if k["학교명"] == "한경국립대학교" and "평택" in k["주소"]]
    assert len(kpt) == 1
    before_an = list(an["보유IT계열학과명목록"])
    an["보유IT계열학과명목록"] = [d for d in an["보유IT계열학과명목록"] if d not in HK_PT_MOVE]
    an["평택행으로_이동한학과"] = {"학과": HK_PT_MOVE, "이동": APPROVAL}
    pt = {"대학명": HK_PT_NAME, "캠퍼스구분": "평택캠퍼스", "보유IT계열학과명목록": list(HK_PT_MOVE),
          "미분류IT후보학과명목록": [], "학부구분": "undergrad", "권역": "경기",
          "권역판정근거": "사용자 지정: 한경국립대학교 평택캠퍼스 별도 행 (%s)" % TODAY,
          "연결캠퍼스명": "한경국립대학교 (%s)" % kpt[0]["본분교"], "매칭방식": "user_designated_campus_row",
          "좌표미확보": False, "위도": g["lat"], "경도": g["lon"], "주소": HK_PT_ADDR,
          "좌표출처": "KEDI 평택 행 주소(한경대학로 35) -> VWorld Geocoder", "지오코딩방식": g["type"],
          "복수캠퍼스후보": None,
          "source": {"지정": APPROVAL, "좌표근거": HK_PT_BASIS,
                     "공식주소": {"주소": "경기도 평택시 삼남로 283",
                              "url": "https://www.hknu.ac.kr/sanhak/3034/subview.do",
                              "위치": "페이지 하단 주소", "확인일": TODAY, "확인자": "사용자"},
                     "IT학과근거": "univ_major_dedup.json: 한경국립대학교 평택시 소재 AI반도체융합전공·AI반도체융합학부(기존)"}}
    by_region["경기"].append(pt)
    rows[(HK_PT_NAME, "경기")] = pt
    for m in mk:
        if (m["univ"], m["region"]) == HK_ANSEONG:
            m["itDepts"] = an["보유IT계열학과명목록"]
    mk.append({"univ": HK_PT_NAME, "campus": "한경국립대학교 평택캠퍼스 (%s)" % kpt[0]["본분교"], "region": "경기",
               "lat": g["lat"], "lon": g["lon"], "hasITDept": True, "itDepts": list(HK_PT_MOVE),
               "coordSource": "v5 사용자 지정 (%s)" % HK_PT_BASIS, "address": HK_PT_ADDR})
    added.append(HK_PT_NAME)
    ent = next(e for e in merged["items"] if e["구학교명"] == "한국복지대학교")
    s0 = ent["후속캠퍼스"][0]
    s0.update({"마스터행": HK_PT_NAME, "lat": g["lat"], "lon": g["lon"], "좌표주소": HK_PT_ADDR,
               "좌표근거": HK_PT_BASIS, "마커": "이번에 추가: %s" % HK_PT_NAME})
    s0.pop("좌표상태", None)
    s0["이전_좌표참고_판단필요"] = s0.pop("좌표참고_판단필요", None)
    ent["확인상태"] = "확인(사용자 확정, 공식 홈페이지 주소). 좌표는 한경대학로 35 VWorld 좌표 사용(사용자 결정)"
    review["items"] = [it for it in review["items"] if it["univ"] != "한국복지대학교"]
    rep.append("[11-1] 평택 행 '%s' 추가 (%.6f, %.6f, %s) | 안성 행 IT %d -> %d, 이동 %s" % (
        HK_PT_NAME, g["lat"], g["lon"], g["refined"], len(before_an), len(an["보유IT계열학과명목록"]), HK_PT_MOVE))
    a_an, c_an, _ = dept_split("한경국립대학교", "경기", an["보유IT계열학과명목록"])
    rep.append("[11-1] 안성 행 남은 IT 학과: 모집 중 %d / 폐지 %d" % (len(a_an), len(c_an)))

    # ---------------- 11-2 경남과학기술대학교 -> 통합·폐교
    r = take(GN)
    dm = drop_marker(*GN)
    a, c, u = dept_split(GN[0], GN[1], r["보유IT계열학과명목록"])
    gk = [k for k in kedi_nongrad if k["학교명"] == GN[0]]
    gsang = rows[("경상국립대학교", "영남")]
    gs_act = defaultdict(set)
    for x in dedup:
        if x["schlNm"] == "경상국립대학교" and x["scsbjtNm"] in set(gsang["보유IT계열학과명목록"]) \
                and x["scsbjtSttsNm"] in ACTIVE:
            gs_act[x["sggNm"]].add(x["scsbjtNm"])
    overlap = sorted(set().union(*gs_act.values()) & set(r["보유IT계열학과명목록"])) if gs_act else []
    chilam_note = ("표준데이터 소재지는 시군구 단위(진주시)까지만 있음. 가좌(진주대로 501)와 칠암(동진로 33)이 모두 "
                   "진주시라 칠암 소재 여부를 데이터로 구분할 수 없음")
    merged["items"].append({
        "구학교명": GN[0], "권역": GN[1],
        "KEDI구학교행": [{"본분교": k["본분교"], "학제": k["학제"], "상태": k["상태"], "주소": k["주소"]} for k in gk],
        "IT학과수": {"전체": len(a) + len(c), "운영중": len(a), "폐지": len(c)}, "IT학과_운영중": a, "IT학과_폐지": c,
        "IT학과수_기준": "univ_major_dedup.json. 같은 학과명에 기존·신설·변경 상태가 하나라도 있으면 운영중, 폐과만 있으면 폐지",
        "후속학교": "경상국립대학교", "후속캠퍼스": [{"후속학교": "경상국립대학교", "후속캠퍼스": GN_SUCC_TEXT,
                                                "마커": "만들지 않음 (%s)" % APPROVAL}],
        "칠암_IT학과_확인": {"경상국립대_모집중_IT학과_시군구별": {k: sorted(v) for k, v in gs_act.items()},
                        "구학교_IT학과명과_일치": overlap, "판단": chilam_note},
        "별도마커": "없음(%s)" % APPROVAL, "삭제한_v3마커": dm, "확인상태": "후속 학교 확인(사용자), 후속 캠퍼스 미확인"})
    excl["items"].append(dict(r, 제외사유="통합·폐교", 후속캠퍼스=GN_SUCC_TEXT, 후속학교="경상국립대학교", 제외승인=APPROVAL))
    rep.append("[11-2] 경남과기대 제외(통합·폐교), 마커 삭제 %s | IT 운영 %d / 폐지 %d" % (dm, len(a), len(c)))
    rep.append("[11-2] 경상국립대 모집 중 IT 학과 시군구별: %s" % {k: len(v) for k, v in gs_act.items()})
    rep.append("[11-2] 그중 옛 경남과기대 IT 학과명과 같은 것: %s" % overlap)

    # ---------------- 11-3 한밭대학교(산업대) -> 국립한밭대학교 중복 행
    r = take(HB_DUP)
    dm = drop_marker(*HB_DUP)
    cur = rows[HB_CUR]
    only_old = sorted(set(r["보유IT계열학과명목록"]) - set(cur["보유IT계열학과명목록"]))
    a, c, u = dept_split(HB_DUP[0], HB_DUP[1], r["보유IT계열학과명목록"])
    dup = {"구행": HB_DUP[0], "권역": HB_DUP[1], "현재행": HB_CUR[0], "현재행_캠퍼스": cur.get("연결캠퍼스명"),
           "처리": "중복 행(같은 학교의 옛 학제·옛 이름 행). 별도 마커 없음. %s" % APPROVAL,
           "구행_연결": r.get("연결캠퍼스명"), "구행_주소": r.get("주소"),
           "두행_거리_m": round(km((r["위도"], r["경도"]), (cur["위도"], cur["경도"])) * 1000),
           "구행_IT학과": {"운영중": a, "폐지": c},
           "현재행에_없는_구행_IT학과명": only_old, "삭제한_v3마커": dm}
    merged.setdefault("중복행", []).append(dup)
    excl["items"].append(dict(r, 제외사유="중복 행(옛 학제·옛 이름)", 대응행=HB_CUR[0], 제외승인=APPROVAL))
    rep.append("[11-3] 한밭대(산업대) 제외 -> 국립한밭대학교 대응, 마커 삭제 %s, 두 좌표 거리 %dm, 현재 행에 없는 옛 IT 학과명 %s"
               % (dm, dup["두행_거리_m"], only_old))

    # ---------------- 11-5 태재대학교 -> 원격대학
    r = take(TAEJAE)
    dm = drop_marker(*TAEJAE)
    tk = sorted(set(k["학제"] for k in kedi_nongrad if k["학교명"] == TAEJAE[0]))
    excl["items"].append(dict(r, 제외사유="원격대학", KEDI학제=tk, 삭제한마커=dm, 제외승인=APPROVAL))
    rep.append("[11-5] 태재대 제외(원격대학, KEDI 학제 %s), 마커 삭제 %s" % (tk, dm))

    # ---------------- 11-8 예원예대 양주 KEDI 학부 주소 재시도
    yr = rows[YEWON]
    gy = geocode_variants(key, YEWON_KEDI)
    if "lat" in gy:
        prev = (yr["위도"], yr["경도"], yr["주소"])
        dist = km((prev[0], prev[1]), (gy["lat"], gy["lon"])) * 1000
        yr.update({"위도": gy["lat"], "경도": gy["lon"], "주소": YEWON_KEDI, "좌표출처": "KEDI 학부 주소 -> VWorld",
                   "지오코딩방식": gy["type"], "이전좌표": {"위도": prev[0], "경도": prev[1], "주소": prev[2]}})
        for m in mk:
            if (m["univ"], m["region"]) == YEWON:
                m.update({"lat": gy["lat"], "lon": gy["lon"], "address": YEWON_KEDI})
        rep.append("[11-8] 예원 KEDI 주소 조회 성공 -> 좌표 변경. 이전 %s, 거리 %.0fm" % (prev, dist))
    else:
        rep.append("[11-8] 예원 KEDI 주소 '%s' VWorld 조회 실패 (%d회 시도, 모두 %s) -> 예원대학로 56 유지" % (
            YEWON_KEDI, len(gy["tries"]), sorted(set(t["status"] for t in gy["tries"]))))

    # ---------------- 11-4 폐지 학과만 있는 마커 -> 판정불가 (마커 + 마스터 행)
    undetermined = []
    for m in mk:
        src = m.get("mergedFrom") or m["univ"]
        a, c, u = dept_split(src, m["region"], m["itDepts"])
        row = rows.get((m["univ"], m["region"])) if "mergedFrom" not in m else None
        if m["itDepts"] and not a and c:
            m.update({"itStatus": "판정불가", "itJudgement": "판정불가", "hasITDept": None,
                      "itStatusReason": UNDET_REASON, "itStatusProvisional": True,
                      "itDeptCounts": {"active": 0, "closed": len(c), "unknown": len(u)}})
            if row is not None:
                row.update({"IT유무상태": "판정불가", "IT유무판정": "판정불가", "IT유무사유": UNDET_REASON,
                            "IT유무잠정": True})
            undetermined.append((m, src, c, u))
        else:
            m.update({"itStatus": "IT있음" if m["itDepts"] else "IT없음", "itJudgement": "확인됨",
                      "itStatusProvisional": True,
                      "itDeptCounts": {"active": len(a), "closed": len(c), "unknown": len(u)}})
            if row is not None:
                row.update({"IT유무상태": m["itStatus"], "IT유무판정": "확인됨", "IT유무잠정": True})
    for reg in by_region:
        for row in by_region[reg]:
            if "IT유무상태" not in row:
                row.update({"IT유무상태": "IT있음" if row["보유IT계열학과명목록"] else "IT없음", "IT유무판정": "확인됨",
                            "IT유무잠정": True})
    master["IT유무상태_필드"] = {
        "마커": "itStatus(IT있음/IT없음/판정불가), itJudgement(확인됨/판정불가), itStatusReason(판정불가 사유), "
              "itStatusProvisional(SPEC 14: CSV 완전본 확보 전 잠정값), itDeptCounts(active/closed/unknown). "
              "판정불가 마커의 hasITDept는 없음(false)으로 읽히지 않도록 null",
        "마스터행": "IT유무상태, IT유무판정, IT유무사유, IT유무잠정",
        "판정불가_기준": "보유 IT 학과가 표준데이터(univ_major_dedup.json)에서 모두 폐과이고 모집 중(기존·신설·변경) 학과가 0개",
        "근거": "SPEC 3번(확인됨·판정불가 구분, 판정불가를 없음으로 표시하지 않음), SPEC 14번(잠정값)", "적용": APPROVAL}
    rep.append("[11-4] 판정불가 마커 %d개: %s" % (len(undetermined), [m["campus"] for m, *_ in undetermined]))

    # ---------------- 정리·저장
    excl["count"] = len(excl["items"])
    excl["사유별"] = defaultdict(int)
    for e in excl["items"]:
        excl["사유별"][e["제외사유"]] += 1
    excl["사유별"] = dict(excl["사유별"])
    undergrad = [r for reg in by_region for r in by_region[reg]]
    master["학부조사대상_전체"] = len(undergrad)
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])
    master["regionCounts"] = {reg: len(by_region[reg]) for reg in by_region}
    master.setdefault("변경이력", []).append(
        "%s apply_decisions_v5.py: 한경국립대 평택 행 추가, 경남과기대·한밭대(산업대)·태재대 제외, IT유무상태 필드 추가" % TODAY)
    rc = defaultdict(int)
    for m in mk:
        rc[m["region"]] += 1
    markers["stats"] = {"totalMarkers": len(mk), "regionCounts": dict(rc), "prevMarkers": 308,
                        "removed": len(removed), "added": len(added),
                        "itStatusCounts": {s: sum(1 for m in mk if m["itStatus"] == s) for s in ("IT있음", "IT없음", "판정불가")}}
    markers["note"].append("%s apply_decisions_v5.py: 평택 마커 추가, 경남과기대·한밭대(산업대)·태재대 마커 삭제, "
                           "itStatus/itJudgement 필드 추가(판정불가 %d)" % (TODAY, len(undetermined)))
    linked = {(r["대학명"], r["권역"]) for r in undergrad if not r["좌표미확보"]}
    mkeys = {(m["univ"], m["region"]) for m in mk if "mergedFrom" not in m}
    assert linked == mkeys, linked ^ mkeys
    review["count"] = len(review["items"])
    merged["count"] = len(merged["items"])
    merged["updated"] = TODAY
    save_json("university_master_list_v2.json", master)
    save_json("phase1_markers_v3.json", markers)
    save_json("coords_review_v2.json", review)
    save_json("merged_schools.json", merged)
    rep.append("[저장] 마커 308 -> %d (추가 %s / 삭제 %s) | 마스터 학부 %d행 (좌표 %d / 미확보 %d) | 제외 %d %s | 검토 %d" % (
        len(mk), added, removed, len(undergrad), master["linkedCampusCount"], master["unlinkedCampusCount"],
        excl["count"], excl["사유별"], review["count"]))
    rep.append("[저장] 마커 IT 상태: %s" % markers["stats"]["itStatusCounts"])

    # ---------------- 11-9 4yr 목록 재생성
    for regs, title, fn in ((("경기", "인천", "영남"), "경기·인천·영남", "4yr_list_gyeonggi_incheon_yeongnam.md"),
                            (("서울", "충청", "강원", "제주", "호남"), "서울·충청·강원·제주·호남",
                             "4yr_list_seoul_chungcheong_gangwon_jeju_honam.md")):
        cnt, nno, types, nolist = build_4yr(master, kedi_nongrad, regs, title, fn)
        rep.append("[11-9] %s: 4년제 %d %s / 학제 값 없음 %d %s / 비4년제 %s" % (fn, sum(cnt.values()), cnt, nno, nolist, types))

    # ---------------- 12 판정불가 마커 점검표
    exclude_names = set(flat(load_json("final_exclude_list.json")))
    urow = {(r["대학명"], r["권역"]): r for r in undergrad}
    lines = ["# 판정불가 마커 점검 (%s)" % TODAY, "",
             "- 대상: 작업 11-4에서 IT있음 -> 판정불가로 바꾼 마커 %d개" % len(undetermined),
             "- 방법: univ_major_dedup.json에서 같은 학교명(통합 후속 마커는 구 학교명)·같은 권역·같은 시군구(캠퍼스 주소 기준)의 "
             "모집 중 학과(학과상태 기존·신설·변경) 가운데 학과명에 IT 키워드(%s)가 들어간 학과를 찾음" % ", ".join(IT_KEYWORDS),
             "- 시군구 단위까지만 구분됨. 같은 시군구에 캠퍼스가 둘 이상이면 캠퍼스를 구분하지 못함",
             "- '제외목록'은 final_exclude_list.json(IT 아님으로 확정한 학과명)에 있는 학과. 키워드가 들어가도 IT로 보지 않은 학과",
             "- 이 표는 확인용이며 IT 상태를 바꾸지 않음. 재판정은 2차 IT 판정에서 함", "",
             "| # | 마커 | 권역 | 캠퍼스 시군구 | 폐지 IT 학과 수 | 모집 중 IT 키워드 학과 | 그중 제외목록 | 제외목록 밖 |",
             "|---|---|---|---|---|---|---|---|"]
    found_cnt = 0
    for i, (m, src, c, u) in enumerate(undetermined, 1):
        addr = m.get("address") or (urow.get((m["univ"], m["region"])) or {}).get("주소") or ""
        cands = [x for x in dedup if nm(x["schlNm"]) == nm(src) and SIDO_ALIASES.get(x["ctpvNm"]) == m["region"]]
        sggs = sorted(set(x["sggNm"] for x in cands))
        in_sgg = [s for s in sggs if s == "없음" or all(t in addr for t in s.split())]
        use = [x for x in cands if x["sggNm"] in in_sgg] if in_sgg else cands
        hits = sorted(set(x["scsbjtNm"] for x in use if x["scsbjtSttsNm"] in ACTIVE
                          and any(k in x["scsbjtNm"] for k in IT_KEYWORDS)))
        ex = [h for h in hits if h in exclude_names]
        rest = [h for h in hits if h not in exclude_names]
        found_cnt += bool(rest)
        sgg_txt = ", ".join(in_sgg) if in_sgg else "주소로 못 가름(권역 전체: %s)" % ", ".join(sggs)
        lines.append("| %d | %s%s | %s | %s | %d | %s | %s | %s |" % (
            i, m["campus"], " (구 %s)" % m["mergedFrom"] if m.get("mergedFrom") else "", m["region"], sgg_txt, len(c),
            ", ".join(hits) or "없음", ", ".join(ex) or "-", ", ".join(rest) or "-"))
    lines += ["", "요약: 제외목록 밖의 모집 중 IT 키워드 학과가 있는 마커 %d개 / 전체 %d개" % (found_cnt, len(undetermined))]
    with io.open(P("undetermined_markers_check_20260924.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    rep.append("[12] undetermined_markers_check_20260924.md: %d개 중 제외목록 밖 모집 중 IT 키워드 학과 있는 마커 %d개" % (
        len(undetermined), found_cnt))

    assert sha("univ_major_dedup.json") == dedup_sha
    rep.append("univ_major_dedup.json 변경 없음")
    with io.open(P("decisions_v5_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(rep))
    print("\n".join(rep))


if __name__ == "__main__":
    main()
