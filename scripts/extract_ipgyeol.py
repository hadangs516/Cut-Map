# -*- coding: utf-8 -*-
"""학종(학생부종합전형) IT 학과 모집단위의 70% 컷을 sources/ipgyeol/ 원본 파일에서 뽑아 docs/data/ipgyeol.json 에 넣는다.

입력
  data/ipgyeol_sources.json   학교별 상태(받음)와 파일 목록, 원본 주소
  docs/data/targets.json      지도에 보이는 대상 마커
  docs/data/markers.json      마커별 IT 학과명(itDepts)
  sources/ipgyeol/            받은 원본 파일(수정하지 않는다)
출력
  docs/data/ipgyeol.json      { 마커 이름: [ {department, admission, year, cut70, note, ocr, source_file, page, source_url} ] }
  ipgyeol_extract_review.md   뽑은 값과 근거(행·열 이름, 찾은 방법, 원문 글자)

원칙
  - 값은 표의 행 이름(학과)과 열 이름(70% 컷)으로 코드가 찾은 것만 쓴다. 사람이나 AI가 숫자를 옮겨 적지 않는다.
  - 학종 행: 전형명에 "종합"이 들어 있거나, 그 파일 안에서 학생부종합전형으로 분류된 전형.
  - IT 학과 대응: markers.json 의 itDepts 와 표의 모집단위 이름이 띄어쓰기와 끝말(학과, 학부, 전공)만 빼고 같을 때만 맞춘다.
    같은 키가 한 전형에 두 번 나오면(값이 다르면) 맞추지 않고 보고한다.
  - 학교마다 가장 최근 학년도 값만 넣는다.
  - 70% 컷 열이 없고 50% 컷이나 평균만 있으면 cut70 은 null, note 에 "70% 컷 미공개(공개 항목: 열 이름)".
  - 글자가 없는 이미지 PDF는 tesseract 한국어 OCR 로 읽고 그 값은 ocr=true.

사용: python scripts/extract_ipgyeol.py [--write]   (--write 없으면 파일을 쓰지 않고 요약만 출력)
"""
import io
import json
import os
import re
import sys
import zipfile
from collections import OrderedDict, defaultdict

import fitz  # PyMuPDF
import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC_DIR = os.path.join(ROOT, "sources", "ipgyeol")
SOURCES_JSON = os.path.join(ROOT, "data", "ipgyeol_sources.json")
TARGETS_JSON = os.path.join(ROOT, "docs", "data", "targets.json")
MARKERS_JSON = os.path.join(ROOT, "docs", "data", "markers.json")
OUT_JSON = os.path.join(ROOT, "docs", "data", "ipgyeol.json")
OUT_MD = os.path.join(ROOT, "ipgyeol_extract_review.md")

NUM_RE = re.compile(r"^-?\d+(?:,\d{3})*(?:\.\d+)?$")


# ---------------------------------------------------------------- 공통 도구
PUNCT_RE = re.compile(r"[\s()\[\]{}（）［］\-－–—‐]")


def exact_key(name):
    """띄어쓰기, 괄호 기호, 붙임표(-)를 없앤 이름(끝말은 남긴다)."""
    return PUNCT_RE.sub("", name or "")


def norm_dept(name):
    """띄어쓰기, 괄호 기호, 붙임표를 없애고 끝말(학과, 학부, 전공) 하나만 뗀다."""
    return re.sub(r"(학과|학부|전공)$", "", exact_key(name))


def to_num(t):
    t = t.strip().replace(",", "")
    if NUM_RE.match(t):
        return float(t)
    return None


class W(object):
    """PDF 단어 하나."""
    __slots__ = ("x0", "x1", "y0", "y1", "t")

    def __init__(self, w):
        self.x0, self.y0, self.x1, self.y1, self.t = w[0], w[1], w[2], w[3], w[4]

    @property
    def xc(self):
        return (self.x0 + self.x1) / 2.0

    @property
    def yc(self):
        return (self.y0 + self.y1) / 2.0


def page_words(page):
    return [W(w) for w in page.get_text("words")]


def in_box(w, x0=-1e9, x1=1e9, y0=-1e9, y1=1e9):
    return x0 <= w.xc <= x1 and y0 <= w.yc <= y1


def find_words(ws, rx, **box):
    r = re.compile(rx)
    return sorted([w for w in ws if r.search(w.t) and in_box(w, **box)], key=lambda w: (w.x0, w.y0))


def line_text(ws, y, tol=3.0, **box):
    sel = sorted([w for w in ws if abs(w.yc - y) <= tol and in_box(w, **box)], key=lambda w: w.x0)
    return " ".join(w.t for w in sel)


def text_lines(ws, tol=2.5):
    out, cur, cy = [], [], None
    for w in sorted(ws, key=lambda w: (w.yc, w.x0)):
        if cy is None or abs(w.yc - cy) <= tol:
            cur.append(w)
            cy = w.yc if cy is None else (cy + w.yc) / 2.0
        else:
            out.append((cy, sorted(cur, key=lambda w: w.x0)))
            cur, cy = [w], w.yc
    if cur:
        out.append((cy, sorted(cur, key=lambda w: w.x0)))
    return out


def read_rows(ws, label_x, val_cols, y0, y1, tol_cols=14.0, anchor=None):
    """표를 좌표로 읽는다.
    label_x  : (x0, x1) 모집단위 이름이 있는 칸의 가로 범위
    val_cols : {열 이름: 가로 중심} 값 칸
    anchor   : 행의 세로 위치를 정하는 열 이름(없으면 값이 하나라도 있는 줄)
    반환     : [{"label": 이름, "y": 세로 위치, "vals": {열 이름: 숫자 또는 None 또는 문자 '-'}, "raw": 한 줄 글자}]
    """
    vals = {}
    for w in ws:
        if not (y0 <= w.yc <= y1):
            continue
        for name, cx in val_cols.items():
            if abs(w.xc - cx) <= tol_cols and (NUM_RE.match(w.t.replace(",", "")) or w.t in ("-", "－", "–")):
                vals.setdefault(round(w.yc, 0), {})[name] = w
    # 값 줄을 가까운 것끼리 묶는다
    ys = sorted(vals)
    groups = []
    for y in ys:
        if groups and abs(y - groups[-1][-1]) <= 3.5:
            groups[-1].append(y)
        else:
            groups.append([y])
    rows = []
    for g in groups:
        cells = {}
        for y in g:
            cells.update(vals[y])
        if anchor and anchor not in cells:
            continue
        yc = sum(c.yc for c in cells.values()) / len(cells)
        rows.append({"y": yc, "cells": cells})
    # 이름 칸 단어를 가장 가까운 행에 붙인다
    lab_words = [w for w in ws if y0 <= w.yc <= y1 and label_x[0] <= w.xc <= label_x[1]]
    for w in lab_words:
        if not rows:
            break
        best = min(rows, key=lambda r: abs(r["y"] - w.yc))
        if abs(best["y"] - w.yc) <= 22:
            best.setdefault("lab", []).append(w)
    out = []
    for r in rows:
        lab = sorted(r.get("lab", []), key=lambda w: (round(w.yc / 4.0), w.x0))
        label = "".join(w.t for w in lab) if lab else ""
        v = {}
        for name, c in r["cells"].items():
            v[name] = to_num(c.t)
        xmax = max(val_cols.values()) + 30
        out.append({"label": label, "y": r["y"], "vals": v,
                    "raw": line_text(ws, r["y"], tol=3.5, x0=label_x[0] - 4, x1=xmax),
                    "xr": (label_x[0] - 4, xmax), "label_words": lab})
    return out


def col_center(ws, rx, nth=0, **box):
    c = find_words(ws, rx, **box)
    if len(c) <= nth:
        return None
    return c[nth].xc


# ---------------------------------------------------------------- 결과 기록
class Rec(object):
    """뽑은 항목 하나(검토 파일에 한 줄)."""

    def __init__(self, **kw):
        self.school = kw.get("school")
        self.marker = kw.get("marker")
        self.dept = kw.get("dept")           # 표의 모집단위 이름
        self.admission = kw.get("admission")
        self.year = kw.get("year")
        self.cut70 = kw.get("cut70")
        self.note = kw.get("note")
        self.ocr = kw.get("ocr", False)
        self.file = kw.get("file")
        self.page = kw.get("page")
        self.table = kw.get("table")         # 표 제목, 행·열 이름
        self.method = kw.get("method")
        self.raw = kw.get("raw")             # 원문 한 줄


def load_json(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- 학교별 추출기
# 각 추출기는 raw 행 목록을 돌려준다.
#   raw = {dept, admission, year, cut70, cols, file, page, table, method, raw, ocr, no70col}
#   cut70      : 70% 컷 열의 값(숫자) 또는 None
#   no70col    : True 이면 그 표에 70% 컷 열이 없다 -> cols(공개 항목 열 이름)로 note 를 만든다
EXTRACTORS = OrderedDict()


def extractor(marker):
    def deco(fn):
        EXTRACTORS[marker] = fn
        return fn
    return deco


def src_path(fname):
    return os.path.join(SRC_DIR, fname)


def open_pdf(fname):
    return fitz.open(src_path(fname))


def mk(dept, admission, year, cut70, file, page, table, method, raw, cols=None, no70col=False, ocr=False, loc=None, ctx=None,
       other=None, note=None, force=False, note_only=False):
    """other: [{"label": 원문 열 이름, "value": 숫자}] 70% 컷이 아닌 공개 기준 값. note: 학교 쪽 설명(있으면 note 앞에 붙는다).
    force: IT 학과 대응을 거치지 않고 그대로 넣는 항목(학교 전체 값)."""
    return {"dept": dept, "admission": admission, "year": year, "cut70": cut70, "cols": cols or [], "file": file,
            "page": page, "table": table, "method": method, "raw": raw, "ocr": ocr, "no70col": no70col,
            "loc": loc, "ctx": ctx, "other": other or [], "note": note, "force": force, "note_only": note_only}


def others_from(vals, labels):
    """read_rows 가 읽은 vals 에서 'o:이름' 열의 숫자를 other 목록으로 만든다. labels: {'o:이름': 표시 이름}"""
    out = []
    for k, lab in labels.items():
        v = vals.get(k)
        if isinstance(v, (int, float)):
            out.append({"label": lab, "value": v})
    return out


@extractor("건국대학교(서울)")
def ex_konkuk(ctx):
    fname = "건국대학교(서울)_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    head = None
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        lines = text_lines(ws)
        ev = []
        for cy, l in lines:
            t = " ".join(w.t for w in l)
            if t.lstrip().startswith("▷"):
                ev.append((cy, "H", t.lstrip()[1:].strip()))
        for w in find_words(ws, r"^70%$"):
            nxt = [x for x in ws if abs(x.yc - w.yc) < 3 and 0 < x.x0 - w.x1 < 6 and x.t.lower().startswith("cut")]
            if nxt:
                ev.append((w.yc, "C", w.xc))
        ev.sort(key=lambda e: e[0])
        # 모집단위, 모집인원 머리말 칸으로 이름 범위를 정한다
        lab_hdr = find_words(ws, r"^모집단위$")
        cnt_hdr = find_words(ws, r"^모집인원$")
        col_hdr = find_words(ws, r"^단과대학$")
        if lab_hdr and cnt_hdr and col_hdr:
            label_x = (col_hdr[0].x1 + 20, cnt_hdr[0].x0 - 8)
        else:
            label_x = (110, 280)
        cur_col = None
        cur_hy = None
        seg_start = None
        segs = []  # (y0, y1, head, c70x, 머리말 y)
        pts = ev + [(page.rect.height + 1, "E", None)]
        last_y = 0
        for y, kind, data in pts:
            if kind == "H":
                if seg_start is not None and cur_col is not None:
                    segs.append((seg_start, y - 1, head, cur_col, cur_hy))
                head, cur_col, seg_start = data, None, None
            elif kind == "C":
                if seg_start is not None and cur_col is not None:
                    segs.append((seg_start, y - 1, head, cur_col, cur_hy))
                cur_col, seg_start, cur_hy = data, y + 12, y
            else:
                if seg_start is not None and cur_col is not None:
                    segs.append((seg_start, y, head, cur_col, cur_hy))
        for y0, y1, h, cx, hy in segs:
            if not h or "종합" not in h:
                continue
            c50 = [w for w in find_words(ws, r"^50%$", y0=hy - 4, y1=hy + 4) if w.xc < cx - 3]
            vc = {"70% Cut": cx}
            if c50:
                vc["o:50%"] = max(c50, key=lambda w: w.xc).xc
            rows = read_rows(ws, label_x, vc, y0, y1, tol_cols=16)
            for r in rows:
                if not r["label"]:
                    continue
                v = r["vals"].get("70% Cut")
                out.append(mk(r["label"], h, 2026, v, fname, pno,
                              "[수시] " + h + ", 열: 학생부 환산등급 > 70% Cut", "좌표(행=모집단위, 열=70% Cut)", r["raw"], loc=(pno, r["y"], r["xr"]),
                              other=others_from(r["vals"], {"o:50%": "학생부 환산등급 50% Cut"})))
    return out


@extractor("강원대학교(춘천)")
def ex_kangwon(ctx):
    """xlsx: 시트 '학생부종합'(전형 열은 세부전형)과 산포도 파일은 같은 전형이라 첫 파일만 쓴다."""
    fname = "강원대학교_2026_수시입결_1.xlsx"
    wb = openpyxl.load_workbook(src_path(fname), data_only=True)
    ws = wb["학생부종합"]
    # 머리말 두 줄(2,3행)에서 최종등록자 교과등급 현황 열 이름을 읽는다
    grp = None
    hdr = {}
    for c in ws[2]:
        if c.value and "최종등록자" in str(c.value):
            grp = c.column
    cols = []
    colidx = {}
    for c in ws[3]:
        if grp is not None and c.column >= grp and c.value:
            cols.append(str(c.value).replace("\n", ""))
            colidx[str(c.value).replace("\n", "")] = c.column
    out = []
    for r in ws.iter_rows(min_row=4):
        campus, college, dept, adm = [r[i].value for i in range(4)]
        if campus != "춘천" or not dept:
            continue
        oth = []
        for name in cols:
            if name == "표준편차":
                continue   # 분포 통계라 기준 값으로 보지 않는다
            v = ws.cell(r[0].row, colidx[name]).value
            if isinstance(v, (int, float)):
                oth.append({"label": "최종등록자 교과등급 " + name, "value": v})
        out.append(mk(str(dept).strip(), "학생부종합 " + str(adm).strip(), 2026, None, fname, "시트 학생부종합 %d행" % r[0].row,
                      "시트 '학생부종합', 열: 2026학년도 최종등록자 교과등급 현황 > " + ", ".join(cols),
                      "엑셀 셀(행=모집단위, 열=머리말 이름)", " | ".join(str(c.value) for c in r[:4]),
                      cols=["최종등록자 교과등급 " + c for c in cols[:1]] + cols[1:], no70col=True, other=oth))
    return out


# ---------------------------------------------------------------- 공통 처리
def build_notes(raw):
    """항목의 note. 학교 쪽 설명(raw["note"])이 있으면 그것을, 값이 없으면 이유를 덧붙인다."""
    extra = None
    if raw.get("note_only"):
        return raw.get("note")
    if raw["cut70"] is None:
        if raw["no70col"]:
            if raw.get("other"):
                extra = "70% 컷 미공개(공개 항목: " + ", ".join(o["label"] for o in raw["other"]) + ")"
            elif raw["cols"]:
                extra = "70% 컷 미공개(공개 항목: " + ", ".join(raw["cols"]) + ")"
            else:
                extra = "70% 컷 미공개"
        else:
            extra = "70% 컷 칸이 비어 있음('-', 공개 안 함)"
    if raw.get("note") and extra:
        return raw["note"] + " / " + extra
    return raw.get("note") or extra


@extractor("연세대학교(서울)")
def ex_yonsei(ctx):
    fname = "연세대학교(서울)_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        mid = page.rect.width / 2.0
        for half, (xa, xb) in (("좌", (0, mid)), ("우", (mid, 1e9))):
            hw = [w for w in ws if xa <= w.xc <= xb]
            # 표 제목: "N 학생부종합[...]" 이 있는 줄
            title = None
            for cy, l in text_lines(hw):
                t = " ".join(w.t for w in l)
                if cy < 175 and re.search(r"\d\s*학생부(교과|종합)\[", t):
                    title = re.sub(r"^\d+\s*", "", t.strip())
                    ty = cy
            if not title or "종합" not in title:
                continue
            h70 = [w for w in find_words(hw, r"^70%$", y0=ty, y1=ty + 70)]
            hcnt = find_words(hw, r"^모집인원$", y0=ty, y1=ty + 70)
            hlab = find_words(hw, r"^모집단위$", y0=ty, y1=ty + 70)
            hcol = find_words(hw, r"^단과대학$", y0=ty, y1=ty + 70)
            if not (h70 and hcnt and hlab and hcol):
                continue
            label_x = (hcol[0].x1 + 12, hcnt[0].x0 - 8)
            c50 = [w for w in find_words(hw, r"^50%$", y0=ty, y1=ty + 70) if w.xc < h70[0].xc - 3]
            vc = {"모집인원": hcnt[0].xc, "70%": h70[0].xc}
            if c50:
                vc["o:50%"] = max(c50, key=lambda w: w.xc).xc
            rows = read_rows(hw, label_x, vc, ty + 60, page.rect.height, tol_cols=16, anchor="모집인원")
            for r in rows:
                if not r["label"]:
                    continue
                out.append(mk(r["label"], title, 2026, r["vals"].get("70%"), fname, pno,
                              "표 '" + title + "', 열: 최종등록자 학생부 교과등급 > 70%", "좌표(행=모집단위, 열=70%)", r["raw"], loc=(pno, r["y"], r["xr"]),
                              other=others_from(r["vals"], {"o:50%": "최종등록자 학생부 교과등급 50%"})))
    return out


def page_regions(doc, heading_rx, line_filter=None):
    """제목 줄(heading_rx)로 나뉜 구역을 차례로 돌려준다. 앞 쪽에서 이어지는 구역도 포함.
    반환: (쪽 번호, 단어 목록, y0, y1, 제목 글자, 이어짐 여부)"""
    rx = re.compile(heading_rx)
    carry = None
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        heads = []
        for cy, l in text_lines(ws):
            t = " ".join(w.t for w in l)
            if rx.search(t):
                heads.append((cy, t.strip()))
        pts = [(0, carry)] + heads if carry else heads
        if carry and (not heads or heads[0][0] > 0):
            first = heads[0][0] if heads else page.rect.height
            yield pno, ws, 0, first - 1, carry, True
        for i, (y, t) in enumerate(heads):
            y_end = heads[i + 1][0] - 1 if i + 1 < len(heads) else page.rect.height
            yield pno, ws, y, y_end, t, False
        if heads:
            carry = heads[-1][1]


@extractor("서강대학교(서울)")
def ex_sogang(ctx):
    fname = "서강대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, ws, y0, y1, head, cont in page_regions(doc, r"^\d-\d\.\s*\S+"):
        if "종합" not in head:
            continue
        h70 = find_words(ws, r"^70%$", y0=y0, y1=y1)
        hcnt = find_words(ws, r"^모집인원$", y0=y0, y1=y1)
        hlab = find_words(ws, r"^모집단위$", y0=y0, y1=y1)
        if not (h70 and hcnt and hlab):
            continue
        h70 = h70[0]
        label_x = (hlab[0].x0 - 40, hcnt[0].x0 - 3)
        c50 = [w for w in find_words(ws, r"^50%컷$", y0=y0, y1=h70.y1 + 4) if w.xc < h70.xc - 3]
        vc = {"모집인원": hcnt[0].xc, "70%": h70.xc}
        if c50:
            vc["o:50%컷"] = max(c50, key=lambda w: w.xc).xc
        rows = read_rows(ws, label_x, vc, h70.y1 + 2, y1, tol_cols=14, anchor="모집인원")
        title = re.sub(r"^\d-\d\.\s*", "", head)
        for r in rows:
            if not r["label"] or r["label"].startswith("총계"):
                continue
            out.append(mk(r["label"], title, 2026, r["vals"].get("70%"), fname, pno,
                          "표 '" + head + "', 열: 최종등록자 석차등급 평균 > 70% cut", "좌표(행=모집단위, 열=70% cut)", r["raw"], loc=(pno, r["y"], r["xr"]),
                          other=others_from(r["vals"], {"o:50%컷": "최종등록자 석차등급 평균 50%컷"})))
    return out


def simple_table(ws, y0, y1, anchor_rx, c70_rx=None, lab_rx=r"^모집단위$", lab_pad=40, label_x=None, tol=14.0,
                 c70_nth=0, anchor_nth=0, lab_after=3, band=45.0, extra=None, extra_x=None):
    """구역 안에서 모집단위 행을 읽는다. c70_rx 열이 있으면 그 값을, 없으면 None 으로 둔다.
    머리말 칸은 기준 열(anchor) 머리말에서 아래로 band 만큼 안에서만 찾는다(자료 칸의 같은 글자와 섞이지 않게).
    반환: (rows, has70, info)  info = {"anchor_x", "c70_x"}"""
    hanc = find_words(ws, anchor_rx, y0=y0, y1=y1)
    if len(hanc) <= anchor_nth:
        return [], False, None
    anc = hanc[anchor_nth]
    hb = anc.yc + band
    h70 = find_words(ws, c70_rx, y0=y0, y1=hb) if c70_rx else []
    hlab = find_words(ws, lab_rx, y0=y0, y1=hb)
    if label_x is None:
        if not hlab:
            return [], False, None
        label_x = (hlab[0].x0 - lab_pad, anc.x0 - lab_after)
    cols = {"anchor": anc.xc}
    c70x = None
    if len(h70) > c70_nth:
        c70x = h70[c70_nth].xc
        cols["c70"] = c70x
    # 다른 공개 기준 열(other): 머리말 이름(정규식)으로 찾고, 70% 열이 있으면 그 왼쪽에서 가장 가까운 것
    elabels = {}
    for lab, rx in (extra or {}).items():
        cands = sorted(find_words(ws, rx, y0=y0, y1=hb), key=lambda w: w.xc)
        if c70x is not None:
            cands = [w for w in cands if w.xc < c70x - 3]
            pick = cands[-1] if cands else None
        else:
            pick = cands[0] if cands else None
        if pick is not None:
            cols["o:" + lab] = pick.xc
            elabels["o:" + lab] = lab
    for lab, x in (extra_x or {}).items():
        cols["o:" + lab] = x
        elabels["o:" + lab] = lab
    y_start = max([w.y1 for w in h70[:1]] + [anc.y1]) + 2
    rows = read_rows(ws, label_x, cols, y_start, y1, tol_cols=tol, anchor="anchor")
    for r in rows:
        r["c70"] = r["vals"].get("c70")
        r["other"] = others_from(r["vals"], elabels)
    return rows, c70x is not None, {"anchor_x": anc.xc, "c70_x": c70x}


@extractor("세종대학교(서울)")
def ex_sejong(ctx):
    fname = "세종대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    section = None
    for pno, ws, y0, y1, head, cont in page_regions(doc, r"^(□|I{1,3}\.)"):
        if re.match(r"^I{1,3}\.", head):
            section = head
            continue
        if not section or "학생부종합" not in section:
            continue
        rows, has70, info = simple_table(ws, y0, y1, r"^모집$", c70_rx=r"^70%$", lab_pad=100, label_x=(54, 262),
                                         extra={"50%": r"^50%$", "평균": r"^평균$", "최고": r"^최고$"})
        title = head.lstrip("□").strip()
        for r in rows:
            if not r["label"] or "요약" in r["label"]:
                continue
            out.append(mk(r["label"], "학생부종합 " + title, 2026, r["c70"], fname, pno,
                          "표 '" + head + "', 열: 최종등록자 학생부등급평균[진로선택 제외] > 70%", "좌표(행=모집단위, 열=70%)", r["raw"], loc=(pno, r["y"], r["xr"]),
                          cols=["최종등록자 학생부등급평균 최고, 평균, 50%"], no70col=not has70,
                          other=[dict(o, label="최종등록자 학생부등급평균 " + o["label"]) for o in r["other"]]))
    return out


@extractor("부산대학교(부산)")
def ex_pusan(ctx):
    fname = "부산대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, ws, y0, y1, head, cont in page_regions(doc, r"^\d-\d\s+\S+"):
        if "…" in head or "종합" not in head:
            continue
        rows, has70, info = simple_table(ws, y0, y1, r"^모집$", c70_rx=r"^70%$", lab_pad=30,
                                         extra={"50%": r"^50%$", "평균": r"^평균$"})
        title = re.sub(r"^\d-\d\s+", "", head)
        for r in rows:
            if not r["label"]:
                continue
            out.append(mk(r["label"], title, 2026, r["c70"], fname, pno,
                          "표 '" + head + "', 열: 교과종합등급 > 70%", "좌표(행=모집단위, 열=교과종합등급 70%)", r["raw"], loc=(pno, r["y"], r["xr"]),
                          cols=["교과종합등급 평균, 50%, 표준편차"], no70col=not has70,
                          other=[dict(o, label="교과종합등급 " + o["label"]) for o in r["other"]]))
    return out


def top_titles(ws, ymax=72):
    return [" ".join(w.t for w in l) for cy, l in text_lines(ws) if cy < ymax]


@extractor("숭실대학교(서울)")
def ex_soongsil(ctx):
    fname = "숭실대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    jong, adm = False, None
    for pno, page in enumerate(doc, 1):
        if pno > 38:
            break  # 39쪽부터는 2027학년도 모집 안내
        ws = page_words(page)
        tops = top_titles(ws, 60)
        if tops:
            jong = tops[0].strip() == "학생부종합"
            adm = tops[1].strip() if jong and len(tops) > 1 else None
        if not jong or not adm or "통계" in adm or "추이" in adm:
            continue
        txt = " ".join(w.t for w in ws)
        # 첫 각주(* ...) 위까지가 표다
        foot = [w.yc for w in ws if w.t == "*" and w.x0 < 60 and w.yc > 100]
        ybot = (min(foot) - 2) if foot else page.rect.height
        if find_words(ws, r"^70%$", y0=100, y1=140):
            # 등급 표(모집단위, 주요교과 등급 평균·70%)
            rows, has70, info = simple_table(ws, 0, ybot, r"^평균$", c70_rx=r"^70%$", lab_pad=60, label_x=(40, 150),
                                             extra={"평균": r"^평균$"})
            tbl = "표 '" + adm + "', 열: 주요교과 등급 > 70%"
            for r in rows:
                if r["label"]:
                    out.append(mk(r["label"], "학생부종합 " + adm, 2026, r["c70"], fname, pno, tbl,
                                  "좌표(행=모집단위, 열=주요교과 등급 70%)", r["raw"], loc=(pno, r["y"], r["xr"]), cols=["주요교과 등급 평균"], no70col=not has70,
                                  other=[dict(o, label="주요교과 등급 " + o["label"]) for o in r["other"]],
                                  note="대상 집단 표기 없음" if r["c70"] is not None and adm == "SSU미래인재전형" else None))
        elif "주요교과" in txt and find_words(ws, r"^모집인원$", y0=100, y1=160):
            # 70% 열이 없는 표: 모집인원·경쟁률·충원 + 주요교과 평균
            # 주요교과 평균 열: 머리말 '주요교과' 아래 글자로 열 이름을 만든다(예: 주요교과 평균성적, 주요교과 평균 등급)
            hj = find_words(ws, r"^주요교과$", y0=100, y1=160)
            ex = {}
            if hj:
                below = [w for w in ws if abs(w.xc - hj[0].xc) <= 35 and hj[0].y1 < w.yc <= hj[0].yc + 28]
                nm = " ".join(w.t for w in sorted(below, key=lambda w: (round(w.yc / 3), w.x0)))
                ex = {"주요교과 " + nm: hj[0].xc}
            rows, has70, info = simple_table(ws, 0, ybot, r"^모집인원$", c70_rx=None, lab_pad=60,
                                             label_x=(40, 150), extra_x=ex)
            for r in rows:
                if r["label"]:
                    out.append(mk(r["label"], "학생부종합 " + adm, 2026, None, fname, pno,
                                  "표 '" + adm + "', 열: 주요교과 평균(70% 열 없음)", "좌표(행=모집단위)", r["raw"], loc=(pno, r["y"], r["xr"]),
                                  cols=["주요교과 평균"], no70col=True, other=r["other"]))
    return out


def read_label_rows(ws, label_x, val_cols, y0, y1, tol_cols=10.0, ytol=4.0):
    """이름 칸의 줄마다 한 행으로 보고, 같은 줄의 값 칸 숫자를 읽는다(값이 비어 있어도 행은 남는다)."""
    lab = [w for w in ws if y0 <= w.yc <= y1 and label_x[0] <= w.xc <= label_x[1]]
    rows = []
    for cy, l in text_lines(lab, tol=2.5):
        label = " ".join(w.t for w in l)
        v = {}
        for w in ws:
            if abs(w.yc - cy) <= ytol:
                for name, cx in val_cols.items():
                    if abs(w.xc - cx) <= tol_cols and (NUM_RE.match(w.t.replace(",", "")) or w.t in ("-", "－", "–")):
                        v[name] = to_num(w.t)
        xmax = max(val_cols.values()) + 30
        rows.append({"label": label, "y": cy, "vals": v, "raw": line_text(ws, cy, tol=ytol, x0=label_x[0] - 4, x1=xmax),
                     "xr": (label_x[0] - 4, xmax)})
    return rows


@extractor("경희대학교 (본교(제2캠퍼스))")
def ex_khu(ctx):
    fname = "경희대학교(국제캠퍼스)_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        foot = [" ".join(w.t for w in l) for cy, l in text_lines(ws) if cy > page.rect.height - 40]
        ft = " ".join(foot)
        m = re.search(r"통계자료\s+(학생부종합\s*\[[^\]|]*\])", ft)
        if not m:
            continue
        adm = re.sub(r"\s+", " ", m.group(1))
        # 오른쪽 표: 최종등록자 학생부등급 50% CUT / 70% CUT
        h70 = find_words(ws, r"^70%$", x0=640, y0=100, y1=260)
        hlab = find_words(ws, r"^모집단위$", x0=600, y0=100, y1=260)
        if not hlab:
            continue
        if not h70:
            # 70% 열이 없는 표(기회균형 등): 합격자 학생부 교과등급 평균만 공개
            havg = find_words(ws, r"^평균$", x0=700, y0=100, y1=260)
            if not havg:
                continue
            label_x = (hlab[0].x0 - 40, havg[0].x0 - 6)
            rows = read_label_rows(ws, label_x, {"o:avg": havg[0].xc}, havg[0].y1 + 8, page.rect.height - 45)
            for r in rows:
                if r["label"] and r["vals"]:
                    out.append(mk(r["label"], adm, 2026, None, fname, pno,
                                  "표 '" + adm + "', 열: 합격자 학생부 교과등급 > 평균(70% 열 없음)", "좌표(행=모집단위)", r["raw"], loc=(pno, r["y"], r["xr"]),
                                  cols=["합격자 학생부 교과등급 평균", "합격자 학생부 교과등급 분포(1~9등급)"], no70col=True,
                                  other=others_from(r["vals"], {"o:avg": "합격자 학생부 교과등급 평균"})))
            continue
        h70 = h70[0]
        h50 = find_words(ws, r"^50%$", x0=640, y0=100, y1=260)
        label_x = (hlab[0].x0 - 40, (h50[0].x0 if h50 else h70.x0 - 20) - 4)
        vc = {"c70": h70.xc}
        labs = {}
        if h50:
            vc["o:50"] = h50[0].xc
            labs["o:50"] = "최종등록자 학생부등급 50% CUT"
        havg2 = find_words(ws, r"^평균$", x0=700, y0=100, y1=260)
        if havg2:
            vc["o:avg"] = havg2[0].xc
            labs["o:avg"] = "합격자 학생부등급 평균"
        rows = read_label_rows(ws, label_x, vc, h70.y1 + 8, page.rect.height - 45)
        for r in rows:
            if not r["label"]:
                continue
            out.append(mk(r["label"], adm, 2026, r["vals"].get("c70"), fname, pno,
                          "표 '" + adm + "', 열: 최종등록자 학생부등급 > 70% CUT", "좌표(행=모집단위, 열=70% CUT)", r["raw"], loc=(pno, r["y"], r["xr"]),
                          other=others_from(r["vals"], labs)))
    return out


@extractor("충북대학교(청주)")
def ex_chungbuk(ctx):
    """세로로 돌려 놓은 표: 모집단위가 열, 70% 등이 행. 행 이름은 최종등록자 > 내신등급 > 70%."""
    out = []
    for fname in ("충북대학교_2026_수시입결_1.pdf", "충북대학교_2026_수시입결_2.pdf", "충북대학교_2026_수시입결_3.pdf"):
        doc = open_pdf(fname)
        for pno, page in enumerate(doc, 1):
            ws = page_words(page)
            lab70 = sorted([w for w in ws if w.t == "70%" and w.xc < 190], key=lambda w: w.xc)
            lab_dept = sorted([w for w in ws if w.t == "모집단위" and w.xc < 190], key=lambda w: w.xc)
            grp = [w for w in ws if w.t == "최종등록자" and w.xc < 190]
            first = [w for w in ws if w.t == "최초합격자" and w.xc < 190]
            if not (lab70 and lab_dept and grp):
                continue
            l70, ld, g = lab70[0], lab_dept[0], grp[0]
            if first and l70.yc > first[0].yc:
                continue  # 최초합격자 쪽 70% 는 쓰지 않는다
            title = [w.t for w in ws if re.match(r"^\[학생부", w.t)]
            adm = title[0].strip("[]") if title else None
            if not adm:
                continue
            names = sorted([w for w in ws if abs(w.yc - ld.yc) < 14 and w.xc > ld.xc + 8], key=lambda w: w.xc)
            for nm in names:
                cell = [w for w in ws if abs(w.xc - nm.xc) < 6 and abs(w.yc - l70.yc) < 6 and NUM_RE.match(w.t)]
                v = to_num(cell[0].t) if cell else None
                v50 = [w for w in ws if abs(w.xc - nm.xc) < 6 and abs(w.yc - (l70.yc + 46)) < 6 and NUM_RE.match(w.t)]
                ctx = ["모집단위: " + nm.t + " (가로 위치 %d)" % nm.xc,
                       "최종등록자 > 내신등급 > 70%: " + (cell[0].t if cell else "(빈 칸)"),
                       "최종등록자 > 내신등급 > 50%: " + (v50[0].t if v50 else "(빈 칸)")]
                out.append(mk(nm.t, adm, 2026, v, fname, pno,
                              "표 '" + adm + "', 열(세로 표의 행): 최종등록자 > 내신등급 > 70%", "좌표(열=모집단위, 행=70%)",
                              nm.t + " | 70%=" + (cell[0].t if cell else "(빈 칸)"), ctx=ctx))
    return out


@extractor("한양대학교(에리카)")
def ex_erica(ctx):
    fname = "한양대학교(ERICA)_2024-2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        title = " ".join(w.t for cy, l in text_lines(ws) if cy < 60 for w in l)
        if "학생부종합" not in title or "고른기회" in title:
            continue
        h70 = [w for w in find_words(ws, r"^70%$", y0=40, y1=110)]
        if not h70:
            continue
        h70 = h70[0]
        # 70% cut 그룹 아래의 학년도 머리말 중 가장 최근 것
        yrs = [w for w in find_words(ws, r"^20\d\d$", y0=100, y1=130) if h70.x0 - 130 <= w.xc <= h70.x1 + 20]
        if not yrs:
            continue
        ylast = max(yrs, key=lambda w: int(w.t))
        hlab = find_words(ws, r"^모집단위$", y0=60, y1=130)
        label_x = (80, min(w.x0 for w in yrs) - 10 if False else 235)
        cols = {"c70": ylast.xc}
        # 행 위치는 같은 그룹의 학년도 세 칸 중 어느 하나라도 값이 있는 줄
        cols2 = {"y%s" % w.t: w.xc for w in yrs}
        cols2["c70"] = ylast.xc
        # 다른 공개 기준: 같은 학년도 칸의 최초합격자 평균등급, 최종등록자 평균등급(머리말 순서: 최초합격자, 최종등록자, 최종등록자 70% cut)
        all_last = sorted(find_words(ws, "^" + ylast.t + "$", y0=100, y1=130), key=lambda w: w.xc)
        elab = {}
        if len(all_last) == 3:
            cols2["o:최초"], cols2["o:최종"] = all_last[0].xc, all_last[1].xc
            elab = {"o:최초": "최초합격자 평균등급", "o:최종": "최종등록자 평균등급"}
        rows = read_rows(ws, label_x, cols2, ylast.y1 + 4, 960, tol_cols=14)
        for r in rows:
            if not r["label"] or r["vals"].get("c70", None) is None and "c70" not in r["vals"] and not r["vals"]:
                continue
            out.append(mk(r["label"], "학생부종합(서류형, 면접형)", int(ylast.t), r["vals"].get("c70"), fname, pno,
                          "표 '2024~2026학년도 수시모집 학생부종합전형 입시결과', 열: 최종등록자 평균등급 70% cut > " + ylast.t,
                          "좌표(행=모집단위, 열=70% cut의 " + ylast.t + "학년도 칸)", r["raw"], loc=(pno, r["y"], r["xr"]),
                          other=others_from(r["vals"], elab)))
    return out


@extractor("동국대학교(서울)")
def ex_dongguk(ctx):
    """학종 표는 2026학년도·2025학년도 두 묶음이고 열은 지원현황, 학생부 평균·최저, 충원율이다(70% 열 없음)."""
    fname = "동국대학교(서울)_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, ws, y0, y1, head, cont in page_regions(doc, r"^■ \[학생부"):
        if "종합" not in head or cont:
            continue
        adm = re.sub(r"\s*최종등록자 기준|\s*1단계 합격자 기준", "", re.sub(r"^■\s*", "", head)).strip()
        hm = find_words(ws, r"^모집$", y0=y0, y1=y1)
        if not hm:
            continue
        vc = {"m": hm[0].xc}
        elab = {}
        for nm, rx in (("학생부 평균", r"^평균$"), ("학생부 최저", r"^최저$")):
            hh = find_words(ws, rx, y0=hm[0].y0 - 5, y1=hm[0].y0 + 40)   # 왼쪽 묶음이 2026학년도
            if hh:
                vc["o:" + nm] = hh[0].xc
                elab["o:" + nm] = nm
        rows = read_label_rows(ws, (125, 232), vc, hm[0].y1 + 2, y1)
        for r in rows:
            r["label"] = re.sub(r"\s+\d+$", "", re.sub(r"(?<=[가-힣A-Za-z])\d+$", "", r["label"]))
            if r["label"] and r["vals"]:   # 모집 칸이 비어 있으면 그 전형에서 모집하지 않는 단위
                out.append(mk(r["label"], adm, 2026, None, fname, pno,
                              "표 '" + head + "', 열: 2026학년도 지원현황, 학생부 평균·최저, 충원율(70% 열 없음)",
                              "좌표(행=모집단위)", r["raw"], loc=(pno, r["y"], r["xr"]), cols=["2026학년도 학생부 평균", "학생부 최저"], no70col=True,
                              other=others_from(r["vals"], elab)))
    return out


@extractor("광운대학교(서울)")
def ex_kwangwoon(ctx):
    """학종 표에는 70% 열이 없다. 열은 학생부 등급(진로선택제외)이고, 안내문에 최종등록자 환산점수 기준 70% 컷 학생의 성적이라고 적혀 있다."""
    fname = "광운대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, ws, y0, y1, head, cont in page_regions(doc, r"^\[수시\]"):
        if "종합" not in head:
            continue
        adm = re.sub(r"^\[수시\]\s*", "", head)
        hm = find_words(ws, r"^인원$", y0=y0, y1=y1)
        if not hm:
            continue
        hc = find_words(ws, r"^\(진로선택제외\)$", y0=y0, y1=y1)
        vc = {"m": hm[0].xc}
        if hc:
            vc["c70"] = hc[0].xc
        rows = read_label_rows(ws, (60, 222), vc, hm[0].y1 + 3, y1)
        guide = "학교 안내문: 최종등록자 환산점수 기준 70% 컷 학생의 성적"
        for r in rows:
            if r["label"] and "※" not in r["label"] and r["vals"]:   # 모집 칸이 비어 있으면 그 전형에서 모집하지 않는 단위
                out.append(mk(r["label"], adm, 2026, r["vals"].get("c70"), fname, pno,
                              "표 '" + head + "', 열: 학생부 등급(진로선택제외)(학교 안내문: 최종등록자 환산점수 기준 70% 컷 학생의 성적)",
                              "좌표(행=모집단위, 열=학생부 등급(진로선택제외))", r["raw"], loc=(pno, r["y"], r["xr"]),
                              cols=["학생부 등급(진로선택제외)"], no70col=not hc, note=guide))
    return out


def xlsx_groups(ws, grp_row, first_col=1):
    """머리말 행의 묶음 이름과 열 범위를 돌려준다(이름이 있는 칸에서 다음 이름 전까지)."""
    heads = [(c.column, str(c.value).strip().replace("\n", " ")) for c in ws[grp_row] if c.value not in (None, "") and c.column > first_col]
    out = []
    for i, (col, name) in enumerate(heads):
        end = (heads[i + 1][0] - 1) if i + 1 < len(heads) else ws.max_column
        out.append((name, col, end))
    return out


def col_names(ws, rows, c0, c1):
    names = {}
    for col in range(c0, c1 + 1):
        parts = []
        for r in rows:
            v = ws.cell(r, col).value
            if v not in (None, ""):
                parts.append(str(v).strip().replace("\n", " "))
        names[col] = " ".join(parts)
    return names


@extractor("대구가톨릭대학교(경산)")
def ex_dcu(ctx):
    """성적자료 엑셀: 학생부종합(종합전형) 묶음의 열은 평균 등급, 85% 컷 등(70% 열 없음). 같은 표의 PDF는 읽지 않는다."""
    fname = "대구가톨릭대학교_2026_수시입결_2.xlsx"
    wb = openpyxl.load_workbook(src_path(fname), data_only=True)
    ws = wb.worksheets[0]
    out = []
    for name, c0, c1 in xlsx_groups(ws, 10):
        if "종합" not in name:
            continue
        cn = col_names(ws, [11], c0, c1)
        c70 = [c for c, n in cn.items() if re.match(r"^70\s*%", n)]
        score_cols = [n.replace(" ", "") if "컷" in n else n for c, n in cn.items() if re.search(r"등급|컷|점수|평균", n)]
        first_val_col = c0 + 1   # '모집' 칸(2027 모집인원 다음)
        for r in range(12, ws.max_row + 1):
            dept = ws.cell(r, 1).value
            if not dept or ws.cell(r, first_val_col).value in (None, ""):
                continue
            v70 = ws.cell(r, c70[0]).value if c70 else None
            oth = [{"label": n, "value": ws.cell(r, c).value} for c, n in cn.items()
                   if re.search(r"등급|컷|점수|평균", n) and not re.match(r"^70\s*%", n) and isinstance(ws.cell(r, c).value, (int, float))]
            out.append(mk(str(dept).strip(), name, 2026, v70 if isinstance(v70, (int, float)) else None, fname, "시트 %s %d행" % (ws.title, r),
                          "시트 '성적자료_공개용', 묶음 '" + name + "', 열: " + ", ".join(cn.values()),
                          "엑셀 셀(행=모집단위명, 열=머리말 이름)", " | ".join(str(ws.cell(r, c).value) for c in [1] + list(range(c0, c1 + 1))),
                          cols=score_cols, no70col=not c70, other=oth))
    return out


@extractor("대구대학교(경산)")
def ex_daegu(ctx):
    """엑셀: 학생부종합(서류전형)·(지역인재전형) 묶음의 열은 전 과목 (참고) 등급 평균 등(70% 열 없음). 같은 표의 PDF는 읽지 않는다."""
    fname = "대구대학교_2026_수시입결_2.xlsx"
    wb = openpyxl.load_workbook(src_path(fname), data_only=True)
    ws = wb.worksheets[0]
    out = []
    for name, c0, c1 in xlsx_groups(ws, 13, first_col=3):
        if "종합" not in name:
            continue
        cn = col_names(ws, [15, 16], c0, c1)
        c70 = [c for c, n in cn.items() if re.match(r"^70\s*%", n)]
        score_cols = [n for c, n in cn.items() if re.search(r"등급|컷|점수|평균", n)]
        if not score_cols:
            continue   # 결과 열이 없는 묶음(지역인재전형: 모집인원만 있음)
        # 2026학년도 모집인원 칸(머리말 행 14 에 2026)
        c2026 = [c for c in range(c0, c1 + 1) if ws.cell(14, c).value == 2026]
        key_col = c2026[0] if c2026 else c0
        for r in range(18, ws.max_row + 1):
            dept = ws.cell(r, 2).value
            if not dept or ws.cell(r, key_col).value in (None, "", 0):
                continue
            oth = [{"label": n, "value": ws.cell(r, c).value} for c, n in cn.items()
                   if re.search(r"등급|컷|점수|평균", n) and isinstance(ws.cell(r, c).value, (int, float))]
            out.append(mk(str(dept).strip(), name, 2026, None, fname, "시트 %s %d행" % (ws.title, r),
                          "시트 '" + ws.title + "', 묶음 '" + name + "', 열: " + ", ".join(cn.values()),
                          "엑셀 셀(행=모집단위명, 열=머리말 이름)", " | ".join(str(ws.cell(r, c).value) for c in [2] + list(range(c0, c1 + 1))),
                          cols=score_cols, no70col=not c70, other=oth))
    return out


@extractor("한양대학교(서울)")
def ex_hanyang_seoul(ctx):
    """학종 표(추천형·서류형·면접형)의 열은 경쟁률, 추가합격인원, 최종등록자 내신등급 평균, 수능최저충족률이다(70% 열 없음)."""
    fname = "한양대학교(서울)_2024-2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno in (6, 7):
        page = doc[pno - 1]
        ws = page_words(page)
        mid = page.rect.width / 2.0
        for xa, xb in ((0, mid), (mid, 1e9)):
            hw = [w for w in ws if xa <= w.xc <= xb]
            titles = [w for cy, l in text_lines(hw) if 70 < cy < 95 for w in l]
            title = "".join(w.t for w in titles).strip()
            if "학생부종합" not in title:
                continue
            g = [w for w in hw if w.t in ("최종등록자", "내신등급", "평균") and 140 < w.yc < 150]
            if not g:
                continue
            gx0, gx1 = min(w.x0 for w in g), max(w.x1 for w in g)
            yrs = sorted([w for w in find_words(hw, r"^2026$", y0=155, y1=170) if gx0 - 12 <= w.xc <= gx1 + 12], key=lambda w: w.xc)
            hlab = find_words(hw, r"^모집단위$", y0=145, y1=165)
            hcls = find_words(hw, r"^계열$", y0=145, y1=165)
            if not (yrs and hlab and hcls):
                continue
            label_x = (hlab[0].x0 - 45, hcls[0].x0 - 3)
            rows = read_rows(hw, label_x, {"c": yrs[0].xc}, 172, page.rect.height - 40, tol_cols=12, anchor="c")
            for r in rows:
                if r["label"]:
                    out.append(mk(r["label"], title, 2026, None, fname, pno,
                                  "표 '" + title + "', 열: 최종등록자 내신등급 평균 > 2026(70% 열 없음)", "좌표(행=모집단위)", r["raw"], loc=(pno, r["y"], r["xr"]),
                                  cols=["최종등록자 내신등급 평균"], no70col=True,
                                  other=others_from({"o:평균": r["vals"].get("c")}, {"o:평균": "최종등록자 내신등급 평균"})))
    return out


@extractor("홍익대학교 (본교(제1캠퍼스))")
def ex_hongik(ctx):
    """zip 안 PDF(글자 있음). 학종은 '학교생활우수자_종합' 표: 최종등록자 교과등급 평균·70%."""
    zname = "홍익대학교(서울)_2026_수시입결_1.zip"
    zf = zipfile.ZipFile(src_path(zname))
    inner = zf.namelist()[0]
    doc = fitz.open(stream=zf.read(inner), filetype="pdf")
    out = []
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        tops = [(cy, " ".join(w.t for w in l)) for cy, l in text_lines(ws) if 70 < cy < 100]
        title = tops[0][1].strip() if tops else ""
        if "종합" not in title:
            continue
        rows, has70, info = simple_table(ws, 0, page.rect.height - 40, r"^모집인원$", c70_rx=r"^70%$", lab_pad=30, band=60,
                                         extra={"평균": r"^평균$"})
        for r in rows:
            if r["label"].replace(" ", "").startswith("서울캠퍼스합계"):
                break  # 이 아래는 세종캠퍼스 행(다른 마커)
            if r["label"] and r["label"] != "공과대학":
                out.append(mk(r["label"], title, 2026, r["c70"], zname + " > " + inner, pno,
                              "표 '" + title + "', 열: 최종등록자 교과등급 > 70%", "좌표(행=모집단위, 열=교과등급 70%), zip 안 PDF 글자 추출",
                              r["raw"], loc=(pno, r["y"], r["xr"]), cols=["최종등록자 교과등급 평균"], no70col=not has70,
                              other=[dict(o, label="최종등록자 교과등급 " + o["label"]) for o in r["other"]]))
    return out


class OcrUnavailable(Exception):
    pass


def ocr_page_text(doc, pno, dpi=220):
    """이미지 쪽을 tesseract 한국어로 읽는다. 도구가 없으면 OcrUnavailable."""
    import shutil
    import subprocess
    import tempfile
    exe = shutil.which("tesseract")
    if not exe:
        raise OcrUnavailable("tesseract 없음")
    langs = subprocess.run([exe, "--list-langs"], capture_output=True, text=True).stdout
    if "kor" not in langs.split():
        raise OcrUnavailable("tesseract 한국어(kor) 데이터 없음")
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "p.png")
        doc[pno - 1].get_pixmap(dpi=dpi).save(png)
        subprocess.run([exe, png, os.path.join(td, "o"), "-l", "kor+eng", "--psm", "6"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        with io.open(os.path.join(td, "o.txt"), encoding="utf-8") as f:
            return f.read()


@extractor("한동대학교(포항)")
def ex_handong(ctx):
    """학과별 표가 없고 전형별 표만 있다. 2쪽 '입학생 평균 내신등급(학생부종합)' 표의 G-IMPACT인재 행을
    학과 구분 없는 항목으로 넣는다(IT 학과 대응을 거치지 않는다)."""
    fname = "한동대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    page = doc[1]
    ws = page_words(page)
    tt = find_words(ws, r"^내신등급\(학생부종합\)$")
    if not tt:
        return out
    y0 = tt[0].y1
    h70 = find_words(ws, r"^등급\(70%Cut\)$", y0=y0, y1=y0 + 80)
    havg = find_words(ws, r"^등급\(평균\)$", y0=y0, y1=y0 + 80)
    rw = find_words(ws, r"^G-IMPACT인재$", y0=y0, y1=y0 + 160)
    if not (h70 and havg and rw):
        return out
    cols = {"c70": h70[0].xc, "o:avg": havg[0].xc}
    rows = read_rows(ws, (rw[0].x0 - 4, rw[0].x1 + 4), cols, rw[0].y0 - 3, rw[0].y1 + 3, tol_cols=14, anchor="c70")
    for r in rows:
        v = r["vals"]
        if not isinstance(v.get("c70"), (int, float)):
            continue
        out.append(mk("전형 전체(학과 구분 없음)", "G-IMPACT인재", 2026, v["c70"], fname, 2,
                      "표 '입학생 평균 내신등급(학생부종합)', 열: 등급(70%Cut)", "좌표(행=전형명, 열=등급(70%Cut))",
                      r["raw"], loc=(2, r["y"], r["xr"]), other=others_from(v, {"o:avg": "등급(평균)"}), force=True))
    return out


@extractor("성균관대학교 (본교(제2캠퍼스))")
def ex_skku(ctx):
    """글자 없는 이미지 PDF: OCR 로 읽는다. 학종 표(융합형·탐구형·기회균형·성균인재·과학인재)에는 학생부 성적 열이 없다.
    50%cut·70%cut 열은 학교장추천(학생부교과) 표에만 있다."""
    fname = "성균관대학교(수원)_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    head = None
    for pno in range(2, len(doc) + 1):
        txt = ocr_page_text(doc, pno)
        cols_seen = [c for c in ("모집인원", "지원인원", "경쟁률", "충원합격인원", "충원율") if c in txt.replace(" ", "")]
        for line in txt.splitlines():
            m = re.search(r"학생부종합\(([^)]*)\)", line)
            if m:
                head = "학생부종합(" + m.group(1) + ")"
                continue
            if re.search(r"(정원외 특별전형|논술위주|학교장추천|일반전형|특별전형)", line):
                head = None
                continue
            if not head:
                continue
            m = re.match(r"^[\s\[\]|(·]*([가-힣A-Za-z·()0-9]{2,20}?)(?:\s{2,}|\s*\||\s+[0-9]|$)", line)
            if m:
                label = m.group(1)
                lines = txt.splitlines()
                k = lines.index(line)
                ctx = [x.strip() for x in lines[max(0, k - 1):k + 2]]
                out.append(mk(label, head, 2026, None, fname, pno,
                              "표 '" + head + "'(OCR), 열: " + ", ".join(cols_seen) + "(성적 열 없음)", "OCR 글자(행=모집단위)", line.strip(),
                              cols=["모집인원", "지원인원", "경쟁률", "충원합격인원", "충원율"], no70col=True, ocr=True, ctx=ctx,
                              note="학종 성적 미공개", note_only=True))
    return out


# ---------------------------------------------------------------- 학교 한 곳 처리, 결과 모으기
# 사용자 지시로 값 대신 note 만 넣는 마커
SPECIAL = OrderedDict([
    ("서울대학교(서울)", {"note": "입결 미공개", "file": None, "reason": "받은 파일 없음(학종 자료 없음)"}),
])


def punct_key(name):
    """가운뎃점, 밑줄, 쉼표, 빗금까지 모두 뺀 비교용 키(근접 후보 보고에만 쓴다)."""
    return norm_dept(re.sub(r"[·_/,]", "", name or ""))


def process_school(marker, raws, it_names):
    """raw 행 -> (맞춘 항목, 짝 목록, 버린 항목, 근접 후보, 학년도)."""
    exact_set = {exact_key(n) for n in it_names}
    itmap = defaultdict(list)
    for n in it_names:
        itmap[norm_dept(n)].append(n)
    forced = [r for r in raws if r.get("force")]
    cand = [r for r in raws if not r.get("force") and norm_dept(r["dept"]) in itmap]
    # 가장 최근 학년도만
    years = [r["year"] for r in cand if r["year"] is not None]
    latest = max(years) if years else None
    cand = [r for r in cand if r["year"] == latest]
    matched, dropped = [], []
    # 한 표(전형, 학년도) 안에서 끝말을 뗀 이름이 같은 행이 둘 이상이면: 이름 전체가 IT 학과명과 같은 행만 맞춘다
    by_key = defaultdict(list)
    for r in cand:
        by_key[(r["admission"], r["year"], norm_dept(r["dept"]))].append(r)
    for key, g in by_key.items():
        names = {exact_key(r["dept"]) for r in g}
        if len(names) > 1:
            keep = [r for r in g if exact_key(r["dept"]) in exact_set]
            drop = [r for r in g if r not in keep]
            matched += keep
            if drop:
                dropped.append(("같은 전형 안에 끝말만 다른 이름이 여러 개이고 이름 전체가 일치하지 않음", drop))
        else:
            matched += g
    # 같은 (이름, 전형, 학년도)가 여러 번: 값이 모두 같으면 하나, 다르면 버린다
    final, seen = [], OrderedDict()
    for r in matched:
        seen.setdefault((exact_key(r["dept"]), r["admission"], r["year"]), []).append(r)
    for k, g in seen.items():
        if len({x["cut70"] for x in g}) > 1:
            dropped.append(("같은 이름·전형·학년도에 값이 서로 다른 행이 둘 이상", g))
        else:
            final.append(g[0])
    pairs = []
    for r in final:
        e = exact_key(r["dept"])
        same = [n for n in it_names if exact_key(n) == e] or itmap[norm_dept(r["dept"])]
        pairs.append((r["dept"], same[0] if len(set(same)) == 1 else " / ".join(sorted(set(same)))))
    # 근접 후보: 가운뎃점·밑줄 등까지 무시하면 같아지지만 규칙으로는 안 맞은 이름
    pk = defaultdict(list)
    for n in it_names:
        pk[punct_key(n)].append(n)
    near = OrderedDict()
    for r in raws:
        if r.get("force") or r["year"] != latest or norm_dept(r["dept"]) in itmap:
            continue
        k = punct_key(r["dept"])
        if k in pk:
            near.setdefault((r["dept"], tuple(sorted(set(pk[k])))), r["admission"])
    return forced + final, sorted(set(pairs)), dropped, list(near.items()), latest


def collect(only=None):
    srcs = load_json(SOURCES_JSON)
    markers = {m["campus"]: m for m in load_json(MARKERS_JSON)["markers"]}
    targets = [t["marker"] for t in load_json(TARGETS_JSON)["targets"]]
    url_by_file = {r["file"]: r["url"] for r in srcs["rows"] if r.get("file") and r["file"] != "-"}
    url_by_marker = {}
    for r in srcs["rows"]:
        url_by_marker.setdefault(r["marker"], r["url"])
    status = {r["marker"]: srcs["school_status"].get(r["school"]) for r in srcs["rows"]}
    results = OrderedDict()
    for marker in targets:
        if only and marker not in only:
            continue
        res = {"marker": marker, "status": status.get(marker), "entries": [], "pairs": [], "dropped": [], "near": [],
               "latest": None, "raw_count": 0, "skipped": None, "special": None}
        if marker in SPECIAL:
            res["special"] = SPECIAL[marker]
        elif marker in EXTRACTORS:
            try:
                raws = EXTRACTORS[marker]({})
            except OcrUnavailable as e:
                res["skipped"] = "OCR 도구를 쓸 수 없어 건너뜀: " + str(e)
                results[marker] = res
                continue
            res["raw_count"] = len(raws)
            e, p, d, n, latest = process_school(marker, raws, markers[marker]["itDepts"])
            res.update({"entries": e, "pairs": p, "dropped": d, "near": n, "latest": latest})
        else:
            res["skipped"] = "받은 원본 없음(상태: %s)" % status.get(marker)
        results[marker] = res
    return results, url_by_file, url_by_marker


def counts(res):
    """(70% 컷 값 있는 행, 70% 컷 없이 other 만 있는 행, 값이 하나도 없는 행)"""
    if res["special"]:
        return 0, 0, 1
    ents = res["entries"]
    has = sum(1 for r in ents if r["cut70"] is not None)
    oth = sum(1 for r in ents if r["cut70"] is None and r["other"])
    return has, oth, len(ents) - has - oth


def to_json(results, url_by_file, url_by_marker):
    out = OrderedDict()
    for marker, res in results.items():
        items = []
        if res["special"]:
            sp = res["special"]
            fname = sp.get("file")
            items.append(OrderedDict([("department", None), ("admission", None), ("year", None), ("cut70", None),
                                      ("note", sp["note"]), ("other", []), ("ocr", False), ("source_file", fname), ("page", sp.get("page")),
                                      ("source_url", url_by_file.get(fname) if fname else url_by_marker.get(marker))]))
        for r in res["entries"]:
            fname = r["file"].split(" > ")[0]
            items.append(OrderedDict([("department", r["dept"]), ("admission", r["admission"]), ("year", r["year"]),
                                      ("cut70", r["cut70"]), ("note", build_notes(r)), ("other", r["other"]), ("ocr", bool(r["ocr"])),
                                      ("source_file", fname), ("page", r["page"]), ("source_url", url_by_file.get(fname))]))
        if items:
            out[marker] = items
    return out


# ---------------------------------------------------------------- 검토 파일
def context_lines(r):
    """값 주변 원문 글자 3줄(위, 그 줄, 아래)."""
    if r.get("ctx"):
        return r["ctx"]
    f = r["file"]
    try:
        if r.get("loc") and (f.endswith(".pdf") or ".zip" in f):
            pno, y, xr = r["loc"]
            if ".zip" in f:
                zname, inner = f.split(" > ")
                doc = fitz.open(stream=zipfile.ZipFile(src_path(zname)).read(inner), filetype="pdf")
            else:
                doc = open_pdf(f)
            ws = [w for w in page_words(doc[pno - 1]) if xr[0] <= w.xc <= xr[1]]
            tl = text_lines(ws)
            k = min(range(len(tl)), key=lambda i: abs(tl[i][0] - y))
            return [" ".join(w.t for w in tl[i][1]) for i in range(max(0, k - 1), min(len(tl), k + 2))]
        if f.endswith(".xlsx") and isinstance(r["page"], str):
            row = int(re.search(r"(\d+)행", r["page"]).group(1))
            wb = openpyxl.load_workbook(src_path(f), data_only=True)
            ws = wb[re.search(r"시트 (.+?) \d+행", r["page"]).group(1)]
            return [" | ".join("" if c.value is None else str(c.value) for c in ws[i][:32] if c.value not in (None, ""))
                    for i in range(max(1, row - 1), min(ws.max_row, row + 1) + 1)]
    except Exception as e:  # 검토 파일 때문에 추출이 멈추지 않게
        return ["(주변 글자 읽기 실패: %s)" % e]
    return []


def md_cell(x):
    return ("" if x is None else str(x)).replace("|", "\\|").replace("\n", " ")


def write_review(results, markers):
    L = []
    L.append("# 학종 IT 입결 추출 검토 (ipgyeol_extract_review.md)")
    L.append("")
    L.append("scripts/extract_ipgyeol.py 가 만들었다. 값은 표의 행 이름(학과)과 열 이름(70% 컷)으로 코드가 찾은 것만 쓴다.")
    L.append("")
    L.append("## 학교별 요약")
    L.append("")
    L.append("| 학교(마커) | 상태 | 70% 컷 값 있는 학과 수 | other 만 있는 학과 수 | 값 없는 학과 수 | 비고 |")
    L.append("|---|---|---|---|---|---|")
    for m, res in results.items():
        ents = res["entries"]
        has, oth, nul = counts(res)
        why = res["skipped"] or (res["special"]["reason"] if res["special"] else "")
        if not why and not ents:
            why = "표에서 맞는 IT 학과 행 없음(이름이 정확히 같은 행 없음)"
        L.append("| %s | %s | %d | %d | %d | %s |" % (md_cell(m), md_cell(res["status"]), has, oth, nul, md_cell(why)))
    L.append("")
    L.append("## 값 목록")
    L.append("")
    L.append("| 학교 | 학과 | 전형명 | 학년도 | 값 | other | note | ocr | 파일명 | 페이지 | 표 제목과 행·열 이름 | 찾은 방법 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for m, res in results.items():
        if res["special"]:
            sp = res["special"]
            L.append("| %s | (학교 전체) | - | - | null | - | %s | false | %s | - | - | 사용자 지시(#1005-49 작업 7) |" % (md_cell(m), md_cell(sp["note"]), md_cell(sp.get("file") or "(받은 파일 없음)")))
        for r in res["entries"]:
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                md_cell(m), md_cell(r["dept"]), md_cell(r["admission"]), r["year"], "null" if r["cut70"] is None else r["cut70"],
                md_cell("; ".join("%s %s" % (o["label"], o["value"]) for o in r["other"]) or "-"), md_cell(build_notes(r)), "true" if r["ocr"] else "false", md_cell(r["file"]), md_cell(r["page"]),
                md_cell(r["table"]), md_cell(r["method"])))
    L.append("")
    L.append("## 맞춘 학과명 쌍(표의 이름 -> markers.json 의 IT 학과명)")
    L.append("")
    for m, res in results.items():
        if res["pairs"]:
            L.append("- **%s**: " % m + "; ".join("%s -> %s" % (a, b) for a, b in res["pairs"]))
    L.append("")
    L.append("## 맞추지 않은 것")
    L.append("")
    L.append("### 근접 후보(괄호·가운뎃점·붙임표를 무시하면 같아지지만 규칙(띄어쓰기와 끝말만 무시)으로는 안 맞아 넣지 않음)")
    L.append("")
    anyn = False
    for m, res in results.items():
        if res["near"]:
            anyn = True
            L.append("- **%s**: " % m + "; ".join("%s ~ %s (%s)" % (k[0], "/".join(k[1]), adm) for k, adm in res["near"][:40]))
    if not anyn:
        L.append("- 없음")
    L.append("")
    L.append("### 애매해서 버린 행")
    L.append("")
    anyd = False
    for m, res in results.items():
        for why, rows in res["dropped"]:
            anyd = True
            L.append("- **%s**: %s: " % (m, why) + "; ".join("%s(%s) %s" % (r["dept"], r["admission"], r["cut70"]) for r in rows))
    if not anyd:
        L.append("- 없음")
    L.append("")
    L.append("## 학교마다 값 하나와 주변 원문 글자 3줄")
    L.append("")
    for m, res in results.items():
        ents = res["entries"]
        if res["special"]:
            L.append("### %s" % m)
            L.append("")
            L.append("- 사용자 지시로 note 만 넣음: %s (%s)" % (res["special"]["note"], res["special"]["reason"]))
            L.append("")
            continue
        if not ents:
            continue
        pick = next((r for r in ents if r["cut70"] is not None), ents[0])
        L.append("### %s" % m)
        L.append("")
        L.append("- 고른 값: %s / %s / %s학년도 / cut70=%s%s" % (pick["dept"], pick["admission"], pick["year"],
                 "null" if pick["cut70"] is None else pick["cut70"], (" / " + build_notes(pick)) if pick["cut70"] is None else ""))
        L.append("- 파일 %s, 위치 %s" % (pick["file"], pick["page"]))
        L.append("")
        L.append("```")
        for ln in context_lines(pick):
            L.append(ln)
        L.append("```")
        L.append("")
    with io.open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main():
    write = "--write" in sys.argv
    results, url_by_file, url_by_marker = collect()
    markers = {m["campus"]: m for m in load_json(MARKERS_JSON)["markers"]}
    data = to_json(results, url_by_file, url_by_marker)
    print("%-26s %-12s %6s %6s %6s  %s" % ("마커", "상태", "70%컷", "other만", "값없음", "비고"))
    tot_v = tot_o = tot_n = 0
    for m, res in results.items():
        ents = res["entries"]
        has, oth, nul = counts(res)
        tot_v += has
        tot_o += oth
        tot_n += nul
        why = res["skipped"] or (res["special"]["reason"] if res["special"] else "")
        if not why and not ents:
            why = "표에서 맞는 IT 학과 행 없음"
        print("%-26s %-12s %6d %6d %6d  %s" % (m, res["status"], has, oth, nul, why))
    print("합계: 70%% 컷 %d, other만 %d, 값 없음 %d" % (tot_v, tot_o, tot_n))
    if write:
        with io.open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.write("\n")
        write_review(results, markers)
        print("쓴 파일:", OUT_JSON, OUT_MD)
    else:
        print("(--write 없음: 파일을 쓰지 않음)")


if __name__ == "__main__":
    main()
