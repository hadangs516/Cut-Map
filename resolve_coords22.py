# -*- coding: utf-8 -*-
"""좌표 누락 22행(marker_missing_coords.json)을 유형 A~D로 나눠 처리한다.

원칙
  - 기존 파일은 읽기만 한다. 결과는 새 파일 3개로 저장한다.
      phase1_markers_v2.json  : 기존 마커 + 이번에 확정된 행
      coords_review.json      : 후보 2개 이상 / 사람이 판단할 사항이 있는 행
      coords_unresolved.json  : 보유 자료로 해결 못 한 행 + 필요한 자료
  - 좌표를 추정하지 않는다. VWorld가 돌려준 좌표만 쓴다.
  - 후보가 2개 이상이면 자동 선택하지 않는다.
  - 외부 자료는 VWorld Geocoder 호출 외에 쓰지 않는다 (대학어디가 접근 안 함).
"""
import hashlib
import io
import json
import math
import os
import re
import sys
import time
from collections import defaultdict

from build_university_master_list import SIDO_ALIASES
from fill_coords_from_kedi import load_kedi
from geocode_gyeongnam_univ import call_geocoder, load_env

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)
INPUTS = ["phase1_markers.json", "marker_missing_coords.json", "kedi_multi_address_review.json",
          "university_master_list.json"]
DEDUP = "univ_major_dedup.json"
GN_CSV = "경상남도교육청_대학정보_20250918.csv"
OUT_MARKERS = "phase1_markers_v2.json"
OUT_REVIEW = "coords_review.json"
OUT_UNRESOLVED = "coords_unresolved.json"
REPORT = "coords22_report.txt"
KEDI_SRC = "KEDI 2026 고등교육통계 학교별 주요 현황(xlsx)"
DEDUP_SRC = "univ_major_dedup.json (data.go.kr 전국대학별학과정보표준데이터, 2025)"

TYPE_A = ["재능대학교", "포항대학교", "예원예술대학교"]
TYPE_B = ["경동대학교", "유원대학교", "국립한국교통대학교"]
TYPE_C = ["한국폴리텍 I 대학 서울정수캠퍼스", "한국폴리텍 II 대학 인천캠퍼스", "한국폴리텍 VI 대학 영주캠퍼스",
          "한국폴리텍 VII 대학 부산캠퍼스", "서울과학기술대학교 나노IT디자인융합대",
          "한국외국어대학교 글로벌미디어커뮤니케이", "한국공학대학교 지식기반기술·에너지대학",
          "한국기술교육대학교 IT융합과학경영산업"]
TYPE_D = ["국립강릉원주대학교", "홍익대학교", "한국복지대학교", "전남도립대학교", "경남도립거창대학",
          "경북도립대학교", "서라벌대학교", "성심외국어대학"]

SIDO_SHORT = {"서울특별시": "서울", "인천광역시": "인천", "경기도": "경기", "강원특별자치도": "강원", "강원도": "강원",
              "충청북도": "충북", "충청남도": "충남", "대전광역시": "대전", "세종특별자치시": "세종",
              "전라남도": "전남", "전라북도": "전북", "전북특별자치도": "전북", "광주광역시": "광주",
              "경상북도": "경북", "경상남도": "경남", "부산광역시": "부산", "대구광역시": "대구", "울산광역시": "울산",
              "제주특별자치도": "제주"}


def load_json(name):
    with io.open(P(name), encoding="utf-8") as f:
        return json.load(f)


def save_json(name, data):
    with io.open(P(name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sha(name):
    return hashlib.sha256(open(P(name), "rb").read()).hexdigest()


def addr_key(a):
    """도로명+건물번호까지 자르고 시도명 약칭·공백을 통일. 같은 주소인지 비교할 때만 쓴다."""
    a = addr_core(a)
    for full, short in SIDO_SHORT.items():
        if a.startswith(full):
            a = short + a[len(full):]
    return re.sub(r"\s+", "", a)


def addr_core(a):
    """도로명 + 건물번호까지만 남긴다 (끝의 건물명 텍스트 제거)."""
    a = re.sub(r"\s*\([^)]*\)", "", a or "").strip()
    m = re.match(r"^(.*?(?:로|길)\s*\d+(?:-\d+)?)(?:\s|$)", a)
    return m.group(1) if m else a


def region_of_sido(sido):
    return SIDO_ALIASES.get(sido)


# ---------------------------------------------------------------- 지오코딩
GEO_CACHE = {}


def geocode_variants(key, address):
    """주소 표기를 정리한 변형들을 도로명(road) -> 지번(parcel) 순으로 시도. 모든 시도를 기록한다."""
    base = re.sub(r"\s*\([^)]*\)", "", address).strip()          # 괄호 제거
    core = addr_core(base)                                         # 건물명·상세주소 제거
    variants = []
    for v in (address, base, core):
        if v and v not in variants:
            variants.append(v)
    for v in list(variants):
        for full, short in SIDO_SHORT.items():                    # 시도 약칭 표기
            if v.startswith(full):
                s = short + v[len(full):]
                if s not in variants:
                    variants.append(s)
        sp = re.sub(r"(\d+)번길", r" \1번길", v) if re.search(r"[가-힣]\d+번길", v) else None
        if sp and sp not in variants:                              # '화합로1134번길' -> '화합로 1134번길'
            variants.append(sp)
    tries = []
    for typ in ("road", "parcel"):
        for v in variants:
            ck = (v, typ)
            if ck not in GEO_CACHE:
                GEO_CACHE[ck] = call_geocoder(key, v, typ)
                time.sleep(0.2)
            resp = GEO_CACHE[ck].get("response", {})
            st = resp.get("status")
            tries.append({"address": v, "type": typ, "status": st})
            if st == "OK":
                pt = resp["result"]["point"]
                refined = (resp.get("refined") or {}).get("text", "")
                return {"lat": float(pt["y"]), "lon": float(pt["x"]), "type": typ, "usedAddress": v,
                        "refined": refined, "tries": tries}
    return {"tries": tries}


def km(a, b):
    r = 6371.0
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- 보조 자료
def load_gn_csv():
    import csv
    raw = open(P(GN_CSV), "rb").read()
    txt = raw.decode("cp949")
    rows = list(csv.DictReader(io.StringIO(txt)))
    return rows


def dept_locations(dedup_items, univ, it_depts):
    """학과 표준데이터에서 이 대학 IT 학과의 소재 시도/시군구를 모은다."""
    it = set(it_depts)
    g = defaultdict(list)
    kinds = defaultdict(int)
    for r in dedup_items:
        if r["schlNm"] != univ:
            continue
        kinds[(r["schlSeNm"], r["degCrseCrsNm"])] += 1
        if r["scsbjtNm"] in it:
            loc = "%s %s" % (r["ctpvNm"], r["sggNm"])
            tag = r["scsbjtNm"] + ("" if r["scsbjtSttsNm"] == "기존" else "[%s]" % r["scsbjtSttsNm"])
            if tag not in g[loc]:
                g[loc].append(tag)
    out = []
    for loc, ds in g.items():
        active = [d for d in ds if "[" not in d or "[신설]" in d or "[변경]" in d]
        out.append({"소재지": loc, "IT학과수": len(ds), "기존·신설·변경": len(active),
                    "폐과": len(ds) - len(active), "학과": sorted(ds)})
    out.sort(key=lambda x: -x["IT학과수"])
    return out, {"%s/%s" % k: v for k, v in kinds.items()}


def kedi_view(k):
    return {"학교명": k["학교명"], "학제": k["학제"], "상태": k["상태"], "본분교": k["본분교"],
            "시도": k["시도"], "주소": k["주소"]}


def is_grad(k):
    return "대학원" in k["학제"]


# ---------------------------------------------------------------- 메인
def main():
    before = {n: sha(n) for n in INPUTS}
    markers = load_json("phase1_markers.json")
    missing = load_json("marker_missing_coords.json")
    kedi_review = load_json("kedi_multi_address_review.json")
    master = load_json("university_master_list.json")

    # 0) 입력 검증
    assert len(markers["markers"]) == 295, "마커 수가 295가 아님"
    assert len(missing["items"]) == 22 and missing["count"] == 22, "누락 행이 22가 아님"
    names = [it["univ"] for it in missing["items"]]
    typed = TYPE_A + TYPE_B + TYPE_C + TYPE_D
    assert sorted(names) == sorted(typed), "유형 분류 대상과 누락 행 목록이 다름: %s" % (
        set(names) ^ set(typed))
    master_rows = {(r["대학명"], r["권역"]): r for reg in master["byRegion"] for r in master["byRegion"][reg]}
    for it in missing["items"]:
        row = master_rows.get((it["univ"], it["region"]))
        assert row is not None and row["좌표미확보"], "마스터 행 상태 불일치: %s" % it["univ"]
    review_by_univ = {it["univ"]: it for it in kedi_review["items"]}

    key = load_env(P(".env")).get("VWORLD_KEY")
    if not key:
        raise SystemExit(".env에 VWORLD_KEY가 없음")
    kedi = load_kedi()
    gn = load_gn_csv()
    dedup_items = load_json(DEDUP)["items"]

    resolved, review, unresolved = [], [], []
    type_of = {}
    for t, lst in (("A", TYPE_A), ("B", TYPE_B), ("C", TYPE_C), ("D", TYPE_D)):
        for u in lst:
            type_of[u] = t

    def base_entry(item):
        locs, kinds = dept_locations(dedup_items, item["univ"], item["itDepts"])
        return {"univ": item["univ"], "region": item["region"], "type": type_of[item["univ"]],
                "itDepts": item["itDepts"], "prevReason": item["reason"],
                "학과소재지_표준데이터": locs, "학교구분_학위과정_행수": kinds}

    def geo_candidate(c):
        g = geocode_variants(key, c["주소"])
        c = dict(c)
        if "lat" in g:
            c.update({"lat": g["lat"], "lon": g["lon"], "geocode": {k: g[k] for k in
                                                                      ("type", "usedAddress", "refined")}})
        else:
            c["geocode"] = {"status": "실패", "tries": g["tries"]}
        return c

    def resolve(item, entry, cand, campus_label, evidence, g):
        entry.update({"result": "해결", "campus": campus_label, "address": cand["주소"],
                      "lat": g["lat"], "lon": g["lon"],
                      "geocode": {"type": g["type"], "usedAddress": g["usedAddress"], "refined": g["refined"],
                                  "attempts": len(g["tries"])},
                      "evidence": evidence})
        resolved.append(entry)

    for item in missing["items"]:
        u, region = item["univ"], item["region"]
        t = type_of[u]
        entry = base_entry(item)

        # ---------------- 유형 A: 주소 1개(또는 사용자 지정)인데 VWorld 변환 실패
        if t == "A":
            m = re.search(r"실패:\s*(.+)$", item["reason"])
            addr = m.group(1).strip()
            k_rows = [k for k in kedi if not is_grad(k) and k["상태"] != "폐교" and addr_key(k["주소"]) == addr_key(addr)]
            full = k_rows[0]["주소"] if k_rows else addr
            g = geocode_variants(key, full)
            campus = "%s (%s)" % (k_rows[0]["학교명"], k_rows[0]["본분교"]) if k_rows else u
            ev = ["KEDI 주소: %s" % full,
                  "변형 %d가지(괄호 제거, 건물명 제거, 시도 약칭, 번길 띄어쓰기) x 도로명/지번 시도" % len(
                      set(x["address"] for x in g["tries"]))]
            if "지정" in item["reason"]:
                ev.append("캠퍼스는 이전 작업에서 사용자가 지정함(%s)" % re.search(r"지정됨\((.+?)\)이나", item["reason"]).group(1))
            if "lat" in g:
                ev.append("VWorld %s 성공: '%s' -> %s" % (g["type"], g["usedAddress"], g["refined"]))
                resolve(item, entry, {"주소": full}, campus, ev, g)
                continue
            # 같은 캠퍼스(학교명·본분교 동일)의 다른 KEDI 주소가 있으면 참고 후보로만 적는다
            alt = []
            if k_rows:
                alt = [k for k in kedi if k["학교명"].startswith(k_rows[0]["학교명"]) and k["본분교"] == k_rows[0]["본분교"]
                       and k["상태"] != "폐교" and addr_key(k["주소"]) != addr_key(full)]
            alt_addrs = sorted(set(k["주소"] for k in alt))
            entry["geocodeTries"] = g["tries"]
            if alt_addrs:
                entry.update({"result": "검토",
                              "candidates": [geo_candidate({"주소": a, "출처": "KEDI 같은 캠퍼스(%s)의 대학원 행 주소" %
                                                                          k_rows[0]["본분교"],
                                                            "KEDI행": [kedi_view(k) for k in alt if k["주소"] == a]})
                                             for a in alt_addrs],
                              "evidence": ev + ["학부 행 주소는 변형 전부 NOT_FOUND",
                                                "같은 캠퍼스의 대학원 행에 다른 주소가 있음. 학부 행 주소와 표기가 달라 "
                                                "같은 곳인지 자료로 확인되지 않아 자동 적용 안 함"]})
                review.append(entry)
            else:
                entry.update({"result": "미확인", "evidence": ev + ["변형 전부 NOT_FOUND"],
                              "needed": ["캠퍼스 지번주소(예: 도로명주소 안내시스템 juso.go.kr에서 조회) 또는 "
                                         "대학 공식 홈페이지의 캠퍼스 주소·좌표"]})
                unresolved.append(entry)
            continue

        # ---------------- 유형 B: 캠퍼스 미확정 (좌표 확정 안 함)
        if t == "B":
            cands = review_by_univ[u]["candidates"]
            gn_rows = [r for r in gn if r["대학이름"].startswith(u.replace("국립", "")[:4])]
            other = [l for l in entry["학과소재지_표준데이터"] if region_of_sido(l["소재지"].split()[0]) != region]
            locs = [l for l in entry["학과소재지_표준데이터"] if region_of_sido(l["소재지"].split()[0]) == region]
            ev = ["KEDI 같은 권역 주소 %d개 (kedi_multi_address_review.json)" % len(cands)]
            if other:
                ev.append("다른 권역 IT학과(이 행과 무관, 참고): %s" % ", ".join(l["소재지"] for l in other))
            per = []
            for c in cands:
                sgg = re.search(r"(\S+[시군])\s", c["주소"]).group(1)
                match = [l for l in locs if l["소재지"].split()[-1] == sgg]
                if match:
                    l = match[0]
                    per.append("%s(%s): IT학과 %d개 (기존·신설·변경 %d, 폐과 %d)" % (
                        c["본분교"], sgg, l["IT학과수"], l["기존·신설·변경"], l["폐과"]))
                else:
                    per.append("%s(%s): 표준데이터에 이 시군의 IT학과 없음" % (c["본분교"], sgg))
            ev += per
            only = [l for l in locs if l["IT학과수"] > 0]
            if len(only) == 1:
                ev.append("표준데이터상 이 권역 IT학과는 모두 %s 소재 -> 그 캠퍼스 소속으로 확인됨. "
                          "단 지시에 따라 좌표는 확정하지 않음" % only[0]["소재지"])
            else:
                act = [l for l in only if l["기존·신설·변경"] > 0]
                ev.append("IT학과가 %d개 시군에 걸쳐 있음. 현재 운영(기존·신설·변경) 학과가 있는 곳: %s" % (
                    len(only), ", ".join(l["소재지"] for l in act) or "없음"))
            if gn_rows:
                ev.append("경남교육청 CSV: %s" % " / ".join("%s: %s" % (r["대학이름"], r["주소"]) for r in gn_rows))
            entry.update({"result": "검토", "candidates": [geo_candidate(dict(c, 출처=KEDI_SRC)) for c in cands],
                          "evidence": ev})
            review.append(entry)
            continue

        # ---------------- 유형 C: KEDI 학교명 없음 / 이름 잘림
        if t == "C":
            if "폴리텍" in u:
                camp = re.search(r"(\S+캠퍼스)$", u).group(1)
                def kcamp(name):
                    mm = re.search(r"([^\s대]+캠퍼스)$", name)
                    return mm.group(1) if mm else None
                cands = [k for k in kedi if "폴리텍" in k["학교명"] and not is_grad(k) and k["상태"] != "폐교"
                         and kcamp(k["학교명"]) == camp and region_of_sido(k["시도"]) == region]
                gn_c = [r for r in gn if "폴리텍" in r["대학이름"]]
                ev = ["KEDI에서 '폴리텍' + 캠퍼스명 '%s' 완전일치(권역 %s)로 재매칭: %d건" % (camp, region, len(cands)),
                      "경남교육청 CSV에는 폴리텍 행 %d건" % len(gn_c)]
                similar = [k["학교명"] for k in kedi if "폴리텍" in k["학교명"] and camp[:-3] in k["학교명"]
                           and k not in cands]
                if similar:
                    ev.append("캠퍼스명이 부분만 겹쳐 제외한 KEDI 행: %s" % ", ".join(sorted(set(similar))))
            else:
                parent = re.match(r"^(\S+대학교)", u).group(1)
                tail = u[len(parent):].strip()
                cands = [k for k in kedi if k["학교명"] == parent and k["학제"] == "대학교" and k["상태"] != "폐교"
                         and region_of_sido(k["시도"]) == region]
                grad = [k for k in kedi if k["학교명"].replace(" ", "").startswith((parent + tail).replace(" ", ""))]
                gn_c = [r for r in gn if r["대학이름"].startswith(parent)
                        and region_of_sido(r["지역"]) == region]
                ev = ["상위 대학명 '%s'(학제 대학교, 권역 %s)로 KEDI 재매칭: %d건" % (parent, region, len(cands))]
                if gn_c:
                    ev.append("경남교육청 CSV 같은 권역: %s" % " / ".join("%s: %s" % (r["대학이름"], r["주소"]) for r in gn_c))
                if grad:
                    ev.append("KEDI에 '%s'로 시작하는 행: %s" % (tail, "; ".join(
                        "%s [%s, %s]" % (k["학교명"], k["학제"], k["상태"]) for k in grad)))
                kinds = entry["학교구분_학위과정_행수"]
                ev.append("표준데이터 학교구분/학위과정: %s" % kinds)
            addrs = sorted(set(addr_key(k["주소"]) for k in cands))
            if len(addrs) == 1:
                k = cands[0]
                grad_like = t == "C" and "폴리텍" not in u and any("대학원" in s for s in entry["학교구분_학위과정_행수"])
                if grad_like:
                    # 주소 후보는 1개지만 행 자체가 대학원이라 학부 지도에 넣을지 사람이 정해야 함
                    parent_marker = [m for m in markers["markers"] if m["univ"] == k["학교명"] and m["region"] == region]
                    c = geo_candidate(dict(kedi_view(k), 출처=KEDI_SRC))
                    if parent_marker:
                        pm = parent_marker[0]
                        if "lat" in c:
                            ev.append("상위 대학 기존 마커 '%s'와 거리 %.2fkm" % (pm["campus"], km((c["lat"], c["lon"]),
                                                                                         (pm["lat"], pm["lon"]))))
                    ev.append("주소 후보는 1개지만, 이 행은 학부가 아니라 대학원(표준데이터 학교구분이 대학원, 학위과정 석사 등)."
                              " 학부 조사 대상 지도에 별도 마커로 넣을지 결정 필요 -> 자동 확정 안 함")
                    entry.update({"result": "검토", "candidates": [c], "evidence": ev,
                                  "decisionNeeded": "대학원 행을 지도 대상에서 뺄지, 상위 대학 마커에 합칠지, 별도 마커로 둘지"})
                    review.append(entry)
                    continue
                g = geocode_variants(key, k["주소"])
                if "lat" in g:
                    ev.append("VWorld %s 성공: '%s' -> %s" % (g["type"], g["usedAddress"], g["refined"]))
                    resolve(item, entry, k, "%s (%s)" % (k["학교명"], k["본분교"]), ev, g)
                else:
                    entry.update({"result": "미확인", "geocodeTries": g["tries"],
                                  "evidence": ev + ["후보 1건이나 VWorld 변환 실패"],
                                  "needed": ["캠퍼스 지번주소 또는 공식 좌표"]})
                    unresolved.append(entry)
            elif len(addrs) >= 2:
                entry.update({"result": "검토", "evidence": ev,
                              "candidates": [geo_candidate(dict(kedi_view(k), 출처=KEDI_SRC)) for k in cands]})
                review.append(entry)
            else:
                entry.update({"result": "미확인", "evidence": ev,
                              "needed": ["캠퍼스 주소가 담긴 자료(KEDI 학교별 현황 이외의 캠퍼스 목록 등)"]})
                unresolved.append(entry)
            continue

        # ---------------- 유형 D: 같은 권역 운영 주소 없음
        if t == "D":
            own = [k for k in kedi if not is_grad(k) and re.sub(r"\s", "", k["학교명"]).startswith(re.sub(r"\s", "", u))]
            own_region = [k for k in own if region_of_sido(k["시도"]) == region]
            ev = ["KEDI 본 학교명 행(대학원 제외): %s" % ("; ".join(
                "%s [%s, %s, %s] %s" % (k["학교명"], k["학제"], k["상태"], k["본분교"], k["주소"]) for k in own) or "없음")]
            active = [k for k in own_region if k["상태"] != "폐교"]
            cands = []
            if active:
                # 학교명에 캠퍼스명이 붙은 KEDI 행 (예: '홍익대학교 세종캠퍼스')
                cands = active
                ev.append("같은 권역의 운영 중 행 %d건 (학교명에 캠퍼스명이 붙어 기존 매칭에서 빠졌던 행)" % len(active))
            else:
                closed = [k for k in own_region if k["상태"] == "폐교"]
                for c in closed:
                    succ = [k for k in kedi if not is_grad(k) and k["상태"] != "폐교"
                            and addr_key(k["주소"]) == addr_key(c["주소"])]
                    for s in succ:
                        if s not in cands:
                            cands.append(s)
                if closed:
                    ev.append("KEDI상 폐교. 폐교 행 주소와 같은 주소의 운영 중 행: %s" % ("; ".join(
                        "%s [%s, %s] %s" % (s["학교명"], s["학제"], s["본분교"], s["주소"]) for s in cands) or "없음"))
            addrs = sorted(set(addr_key(k["주소"]) for k in cands))
            if len(addrs) == 1:
                k = cands[0]
                g = geocode_variants(key, k["주소"])
                if "lat" in g:
                    ev.append("VWorld %s 성공: '%s' -> %s" % (g["type"], g["usedAddress"], g["refined"]))
                    same = [m for m in markers["markers"] if "lat" in g and km((g["lat"], g["lon"]), (m["lat"], m["lon"])) < 0.3]
                    if same:
                        ev.append("주의: 기존 마커와 300m 이내 -> %s" % ", ".join(
                            "%s(%.0fm)" % (m["campus"], km((g["lat"], g["lon"]), (m["lat"], m["lon"])) * 1000) for m in same))
                        entry["overlapWith"] = [m["campus"] for m in same]
                    resolve(item, entry, k, "%s (%s)" % (k["학교명"], k["본분교"]), ev, g)
                else:
                    entry.update({"result": "미확인", "geocodeTries": g["tries"],
                                  "evidence": ev + ["후보 1건이나 VWorld 변환 실패"],
                                  "needed": ["캠퍼스 지번주소 또는 공식 좌표"]})
                    unresolved.append(entry)
            elif len(addrs) >= 2:
                entry.update({"result": "검토", "evidence": ev,
                              "candidates": [geo_candidate(dict(kedi_view(k), 출처=KEDI_SRC)) for k in cands]})
                review.append(entry)
            else:
                closed = [k for k in own_region if k["상태"] == "폐교"]
                needed = ["이 권역 캠퍼스 주소가 담긴 자료"]
                if closed:
                    c0 = closed[0]
                    g = geocode_variants(key, c0["주소"])
                    entry["geocodeTries"] = g["tries"]
                    ev.append("운영 중 행 가운데 폐교 행과 같은 주소는 없음 (통합·승계 관계를 보여주는 자료가 보유 파일에 없음)")
                    if "lat" in g:
                        ev.append("폐교 행 주소는 VWorld 변환 성공(%s)했으나 폐교 기관 주소라 자동 확정 안 함" % g["refined"])
                    else:
                        ev.append("폐교 행 주소 '%s'는 변형 %d가지 x 도로명/지번 모두 NOT_FOUND" % (
                            c0["주소"], len(set(x["address"] for x in g["tries"]))))
                    needed = ["이 캠퍼스를 현재 운영하는 대학·캠퍼스명과 주소를 보여주는 자료 "
                              "(예: 통합 이후 캠퍼스 목록이 반영된 KEDI 학교별 현황 또는 교육부 통합 승인 자료)",
                              "또는 폐교 행 주소(%s)의 지번주소" % addr_core(c0["주소"])]
                entry.update({"result": "미확인", "evidence": ev, "needed": needed})
                unresolved.append(entry)
            continue

    # ---------------------------------------------------------------- 저장
    new_markers = json.loads(json.dumps(markers))
    for e in resolved:
        row = master_rows[(e["univ"], e["region"])]
        new_markers["markers"].append({
            "univ": e["univ"], "campus": e["campus"], "region": e["region"],
            "lat": e["lat"], "lon": e["lon"],
            "hasITDept": len(row["보유IT계열학과명목록"]) > 0,
            "itDepts": row["보유IT계열학과명목록"],
            "coordSource": "coords22 (%s)" % e["type"], "address": e["address"],
        })
    rc = defaultdict(int)
    for m in new_markers["markers"]:
        rc[m["region"]] += 1
    new_markers["stats"] = {"totalMarkers": len(new_markers["markers"]), "regionCounts": dict(rc),
                            "baseMarkers": 295, "addedThisRun": len(resolved)}
    new_markers["note"].append("좌표 누락 22행 재처리(resolve_coords22.py, 2026-09-24): %d행 추가. 추가 행에만 "
                               "coordSource/address 필드가 있음. 원본 phase1_markers.json은 수정하지 않음." % len(resolved))
    new_markers["source"] = new_markers.get("source", "") + " + resolve_coords22.py"

    save_json(OUT_MARKERS, new_markers)
    save_json(OUT_REVIEW, {"version": 1, "generatedBy": "resolve_coords22.py", "date": "2026-09-24",
                           "note": "후보가 2개 이상이거나, 후보는 1개지만 지도 포함 여부를 사람이 정해야 하는 행. "
                                   "후보 좌표는 판단용 참고값이며 마커에 넣지 않았음.",
                           "sources": [KEDI_SRC, DEDUP_SRC, GN_CSV, "VWorld Geocoder 2.0"],
                           "count": len(review), "items": review})
    save_json(OUT_UNRESOLVED, {"version": 1, "generatedBy": "resolve_coords22.py", "date": "2026-09-24",
                               "note": "보유 자료로 주소·좌표를 확인하지 못한 행. 좌표를 추정하지 않음.",
                               "count": len(unresolved), "items": unresolved})

    after = {n: sha(n) for n in INPUTS}
    assert before == after, "원본 파일이 바뀌었음"

    lines = ["해결 %d / 검토 %d / 미확인 %d (합계 %d)" % (len(resolved), len(review), len(unresolved),
                                                      len(resolved) + len(review) + len(unresolved)),
             "마커 %d -> %d" % (len(markers["markers"]), len(new_markers["markers"])), "원본 4개 파일 해시 변동 없음", ""]
    for e in resolved + review + unresolved:
        lines.append("[%s] %s | %s | %s | %s" % (e["result"], e["type"], e["univ"], e["region"], e.get("campus", "")))
        for x in e["evidence"]:
            lines.append("    - " + x)
        for c in e.get("candidates", []):
            lines.append("    * 후보 %s %s %s -> %s" % (c.get("학교명", ""), c.get("본분교", ""), c["주소"],
                                                   ("%.5f,%.5f" % (c["lat"], c["lon"])) if "lat" in c else "변환실패"))
        for l in e["학과소재지_표준데이터"]:
            lines.append("    · %s: IT %d (운영 %d, 폐과 %d)" % (l["소재지"], l["IT학과수"], l["기존·신설·변경"], l["폐과"]))
    with io.open(P(REPORT), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
