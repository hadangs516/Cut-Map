# -*- coding: utf-8 -*-
"""작업 16: 2027_정시모집요강_URL_누적.md 정리 (백업: backup_20260924_decisions_v6/).

- '조사 완료 대학' 표에서 파일 URL·게시 페이지 URL·파일명이 모두 '미확인'이고 '조사 비고' 표에 없는 대학 행은
  세 칸을 '미조사'로 바꾼다. (이 파일에는 행별 비고 열이 없어 '조사 비고' 표를 비고로 본다)
- 경남과학기술대학교 행(표·목록)을 뺀다.
- 한경국립대학교(평택) 행을 추가한다 (안성과 입학처 공유, 미조사).
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "2027_정시모집요강_URL_누적.md")
BK = os.path.join(HERE, "backup_20260924_decisions_v6", "2027_정시모집요강_URL_누적.md")
PT_ROW = "| 한경국립대학교(평택) | 한경국립대학교 (본교(제2캠퍼스)) | 미조사 | 미조사 | 미조사 | - |"
PT_NOTE = "| 한경국립대학교(평택) | 안성과 입학처 공유, 미조사 |"
PT_ITEM = "- 한경국립대학교(평택) (한경국립대학교 (본교(제2캠퍼스)))"


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main():
    assert os.path.exists(BK), "백업 없음"
    lines = io.open(F, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")
    assert "한경국립대학교(평택)" not in "\n".join(lines), "이미 평택 행이 있음"

    sec = ""
    notes = set()
    for ln in lines:
        if ln.startswith("## "):
            sec = ln[3:].strip()
        elif sec == "조사 비고" and ln.startswith("| ") and not ln.startswith("| 대학명"):
            notes.add(cells(ln)[0])

    out, sec, sub = [], "", ""
    changed, removed = [], []
    for ln in lines:
        if ln.startswith("## "):
            sec, sub = ln[3:].strip(), ""
        elif ln.startswith("### "):
            sub = ln[4:].strip()
        if "경남과학기술대학교" in ln and (ln.startswith("| ") or ln.startswith("- ")):
            removed.append("%s%s: %s" % (sec, "/" + sub if sub else "", ln.strip()[:60]))
            continue
        if sec == "조사 완료 대학" and ln.startswith("| ") and not ln.startswith("| 대학명"):
            c = cells(ln)
            if c[2:5] == ["미확인"] * 3 and c[0] not in notes:
                c[2:5] = ["미조사"] * 3
                ln = "| " + " | ".join(c) + " |"
                changed.append(c[0] + " / " + c[1])
            out.append(ln)
            if c[0] == "한경국립대학교":
                out.append(PT_ROW)
            continue
        if sec == "조사 비고" and ln.startswith("| ") and not ln.startswith("| 대학명"):
            c = cells(ln)
            out.append(ln)
            if c[0] > "한경국립대학교(평택)" and PT_NOTE not in out:
                out.insert(len(out) - 1, PT_NOTE)
            continue
        if sec == "미조사 대학 목록" and sub == "경기" and ln.strip() == "- 없음":
            out.append(PT_ITEM)
            continue
        out.append(ln)
    if PT_NOTE not in out:  # 조사 비고 표 끝에 추가
        i = max(i for i, l in enumerate(out) if l.startswith("| ") and cells(l)[0] in notes)
        out.insert(i + 1, PT_NOTE)
    if PT_ITEM not in out:
        raise SystemExit("미조사 목록(경기)에 평택 항목을 넣을 자리를 찾지 못함")
    # 머리말에 관리 주체 기록
    for i, l in enumerate(out):
        if l.startswith("> 확인일:"):
            out.insert(i + 1, ">")
            out.insert(i + 2, "> 관리: 2026-09-28부터 Claude Code가 관리 (GPT 조사 중단). '미조사'는 확인을 시도하지 않은 칸, "
                              "'미확인'은 확인했으나 찾지 못한 칸 (SPEC 12번).")
            break
    io.open(F, "w", encoding="utf-8", newline="").write("\r\n".join(out))  # 원본과 같은 CRLF
    print("미조사로 바꾼 행 %d" % len(changed))
    for c in changed:
        print("  -", c)
    print("뺀 줄 %d: %s" % (len(removed), removed))


if __name__ == "__main__":
    main()
