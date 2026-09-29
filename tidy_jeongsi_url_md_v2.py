# -*- coding: utf-8 -*-
"""#0929-01-A 답 1·2: 2027_정시모집요강_URL_누적.md 정리 (백업: backup_20260929_v1/).

1. 세 칸이 미조사인 행의 확인일을 '-'로 바꾸고, 그 대학을 '미확인 대학 목록'에서 '미조사 대학 목록'의 같은 권역으로 옮긴다.
2. 예원예술대학교 행의 캠퍼스 칸('-')을 master 기준 연결캠퍼스명으로 채운다.
"""
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(HERE, "2027_정시모집요강_URL_누적.md")
BK = os.path.join(HERE, "backup_20260929_v1", "2027_정시모집요강_URL_누적.md")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def main():
    assert os.path.exists(BK), "백업 없음"
    ms = json.load(io.open(os.path.join(HERE, "university_master_list_v2.json"), encoding="utf-8"))
    yw = [r for r in ms["byRegion"]["경기"] if r["대학명"] == "예원예술대학교"]
    assert len(yw) == 1
    yw_campus = yw[0]["연결캠퍼스명"]

    lines = io.open(F, encoding="utf-8", newline="").read().replace("\r\n", "\n").split("\n")
    # 1) 표: 미조사 행 확인일 '-', 예원 캠퍼스
    sec, undone, date_changed = "", set(), 0
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            sec = ln[3:].strip()
        if sec == "조사 완료 대학" and ln.startswith("| ") and not ln.startswith("| 대학명"):
            c = cells(ln)
            if c[0] == "예원예술대학교" and c[1] == "-":
                c[1] = yw_campus
            if c[2:5] == ["미조사"] * 3:
                if c[5] != "-":
                    c[5] = "-"
                    date_changed += 1
                undone.add(c[0])
            lines[i] = "| " + " | ".join(c) + " |"
    # 2) 목록: 미확인 -> 미조사 (같은 권역 소제목 아래로)
    out, sec, sub = [], "", ""
    moved = {}
    for ln in lines:
        if ln.startswith("## "):
            sec, sub = ln[3:].strip(), ""
        elif ln.startswith("### "):
            sub = ln[4:].strip()
        m = re.match(r"^- (.+?) \((.+)\)\s*$", ln)
        if sec == "미확인 대학 목록" and m and m.group(1) in undone:
            camp = yw_campus if m.group(1) == "예원예술대학교" and m.group(2) == "-" else m.group(2)
            moved.setdefault(sub, []).append("- %s (%s)" % (m.group(1), camp))
            continue
        out.append(ln)
    final, sec, sub = [], "", ""
    for ln in out:
        if ln.startswith("## "):
            sec, sub = ln[3:].strip(), ""
        elif ln.startswith("### "):
            sub = ln[4:].strip()
        if sec == "미조사 대학 목록" and sub in moved and ln.startswith("- "):
            if ln.strip() == "- 없음":
                continue
            final.append(ln)
            continue
        final.append(ln)
        if sec == "미조사 대학 목록" and ln.startswith("### ") and sub in moved:
            final.append("")
            existing = []
            final.extend(sorted(set(moved[sub])))
    # 중복 빈 줄 정리(같은 소제목 아래 기존 항목과 옮긴 항목 사이)
    text = "\n".join(final)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 미조사 목록 안의 항목 정렬: 소제목별로 모아 가나다순
    blocks = re.split(r"(?m)^(### .+)$", text.split("## 미조사 대학 목록", 1)[1])
    head = text.split("## 미조사 대학 목록", 1)[0] + "## 미조사 대학 목록"
    rebuilt = blocks[0]
    for j in range(1, len(blocks), 2):
        title, body = blocks[j], blocks[j + 1]
        items = sorted(set(l for l in body.split("\n") if l.startswith("- ")))
        rest = [l for l in body.split("\n") if l.strip() and not l.startswith("- ")]
        rebuilt += title + "\n\n" + "\n".join(rest + items) + "\n\n"
    text = head + rebuilt.rstrip("\n") + "\n"
    io.open(F, "w", encoding="utf-8", newline="").write(text.replace("\n", "\r\n"))
    n_moved = sum(len(v) for v in moved.values())
    print("미조사 행(평택 포함) %d, 확인일 '-'로 바꾼 행 %d, 목록 이동 %d %s, 예원 캠퍼스 -> %s" % (
        len(undone), date_changed, n_moved, {k: len(v) for k, v in moved.items()}, yw_campus))


if __name__ == "__main__":
    main()
