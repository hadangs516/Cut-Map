# -*- coding: utf-8 -*-
"""전국대학별학과정보표준데이터.csv -> catalog.json (전 대학·전 학과 이름 목록)

이 파일만 완전한 것으로 바꿔서 다시 돌리면 결과가 갱신된다.
CSV 인코딩은 CP949. UTF-8로 읽으면 깨진다.

지금 쓰는 CSV는 공공데이터포털의 5만 건 다운로드 제한 때문에 잘린 불완전한 파일이다.
그래서 결과에 incomplete 플래그를 넣는다. 없는 학교를 지어내지 않는다.
"""
import csv
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "전국대학별학과정보표준데이터.csv")
EXTRA = os.path.join(HERE, "catalog_extra.json")   # 추가 조사로 채운 행 (없어도 됨)
OUT = os.path.join(HERE, "catalog.json")

KEEP_KINDS = {"대학교", "교육대학"}          # SPEC 0-4: 4년제 일반·교육대학만. 산업대·전문대 제외
DROP_DEPT = {"기타(소속학과없음)"}
SUBJ_CAP = 16                                # 검색용으로 남길 주요교과목 개수
JOB_CAP = 12                                 # 검색용으로 남길 관련직업 개수

# 표준분류계열코드 첫 글자 -> 계열.
# 근거: 이 파일 안에서 첫 글자와 '대학자체계열명'을 교차 집계해 96~100% 일치하는 쪽으로 정했다.
#   A 3356행 중 인문사회 98% / B 1432행 중 자연과학 96% / C 1260행 중 예체능 96%
#   D 2263행 중 공학 96% / E 57행 중 의학 100% / F 182행은 자유전공 계열이 섞여 있어 별도로 둔다.
SERIES = {
    "A": "인문사회",
    "B": "자연과학",
    "C": "예체능",
    "D": "공학",
    "E": "의학",
    "F": "자유전공",
}


def norm_name(s):
    """이름 비교용. 공백과 괄호만 없앤다. 글자를 바꾸지는 않는다."""
    return re.sub(r"[\s()（）]", "", s or "")


def split_list(v):
    return [x.strip() for x in (v or "").split("+") if x.strip()]


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def load_rows():
    with io.open(CSV, encoding="cp949", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def build():
    rows = load_rows()
    total = len(rows)

    kept = [r for r in rows
            if r["학교구분명"] in KEEP_KINDS
            and r["학위과정명"] == "학사"
            and r["학과상태명"] != "폐과"
            and r["학과명"] not in DROP_DEPT]

    # 같은 (학교, 학과)가 여러 행이면 하나로 합친다.
    # 정원은 최댓값을 쓴다. 0인 행과 실제 값이 있는 행이 같이 있는 경우가 있어서 0에 덮이면 안 된다.
    # 주야가 나뉜 경우도 한 학과로 보고 정원은 합치지 않는다(중복 계상 위험).
    merged = {}
    dup_rows = 0
    for r in kept:
        key = (r["학교명"], r["학과명"])
        cap = to_int(r["입학정원수"])
        if key in merged:
            dup_rows += 1
            m = merged[key]
            if cap > m["cap"]:
                m["cap"] = cap
            if not m["col"] or m["col"] == "단과대구분없음":
                m["col"] = r["단과대학명"]
            if len(split_list(r["주요교과목명"])) > len(m["subjects"]):
                m["subjects"] = split_list(r["주요교과목명"])
            if len(split_list(r["관련직업명"])) > len(m["jobs"]):
                m["jobs"] = split_list(r["관련직업명"])
            continue
        merged[key] = {
            "univ": r["학교명"],
            "name": r["학과명"],
            "cap": cap,
            "col": r["단과대학명"],
            "series": SERIES.get((r["표준분류계열코드"] or "")[:1], "기타"),
            "selfSeries": r["대학자체계열명"],
            "state": r["학과상태명"],
            "region": r["시도명"],
            "city": r["시군구명"],
            "subjects": split_list(r["주요교과목명"]),
            "jobs": split_list(r["관련직업명"]),
            "src": "csv",
        }

    depts = list(merged.values())

    # 검색용이라 과목·직업 목록을 앞쪽 일부만 남긴다. 전부 담으면 8MB가 넘어 휴대폰에서 무겁다.
    # 원본은 CSV에 그대로 있고, 필요하면 아래 상한만 올리면 된다.
    for d in depts:
        d["subjects"] = d["subjects"][:SUBJ_CAP]
        d["jobs"] = d["jobs"][:JOB_CAP]

    # "○○학부" 행은 하위 학과가 아니라 모집 단위로 본다.
    # 주요교과목명에 하위 학과 이름이 섞여 있어도 쪼개지 않는다. 쪼개면 없는 학과를 만들어내게 된다.
    for d in depts:
        d["isDivision"] = d["name"].endswith("학부")

    # 추가 조사로 채운 행 붙이기 (출처 URL 필수)
    extra_count = 0
    if os.path.exists(EXTRA):
        with io.open(EXTRA, encoding="utf-8") as f:
            ex = json.load(f)
        for d in ex.get("depts", []):
            if not d.get("sourceUrl"):
                raise SystemExit("catalog_extra.json의 행에 sourceUrl이 없음: %r" % d)
            d.setdefault("subjects", [])
            d.setdefault("jobs", [])
            d.setdefault("cap", 0)
            d.setdefault("isDivision", str(d.get("name", "")).endswith("학부"))
            d["src"] = "extra"
            depts.append(d)
            extra_count += 1

    univs = {}
    for d in depts:
        u = univs.setdefault(d["univ"], {
            "name": d["univ"], "region": d.get("region", ""), "city": d.get("city", ""),
            "n": 0, "src": d["src"],
        })
        u["n"] += 1
        if d["src"] == "extra" and u["src"] == "csv":
            u["src"] = "mixed"

    series_counts = {}
    for d in depts:
        series_counts[d["series"]] = series_counts.get(d["series"], 0) + 1

    out = {
        "version": 1,
        "incomplete": True,
        "baseYear": 2025,
        "note": [
            "공공데이터포털 '전국대학별학과정보표준데이터'(제공 한국대학교육협의회, 소관 교육부)에서 만들었다.",
            "포털의 5만 건 다운로드 제한 때문에 원본 CSV가 잘려 있다. 학교와 학과가 빠져 있을 수 있다.",
            "완전한 파일(또는 오픈 API 전체분)로 바꾼 뒤 make_catalog.py를 다시 돌리면 갱신된다.",
            "src=csv는 파일에서 온 행, src=extra는 추가 조사로 채운 행이며 sourceUrl이 붙어 있다.",
            "학부 행은 하위 학과로 쪼개지 않았다. 주요교과목명에 하위 학과 이름이 섞여 있어도 추측으로 나누지 않는다.",
            "입학정원은 같은 학과의 여러 행 중 최댓값이다. 0인 행이 섞여 있어 합산하지 않았다. 학부 단위에 정원이 몰려 있어 학과 정원으로 그대로 읽으면 안 된다.",
        ],
        "source": {
            "title": "전국대학별학과정보표준데이터",
            "url": "https://www.data.go.kr/data/15107737/standard.do",
            "provider": "한국대학교육협의회",
            "authority": "교육부",
            "license": "페이지에 이용허락범위 표기가 없음 (2026-09-20 확인)",
        },
        "stats": {
            "csvRows": total,
            "keptRows": len(kept),
            "mergedDepts": len(merged),
            "mergedFrom": dup_rows,
            "extraDepts": extra_count,
            "univs": len(univs),
            "series": series_counts,
        },
        "series": sorted(series_counts.keys()),
        "univs": sorted(univs.values(), key=lambda x: x["name"]),
        "depts": sorted(depts, key=lambda d: (d["univ"], d["name"])),
    }
    return out


def main():
    data = build()
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    s = data["stats"]
    print("catalog.json 생성")
    print("  CSV 행 %d -> 필터 %d -> 학과 %d (중복 %d행 합침) + 추가 %d"
          % (s["csvRows"], s["keptRows"], s["mergedDepts"], s["mergedFrom"], s["extraDepts"]))
    print("  학교 %d" % s["univs"])
    print("  계열", s["series"])
    print("  크기 %.1f KB" % (os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
