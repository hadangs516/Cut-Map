# -*- coding: utf-8 -*-
"""KEDI 2026 고등교육통계 학교별 주요 현황의 주소로 좌표 누락 행을 채운다.

대상: marker_missing_coords.json의 행 (= 학부 조사 대상 중 좌표미확보 행).
후보 주소 조건 (기존 재연결 규칙과 같은 취지):
  - 학교명 본명(괄호 캠퍼스 표기 제거)이 같음
  - 학제가 대학원이 아니고, 학교상태가 폐교가 아님
  - KEDI 시도와 주소 자체가 가리키는 권역이 모두 행 권역과 같음
  - 서로 다른 주소가 정확히 1개일 때만 VWorld로 좌표 변환 (road -> parcel,
    실패하면 끝의 괄호 부가정보를 떼고 road -> parcel 한 번 더)
주소가 2개 이상이면 자동 선택하지 않고 kedi_multi_address_review.json에 후보를 나열한다.
변환에 실패하거나 후보가 없으면 좌표를 추정하지 않고 누락으로 남긴다.
"""
import io
import json
import os
import re
import time
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

from build_university_master_list import REGIONS, SIDO_ALIASES, region_of
from geocode_gyeongnam_univ import call_geocoder, load_env

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "2026년 고등 학교별 학과수 입학정원 지원 입학 학생 외국학생 졸업 교직원_260826H.xlsx")
MASTER_PATH = os.path.join(HERE, "university_master_list.json")
MARKERS_PATH = os.path.join(HERE, "phase1_markers.json")
MISSING_PATH = os.path.join(HERE, "marker_missing_coords.json")
REVIEW_PATH = os.path.join(HERE, "kedi_multi_address_review.json")
ENV_PATH = os.path.join(HERE, ".env")

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SOURCE_TAG = "KEDI 2026 고등교육통계 학교별 주요 현황 주소 -> VWorld"
SLEEP_SEC = 0.2


def load_json(path):
    if not os.path.exists(path):
        raise SystemExit("입력 파일 없음: %s" % path)
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def norm(name):
    return re.sub(r"[\s()（）]", "", re.sub(r"\([^)]*\)\s*$", "", name or ""))


def load_kedi():
    if not os.path.exists(XLSX):
        raise SystemExit("입력 파일 없음: %s" % XLSX)
    z = zipfile.ZipFile(XLSX)
    shared = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    rows = ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:sheetData/m:row", NS)
    header_row = next(r for r in rows if any(
        c.get("r", "").startswith("E") and c.find("m:v", NS) is not None
        and c.get("t") == "s" and shared[int(c.find("m:v", NS).text)] == "학교명"
        for c in r.findall("m:c", NS)))
    start = rows.index(header_row) + 1
    out = []
    for row in rows[start:]:
        c = {}
        for cell in row.findall("m:c", NS):
            v = cell.find("m:v", NS)
            if v is None:
                continue
            c[re.sub(r"\d+", "", cell.get("r"))] = shared[int(v.text)] if cell.get("t") == "s" else v.text
        if c.get("E"):
            out.append({"학제": c.get("B", ""), "학교명": c.get("E", ""), "상태": c.get("F", ""),
                        "본분교": c.get("G", ""), "시도": c.get("H", ""), "주소": c.get("L", "")})
    return out


def geocode(key, address):
    attempts = [(address, "road"), (address, "parcel")]
    stripped = re.sub(r"\s*\([^)]*\)\s*$", "", address).strip()
    if stripped != address:
        attempts += [(stripped, "road"), (stripped, "parcel")]
    for addr, typ in attempts:
        data = call_geocoder(key, addr, typ)
        time.sleep(SLEEP_SEC)
        resp = data.get("response", {})
        if resp.get("status") == "OK":
            p = resp["result"]["point"]
            return {"lat": float(p["y"]), "lon": float(p["x"]), "type": typ,
                    "usedAddress": addr, "stripped": addr != address}
    return None


def main():
    master = load_json(MASTER_PATH)
    markers = load_json(MARKERS_PATH)
    missing = load_json(MISSING_PATH)
    key = load_env(ENV_PATH).get("VWORLD_KEY")
    if not key:
        raise SystemExit(".env에 VWORLD_KEY가 없음")

    rows_by_key = {}
    for region in master["byRegion"]:
        for row in master["byRegion"][region]:
            rows_by_key[(row["대학명"], row["권역"])] = row
    if any(r.get("좌표출처") == SOURCE_TAG for r in rows_by_key.values()):
        raise SystemExit("이미 KEDI 주소로 채운 행이 있음. 백업본으로 되돌린 뒤 다시 실행하세요.")

    kedi_index = defaultdict(list)
    for k in load_kedi():
        kedi_index[norm(k["학교명"])].append(k)

    filled, review, still_missing = [], [], []
    for item in missing["items"]:
        row = rows_by_key.get((item["univ"], item["region"]))
        if row is None:
            raise SystemExit("누락 항목에 대응하는 마스터 행 없음: %s / %s" % (item["univ"], item["region"]))
        cands = [k for k in kedi_index.get(norm(item["univ"]), [])
                 if "대학원" not in k["학제"] and k["상태"] != "폐교" and k["주소"]
                 and SIDO_ALIASES.get(k["시도"]) == item["region"]
                 and region_of(k["주소"])[0] == item["region"]]
        addrs = sorted(set(k["주소"] for k in cands))

        if len(addrs) == 1:
            k = next(c for c in cands if c["주소"] == addrs[0])
            g = geocode(key, addrs[0])
            if g:
                campus = "%s (%s)" % (k["학교명"], k["본분교"]) if k["본분교"] else k["학교명"]
                row.update({"연결캠퍼스명": campus, "매칭방식": "kedi_address_geocoded", "좌표미확보": False,
                            "위도": g["lat"], "경도": g["lon"], "주소": addrs[0], "좌표출처": SOURCE_TAG,
                            "지오코딩방식": g["type"] + (" (괄호 부가정보 제거 후)" if g["stripped"] else "")})
                filled.append((item, row))
                continue
            item["reason"] = "KEDI 주소 1개 있으나 VWorld 변환 실패: %s" % addrs[0]
            still_missing.append(item)
        elif len(addrs) >= 2:
            cand_list = [{"학교명": c["학교명"], "본분교": c["본분교"], "학제": c["학제"], "주소": c["주소"]}
                         for c in cands]
            uniq = []
            seen = set()
            for c in cand_list:
                if c["주소"] not in seen:
                    seen.add(c["주소"])
                    uniq.append(c)
            item["reason"] = "KEDI 같은 권역 주소 %d개라 자동 선택 안 함 (kedi_multi_address_review.json)" % len(uniq)
            item["kediCandidates"] = uniq
            row["KEDI주소후보"] = uniq
            review.append({"univ": item["univ"], "region": item["region"], "itDepts": item["itDepts"],
                           "candidates": uniq})
            still_missing.append(item)
        else:
            if not kedi_index.get(norm(item["univ"])):
                item["reason"] = item["reason"] + " / KEDI에 학교명 없음"
            else:
                item["reason"] = item["reason"] + " / KEDI에 같은 권역 운영 중 주소 없음"
            still_missing.append(item)

    for item, row in filled:
        markers["markers"].append({
            "univ": row["대학명"], "campus": row["연결캠퍼스명"], "region": row["권역"],
            "lat": row["위도"], "lon": row["경도"],
            "hasITDept": len(row["보유IT계열학과명목록"]) > 0,
            "itDepts": row["보유IT계열학과명목록"],
        })
    region_counts = defaultdict(int)
    for m in markers["markers"]:
        region_counts[m["region"]] += 1
    markers["stats"] = {"totalMarkers": len(markers["markers"]), "regionCounts": dict(region_counts)}
    markers["note"].append("좌표 누락 행 중 %s로 좌표를 채운 행을 추가함." % SOURCE_TAG)
    missing["items"] = still_missing
    missing["count"] = len(still_missing)

    undergrad = [r for reg in master["byRegion"] for r in master["byRegion"][reg]]
    master["linkedCampusCount"] = sum(1 for r in undergrad if not r["좌표미확보"])
    master["unlinkedCampusCount"] = sum(1 for r in undergrad if r["좌표미확보"])

    save_json(MASTER_PATH, master)
    save_json(MARKERS_PATH, markers)
    save_json(MISSING_PATH, missing)
    save_json(REVIEW_PATH, {"version": 1, "source": os.path.basename(XLSX),
                            "note": "같은 권역에 KEDI 주소가 2개 이상이라 자동 선택하지 않은 행. 사람이 캠퍼스를 골라야 함.",
                            "count": len(review), "items": review})

    lines = ["좌표 누락 대상: %d" % (len(filled) + len(still_missing)),
             "KEDI 주소로 좌표 연결: %d" % len(filled),
             "  (괄호 부가정보 제거 후 성공: %d)" % sum(1 for _, r in filled if "제거" in r["지오코딩방식"]),
             "주소 2개 이상 검토 목록: %d" % len(review),
             "여전히 누락: %d" % len(still_missing),
             "전체 마커: %d / 누락 파일: %d" % (len(markers["markers"]), missing["count"]), "",
             "권역별 커버리지:"]
    for reg in REGIONS:
        rs = [r for r in undergrad if r["권역"] == reg]
        lines.append("  %s: %d / %d" % (reg, sum(1 for r in rs if not r["좌표미확보"]), len(rs)))
    lines.append("")
    lines.append("여전히 누락 (검토목록 제외):")
    for it in still_missing:
        if "kediCandidates" not in it:
            lines.append("  - %s | %s | %s" % (it["univ"], it["region"], it["reason"]))
    lines.append("")
    lines.append("주요 확인: %s" % [(r["대학명"], r["권역"], r["연결캠퍼스명"], r["위도"], r["경도"])
                                  for _, r in filled if r["대학명"] in ("가톨릭대학교", "연세대학교")])
    with io.open(os.path.join(HERE, "kedi_fill_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
