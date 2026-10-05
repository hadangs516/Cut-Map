# -*- coding: utf-8 -*-
"""#1005-30 작업 103~106: 2028학년도 대입전형 시행계획 PDF에서 IT 계열 모집단위의 요구사항을 정리해 시험 결과 파일을 만든다.

입력: sources/2028_plan/ 의 PDF(원본 파일은 커밋하지 않는다), 시스템의 pdftotext(-table 모드)
출력: data/requirements_2028_test.json, requirements_2028_review.md
화면 코드는 건드리지 않는다.

방식(SPEC 16번): 값은 AI가 원문을 읽고 정리한 것이다(확인상태 "AI 정리, 사용자 미검토").
 - 근거 문장은 사람이 옮기지 않고 스크립트가 PDF 텍스트 쪽에서 정규식으로 찾아 그 줄을 그대로(공백 연속만 한 칸으로 정리) 가져온다.
   찾지 못하면 실행이 멈춘다. 표 안의 값은 근거 문장 자리에 표 제목과 행·열 이름을 적고, 스크립트가 표 제목과 행 이름이 그 쪽에 있는지, 행의 칸 값이 적어 둔 값과 같은지 검사한다.
 - 비율 합계, 환산 점수 같은 계산은 하지 않는다.
 - 쪽 번호는 PDF 파일의 쪽 순서(1쪽부터)다. 학교마다 쪽 아래에 인쇄된 번호가 다를 수 있다.
사용: python scripts/build_requirements_2028_test.py
"""
import io
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "sources", "2028_plan")
OUT_JSON = os.path.join(ROOT, "data", "requirements_2028_test.json")
OUT_MD = os.path.join(ROOT, "requirements_2028_review.md")
STATE = "AI 정리, 사용자 미검토"
UNCONFIRMED = "미확인"
UNIT_UNCONFIRMED = "모집단위 미확인"


def sp(s):
    return re.sub(r"\s+", " ", s).strip()


def nn(s):
    return re.sub(r"\s+", "", s)


class Doc(object):
    def __init__(self, fname):
        self.fname = fname
        path = os.path.join(SRC, fname)
        raw = subprocess.check_output(["pdftotext", "-enc", "UTF-8", "-table", path, "-"])
        self.pages = raw.decode("utf-8").split("\f")[:-1]
        self.n = len(self.pages)

    def lines(self, p):
        return [sp(l) for l in self.pages[p - 1].split("\n") if l.strip()]

    def line(self, p, rx, nth=0):
        hits = [l for l in self.lines(p) if re.search(rx, l)]
        if len(hits) <= nth:
            raise AssertionError("근거 줄을 찾지 못함: %s p%d /%s/" % (self.fname, p, rx))
        return hits[nth]

    def has(self, p, text):
        return nn(text) in nn(self.pages[p - 1])

    def row_candidates(self, p, row_label):
        """행 이름(공백 무시)이 들어 있는 줄마다 그 이름 뒤의 칸 값 목록을 돌려준다."""
        out = []
        last = row_label.split()[-1]
        for l in self.pages[p - 1].splitlines():
            if nn(row_label) in nn(l):
                pos = l.rfind(last)
                out.append(l[pos + len(last):].split() if pos >= 0 else l.split())
        if not out:
            raise AssertionError("행을 찾지 못함: %s p%d %s" % (self.fname, p, row_label))
        return out

    def check_row(self, p, row_label, expect):
        """행 이름 뒤의 칸 값 목록 안에 expect 값이 같은 순서로 들어 있는 줄이 하나라도 있어야 한다."""
        cands = self.row_candidates(p, row_label)
        for toks in cands:
            i = 0
            for e in expect:
                while i < len(toks) and toks[i] != e:
                    i += 1
                if i >= len(toks):
                    break
                i += 1
            else:
                return
        raise AssertionError("행 칸 값이 다름: %s p%d %s 기대 %s 실제 %s" % (self.fname, p, row_label, expect, cands))

    def second_last_pos(self, p, row_label, token):
        """행 끝에서 둘째 칸(정시 군 칸) 값이 token 인 줄에서 그 칸의 글자 위치를 돌려준다."""
        last = row_label.split()[-1]
        for l in self.pages[p - 1].splitlines():
            if nn(row_label) in nn(l):
                k = l.rfind(last)
                toks = [(k + len(last) + m.start(), m.group()) for m in re.finditer(r"\S+", l[k + len(last):])]
                if len(toks) >= 2 and toks[-2][1] == token:
                    return toks[-2][0]
        raise AssertionError("정시 칸 위치를 찾지 못함: %s p%d %s %s" % (self.fname, p, row_label, token))

    def donga_group_positions(self, p):
        """동아대 표 머리글에서 정시 열(수능 가군 일반, 가군 지역인재, 나군 일반, 다군 일반, 실기 가군, 실기 나군)의 글자 위치"""
        for l in self.pages[p - 1].splitlines():
            ps = [i for i, c in enumerate(l) if c == "군" and i > 90]
            if len(ps) == 6:
                return dict(zip(["가", "가지역", "나", "다", "실기가", "실기나"], ps))
        raise AssertionError("동아대 정시 열 머리글을 찾지 못함 p%d" % p)

    def hanyang_group_positions(self, p):
        """한양대 표 머리글에서 정시 수능(가군), (나군), (다군) 열의 글자 위치"""
        res = {}
        for l in self.pages[p - 1].splitlines()[:24]:
            for m in re.finditer(r"\(([가나다])군\)", l):
                res.setdefault(m.group(1), m.start())
        assert sorted(res) == ["가", "나", "다"], res
        return res


class Sheet(object):
    """학교 하나의 결과를 모으는 곳"""

    def __init__(self, school, doc, page_note):
        self.school = school
        self.doc = doc
        self.page_note = page_note
        self.units = []
        self.cur = None

    def unit(self, marker_dept, plan_unit, college=None):
        self.cur = OrderedDict([("markerDept", marker_dept), ("planUnit", plan_unit), ("college", college), ("items", [])])
        self.units.append(self.cur)
        return self.cur

    def add(self, kind, item, value, page, evidence):
        self.cur["items"].append(OrderedDict([
            ("구분", kind), ("항목", item), ("값", value), ("파일명", self.doc.fname), ("페이지", page),
            ("근거", evidence), ("확인상태", STATE), ("사용자판정", "")]))

    def quote(self, p, rx, nth=0):
        return self.doc.line(p, rx, nth)

    def table(self, p, title_rx, row, col, expect=None, title_page=None):
        t = self.doc.line(title_page or p, title_rx)
        assert self.doc.has(p, row), (self.doc.fname, p, row)
        if expect:
            self.doc.check_row(p, row, expect)
        return "[표] %s / 행: %s / 열: %s" % (t, row, col)

    def missing(self, marker_dept, searched):
        u = self.unit(marker_dept, None)
        self.add("공통", "모집단위", UNIT_UNCONFIRMED, "전체 1~%d" % self.doc.n, "시행계획 PDF 전체 쪽 텍스트에서 '%s'를 찾았으나 모집단위로 나오지 않음(그 학과가 속한 단과대학·계열 단위로도 나오지 않음)" % searched)


def find_pages(doc, text):
    return [p for p in range(1, doc.n + 1) if nn(text) in nn(doc.pages[p - 1])]


# ------------------------------------------------------------------ 고려대
def korea():
    d = Doc("고려대학교_2028시행계획.pdf")
    s = Sheet("고려대학교(서울)", d, "쪽 번호는 PDF 쪽 순서이며 쪽 아래 인쇄 번호는 PDF 쪽 번호보다 1 작다.")
    # 수시 전형 정의: (키, 전형 이름, 최저 쪽, 최저 근거 정규식, 최저 값, 면접 쪽, 면접 근거 정규식, 면접 값)
    SUSI = OrderedDict([
        ("학교추천", ("학생부교과(학교추천전형)", 12, r"^인문·자연계열\(의학과 제외\) 적용하지 않음", "없음", 11, r"^학생부\(교과\) 80% \+ 서류 20%", "없음(전형요소에 면접이 없음)")),
        ("학업우수", ("학생부종합(학업우수전형)", 13, r"^인문·자연계열\(의학과 제외\) 국어, 수학, 영어, 탐구\* 4개 영역 등급의 합이 9 이내", "있음", 13, r"^2단계 1단계 성적 80% \+ 면접 20%", "있음")),
        ("계열적합", ("학생부종합(계열적합전형)", 14, r"^라\. 수능 최저학력기준: 적용하지 않음", "없음", 14, r"^서류 100%", "없음(전형요소가 서류 100% 일괄합산)")),
        ("고른기회", ("학생부종합(고른기회전형)", 16, r"^라\. 수능 최저학력기준 : 적용하지 않음", "없음", 16, r"^2단계 1단계 성적 80% \+ 면접 20%", "있음")),
        ("다문화", ("학생부종합(다문화전형)", 17, r"^라\. 수능 최저학력기준 : 적용하지 않음", "없음", 17, r"^2단계 1단계 성적 80% \+ 면접 20%", "있음")),
        ("재직자", ("학생부종합(재직자전형)", 18, r"^라\. 수능 최저학력기준 : 적용하지 않음", "없음", 18, r"^2단계 1단계 성적 80% \+ 면접 20%", "있음")),
        ("논술", ("논술(논술전형)", 20, r"^인문·자연계열 국어, 수학, 영어, 탐구\* 4개 영역 등급의 합이 8 이내", "있음", 20, r"^논술 100%", "없음(전형요소가 논술 100%)")),
    ])
    COLS = ["학교추천", "학업우수", "계열적합", "고른기회", "다문화", "재직자", "사이버", "논술", "특기자"]
    # 마커 학과명, 원문 모집단위, 단과대학, 수시 표 쪽, 정시 표 쪽, 수시 행 값, 정시 일반, 정시 교과우수
    UNITS = [
        ("데이터과학과", "데이터과학과", "정보대학", 6, 8, ["40", "7", "8", "5", "2", "-", "◉", "-", "4", "-"], ["40", "10", "4"]),
        ("스마트모빌리티학부", "스마트모빌리티학부", "스마트모빌리티학부", 6, 8, ["50", "-", "10", "20", "-", "-", "-", "-", "-", "-"], ["50", "20", "-"]),
        ("스마트보안학부", "스마트보안학부", "스마트보안학부", 6, 8, ["50", "8", "10", "6", "3", "-", "◉", "-", "5", "-"], ["50", "12", "6"]),
        ("인공지능학과", "인공지능학과", "정보대학", 6, 8, ["102", "17", "20", "13", "5", "-", "◉", "-", "9", "-"], ["102", "25", "13"]),
        ("전기전자공학부", "전기전자공학부", "공과대학", 5, 7, ["205", "35", "40", "27", "11", "3", "◉", "-", "20", "-"], ["205", "51", "21"]),
        ("컴퓨터학과", "컴퓨터학과", "정보대학", 6, 8, ["120", "20", "23", "16", "6", "2", "◉", "-", "11", "-"], ["120", "30", "13"]),
    ]
    for mdept, plan, college, pt, pj, su, js in UNITS:
        s.unit(mdept, plan, college)
        s.add("공통", "모집단위", plan, pt, s.table(pt, r"^2-1\. 수시모집 모집인원", plan, "모집단위", su, title_page=5))
        # ---- 정시(수능 일반전형, 수능 교과우수전형)
        for jname, jkey, jdx, base_p in (("수능(일반전형)", "일반", 1, 24), ("수능(교과우수전형)", "교과우수", 2, 26)):
            if js[jdx] == "-":
                s.add("정시", "[%s] 모집 여부" % jname, "없음(정시 모집인원 표에 '-')", pj, s.table(pj, r"^2-2\. 정시모집 모집인원", plan, "수능 " + jkey + "전형", [js[0], js[1], js[2]], title_page=7))
                continue
            tb = s.table(pj, r"^2-2\. 정시모집 모집인원", plan, "수능 %s전형(모집인원 %s명)" % (jkey, js[jdx]), js, title_page=7)
            s.add("정시", "[%s] 모집군" % jname, "가군", base_p, s.quote(base_p, r"^나\. 모집군 : 가군"))
            if jkey == "일반":
                s.add("정시", "[%s] 수능 영역별 반영 비율" % jname, "국어 200, 수학 240, 탐구 200(원문 표의 반영 점수, 비율로 바꾸지 않음)", 25,
                      "[표] 바. 수능 반영 방법 / 행: 자연 전체 모집단위(가정교육과, 간호학과 제외) / 열: 국어, 수학, 탐구")
                s.add("정시", "[%s] 영어 반영 방식" % jname, "등급별 감점(1등급 0, 2등급 1, 3등급 3, 4등급 6, 5등급 12, 6등급 15, 7등급 18, 8등급 21, 9등급 24)", 25,
                      "[표] %s / 행: 감점 점수 / 열: 등급 1~9 → %s" % (s.quote(25, r"^2\) 영어 등급별 감점 점수"), s.quote(25, r"^감점 점수 0 1 3 6 12 15 18 21 24")))
                s.add("정시", "[%s] 한국사 반영 방식" % jname, "등급별 감점(1~4등급 0, 5등급 0.2, 6등급 0.4, 7등급 0.6, 8등급 0.8, 9등급 2.0)", 25,
                      "[표] %s / 행: 감점 점수 / 열: 등급 1~9 → %s" % (s.quote(25, r"^3\) 한국사 등급별 감점 점수"), s.quote(25, r"^감점 점수 0 0 0 0 0\.2 0\.4 0\.6 0\.8 2\.0")))
                s.add("정시", "[%s] 탐구 반영 방식" % jname, "표준점수 반영(탐구 반영 점수 200). 지정 응시영역은 사회·과학탐구이며 반영 과목 수는 해당 쪽에서 미확인", 25,
                      s.quote(25, r"^1\) 국어, 수학, 탐구영역은 표준점수를 반영함"))
                s.add("정시", "[%s] 학생부 반영 여부" % jname, "없음(전형요소별 반영비율이 수능 100%)", 24,
                      s.quote(24, r"^인문⸱자연계열 일괄합산 100% - - - 100%"))
                s.add("정시", "[%s] 면접 반영 여부" % jname, "없음(위 표의 면접 칸이 '-')", 24,
                      s.quote(24, r"^인문⸱자연계열 일괄합산 100% - - - 100%"))
            else:
                s.add("정시", "[%s] 수능 영역별 반영 비율" % jname, "국어 200, 수학 240, 탐구 200(원문 표의 반영 점수, 비율로 바꾸지 않음)", 27,
                      "[표] 바. 수능 반영 방법 / 행: 자연 전체 모집단위(가정교육과, 간호학과 제외) / 열: 국어, 수학, 탐구")
                s.add("정시", "[%s] 영어 반영 방식" % jname, "등급별 감점(1등급 0, 2등급 1, 3등급 3, 4등급 6, 5등급 12, 6등급 15, 7등급 18, 8등급 21, 9등급 24)", 27,
                      "[표] %s / 행: 감점 점수 / 열: 등급 1~9 → %s" % (s.quote(27, r"^2\) 영어 등급별 감점 점수"), s.quote(27, r"^감점 점수 0 1 3 6 12 15 18 21 24")))
                s.add("정시", "[%s] 한국사 반영 방식" % jname, "등급별 감점(1~4등급 0, 5등급 0.2, 6등급 0.4, 7등급 0.6, 8등급 0.8, 9등급 2.0)", 27,
                      "[표] %s / 행: 감점 점수 / 열: 등급 1~9 → %s" % (s.quote(27, r"^3\) 한국사 등급별 감점 점수"), s.quote(27, r"^감점 점수 0 0 0 0 0\.2 0\.4 0\.6 0\.8 2\.0")))
                s.add("정시", "[%s] 탐구 반영 방식" % jname, "백분위 반영(탐구 반영 점수 200). 지정 응시영역은 사회·과학탐구이며 반영 과목 수는 해당 쪽에서 미확인", 27,
                      s.quote(27, r"^1\) 국어, 수학, 탐구영역은 백분위를 반영함"))
                s.add("정시", "[%s] 학생부 반영 여부" % jname, "있음(학생부(교과) 반영, 아래 표의 학생부(교과) 칸 20%)", 26,
                      s.quote(26, r"^인문⸱자연계열 일괄합산 80% 20% - 100%"))
                s.add("정시", "[%s] 면접 반영 여부" % jname, "없음(적성⸱인성 면접은 의학과만 실시한다고 적혀 있음)", 26,
                      s.quote(26, r"^※ 적성⸱인성 면접\(의학과\)"))
        # ---- 수시
        for key, val in SUSI.items():
            idx = COLS.index(key)
            cell = su[1 + idx]
            if cell == "-":
                continue
            name, pmin, rxmin, vmin, pint, rxint, vint = val
            tb = s.table(pt, r"^2-1\. 수시모집 모집인원", plan, "%s(모집인원 %s)" % (name, cell), [su[0]], title_page=5)
            s.add("수시", "[%s] 전형 이름" % name, name, pt, tb)
            qmin = s.quote(pmin, rxmin)
            s.add("수시", "[%s] 수능 최저 유무" % name, "%s(%s)" % (vmin, qmin) if vmin == "있음" else "없음", pmin, qmin)
            qint = s.quote(pint, rxint)
            s.add("수시", "[%s] 면접 유무" % name, vint, pint, qint)
    # 미확인
    for m in ["산업시스템정보공학과", "전기전자전파공학부", "컴퓨터·통신공학부", "컴퓨터교육과"]:
        assert not find_pages(d, m), m
        s.missing(m, m)
    return s


# ------------------------------------------------------------------ 동아대
def donga():
    d = Doc("동아대학교_2028시행계획.pdf")
    s = Sheet("동아대학교(부산)", d, "쪽 번호는 PDF 쪽 순서이며 쪽 아래 인쇄 번호와 같다.")
    # 수시: (전형 이름, 최저 쪽, 정규식, 값, 면접 쪽, 정규식, 값)
    SUSI = OrderedDict([
        ("잠재능력우수자", ("학생부종합(잠재능력우수자전형)", 10, r"^수능 면제", "없음(수능 면제)", 10, r"^- 2단계 : 면접대상자 중 1단계 성적 60%와 면접 40%를", "있음")),
        ("학교생활우수자", ("학생부종합(학교생활우수자전형)", 11, r"^수능 면제", "없음(수능 면제)", 11, r"^일괄합산 100 1,000", "없음(전형요소가 서류(학생부) 100)")),
        ("기회균형대상자", ("학생부종합(기회균형대상자전형)", 12, r"^수능 면제", "없음(수능 면제)", 12, r"^일괄합산 100 1,000", "없음(전형요소가 서류(학생부) 100)")),
        ("교과성적우수자", ("학생부교과(교과성적우수자전형)", 18, r"^인문계열,자연계열, 수능 4개 영역\[국어, 수학, 영어, 사회/과학탐구\(1개\)\] 중 1개 영역 등급 4 이내", "있음", 18, r"^일괄합산 인문계열, 자연계열, 100 1,000", "없음(전형요소가 교과성적 100)")),
        ("지역인재교과", ("학생부교과(지역인재교과전형)", 19, r"^인문계열, 자연계열, 수능 4개 영역\[국어, 수학, 영어, 사회/과학탐구\(1개\)\] 중 2개 영역 등급의 합 10 이내", "있음", 19, r"^일괄합산 인문계열, 자연계열, 자유전공학부 100 - 1,000", "없음(전형요소가 교과성적 100)")),
        ("교과진로우수자", ("학생부교과(교과진로우수자전형)", 20, r"^인문계열, 자연계열 수능 4개 영역\[국어, 수학, 영어, 사회/과학탐구\(1개\)\] 중 1개 영역 등급 4 이내", "있음", 20, r"^일괄합산 인문계열, 자연계열 80 20 1,000", "없음(전형요소가 교과성적 80 + 서류(학생부) 20)")),
        ("농어촌", ("학생부교과(농·어촌학생전형)", 25, r"^수능 면제 \(의예과 제외\)", "없음(수능 면제, 의예과 제외)", 25, r"^인문계열, 자연계열, 100 - 1,000", "없음(전형요소가 교과성적 100)")),
        ("특성화고", ("학생부교과(특성화고교졸업자(동일계)전형)", 26, r"^수능 면제", "없음(수능 면제)", 26, r"^일괄합산 100 1,000", "없음(전형요소가 교과성적 100)")),
    ])
    # 마커 학과명, 원문 모집단위, 단과대학 표기, 쪽, 수시 표값(잠재, 학생, 기회, 성적우수, 지역인재, 진로, 농어촌, 특성화), 정시 군, 정시 모집인원
    UNITS = [
        ("컴퓨터공학과", "컴퓨터공학과", "소프트웨어대학", 8, [11, 15, 3, 20, 14, 10, 3, 2], "가", "12"),
        ("AI학과", "AⅠ학과", "소프트웨어대학", 8, [11, 15, 3, 17, 13, 10, 2, None], "나", "11"),
        ("전기공학과", "전기공학과", "공과대학", 7, [13, 16, 4, 19, 16, 10, 4, 3], "가", "12"),
        ("전자공학과", "전자공학과", "공과대학", 7, [15, 20, 6, 27, 26, 20, 5, 3], "나", "16"),
        ("스마트그린자원학과", "스마트그린자원학과", "자원과학대학", 7, [6, 6, 2, 9, 9, None, 4, 2], "다", "8"),
    ]
    KEYS = ["잠재능력우수자", "학교생활우수자", "기회균형대상자", "교과성적우수자", "지역인재교과", "교과진로우수자", "농어촌", "특성화고"]
    for mdept, plan, college, pt, su, gun, jn in UNITS:
        s.unit(mdept, plan, college)
        note = "" if mdept == plan else "(마커 학과명 %s, 원문 표기 %s: 영문 I 대신 로마숫자 Ⅰ로 적혀 있음)" % (mdept, plan)
        row_exp = [str(x) for x in su if x is not None]
        s.add("공통", "모집단위", plan + note, pt, s.table(pt, r"^세부 모집인원", plan, "모집단위", row_exp + [jn], title_page=7))
        # 수시
        for key, v in zip(KEYS, su):
            if v is None:
                continue
            name, pmin, rxmin, vmin, pint, rxint, vint = SUSI[key]
            tb = s.table(pt, r"^세부 모집인원", plan, "%s(모집인원 %d)" % (name, v), [str(v)], title_page=7)
            s.add("수시", "[%s] 전형 이름" % name, name, pt, tb)
            qmin = s.quote(pmin, rxmin)
            s.add("수시", "[%s] 수능 최저 유무" % name, "%s(%s)" % (vmin, qmin) if vmin == "있음" else vmin, pmin, qmin)
            qint = s.quote(pint, rxint)
            s.add("수시", "[%s] 면접 유무" % name, vint, pint, qint)
        # 정시(일반학생전형)
        jp, jhead = {"가": (32, r"^1 수능\(가군 일반학생전형\) - 정원내"), "나": (34, r"^3 수능\(나군 일반학생전형\) - 정원내"), "다": (35, r"^4 수능\(다군 일반학생전형\) - 정원내")}[gun]
        tb = s.table(pt, r"^세부 모집인원", plan, "정시 수능 %s군 일반(모집인원 %s)" % (gun, jn), [jn], title_page=7)
        gp = d.donga_group_positions(pt)
        xp = d.second_last_pos(pt, plan, jn)
        assert min(gp, key=lambda k: abs(gp[k] - xp)) == gun, (plan, gp, xp)
        s.add("정시", "[수능(%s군 일반학생전형)] 모집군" % gun, "%s군" % gun, jp, "%s ; %s" % (tb, s.quote(jp, jhead)))
        s.add("정시", "[수능(%s군 일반학생전형)] 수능 영역별 반영 비율" % gun, "국어 25%, 수학 25%, 영어 25%, 탐구 25%(사회 12.5%, 과학 12.5%)", 53,
              "[표] 영역별 반영비율 / 행: 인문계열, 자연계열, 간호학과, 자유전공학부 / 열: 국어, 수학, 영어, 탐구(사회, 과학, 탐구 계) → %s" % s.quote(53, r"^인문계열, 자연계열, 25% 25% 25% 12\.5% 12\.5% 25%"))
        s.add("정시", "[수능(%s군 일반학생전형)] 영어 반영 방식" % gun, "등급별 환산점수(1등급 200, 2등급 198, 3등급 195, 4등급 192, 5등급 187, 6등급 182, 7등급 172, 8등급 162, 9등급 152)", 53,
              "[표] 영어영역 환산점수 / 행: 전 모집단위 / 열: 수능등급 1~9 → %s" % s.quote(53, r"^전 모집단위 200 198 195 192 187 182 172 162 152"))
        s.add("정시", "[수능(%s군 일반학생전형)] 한국사 반영 방식" % gun, "가산점(1~5등급 1점, 6등급 0.9점, 7등급 0.8점, 8등급 0.7점, 9등급 0.6점)", 53,
              "[표] 가산점 부여내용 한국사영역 / 행: 전 모집단위 / 열: 수능등급 → %s" % s.quote(53, r"^전 모집단위 1점 0\.9점 0\.8점 0\.7점 0\.6점"))
        s.add("정시", "[수능(%s군 일반학생전형)] 탐구 반영 방식" % gun, "사회/과학탐구 2개 과목 반영(국어·수학·탐구 3개 영역의 표준점수와 영어영역의 환산점수를 합산)", 53,
              "%s ; %s" % (s.quote(53, r"^자연계열, 수능 4개 영역\[국어, 수학, 영어, 사회/과학탐구\(2개\)\]"), s.quote(53, r"^인문계열, 3개 영역의 표준점수와")))
        s.add("정시", "[수능(%s군 일반학생전형)] 학생부 반영 여부" % gun, "점수 반영 없음(전형요소 수능 100). 제출서류에 학교생활기록부가 있고 학교폭력 조치사항에 따라 총점에서 감점함", jp,
              "%s ; %s" % (s.quote(jp, r"^일괄합산 인문계열, 자연계열, .* 100 800"), s.quote(jp, r"^※ 학교폭력 조치사항에 따라 등급별로 차등하여 총점에서 감점함")))
        s.add("정시", "[수능(%s군 일반학생전형)] 면접 반영 여부" % gun, "없음(전형요소가 수능 100)", jp, s.quote(jp, r"^일괄합산 인문계열, 자연계열, .* 100 800"))
    for m in ["스마트생산융합시스템공학과", "스마트제조공학과", "전기·전자·컴퓨터공학부", "전기·전자·컴퓨터공학부 전기공학과", "전기·전자·컴퓨터공학부 전자공학과", "전기·전자·컴퓨터공학부 컴퓨터공학과",
              "전기전자컴퓨터공학부", "전자공학전공", "컴퓨터·AI공학부 AI학과", "컴퓨터·AI공학부 컴퓨터공학과", "컴퓨터공학전공"]:
        key = m.split(" ")[-1] if " " in m else m
        # 부분 이름(학과 이름 자체)은 다른 모집단위에 나올 수 있으므로 마커 이름 전체로만 찾는다
        assert not find_pages(d, m), m
        s.missing(m, m)
    return s


# ------------------------------------------------------------------ 한양대
def hanyang():
    d = Doc("한양대학교_2028시행계획.pdf")
    s = Sheet("한양대학교(서울 통합)", d, "쪽 번호는 PDF 쪽 순서이며 쪽 아래 인쇄 번호는 PDF 쪽 번호보다 3 작다.")
    SUSI = OrderedDict([
        ("추천형", ("학생부교과(추천형)", 13, r"^자연, 상경, 국어, 수학, 영어, 탐구\(상위 1개 과목\) 중 3개 영역\(수학 포함\) 각 3등급 이내|국어, 수학, 영어, 탐구\(상위 1개 과목\) 중 3개 영역\(수학 포함\) 각", "있음", 13, r"^4\. 전형방법 : 학생부교과 60% \+ 학생부종합평가 40%", "없음(전형요소가 학생부교과 60% + 학생부종합평가 40%)")),
        ("학업형", ("학생부종합(학업형)", 14, r"국어, 수학, 영어, 사회, 과학 중 3개 영역\(수학 포함\) 등급합 7 이내", "있음", 14, r"^❖ 면접 없음", "없음")),
        ("면접형", ("학생부종합(면접형)", 15, r"^❖ 수능 면제", "없음(수능 면제)", 15, r"^2단계 1단계성적 70% \+ 면접 30%", "있음(제시문 기반 면접)")),
        ("고른기회", ("학생부종합(고른기회)", 16, r"^❖ 수능 면제, 면접 없음", "없음(수능 면제)", 16, r"^❖ 수능 면제, 면접 없음", "없음")),
        ("논술", ("논술", 21, r"^전 모집단위\(단, 의예과 제외\) 국어, 수학, 영어, 탐구\(상위 1개 과목\) 중 3개 영역 등급합 7 이내", "있음", 21, r"^4\. 전형방법 : 논술 90% \+ 학생부\(출결\) 10%", "없음(전형요소가 논술 90% + 학생부(출결) 10%)")),
    ])
    # 마커 학과명, 원문 모집단위(표 행 이름), 표시용 단과대학, 수시 칸(추천,학업,면접,고른,논술), 정시 군, 정시 인원, 표 행 값
    UNITS = [
        ("융합전자공학부", "융합전자공학부", "공과대학", [26, 40, 20, 5, 15], "나", "55"),
        ("컴퓨터소프트웨어학부", "컴퓨터소프트웨어학부", "공과대학", [21, 35, 15, 5, 10], "다", "45"),
        ("정보시스템학과", "정보시스템학과(상경)", "공과대학", [8, 9, None, 3, 5], "나", "10"),
        ("전기공학전공", "(전기공학전공)", "공과대학", [14, 14, 7, 3, 5], "나", "15"),
        ("데이터사이언스학부", "데이터사이언스학부", "공과대학", [13, 14, 8, 3, 5], "나", "17"),
    ]
    KEYS = ["추천형", "학업형", "면접형", "고른기회", "논술"]
    for mdept, plan, college, su, gun, jn in UNITS:
        if mdept == "전기공학전공":
            plan_disp = "전기·생체공학부(전기공학전공)"
        else:
            plan_disp = plan
        s.unit(mdept, plan_disp, college)
        row = plan
        if mdept == "전기공학전공":   # 표에서 행 이름이 두 줄로 나뉘어 숫자가 있는 첫 줄 이름으로 찾고, 바로 다음 줄이 (전기공학전공)인지 검사한다
            row = "전기·생체공학부"
            ls = [l for l in d.pages[4].splitlines() if l.strip()]
            k = [i for i, l in enumerate(ls) if nn(row) in nn(l) and "58" in l.split()]
            assert len(k) == 1 and "(전기공학전공)" in ls[k[0] + 1], k
        s.add("공통", "모집단위", plan_disp, 5, s.table(5, r"^□ 정원 내 모집인원", row, "모집단위", [str(x) for x in su if x is not None] + [jn]))
        for key, v in zip(KEYS, su):
            if v is None:
                continue
            name, pmin, rxmin, vmin, pint, rxint, vint = SUSI[key]
            tb = s.table(5, r"^□ 정원 내 모집인원", row, "%s(모집인원 %d)" % (name, v))
            s.add("수시", "[%s] 전형 이름" % name, name, 5, tb)
            qmin = s.quote(pmin, rxmin)
            s.add("수시", "[%s] 수능 최저 유무" % name, "%s(%s)" % (vmin, qmin) if vmin == "있음" else vmin, pmin, qmin)
            qint = s.quote(pint, rxint)
            s.add("수시", "[%s] 면접 유무" % name, vint, pint, qint)
        # 정시 일반전형
        tb = s.table(5, r"^□ 정원 내 모집인원", row, "정시 수능(%s군) 일반(모집인원 %s)" % (gun, jn), [jn])
        gp = d.hanyang_group_positions(5)
        xp = d.second_last_pos(5, row, jn)
        assert min(gp, key=lambda k: abs(gp[k] - xp)) == gun, (plan, gp, xp)
        if mdept == "컴퓨터소프트웨어학부":
            ev = "%s ; %s" % (tb, s.quote(27, r"^❖ 컴퓨터소프트웨어학부, 파이낸스경영학과 \[다\]군 변경"))
        else:
            ev = "%s ; %s" % (tb, s.quote(27, r"^일반\(자연･인문･상경\) 359 수능 90% \+ 학생부종합평가 10%"))
        s.add("정시", "[수능(%s군 일반전형)] 모집군" % gun, "%s군" % gun, 5 if mdept != "컴퓨터소프트웨어학부" else 27, ev)
        s.add("정시", "[수능(%s군 일반전형)] 수능 영역별 반영 비율" % gun,
              "유형 A: 국어·수학은 우수한 영역 순 35, 30 / 영어 10 / 탐구 25(반영 과목수 2). 유형 B: 국어·수학은 우수한 영역 순 40, 35 / 영어 10 / 탐구 15(반영 과목수 2). A, B 유형 중 상위 점수를 반영함", 29,
              "[표] 나. 영역별 반영비율(%%) / 행: 자연·인문·상경 유형 A, 유형 B / 열: 국어, 수학, 영어, 탐구(비율, 반영 과목수) → %s ; %s" % (
                  s.quote(29, r"^자연·인문·상경 유형 A 우수한 영역 순 35, 30 10 25 2"), s.quote(29, r"^※ A, B 유형 중 상위 점수를 반영함")))
        s.add("정시", "[수능(%s군 일반전형)] 영어 반영 방식" % gun,
              "등급에 따른 대학 자체 변환표준점수 반영(변환표준점수 값은 2028학년도 수능성적 발표일 이후 홈페이지 공지 예정으로 원문 표에 없음)", 29, s.quote(29, r"^- 영어영역 : 등급\(대학 자체 변환표준점수 반영\)"))
        s.add("정시", "[수능(%s군 일반전형)] 한국사 반영 방식" % gun,
              "1,000점에서 감점 처리(필수 응시영역). 등급별 감점 표가 계열별로 있으며 자연계열 행은 '만점, -0.1, -0.2, -0.3, -0.4, -0.5'로 적혀 있으나 어느 등급 칸에 해당하는지는 텍스트에서 확정하지 못해 미확인", 30,
              "%s ; [표] 8. 한국사 반영방법 / 행: 자연 / 열: 등급 1~9" % s.quote(30, r"^가\. 한국사는 한양대학교 정시전형 만점인 1,000점에서 감점 처리함"))
        s.add("정시", "[수능(%s군 일반전형)] 탐구 반영 방식" % gun, "백분위(대학 자체 변환표준점수 반영), 사회탐구 및 과학탐구 2과목 필수 응시, 반영 과목수 2", 29,
              "%s ; %s" % (s.quote(29, r"^- 탐구영역 : 백분위\(대학 자체 변환표준점수 반영\)"), s.quote(29, r"^- 사회탐구 및 과학탐구 2과목 필수 응시")))
        s.add("정시", "[수능(%s군 일반전형)] 학생부 반영 여부" % gun, "있음(학생부종합평가 10%)", 27, s.quote(27, r"^❖ 수능위주 일반전형 수능 90% \+ 학생부종합평가 10%로 선발"))
        s.add("정시", "[수능(%s군 일반전형)] 면접 반영 여부" % gun, "없음(전형요소가 수능 90% + 학생부종합평가 10%)", 27, s.quote(27, r"^❖ 수능위주 일반전형 수능 90% \+ 학생부종합평가 10%로 선발"))
    for m in ["데이터사이언스전공", "데이터사이언스학과", "소프트웨어전공", "정보공학전공", "컴퓨터공학부", "컴퓨터전공"]:
        assert not find_pages(d, m), m
        s.missing(m, m)
    # 전기·생체공학부(마커 학과명)는 원문에서 전공 둘로 나뉨
    s.unit("전기·생체공학부", None)
    s.add("공통", "모집단위", UNIT_UNCONFIRMED, "5", "원문 모집단위는 '전기·생체공학부 (전기공학전공)', '전기·생체공학부 (바이오메디컬공학전공)'로 나뉘어 나옴. 전기공학전공은 별도 항목으로 정리하고 바이오메디컬공학전공은 IT 학과명 목록에 없어 정리하지 않음 → " +
          s.table(5, r"^□ 정원 내 모집인원", "(바이오메디컬공학전공)", "모집단위"))
    return s


def main():
    sheets = [korea(), donga(), hanyang()]
    ercia_pages = find_pages(sheets[2].doc, "ERICA") + find_pages(sheets[2].doc, "에리카")
    erica = OrderedDict([
        ("file", sheets[2].doc.fname), ("pages", sorted(set(ercia_pages))),
        ("result", "ERICA·에리카가 나오는 쪽이 없음. 전형계획 안내문이 서울캠퍼스 입학전형 대상이라고 적음"),
        ("evidence", sheets[2].quote(2, r"2028학년도 한양대학교 서울캠퍼스 입학전형")),
        ("included", False)])
    assert not ercia_pages
    out = OrderedDict([
        ("meta", OrderedDict([("title", "2028학년도 대입전형 시행계획 IT 계열 요구사항 시험 정리"), ("order", "#1005-30"), ("state", STATE),
                              ("note", ["값은 AI가 시행계획 원문을 읽고 정리했고 사용자가 아직 검토하지 않았다.", "근거 문장은 스크립트가 PDF 텍스트에서 찾은 줄이다(공백 연속만 한 칸으로 정리).",
                                        "표 안의 값은 근거 자리에 표 제목과 행·열 이름을 적었다. 비율 합계, 환산 점수 같은 계산은 하지 않았다.",
                                        "쪽 번호는 PDF 쪽 순서(1쪽부터)다.", "정시는 일반 경쟁 전형 중심(고려대는 수능 일반전형과 교과우수전형)으로 정리했다. 정원외 특별전형은 정리 대상이 아니다.",
                                        "생성: scripts/build_requirements_2028_test.py"])])),
        ("hanyangEricaCheck", erica),
        ("schools", [OrderedDict([("school", sh.school), ("file", sh.doc.fname), ("pageNote", sh.page_note), ("units", sh.units)]) for sh in sheets]),
    ])
    with io.open(OUT_JSON, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    # ---- review.md
    def esc(x):
        return str(x).replace("|", "/").replace("\n", " ")
    rv = ["# 2028학년도 시행계획 IT 계열 요구사항 시험 정리 (requirements_2028_review.md)", "",
          "scripts/build_requirements_2028_test.py 가 data/requirements_2028_test.json 과 함께 만든 파일이다. 모든 값의 확인상태는 \"%s\"이다." % STATE,
          "근거 문장은 PDF 텍스트에서 찾은 줄(공백 연속만 한 칸으로 정리)이고, 표 안의 값은 표 제목과 행·열 이름이다. 쪽 번호는 PDF 쪽 순서다.", ""]
    stats = []
    for sh in sheets:
        n_val = sum(len(u["items"]) for u in sh.units)
        n_un = sum(1 for u in sh.units for it in u["items"] if UNCONFIRMED in it["값"])
        n_unit = len(sh.units)
        n_unit_un = sum(1 for u in sh.units if u["planUnit"] is None)
        stats.append((sh.school, sh.doc.fname, n_unit, n_unit - n_unit_un, n_unit_un, n_val, n_un))
        rv += ["## %s (%s)" % (sh.school, sh.doc.fname), "", sh.page_note, "",
               "| 모집단위 | 구분(정시/수시) | 항목 | 값 | 파일명 | 페이지 | 근거 문장 | 사용자 판정 |", "|---|---|---|---|---|---|---|---|"]
        for u in sh.units:
            label = "%s" % (u["markerDept"] if u["planUnit"] is None else "%s (원문: %s)" % (u["markerDept"], u["planUnit"]) if u["planUnit"] != u["markerDept"] else u["markerDept"])
            for it in u["items"]:
                rv.append("| %s | %s | %s | %s | %s | %s | %s | |" % (esc(label), it["구분"], esc(it["항목"]), esc(it["값"]), esc(it["파일명"]), esc(it["페이지"]), esc(it["근거"])))
        rv.append("")
    rv += ["## 집계", "", "| 학교 | 모집단위 수 | 원문에서 찾은 모집단위 | 모집단위 미확인 | 정리한 값 개수 | 미확인 개수 |", "|---|---|---|---|---|---|"]
    for st in stats:
        rv.append("| %s | %d | %d | %d | %d | %d |" % (st[0], st[2], st[3], st[4], st[5], st[6]))
    rv.append("")
    with io.open(OUT_MD, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(rv))
    for st in stats:
        print(st)
    print("한양대 ERICA 쪽:", erica["pages"])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
