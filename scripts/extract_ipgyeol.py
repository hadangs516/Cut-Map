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
  - 글자가 없는 이미지 PDF는 tesseract 한국어 OCR 로 읽고 OCR 로 읽은 값에는 ocr=true (성균관은 읽은 숫자 값이 없어 ocr=false).

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
       other=None, note=None, force=False, note_only=False, match=None):
    """other: [{"label": 원문 열 이름, "value": 숫자}] 70% 컷이 아닌 공개 기준 값. note: 학교 쪽 설명(있으면 note 앞에 붙는다).
    force: IT 학과 대응을 거치지 않고 그대로 넣는 항목(학교 전체 값)."""
    return {"dept": dept, "admission": admission, "year": year, "cut70": cut70, "cols": cols or [], "file": file,
            "page": page, "table": table, "method": method, "raw": raw, "ocr": ocr, "no70col": no70col,
            "loc": loc, "ctx": ctx, "other": other or [], "note": note, "force": force, "note_only": note_only, "match": match}


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
    # 표 아래 '산출대상:' 줄(다음 표 제목 전까지)을 note 로 쓴다. 못 찾으면 note 없음
    note = None
    nxt = [w for w in ws if w.y0 > rw[0].y1 and re.match(r"^수능성적", w.t)]
    ylim = min([w.y0 for w in nxt] + [rw[0].y1 + 120])
    tgt = [w for w in find_words(ws, r"^산출대상:$", y0=rw[0].y1, y1=ylim)]
    if tgt:
        note = re.sub(r"^\*\s*", "", line_text(ws, tgt[0].yc, tol=3.5)).strip() or None
    cols = {"c70": h70[0].xc, "o:avg": havg[0].xc}
    rows = read_rows(ws, (rw[0].x0 - 4, rw[0].x1 + 4), cols, rw[0].y0 - 3, rw[0].y1 + 3, tol_cols=14, anchor="c70")
    for r in rows:
        v = r["vals"]
        if not isinstance(v.get("c70"), (int, float)):
            continue
        out.append(mk("전형 전체(학과 구분 없음)", "G-IMPACT인재", 2026, v["c70"], fname, 2,
                      "표 '입학생 평균 내신등급(학생부종합)', 열: 등급(70%Cut)", "좌표(행=전형명, 열=등급(70%Cut))",
                      r["raw"], loc=(2, r["y"], r["xr"]), other=others_from(v, {"o:avg": "등급(평균)"}), force=True, note=note, note_only=True))
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
                              cols=["모집인원", "지원인원", "경쟁률", "충원합격인원", "충원율"], no70col=True, ocr=False, ctx=ctx,
                              note="학종 성적 미공개", note_only=True))
    return out


# ---------------------------------------------------------------- 학교 추가분(#1005-61)
def clean_name(v):
    """엑셀 셀의 모집단위 이름: 줄바꿈과 앞뒤 공백을 정리한다."""
    return re.sub(r"\s*\n\s*", "", str(v)).strip() if v is not None else ""


def xl_num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def xl_page(sheet, row):
    return "시트 %s %d행" % (sheet, row)


@extractor("경북대학교(대구)")
def ex_knu(ctx):
    """시트 '5~9.학생부종합(...)': 입학자 학생부 등급의 평균, 50%, 70%, 85%(머리말 칸이 0.5, 0.7, 0.85 이고 서식은 0%)."""
    fname = "경북대학교_2026_수시입결.xlsx"
    wb = openpyxl.load_workbook(src_path(fname), data_only=True)
    out = []
    for ws in wb.worksheets:
        m = re.match(r"^(\d+)\.(학생부종합.*)$", ws.title)
        if not m:
            continue
        hr = next((r for r in range(1, 12) if ws.cell(r, 2).value == "모집단위"), None)
        if hr is None:
            continue
        gcol = next((c.column for c in ws[hr] if c.value and "입학자 학생부 등급" in str(c.value)), None)
        if gcol is None:
            continue
        cols = {}
        for c in ws[hr + 1]:
            if c.column < gcol:
                continue
            v = c.value
            if v == "평균":
                cols["평균"] = c.column
            elif isinstance(v, (int, float)) and c.number_format == "0%":
                cols["%d%%" % round(v * 100)] = c.column
        if "70%" not in cols:
            continue
        adm = m.group(2)
        for r in range(hr + 2, ws.max_row + 1):
            dept = clean_name(ws.cell(r, 2).value)
            if not dept:
                continue
            c70 = xl_num(ws.cell(r, cols["70%"]).value)
            oth = []
            for k in ("평균", "50%", "85%"):
                if k in cols and xl_num(ws.cell(r, cols[k]).value) is not None:
                    oth.append({"label": "입학자 학생부 등급 " + k, "value": xl_num(ws.cell(r, cols[k]).value)})
            out.append(mk(dept, adm, 2026, c70, fname, xl_page(ws.title, r),
                          "시트 '%s', 열: 입학자 학생부 등급 > 70%%" % ws.title, "엑셀 셀(행=모집단위, 열=머리말 이름)",
                          " | ".join(str(ws.cell(r, i).value) for i in (1, 2, 3, 4)), other=oth,
                          cols=["입학자 학생부 등급 평균, 50%, 85%"], no70col=False))
    return out


@extractor("전남대학교 (본교(제1캠퍼스))")
def ex_jnu(ctx):
    """시트 하나. 광주캠퍼스 행 중 전형구분명이 '학생부종합(...)'인 것. 학생부 > 등급기준(이수단위반영) 의 평균, 50%cut, 70%cut."""
    fname = "전남대학교_2026_수시입결.xlsx"
    ws = openpyxl.load_workbook(src_path(fname), data_only=True).worksheets[0]
    hrow = next(r for r in range(1, 12) if ws.cell(r, 5).value == "모집단위명")
    gcol = next(c.column for c in ws[hrow + 1] if c.value and str(c.value).startswith("등급기준"))
    sub = {}
    for c in ws[hrow + 2]:
        if gcol <= c.column < gcol + 4 and c.value:
            sub[str(c.value).strip()] = c.column
    if "70%cut" not in sub:
        return []
    out = []
    for r in range(hrow + 3, ws.max_row + 1):
        campus, adm, dept = ws.cell(r, 1).value, ws.cell(r, 3).value, clean_name(ws.cell(r, 5).value)
        if not (campus and "광주" in str(campus) and adm and str(adm).startswith("학생부종합") and dept):
            continue
        c70 = xl_num(ws.cell(r, sub["70%cut"]).value)
        oth = [{"label": "학생부 등급기준 " + k, "value": xl_num(ws.cell(r, sub[k]).value)}
               for k in ("평균", "50%cut") if k in sub and xl_num(ws.cell(r, sub[k]).value) is not None]
        out.append(mk(dept, str(adm).strip(), 2026, c70, fname, xl_page(ws.title, r),
                      "시트 '%s', 열: 학생부 > 등급기준(이수단위반영) > 70%%cut" % ws.title, "엑셀 셀(행=모집단위명, 열=머리말 이름)",
                      " | ".join(str(ws.cell(r, i).value) for i in (1, 3, 5)), other=oth,
                      cols=["학생부 등급기준 평균, 50%cut"], no70col=False))
    return out


@extractor("전북대학교(전주)")
def ex_jbnu(ctx):
    """시트 하나(학생부종합 전체). 학생부 등급 > 최종등록자 의 평균, 50% cut, 70% cut. 칸이 '3명 이하' 같은 글자면 그 글자를 note 로 쓴다."""
    fname = "전북대학교_2026_수시입결.xlsx"
    ws = openpyxl.load_workbook(src_path(fname), data_only=True).worksheets[0]
    hrow = next(r for r in range(1, 20) if ws.cell(r, 3).value == "모집단위명")
    g = next(c.column for c in ws[hrow + 1] if c.value and "최종등록자" in str(c.value))
    sub = {}
    for c in ws[hrow + 2]:
        if g <= c.column < g + 5 and c.value:
            sub[str(c.value).strip()] = c.column
    if "70% cut" not in sub:
        return []
    out = []
    for r in range(hrow + 3, ws.max_row + 1):
        adm, dept = ws.cell(r, 1).value, clean_name(ws.cell(r, 3).value)
        if not (adm and dept):
            continue
        raw70 = ws.cell(r, sub["70% cut"]).value
        c70 = xl_num(raw70)
        oth = [{"label": "학생부 등급 최종등록자 " + k, "value": xl_num(ws.cell(r, sub[k]).value)}
               for k in ("평균", "50% cut") if k in sub and xl_num(ws.cell(r, sub[k]).value) is not None]
        note = None
        if c70 is None and isinstance(raw70, str) and raw70.strip():
            note = "70% 컷 칸 원문 표기: " + raw70.strip()
        # 전북대만: 모집단위명이 "계열 이름(학과명)"이면 괄호 안 학과명으로 IT 학과 대응을 본다(표시 이름은 원문 그대로)
        mm = re.match(r"^[^()]+\((.+)\)$", dept)
        out.append(mk(dept, "학생부종합 " + str(adm).strip(), 2026, c70, fname, xl_page(ws.title, r),
                      "시트 '%s', 열: 학생부 등급 > 최종등록자 > 70%% cut" % ws.title, "엑셀 셀(행=모집단위명, 열=머리말 이름)",
                      " | ".join(str(ws.cell(r, i).value) for i in (1, 2, 3)), other=oth,
                      cols=["학생부 등급 최종등록자 평균, 50% cut"], no70col=False, note=note, note_only=bool(note),
                      match=mm.group(1) if mm else None))
    return out


@extractor("제주대학교(제주)")
def ex_jejunu(ctx):
    """시트 '전체성적'. 전형유형 칸이 '학생부종합'이고 모집시기가 '수시'인 블록만 쓴다(블록 = 성적구분 평균/50컷/70컷 세 줄).
    교과성적 열은 '주요교과'와 '전체교과' 둘이다. 지시(#1005-69)로 전체교과 70컷을 cut70(note "전체교과 기준"), 주요교과 70컷을 other 로 쓴다."""
    fname = "제주대학교_2026_수시입결.xlsx"
    ws = openpyxl.load_workbook(src_path(fname), data_only=True, read_only=True)["전체성적"]
    head = list(ws.iter_rows(min_row=1, max_row=30, max_col=24, values_only=True))
    hrow = next(i + 1 for i, v in enumerate(head) if len(v) > 11 and v[11] == "성적구분")
    h = {str(v).strip(): c for c, v in enumerate(head[hrow - 1], 1) if v}
    if not ("주요교과" in h and "전체교과" in h):
        return []
    out = []
    cur = {}
    blk = None
    ncol = max(h.values())
    for r, vals in enumerate(ws.iter_rows(min_row=hrow + 1, max_col=ncol, values_only=True), hrow + 1):
        for key, col in (("college", 1), ("dept", 2), ("term", 3), ("type", 4), ("adm", 5)):
            v = vals[col - 1]
            if v not in (None, ""):
                cur[key] = v
        yv, kind = vals[5], vals[11]
        if yv not in (None, "") and (kind == "평균" or blk is None):
            blk = {"year": yv, "row": r, "vals": {}, "txt": None}
            blk.update({k: cur.get(k) for k in ("dept", "term", "type", "adm")})
            blk["dept"] = clean_name(blk["dept"]) if blk["dept"] else ""
        if blk is None or kind not in ("평균", "50컷", "70컷"):
            continue
        for nm in ("주요교과", "전체교과"):
            blk["vals"][(kind, nm)] = vals[h[nm] - 1]
        # 숫자가 아닌 안내 글자(등록인원 없음 등)는 총점 칸에 적혀 있다
        t = vals[h["총점"] - 1] if "총점" in h else None
        if isinstance(t, str) and not blk["txt"]:
            blk["txt"] = t.strip()
        if kind == "70컷":
            if blk["term"] == "수시" and blk["type"] == "학생부종합" and blk["dept"] and isinstance(blk["year"], int):
                v_all = xl_num(blk["vals"].get(("70컷", "전체교과")))
                v_main = xl_num(blk["vals"].get(("70컷", "주요교과")))
                oth = []
                c70, note = None, None
                if v_all is not None:
                    # 전체교과 70컷을 cut70 으로, 주요교과 70컷은 other 에 남긴다
                    c70, note = v_all, "전체교과 기준"
                    if v_main is not None:
                        oth.append({"label": "교과성적 주요교과 70컷", "value": v_main})
                else:
                    if v_main is not None:
                        oth.append({"label": "교과성적 주요교과 70컷", "value": v_main})
                        note = "전체교과 70컷 칸이 비어 있음"
                    else:
                        # 70컷이 없으면(등록 인원이 적어 일부만 공개) 같은 줄에 공개된 50컷 두 값을 other 에 넣는다
                        for nm in ("주요교과", "전체교과"):
                            v = xl_num(blk["vals"].get(("50컷", nm)))
                            if v is not None:
                                oth.append({"label": "교과성적 %s 50컷" % nm, "value": v})
                        note = blk["txt"] or "70% 컷 칸이 비어 있음"
                out.append(mk(blk["dept"], "학생부종합 " + str(blk["adm"]), int(blk["year"]), c70, fname, xl_page(ws.title, blk["row"]),
                              "시트 '전체성적', 열: 교과성적 > 전체교과 > 성적구분 70컷", "엑셀 셀(블록=평균/50컷/70컷 세 줄)",
                              " | ".join(str(x) for x in (blk["dept"], blk["term"], blk["type"], blk["adm"], blk["year"])),
                              other=oth, no70col=c70 is None, note=note, note_only=True))
            blk = None
    return out


@extractor("영남대학교(경산)")
def ex_yu(ctx):
    """학종 시트 둘(잠재능력우수자, 특성화고교졸업,특성화고졸재직). 교과성적은 1~9등급 분포 칸뿐이고 값이 없다."""
    fname = "영남대학교_2026_수시입결.xlsx"
    wb = openpyxl.load_workbook(src_path(fname), data_only=True)
    out = []
    for ws in wb.worksheets:
        title = str(ws.cell(1, 1).value or "")
        if "[학생부종합]" not in title:
            continue
        hr = next((r for r in range(1, 12) if ws.cell(r, 2).value == "학과(부)"), None)
        if hr is None:
            continue
        for r in range(hr + 2, ws.max_row + 1):
            dept, adm, mj = clean_name(ws.cell(r, 2).value), ws.cell(r, 3).value, ws.cell(r, 4).value
            if not dept or not adm or xl_num(mj) is None:
                continue   # 모집인원이 숫자가 아닌 칸(예: 2027학년도 전공 신설)은 결과 행이 아님
            grades = [ws.cell(r, c).value for c in range(9, 18)]
            if any(xl_num(v) is not None for v in grades):
                continue   # 값이 적힌 경우는 이 추출기가 다루지 않는다(없음을 확인)
            out.append(mk(dept, "학생부종합 " + str(adm).strip(), 2026, None, fname, xl_page(ws.title, r),
                          "시트 '%s', 열: 교과성적 분포(지원자) 1~9등급" % ws.title, "엑셀 셀(행=학과(부))",
                          " | ".join(str(ws.cell(r, i).value) for i in (1, 2, 3, 4)),
                          no70col=True, note="학종 성적 분포만 공개, 셀 값 없음", note_only=True))
    return out


def pdf_text_lines(page):
    ws = page_words(page)
    return ws, text_lines(ws, tol=3.0)


@extractor("경상국립대학교 (본교(제1캠퍼스))")
def ex_gnu(ctx):
    """5~20쪽 '수시모집 입학결과[학생부종합]'. 열: 모집구분, 정원구분, 전형구분, 단과대학, 모집단위, 모집인원, 지원인원, 경쟁률, 최종등록인원, 충원최종예비순위, 학생부등급 평균."""
    fname = "경상국립대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, page in enumerate(doc, 1):
        ws, lines = pdf_text_lines(page)
        if not any("[학생부종합]" in w.t for w in ws if w.y0 < 60):
            continue
        hav = [w for w in find_words(ws, r"^평균$", y0=90, y1=110)]
        if not hav:
            continue
        xavg = hav[0].xc
        for cy, l in lines:
            if not l or l[0].t != "학생부종합" or len(l) < 6:
                continue
            adm = " ".join(w.t for w in l[:3])
            dept_ws = [w for w in l if 380 <= w.xc <= 515 and not NUM_RE.match(w.t)]
            dept = " ".join(w.t for w in dept_ws)
            if not dept:
                continue
            avg = next((to_num(w.t) for w in l if abs(w.xc - xavg) <= 12 and to_num(w.t) is not None), None)
            oth = [{"label": "학생부등급 평균", "value": avg}] if avg is not None else []
            out.append(mk(dept, adm, 2026, None, fname, pno, "표 '수시모집 입학결과[학생부종합]', 열: 학생부등급 > 평균(70% 열 없음)",
                          "좌표(행=모집단위, 열=학생부등급 평균)", " ".join(w.t for w in l), loc=(pno, cy, (40, 800)),
                          other=oth, cols=["학생부등급 평균"], no70col=True))
    return out


@extractor("충남대학교(대전)")
def ex_cnu(ctx):
    """13~25쪽 '학생부종합전형[...]'. 열: 최종등록자_학생부 등급의 Avg, 70%, Low, Std. 학과 이름은 오른쪽의 두 번째 모집단위 칸에서 읽는다."""
    fname = "충남대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    cur_type = None
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        tt = [w for w in ws if 120 <= w.yc <= 140 and w.t.startswith("학생부종합전형[")]
        if not tt:
            continue
        adm = tt[0].t
        h70 = find_words(ws, r"^70%$", y0=175, y1=200)
        if not h70:
            continue
        x70 = h70[0].xc
        avgs = [w for w in find_words(ws, r"^Avg$", y0=175, y1=200) if w.xc < x70 - 3]
        lows = [w for w in find_words(ws, r"^Low$", y0=175, y1=200) if w.xc > x70 + 3]
        if not avgs:
            continue
        xavg = max(avgs, key=lambda w: w.xc).xc
        xlow = min(lows, key=lambda w: w.xc).xc if lows else None
        cps = [w for w in ws if re.match(r"^\d+(?:\.\d+)?:1$", w.t) and w.yc > 190]
        # 종합Ⅱ·Ⅲ 쪽에는 맨 왼쪽 '전형' 칸이 있다(전형이 바뀌는 줄에만 글자가 있어 아래 줄로 이어 쓴다)
        has_type = bool(find_words(ws, r"^전형$", x1=45, y0=178, y1=196))
        types = sorted([w for w in ws if w.x1 <= 37 and w.yc > 195], key=lambda w: w.yc) if has_type else []
        if not has_type:
            cur_type = None
        for cp in sorted(cps, key=lambda w: w.yc):
            y = cp.yc
            cand = [w for w in types if w.yc <= y + 4]
            if cand:
                cur_type = cand[-1].t
            adm_row = adm + (" " + cur_type if has_type and cur_type else "")
            row = [w for w in ws if abs(w.yc - y) <= 3.5]
            d2 = "".join(w.t for w in sorted(row, key=lambda w: w.x0) if 440 <= w.xc <= 512 and not re.match(r"^[\d.,]+%?$", w.t))
            d1 = "".join(w.t for w in sorted(row, key=lambda w: w.x0) if 66 <= w.x0 <= 138 and not re.match(r"^[\d.,]+%?$", w.t))
            dept = d2 or d1
            if not dept:
                continue

            def val(x):
                return next((to_num(w.t) for w in row if abs(w.xc - x) <= 9 and to_num(w.t) is not None), None)
            c70 = val(x70)
            oth = []
            a = val(xavg)
            if a is not None:
                oth.append({"label": "최종등록자 학생부 등급 Avg", "value": a})
            if xlow is not None and val(xlow) is not None:
                oth.append({"label": "최종등록자 학생부 등급 Low", "value": val(xlow)})
            out.append(mk(dept, adm_row, 2026, c70, fname, pno, "표 '%s', 열: 최종등록자_학생부 등급 > 70%%" % adm,
                          "좌표(행=모집단위, 열=최종등록자 학생부 등급 70%)", " ".join(w.t for w in sorted(row, key=lambda w: w.x0)),
                          loc=(pno, y, (10, 840)), other=oth, cols=["최종등록자 학생부 등급 Avg, Low"], no70col=False))
    return out


@extractor("계명대학교(대구)")
def ex_kmu(ctx):
    """1~2쪽 표. 학생부종합 일반전형·지역전형은 열이 평균, 경쟁률, 후보순위뿐이다(70% 열 없음). 평균만 other 에 넣는다."""
    fname = "계명대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    for pno, page in enumerate(doc, 1):
        ws = page_words(page)
        gh = find_words(ws, r"^학생부종합$", y0=90, y1=105)
        if not gh:
            continue
        hv = sorted(find_words(ws, r"^평균$", y0=130, y1=152), key=lambda w: w.xc)
        # 평균 머리말 넷: 교과 일반, 교과 면접, 종합 일반, 종합 지역(왼쪽부터)
        if len(hv) < 4:
            continue
        cols = {"종합 일반전형": hv[2].xc, "종합 지역전형": hv[3].xc}
        lim = find_words(ws, r"^학생부교과\(지역전형\)$", y0=160)
        y1 = lim[0].y0 - 2 if lim else page.rect.height - 40
        rows = read_rows(ws, (30, 125), cols, 158, y1, tol_cols=9)
        for r in rows:
            if not r["label"]:
                continue
            for nm, key in (("학생부종합 일반전형", "종합 일반전형"), ("학생부종합 지역전형", "종합 지역전형")):
                v = r["vals"].get(key)
                if isinstance(v, (int, float)):
                    out.append(mk(r["label"], nm, 2026, None, fname, pno, "표 '학생부종합 %s', 열: 평균(70%% 열 없음), 최종등록자 기준" % key[3:],
                                  "좌표(행=모집단위, 열=학생부종합 평균)", r["raw"], loc=(pno, r["y"], r["xr"]),
                                  other=[{"label": "최종등록자 평균", "value": v}], cols=["평균"], no70col=True))
    return out


@extractor("서울시립대학교(서울)")
def ex_uos(ctx):
    """1쪽 표 '최종등록자 성적 현황(학생부종합Ⅰ·Ⅱ, 기회균형Ⅰ, 사회공헌·통합전형)'. 세 묶음의 등록인원, 평균등급, 표준편차(70% 열 없음)."""
    fname = "서울시립대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    page = doc[0]
    ws = page_words(page)
    hc = sorted(find_words(ws, r"^등록인원$", y0=100, y1=120), key=lambda w: w.xc)
    ha = sorted(find_words(ws, r"^평균등급$", y0=100, y1=120), key=lambda w: w.xc)
    if len(hc) < 3 or len(ha) < 3:
        return []
    names = ["학생부종합전형I", "학생부종합전형II", "기회균형전형I 및 사회공헌·통합전형"]
    cols = {}
    for i in range(3):
        cols["n%d" % i] = hc[i].xc
        cols["a%d" % i] = ha[i].xc
    rows = read_rows(ws, (55, 205), cols, 118, 540, tol_cols=10, anchor=None)
    out = []
    for r in rows:
        if not r["label"]:
            continue
        for i in range(3):
            n = r["vals"].get("n%d" % i)
            if not isinstance(n, (int, float)):
                continue
            a = r["vals"].get("a%d" % i)
            oth = [{"label": "최종등록자 평균등급", "value": a}] if isinstance(a, (int, float)) else []
            out.append(mk(r["label"], names[i], 2026, None, fname, 1, "표 '최종등록자 성적 현황', 열: %s > 평균등급(70%% 열 없음)" % names[i],
                          "좌표(행=모집단위, 열=평균등급)", r["raw"], loc=(1, r["y"], r["xr"]), other=oth,
                          cols=["평균등급"], no70col=True))
    return out


@extractor("중앙대학교(서울)")
def ex_cau(ctx):
    """2쪽 표. 전형명 CAU융합형인재, CAU탐구형인재. 열: 교과등급 지원자 평균, 합격자 평균, 등록자 50% CUT, 등록자 70% CUT."""
    fname = "중앙대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    page = doc[1]
    ws = page_words(page)
    mj = sorted(find_words(ws, r"^모집$", y0=150, y1=165), key=lambda w: w.xc)[:2]
    h70 = sorted(find_words(ws, r"^70%$", y0=163, y1=176), key=lambda w: w.xc)[:2]
    h50 = sorted(find_words(ws, r"^50%$", y0=163, y1=176), key=lambda w: w.xc)[:2]
    ha = sorted(find_words(ws, r"^평균$", y0=168, y1=177), key=lambda w: w.xc)[:4]
    if not (len(mj) == 2 and len(h70) == 2 and len(h50) == 2 and len(ha) == 4):
        return []
    names = ["CAU융합형인재", "CAU탐구형인재"]
    cols = {}
    for g in range(2):
        cols["n%d" % g] = mj[g].xc
        cols["c70_%d" % g] = h70[g].xc
        cols["c50_%d" % g] = h50[g].xc
        cols["ap_%d" % g] = ha[2 * g].xc
        cols["ah_%d" % g] = ha[2 * g + 1].xc
    yrows = [w for w in ws if w.yc > 180 and (abs(w.xc - cols["n0"]) <= 8 or abs(w.xc - cols["n1"]) <= 8) and to_num(w.t) is not None]
    rowys = sorted({round(w.yc, 0) for w in yrows})
    # 같은 줄로 묶기
    ys = []
    for y in rowys:
        if ys and abs(y - ys[-1]) <= 3.5:
            continue
        ys.append(y)
    name_ws = [w for w in ws if 186 <= w.xc <= 292 and w.yc > 180]
    out = []
    for y in ys:
        label_ws = [w for w in name_ws if min(abs(w.yc - yy) for yy in ys) == abs(w.yc - y) and abs(w.yc - y) <= 9]
        label_ws = sorted(label_ws, key=lambda w: (round(w.yc / 4.0), w.x0))
        dept = "".join(w.t for w in label_ws)
        if not dept:
            continue
        row = [w for w in ws if abs(w.yc - y) <= 3.5]

        def val(x):
            return next((to_num(w.t) for w in row if abs(w.xc - x) <= 9 and to_num(w.t) is not None), None)
        for g in range(2):
            if val(cols["n%d" % g]) is None:
                continue
            oth = []
            for key, lab in (("ap_%d" % g, "교과등급 지원자 평균"), ("ah_%d" % g, "교과등급 합격자 평균"), ("c50_%d" % g, "교과등급 등록자 50% CUT")):
                v = val(cols[key])
                if v is not None:
                    oth.append({"label": lab, "value": v})
            out.append(mk(dept, names[g], 2026, val(cols["c70_%d" % g]), fname, 2, "표 '중앙대학교 2026학년도 수시모집 입시결과', 열: %s > 교과등급 > 등록자 70%% CUT" % names[g],
                          "좌표(행=모집단위, 열=교과등급 등록자 70% CUT)", " ".join(w.t for w in sorted(row, key=lambda w: w.x0) if w.x0 < 830),
                          loc=(2, y, (186, 830)), other=oth, cols=["교과등급 지원자 평균, 합격자 평균, 등록자 50% CUT"], no70col=False))
    return out


@extractor("서울과학기술대학교(서울)")
def ex_seoultech(ctx):
    """수시 학종 입시 결과(등급) 표만: 12쪽 '학생부종합(학교생활우수자전형, 창의융합인재전형)'(입학생 평균, 70% cut)과
    13쪽 '학생부종합(국가보훈, 기회균등, 농어촌)'(입학생 평균). 5~9쪽의 경쟁률 표에는 성적 열이 없다."""
    fname = "서울과학기술대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    # 12쪽
    page = doc[11]
    ws = page_words(page)
    t = find_words(ws, r"^입시$", y0=118, y1=135)
    h70 = find_words(ws, r"^70%$", y0=160, y1=175)
    hcut = find_words(ws, r"^cut$", y0=160, y1=175)
    hn = find_words(ws, r"^모집인원$", y0=150, y1=165)
    hav = sorted(find_words(ws, r"^평균$", y0=160, y1=175), key=lambda w: w.xc)
    if t and h70 and hcut and hn and len(hav) >= 3:
        x70 = (h70[0].x0 + hcut[0].x1) / 2.0
        xavg = hav[-1].xc   # 입학생 평균(70% cut 바로 왼쪽)
        adm = "학생부종합(학교생활우수자전형, 창의융합인재전형)"
        rows = read_rows(ws, (30, 225), {"n": hn[0].xc, "avg": xavg, "c70": x70}, 180, 760, tol_cols=9, anchor="n")
        for r in rows:
            if not r["label"] or r["label"].startswith("학생부종합전형"):
                continue
            oth = [{"label": "입학생 평균", "value": r["vals"]["avg"]}] if isinstance(r["vals"].get("avg"), (int, float)) else []
            out.append(mk(r["label"], adm, 2026, r["vals"].get("c70") if isinstance(r["vals"].get("c70"), (int, float)) else None,
                          fname, 12, "표 '학생부종합(학교생활우수자전형, 창의융합인재전형) 입시 결과(등급)', 열: 입학생 > 70% cut",
                          "좌표(행=모집단위, 열=입학생 70% cut)", r["raw"], loc=(12, r["y"], r["xr"]), other=oth,
                          cols=["입학생 평균"], no70col=False))
    # 13쪽
    page = doc[12]
    ws = page_words(page)
    hn = sorted(find_words(ws, r"^모집인원$", y0=180, y1=200), key=lambda w: w.xc)
    hav = sorted(find_words(ws, r"^평균$", y0=180, y1=200), key=lambda w: w.xc)
    hin = sorted(find_words(ws, r"^입학생$", y0=180, y1=200), key=lambda w: w.xc)
    if len(hn) == 3 and len(hav) == 3 and len(hin) == 3:
        names = ["국가보훈대상자", "기회균등전형", "농어촌학생전형"]
        cols = {}
        for i in range(3):
            cols["n%d" % i] = hn[i].xc
            cols["a%d" % i] = (hin[i].x0 + hav[i].x1) / 2.0
        rows = read_rows(ws, (30, 225), cols, 195, 770, tol_cols=9, anchor=None)
        for r in rows:
            if not r["label"] or r["label"].startswith("학생부종합전형"):
                continue
            for i in range(3):
                n = r["vals"].get("n%d" % i)
                if not isinstance(n, (int, float)):
                    continue
                a = r["vals"].get("a%d" % i)
                oth = [{"label": "입학생 평균", "value": a}] if isinstance(a, (int, float)) else []
                out.append(mk(r["label"], "학생부종합(국가보훈, 기회균등, 농어촌) " + names[i], 2026, None, fname, 13,
                              "표 '학생부종합(국가보훈, 기회균등, 농어촌) 입시 결과(등급)', 열: %s > 입학생 평균(70%% 열 없음)" % names[i],
                              "좌표(행=모집단위, 열=입학생 평균)", r["raw"], loc=(13, r["y"], r["xr"]), other=oth,
                              cols=["입학생 평균"], no70col=True))
    return out


@extractor("가톨릭대학교 (본교(제1캠퍼스))")
def ex_cuk(ctx):
    """학생부종합 전형 구간(제목줄 'NN 학생부종합(...)') 안의 '학생부(교과) 성적 통계' 표. 묶음은 지원자, (1단계 합격자), 합격자, 최종등록자이고
    각 묶음에 최고, 평균, 최저가 있다. 70% 열은 없고 최종등록자의 평균과 최저를 other 에 넣는다. 행은 IT 학과 이름으로만 고른다(대학 전체 자료집)."""
    fname = "가톨릭대학교_2026_수시입결.pdf"
    doc = open_pdf(fname)
    out = []
    section = None
    for pno, page in enumerate(doc, 1):
        if pno < 14 or pno > 38:
            continue
        ws = page_words(page)
        lines = text_lines(ws, tol=3.0)
        # 줄 순서대로 구간(학생부종합/교과)과 표 제목을 따라간다
        tables = []   # (y, 전형 이름) 성적 통계 표 제목
        ends = []     # 표 끝으로 볼 제목줄 y
        for cy, l in lines:
            txt = " ".join(w.t for w in l)
            m = re.match(r"^\d\d\s+(학생부종합|학생부교과)\(", txt)
            if m:
                section = m.group(1)
            m = re.match(r"^[가-하]\.\s*(?:2026학년도\s+)?(.+?)\s*학생부\(교과\)\s*성적\s*통계", txt)
            if m and section == "학생부종합":
                tables.append((cy, m.group(1).strip()))
            elif re.match(r"^[가-하]\.\s", txt) or re.match(r"^\d\d\s+학생부", txt):
                ends.append(cy)
        for cy, name in tables:
            y_end = min([e for e in ends if e > cy + 5] + [page.rect.height - 40])
            hm = [w for w in ws if cy < w.yc < y_end and w.t == "최고"]
            if not hm:
                continue
            hy = hm[0].yc
            hline = sorted([w for w in ws if abs(w.yc - hy) <= 3 and w.t in ("최고", "평균", "최저")], key=lambda w: w.x0)
            if len(hline) < 6:
                continue
            last3 = hline[-3:]
            xavg, xlow = last3[1].xc, last3[2].xc
            rows = read_rows(ws, (30, 175), {"avg": xavg, "low": xlow}, hy + 8, y_end - 2, tol_cols=9, anchor="avg")
            for r in rows:
                if not r["label"]:
                    continue
                oth = []
                for k, lab in (("avg", "최종등록자 학생부(교과) 평균"), ("low", "최종등록자 학생부(교과) 최저")):
                    if isinstance(r["vals"].get(k), (int, float)):
                        oth.append({"label": lab, "value": r["vals"][k]})
                out.append(mk(r["label"], "학생부종합 " + name, 2026, None, fname, pno,
                              "표 '%s 학생부(교과) 성적 통계', 열: 최종등록자 > 평균, 최저(70%% 열 없음)" % name, "좌표(행=모집단위, 열=최종등록자 평균)",
                              r["raw"], loc=(pno, r["y"], r["xr"]), other=oth, cols=["최종등록자 학생부(교과) 평균, 최저"], no70col=True))
    return out


@extractor("국민대학교(서울)")
def ex_kookmin(ctx):
    """저장한 조회 화면 html 의 표(id=table): 유형, 전형, 계열, 학과, 2027 모집인원, 2026학년도 모집인원, 경쟁률, 평균등급, 예비순위.
    유형이 '학생부종합'인 행만. 70% 열은 없고 평균등급(최종등록자 기준)을 other 에 넣는다."""
    fname = "국민대학교_2026_수시입결.html"
    with io.open(src_path(fname), encoding="utf-8", errors="replace") as f:
        h = f.read()
    i = h.find('<table id="table" class="tbl_type02 _ipsiUnitList')
    j = h.find("</table>", i) if i >= 0 else -1
    if i < 0 or j < 0:
        return []
    body = h[i:j]
    heads = re.findall(r"<th[^>]*>(.*?)</th>", body[:body.find("<tbody>")], flags=re.S)
    htxt = [re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", x)) for x in heads]
    if not ("평균등급" in htxt and any("2026학년도" in x for x in htxt)):
        return []
    out = []
    for n, tr in enumerate(re.findall(r"<tr class=.*?</tr>", body[body.find("<tbody>"):], flags=re.S), 1):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).replace("&nbsp;", " ").strip()
                 for c in re.findall(r"<td.*?</td>", tr, flags=re.S)]
        if len(cells) < 9 or cells[0] != "학생부종합":
            continue
        # cells: 유형, 전형, 계열, 학과, 2027 모집, 2026 모집, 경쟁률, 평균등급, 예비순위
        avg = to_num(cells[7])
        oth = [{"label": "평균등급", "value": avg}] if avg is not None else []
        out.append(mk(cells[3], "학생부종합 " + cells[1], 2026, None, fname, "표 %d번째 행" % n,
                      "표 '전형/학과안내'(2026학년도), 열: 평균등급(70% 열 없음), 최종등록자 기준", "html 표 칸(행=학과, 열=머리말 이름)",
                      " | ".join(cells[:9]), other=oth, cols=["평균등급"], no70col=True,
                      ctx=[" | ".join(cells[:9])]))
    return out


# ---------------------------------------------------------------- 학교 한 곳 처리, 결과 모으기
# 사용자 지시로 값 대신 note 만 넣는 마커
SPECIAL = OrderedDict([
    ("서울대학교(서울)", {"note": "입결 미공개", "file": None, "reason": "받은 파일 없음(학종 자료 없음)"}),
    ("고려대학교(서울)", {"note": "입결 미공개로 보임", "file": None, "reason": "받은 파일 없음(입결 미공개로 보임, 통합 공지 1~3쪽 확인: 사용자 2026-10-05)"}),
    ("포항공과대학교 (본교(제1캠퍼스))", {"note": "입결 미공개로 보임", "file": None, "reason": "받은 파일 없음(입결 미공개로 보임)"}),
])


def punct_key(name):
    """가운뎃점, 밑줄, 쉼표, 빗금까지 모두 뺀 비교용 키(근접 후보 보고에만 쓴다)."""
    return norm_dept(re.sub(r"[·_/,]", "", name or ""))


def mname(r):
    """IT 학과 대응에 쓰는 이름. 추출기가 match 를 정해 두면(전북대: 계열 이름(학과명)의 괄호 안 학과명) 그것을 쓴다."""
    return r.get("match") or r["dept"]


def process_school(marker, raws, it_names):
    """raw 행 -> (맞춘 항목, 짝 목록, 버린 항목, 근접 후보, 학년도)."""
    exact_set = {exact_key(n) for n in it_names}
    itmap = defaultdict(list)
    for n in it_names:
        itmap[norm_dept(n)].append(n)
    forced = [r for r in raws if r.get("force")]
    cand = [r for r in raws if not r.get("force") and norm_dept(mname(r)) in itmap]
    # 가장 최근 학년도만
    years = [r["year"] for r in cand if r["year"] is not None]
    latest = max(years) if years else None
    cand = [r for r in cand if r["year"] == latest]
    matched, dropped = [], []
    # 한 표(전형, 학년도) 안에서 끝말을 뗀 이름이 같은 행이 둘 이상이면: 이름 전체가 IT 학과명과 같은 행만 맞춘다
    by_key = defaultdict(list)
    for r in cand:
        by_key[(r["admission"], r["year"], norm_dept(mname(r)))].append(r)
    for key, g in by_key.items():
        names = {exact_key(mname(r)) for r in g}
        if len(names) > 1:
            keep = [r for r in g if exact_key(mname(r)) in exact_set]
            drop = [r for r in g if r not in keep]
            matched += keep
            if drop:
                dropped.append(("같은 전형 안에 끝말만 다른 이름이 여러 개이고 이름 전체가 일치하지 않음", drop))
        else:
            matched += g
    # 같은 (이름, 전형, 학년도)가 여러 번: 값이 모두 같으면 하나, 다르면 버린다
    final, seen = [], OrderedDict()
    for r in matched:
        seen.setdefault((exact_key(mname(r)), r["admission"], r["year"]), []).append(r)
    for k, g in seen.items():
        if len({x["cut70"] for x in g}) > 1:
            dropped.append(("같은 이름·전형·학년도에 값이 서로 다른 행이 둘 이상", g))
        else:
            final.append(g[0])
    pairs = []
    for r in final:
        e = exact_key(mname(r))
        same = [n for n in it_names if exact_key(n) == e] or itmap[norm_dept(mname(r))]
        pairs.append((r["dept"], same[0] if len(set(same)) == 1 else " / ".join(sorted(set(same)))))
    # 근접 후보: 가운뎃점·밑줄 등까지 무시하면 같아지지만 규칙으로는 안 맞은 이름
    pk = defaultdict(list)
    for n in it_names:
        pk[punct_key(n)].append(n)
    near = OrderedDict()
    for r in raws:
        if r.get("force") or r["year"] != latest or norm_dept(mname(r)) in itmap:
            continue
        k = punct_key(mname(r))
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
        pick = next((r for r in ents if r["cut70"] is not None), None) or next((r for r in ents if r["other"]), ents[0])
        L.append("### %s" % m)
        L.append("")
        L.append("- 고른 값: %s / %s / %s학년도 / cut70=%s%s" % (pick["dept"], pick["admission"], pick["year"],
                 "null" if pick["cut70"] is None else pick["cut70"], (" / " + build_notes(pick)) if pick["cut70"] is None else ""))
        if pick["other"]:
            L.append("- other: " + "; ".join("%s %s" % (o["label"], o["value"]) for o in pick["other"]))
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
