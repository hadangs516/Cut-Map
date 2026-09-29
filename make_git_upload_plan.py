# -*- coding: utf-8 -*-
"""작업 20-4·6: audit_repo_files.json을 바탕으로 git_upload_plan.md 작성 (점검만, git 작업 없음)."""
import io
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
MB = 1024 * 1024
RAW_EXT = {".xlsx", ".xls", ".pdf", ".hwp", ".hwpx", ".zip", ".docx", ".doc", ".csv"}
SUPERSEDED = {"phase1_markers.json": "phase1_markers_v3.json", "phase1_markers_v2.json": "phase1_markers_v3.json",
              "university_master_list.json": "university_master_list_v2.json", "coords_review.json": "coords_review_v2.json",
              "coords_unresolved.json": "coords_unresolved_v2.json", "marker_missing_coords.json": "phase1_markers_v3.json 등",
              "컷맵_입결위치조사_20260924.md": "컷맵_입결위치조사_20260924_v3.md"}
WORK_ONLY = {"audit_repo_files.json": "이번 점검 산출물(파일 목록·검사 결과). 저장소에 둘 필요 없음"}


def size_txt(n):
    return "%.1f MB" % (n / MB) if n >= MB else "%.1f KB" % (n / 1024)


def classify(f):
    p, top, ext, size = f["path"], f["top"], f["ext"], f["size"]
    name = os.path.basename(p)
    if name == ".env":
        return "제외", "API 키가 든 파일"
    if top.startswith("backup_"):
        return "제외", "백업 폴더"
    if top == "archive":
        return "제외", "archive 폴더"
    if top == "__pycache__" or ext == ".pyc":
        return "제외", "파이썬 캐시"
    if top == ".claude":
        return "제외", "로컬 도구 설정 폴더"
    if size > 100 * MB:
        return "제외", "100MB 초과 (GitHub 한도)"
    if name in WORK_ONLY:
        return "제외", WORK_ONLY[name]
    if ext in {".pdf", ".hwp", ".hwpx", ".zip", ".docx", ".doc", ".xls"}:
        return "제외", "내려받은 입결 원본 형식"
    if ext in (".xlsx", ".csv"):
        return "판단", "내려받은 공공 원본 자료(입결 아님)"
    if size > 50 * MB:
        return "판단", "50MB 초과 (GitHub 경고 크기, 100MB 미만)"
    if name in SUPERSEDED:
        return "판단", "이전 버전 (현재 기준: %s)" % SUPERSEDED[name]
    if name == "it-major-map.html":
        return "올림", "지도 화면 파일 (GitHub의 index.html과 내용 다름)"
    if ext in (".html", ".css", ".js") or top in ("map", "grades") or name.startswith("geo_") or name == "leaflet.min.css":
        return "올림", "지도·화면 파일"
    if name.startswith("SPEC_") or name in ("PROJECT_BRIEF.md", "PROGRESS.md", "CHANGELOG.md", "RELEASE_CHECKLIST.md"):
        return "올림", "기획·명세 문서"
    if name in ("컷맵_입결위치조사_20260924_v3.md", "2027_정시모집요강_URL_누적.md", "cowork_allowed_domains.md") \
            or name.startswith("4yr_list_"):
        return "올림", "현재 기준 조사 md"
    if ext == ".json":
        return "올림", "마커·학과·목록 데이터"
    if ext == ".py":
        return "올림", "처리 스크립트"
    if ext in (".md", ".txt"):
        return "올림", "보고·점검 문서"
    if name == ".gitignore":
        return "올림", "git 설정"
    return "판단", "분류 규칙에 없는 파일"


def main():
    a = json.load(io.open(os.path.join(HERE, "audit_repo_files.json"), encoding="utf-8"))
    files = a["files"]
    groups = defaultdict(list)
    for f in files:
        g, why = classify(f)
        groups[g].append((f, why))
    tot = {g: sum(f["size"] for f, _ in v) for g, v in groups.items()}

    L = ["# GitHub 업로드 계획 (작업 20, 점검만)", "",
         "- 작성: 2026-09-29 / make_git_upload_plan.py (audit_repo_files.py 결과 사용)",
         "- git 작업(commit, push, 저장소 설정 변경)은 하지 않았음. 이 문서는 계획 초안",
         "- 폴더 파일 %d개, 합계 %s" % (len(files), size_txt(sum(f["size"] for f in files))), "",
         "## 1. 요약", "",
         "| 구분 | 파일 수 | 합계 |", "|---|---|---|"]
    for g, label in (("올림", "올릴 후보"), ("판단", "판단 필요"), ("제외", "올리지 않을 후보")):
        L.append("| %s | %d | %s |" % (label, len(groups[g]), size_txt(tot.get(g, 0))))
    L += [""]
    for g, label in (("올림", "2. 올릴 후보"), ("판단", "3. 판단 필요"), ("제외", "4. 올리지 않을 후보")):
        items = groups[g]
        if g == "제외":
            # 폴더 단위는 묶어서 적음
            folders = defaultdict(lambda: [0, 0])
            singles = []
            for f, why in items:
                if f["top"]:
                    folders[(f["top"], why)][0] += 1
                    folders[(f["top"], why)][1] += f["size"]
                else:
                    singles.append((f, why))
            L += ["## %s" % label, "", "| 경로 | 크기 | 사유 |", "|---|---|---|"]
            L += ["| %s/ (파일 %d개) | %s | %s |" % (t, n, size_txt(s), why) for (t, why), (n, s) in sorted(folders.items())]
            L += ["| %s | %s | %s |" % (f["path"], size_txt(f["size"]), why) for f, why in singles]
        else:
            L += ["## %s" % label, "", "| 경로 | 크기 | 분류 |", "|---|---|---|"]
            L += ["| %s | %s | %s |" % (f["path"], size_txt(f["size"]), why) for f, why in sorted(items, key=lambda x: x[0]["path"])]
        L.append("")

    L += ["## 5. .gitignore 초안", "",
          "현재 `.gitignore`에는 `.env`, `__pycache__/`, `*.pyc` 세 줄이 있음. 아래는 추가안(아직 파일에 쓰지 않음).", "",
          "```gitignore",
          "# 비밀값 (API 키)",
          ".env",
          "",
          "# 파이썬 캐시",
          "__pycache__/",
          "*.pyc",
          "",
          "# 백업·보관 폴더",
          "backup_*/",
          "archive/",
          "",
          "# 로컬 도구 설정",
          ".claude/",
          "",
          "# 100MB 초과 파일",
          "univ_major_full.json",
          "",
          "# 내려받은 입결 원본 (Cowork 다운로드 포함)",
          "*.pdf",
          "*.hwp",
          "*.hwpx",
          "*.xls",
          "*.zip",
          "*.docx",
          "",
          "# 점검용 임시 산출물",
          "audit_repo_files.json",
          "",
          "# 판단 필요 항목 (결정 후 주석 해제)",
          "# *.xlsx",
          "# 전국대학별학과정보표준데이터.csv",
          "# 경상남도교육청_대학정보_20250918.csv",
          "# univ_major_dedup.json",
          "```", "",
          "## 6. 전체 파일 목록 (크기 순)", "",
          "표시: [100MB초과] [원본자료] [백업] [archive] [키]", "",
          "| 경로 | 크기 | 표시 |", "|---|---|---|"]
    for f in sorted(files, key=lambda x: -x["size"]):
        tags = []
        if f["size"] > 100 * MB:
            tags.append("100MB초과")
        if f["ext"] in RAW_EXT:
            tags.append("원본자료")
        if f["top"].startswith("backup_"):
            tags.append("백업")
        if f["top"] == "archive":
            tags.append("archive")
        if os.path.basename(f["path"]) == ".env":
            tags.append("키")
        L.append("| %s | %s | %s |" % (f["path"], size_txt(f["size"]), " ".join("[%s]" % t for t in tags) or "-"))
    with io.open(os.path.join(HERE, "git_upload_plan.md"), "w", encoding="utf-8", newline="\n") as fo:
        fo.write("\n".join(L) + "\n")
    print({g: (len(v), size_txt(tot[g])) for g, v in groups.items()})
    for f, why in groups["판단"]:
        print("  판단:", f["path"], size_txt(f["size"]), why)


if __name__ == "__main__":
    main()
