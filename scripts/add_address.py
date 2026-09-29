# -*- coding: utf-8 -*-
"""docs/data/markers.json 의 각 마커에 KEDI 2026 고등교육통계 학교별 주요 현황의 주소를 address 로 붙인다.

입력: 저장소 루트의 KEDI xlsx (2026년 고등 학교별 ... .xlsx), docs/data/markers.json
출력: docs/data/markers.json 갱신(address 만 추가). 그 밖의 필드는 건드리지 않는다.

매칭 규칙 (둘 중 하나일 때만 주소를 붙이고, 나머지는 붙이지 않고 목록에 남긴다)
  A. 본분교 표기 일치: 마커 campus 가 "<KEDI 학교명> (<KEDI 본분교>)" 형식이면
     그 학교명·본분교와 정확히 같은 KEDI 행(폐교·대학원 제외)이 1개일 때만 붙인다.
  B. 단일 후보: 마커 campus 가 그 형식이 아닐 때, 마커 univ 와 정확히 같은 KEDI 학교명의
     운영 중 학부 행이 1개이고, 같은 univ 를 쓰는 마커도 1개일 때만 붙인다.
  두 규칙 모두 KEDI 시도가 가리키는 권역이 마커 region 과 같아야 한다. 다르면 붙이지 않는다.
  후보가 0개이거나 2개 이상이면 붙이지 않는다. 이름을 비슷하게 골라 맞추지 않는다.

이미 address 가 있는 마커는 값을 바꾸지 않는다. KEDI 주소와 다르면 보고에 적는다.
값은 xlsx 에서 그대로 읽어 옮긴다(사람·LLM 이 옮기지 않는다).

사용: python scripts/add_address.py [--dry-run]
"""
import glob
import io
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKERS = os.path.join(ROOT, "docs", "data", "markers.json")
SHEET_NAME = "학교별 교육통계"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}

# KEDI 시도 -> 마커 region
SIDO_REGION = {
    "서울": "서울", "경기": "경기", "인천": "인천", "강원": "강원",
    "대전": "충청", "세종": "충청", "충북": "충청", "충남": "충청",
    "광주": "호남", "전북": "호남", "전남": "호남",
    "부산": "영남", "대구": "영남", "울산": "영남", "경북": "영남", "경남": "영남",
    "제주": "제주",
}
TAG_RE = re.compile(r"^(?P<name>.+?) \((?P<tag>(?:본교|분교)\(제\d+캠퍼스\))\)$")
ROAD_RE = re.compile(r"(?:로|길)\s*\d+(?:-\d+)?(?=[\s,(]|$)")
PARCEL_RE = re.compile(r"(?:동|리|가)\s*\d+(?:-\d+)?(?=[\s,(]|$)")
PLACE_RE = re.compile(r"\(([^()]+)\)$")


def find_xlsx():
    hits = sorted(glob.glob(os.path.join(ROOT, "2026년 고등 학교별*.xlsx")))
    if len(hits) != 1:
        raise SystemExit("KEDI xlsx 를 정확히 1개 찾지 못함: %s" % hits)
    return hits[0]


def load_kedi(path):
    z = zipfile.ZipFile(path)
    shared = ["".join(t.text or "" for t in si.iter("{%s}t" % NS["m"]))
              for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rid = next(s.get("{%s}id" % NS["r"]) for s in wb.findall(".//m:sheet", NS) if s.get("name") == SHEET_NAME)
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    target = next(r.get("Target") for r in rels.findall("p:Relationship", NS) if r.get("Id") == rid)
    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    rows = ET.fromstring(z.read(target)).findall(".//m:sheetData/m:row", NS)

    def cells(row):
        c = {}
        for cell in row.findall("m:c", NS):
            v = cell.find("m:v", NS)
            if v is None:
                continue
            col = re.sub(r"\d+", "", cell.get("r"))
            c[col] = shared[int(v.text)] if cell.get("t") == "s" else v.text
        return c

    start = None
    for i, row in enumerate(rows):
        c = cells(row)
        if c.get("E") == "학교명" and c.get("L") == "주소":
            start = i + 1
            break
    if start is None:
        raise SystemExit("헤더 행(학교명/주소)을 찾지 못함")
    out = []
    for row in rows[start:]:
        c = cells(row)
        if not c.get("E"):
            continue
        out.append({"학제": c.get("B", ""), "대학원구분": c.get("C", ""), "학교명": c.get("E", ""),
                    "상태": c.get("F", ""), "본분교": c.get("G", ""), "시도": c.get("H", ""),
                    "시군구": c.get("I", ""), "주소": (c.get("L") or "").strip()})
    return out


def is_candidate(k):
    """운영 중(폐교 아님) 학부 행."""
    return k["상태"] != "폐교" and not k["대학원구분"] and "대학원" not in k["학제"]


def addr_kind(a):
    body = re.sub(r"\s*\([^)]*\)\s*$", "", a)
    if ROAD_RE.search(body):
        return "도로명"
    if PARCEL_RE.search(body):
        return "지번"
    return "판별불가"


def norm_addr(a):
    return re.sub(r"\s+", " ", re.sub(r"\s*\([^)]*\)\s*$", "", a or "")).strip()


def main():
    dry = "--dry-run" in sys.argv
    kedi = load_kedi(find_xlsx())
    by_name = defaultdict(list)
    for k in kedi:
        if is_candidate(k):
            by_name[k["학교명"]].append(k)

    with io.open(MARKERS, encoding="utf-8") as f:
        data = json.load(f)
    markers = data["markers"]
    univ_count = Counter(m["univ"] for m in markers)

    attached, unmatched, kept_same, kept_diff, kept_nomatch = [], [], [], [], []
    method_count = Counter()
    kind_count = Counter()
    nonroad = []

    for m in markers:
        campus, univ = m["campus"], m["univ"]
        mt = TAG_RE.match(campus)
        chosen, method, reason = None, None, None
        if mt:
            method = "A 본분교 표기 일치"
            cands = [k for k in by_name.get(mt.group("name"), []) if k["본분교"] == mt.group("tag")]
        else:
            method = "B 단일 후보"
            cands = by_name.get(univ, [])
            if len(cands) == 1 and univ_count[univ] != 1:
                cands, reason = [], "같은 학교명 마커 %d개, KEDI 후보 1개라 대응 불분명" % univ_count[univ]
        if reason is None:
            if len(cands) == 0:
                reason = "KEDI에 대응 행 없음"
            elif len(cands) > 1:
                reason = "KEDI 후보 %d개 (%s)" % (len(cands), ", ".join(sorted({k["본분교"] + " " + k["시군구"] for k in cands})))
                pm = PLACE_RE.search(campus)
                if pm:
                    same = [k for k in cands if k["시군구"].split(" ")[-1].rstrip("시군구") == pm.group(1)]
                    if len(same) == 1:
                        reason += " / 참고: 지명 '%s'과 시군구가 같은 후보 1개(%s), 자동 선택 안 함" % (pm.group(1), same[0]["본분교"])
            else:
                k = cands[0]
                if not k["주소"]:
                    reason = "KEDI 주소 비어 있음"
                elif SIDO_REGION.get(k["시도"]) != m["region"]:
                    reason = "권역 불일치(KEDI 시도 %s, 마커 권역 %s)" % (k["시도"], m["region"])
                else:
                    chosen = k
        if chosen is None:
            if "address" in m:
                kept_nomatch.append((campus, m["address"], reason))
            else:
                unmatched.append((campus, reason))
            continue
        if "address" in m:
            (kept_same if norm_addr(m["address"]) == norm_addr(chosen["주소"]) and m["address"] == chosen["주소"]
             else kept_diff).append((campus, m["address"], chosen["주소"]))
            continue
        m["address"] = chosen["주소"]
        attached.append(campus)
        method_count[method.split()[0]] += 1

    for m in markers:
        if "address" in m:
            kind = addr_kind(m["address"])
            kind_count[kind] += 1
            if kind != "도로명":
                nonroad.append((m["campus"], m["address"], kind))
    if not dry:
        with io.open(MARKERS, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")

    with_addr = sum(1 for m in markers if "address" in m)
    print("마커 전체: %d" % len(markers))
    print("KEDI 행(운영 중 학부): %d" % sum(len(v) for v in by_name.values()))
    print("이번에 주소를 붙인 마커: %d (규칙 A %d, 규칙 B %d)" % (len(attached), method_count["A"], method_count["B"]))
    print("기존 address 유지: %d (KEDI와 같음 %d, 다름 %d, KEDI 대응 못 함 %d)" % (
        len(kept_same) + len(kept_diff) + len(kept_nomatch), len(kept_same), len(kept_diff), len(kept_nomatch)))
    print("address 가 있는 마커 합계: %d / 없는 마커: %d" % (with_addr, len(markers) - with_addr))
    print("address 가 있는 마커 전체의 주소 형식(기존 17개 포함): %s" % dict(kind_count))
    print("\n[주소를 못 붙인 마커 %d개]" % len(unmatched))
    for c, r in unmatched:
        print("  - %s | %s" % (c, r))
    print("\n[기존 address 가 KEDI 주소와 다른 마커 %d개]" % len(kept_diff))
    for c, old, new in kept_diff:
        print("  - %s\n      기존: %s\n      KEDI: %s" % (c, old, new))
    print("\n[기존 address 유지, KEDI 대응 못 한 마커 %d개]" % len(kept_nomatch))
    for c, old, r in kept_nomatch:
        print("  - %s | %s | 기존: %s" % (c, r, old))
    print("\n[도로명이 아닌 주소 %d개]" % len(nonroad))
    for c, a, kd in nonroad:
        print("  - %s | %s | %s" % (c, kd, a))
    if dry:
        print("\n(--dry-run: 파일을 쓰지 않음)")


if __name__ == "__main__":
    main()
