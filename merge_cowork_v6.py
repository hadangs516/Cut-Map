"""merge_cowork_v5.py 를 복사한 v6 (#0929-32). v5 코드는 그대로 두고 아래쪽에 v6 처리를 붙였다.

- 작업 31 사전 검사: cowork_20260929_16~20.md 의 대학 수 (16~19번 5곳, 20번 3곳이어야 병합)
- 작업 33: 2027_정시모집요강_URL_누적.md 에 서울·충청·강원 행 추가, 16~20번 결과를 기존 행에 반영
- 표 값은 Cowork 결과의 칸을 그대로 옮긴다(사람이 다시 쓰지 않음)
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
V4 = os.path.join(ROOT, '컷맵_입결위치조사_20260924_v4.md')
V5 = os.path.join(ROOT, '컷맵_입결위치조사_20260929_v5.md')
V6 = os.path.join(ROOT, '컷맵_입결위치조사_20260930_v6.md')
JS = os.path.join(ROOT, '2027_정시모집요강_URL_누적.md')
DATE = '2026-09-29'
CONF = '확인(Cowork 직접 열람, 2026-09-29)'
TRUNC = 160


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def trunc(s, n=TRUNC):
    s = s.strip()
    return s if len(s) <= n else s[:n] + '…'


def cells(line):
    return [c.strip() for c in re.split(r'(?<!\\)\|', line.strip()[1:-1])]   # 칸 안의 \| 는 칸 구분이 아님


def row(cs):
    for c in cs:
        assert '|' not in c.replace('\\|', ''), c
    return '| ' + ' | '.join(cs) + ' |'


# ---------------------------------------------------------------- Cowork 결과 읽기
def read_cowork():
    recs = []
    files = glob.glob(os.path.join(ROOT, 'cowork_results', 'cowork_20260929_*.md')) + glob.glob(os.path.join(ROOT, 'cowork_results', 'cowork_20260930_*.md'))
    for f in sorted(files, key=lambda x: int(re.search(r'_(\d+)\.md$', x).group(1))):
        lines = rd(f).split('\n')
        seen_sep = False
        for l in lines:
            if l.startswith('|---'):
                seen_sep = True
                continue
            if seen_sep and l.startswith('|'):
                c = cells(l)
                assert len(c) == 10, (f, len(c), l[:80])
                recs.append(dict(file=os.path.basename(f), name=c[0], campus=c[1], url=c[2], attach=c[3], fmt=c[4],
                                 year=c[5], jurl=c[6], jfile=c[7], status=c[8], note=c[9]))
            elif seen_sep:
                seen_sep = False
    return recs


# 어느 Cowork 행이 v4의 어느 행인가. (Cowork 대학, 캠퍼스) -> [(v4 섹션, v4 대학명, v4 2열(지역 또는 캠퍼스))]
# v4 섹션: 1-1~1-4는 7열 표(2열=지역), 1-5~1-8은 8열 표(2열=캠퍼스). 'NEW'는 v4에 행이 없어 새로 만든다.
def T(sec, name, col2, new=False):
    return (sec, name, col2, new)


MAP = {
    ('순천향대학교', '아산'): [T('1-4', '순천향대학교', '충청', True)],
    ('서울기독대학교', '서울'): [T('1-3', '서울기독대학교', '서울')],
    ('연세대학교(미래)', '원주'): [T('1-1', '연세대학교(미래)', '강원')],
    ('부산대학교', '부산'): [T('1-8', '부산대학교', '부산', True)],
    ('경북대학교', '대구'): [T('1-8', '경북대학교', '대구', True)],
    ('국립부경대학교', '부산(대연)'): [T('1-8', '국립부경대학교', '부산(대연)', True)],
    ('국립한국해양대학교', '부산'): [T('1-8', '국립한국해양대학교', '부산', True)],
    ('인천대학교', '인천(송도)'): [T('1-7', '인천대학교', '인천(송도)', True)],
    ('인하대학교', '인천'): [T('1-7', '인하대학교', '인천', True)],
    ('가천대학교', '성남(글로벌)'): [T('1-6', '가천대학교', '성남(글로벌)', True)],
    ('단국대학교', '죽전'): [T('1-6', '단국대학교', '죽전', True)],
    ('한국공학대학교', '시흥'): [T('1-6', '한국공학대학교', '시흥', True)],
    ('아주대학교', '수원'): [],  # 보류. v4에 행 없음 -> 대기열
    ('경희대학교', '서울·국제(용인)'): [T('1-5', '경희대학교', '서울'), T('1-6', '경희대학교', '국제(용인)', True)],
    ('한국항공대학교', '고양'): [T('1-6', '한국항공대학교', '고양', True)],
    ('창신대학교', '창원'): [T('1-8', '창신대학교', '창원')],
    ('서울신학대학교', '부천'): [T('1-6', '서울신학대학교', '부천')],
    ('경남대학교', '마산'): [T('1-8', '경남대학교', '마산')],
    ('경성대학교', '부산'): [T('1-8', '경성대학교', '부산')],
    ('경운대학교', '구미'): [T('1-8', '경운대학교', '구미')],
    ('경일대학교', '경산'): [T('1-8', '경일대학교', '경산')],
    ('고신대학교', '부산(영도)'): [T('1-8', '고신대학교', '부산')],
    ('계명대학교', '대구'): [T('1-8', '계명대학교', '대구')],
    ('국립경국대학교', '안동'): [T('1-8', '국립경국대학교', '안동')],
    ('김천대학교', '김천'): [T('1-8', '김천대학교', '김천')],
    ('대구가톨릭대학교', '경산'): [T('1-8', '대구가톨릭대학교', '경산')],
    ('대구예술대학교', '칠곡'): [T('1-8', '대구예술대학교', '칠곡')],
    ('경상국립대학교', '진주'): [T('1-8', '경상국립대학교', '진주')],
    ('신경주대학교', '경주'): [T('1-8', '신경주대학교', '경주')],
    ('영남대학교', '경산'): [T('1-8', '영남대학교', '경산')],
    ('영산대학교', '양산·해운대(입학처 공통)'): [T('1-8', '영산대학교(양산)', '양산'), T('1-8', '영산대학교(해운대)', '해운대')],
    ('인제대학교', '김해'): [T('1-8', '인제대학교', '김해')],
    ('위덕대학교', '경주'): [T('1-8', '위덕대학교', '경주')],
    ('신한대학교', '의정부'): [T('1-6', '신한대학교', '의정부')],
    ('안양대학교', '안양·강화(입학처 공통)'): [T('1-6', '안양대학교', '안양'), T('1-7', '안양대학교', '강화')],
    ('을지대학교', '성남(대전·성남·의정부 입학처 공통)'): [T('1-6', '을지대학교', '성남')],
    ('차의과학대학교', '포천'): [T('1-6', '차의과학대학교', '포천')],
    ('평택대학교', '평택'): [T('1-6', '평택대학교', '평택')],
    ('한경국립대학교', '안성·평택(입학처 공통)'): [T('1-6', '한경국립대학교', '안성'), T('1-6', '한경국립대학교', '평택')],
    ('한신대학교', '오산'): [T('1-6', '한신대학교', '오산')],
    ('협성대학교', '화성'): [T('1-6', '협성대학교', '화성')],
    ('화성의과학대학교', '화성'): [T('1-6', '화성의과학대학교', '화성')],
    ('대구대학교', '경산'): [T('1-8', '대구대학교', '경산')],
    ('부산가톨릭대학교', '부산'): [T('1-8', '부산가톨릭대학교', '부산')],
    ('한림대학교', '춘천'): [T('1-1', '한림대학교', '강원')],
    ('상지대학교', '원주'): [T('1-1', '상지대학교', '강원')],
    ('가톨릭관동대학교', '강릉'): [T('1-1', '가톨릭관동대학교', '강원')],
    ('한라대학교', '원주'): [T('1-1', '한라대학교', '강원')],
    ('광운대학교', '서울'): [T('1-3', '광운대학교', '서울')],
    ('서강대학교', '서울'): [T('1-3', '서강대학교', '서울')],
    ('서울대학교', '서울'): [T('1-3', '서울대학교', '서울')],
    ('서울시립대학교', '서울'): [T('1-3', '서울시립대학교', '서울')],
    ('덕성여자대학교', '서울'): [T('1-3', '덕성여자대학교', '서울')],
    ('삼육대학교', '서울'): [T('1-3', '삼육대학교', '서울')],
    ('서경대', '서울'): [T('1-3', '서경대학교', '서울')],
    ('성공회대', '서울'): [T('1-3', '성공회대학교', '서울')],
    ('성신여자대', '서울'): [T('1-3', '성신여자대학교', '서울')],
    ('세종대', '서울'): [T('1-3', '세종대학교', '서울')],
    ('숙명여자대', '서울'): [T('1-3', '숙명여자대학교', '서울')],
    ('충북대', '청주'): [T('1-4', '충북대학교', '충청')],
    ('국립한밭대', '대전'): [T('1-4', '국립한밭대학교', '충청')],
    ('국립공주대', '천안(대학 통합 자료)'): [T('1-4', '국립공주대학교(천안)', '충청')],
    ('국립한국교통대', '충주'): [T('1-4', '국립한국교통대학교', '충청')],
    ('한국교원대', '청주'): [T('1-4', '한국교원대학교', '충청')],
    ('고려대', '세종'): [T('1-4', '고려대학교(세종)', '충청')],
    ('홍익대', '세종'): [T('1-4', '홍익대학교(세종)', '충청')],
    ('건국대', '글로컬(충주)'): [T('1-4', '건국대학교(글로컬)', '충청')],
    ('한국기술교육대', '천안'): [T('1-4', '한국기술교육대학교', '충청')],
    ('한서대', '서산'): [T('1-4', '한서대학교', '충청')],
    ('중부대', '금산'): [T('1-4', '중부대학교(금산)', '충청')],
}
NEW_REGION = {'1-4': '충청', '1-5': '서울', '1-6': '경기', '1-7': '인천', '1-8': '영남'}


# ---------------------------------------------------------------- 상태 변환
def reason_from(rec):
    m = re.match(r'^없음\s*\((.*)\)$', rec['url'])
    if m:
        return m.group(1)
    first = re.split(r'(?<=[.)])\s+(?=[가-힣A-Za-z0-9])', rec['note'].strip())[0]
    return first.rstrip('.')


def conv_status(rec):
    """Cowork 상태 칸에서 입결 부분만 골라 v4 표기로 바꾼다."""
    n = rec['name']
    st = rec['status'].strip()
    if n == '연세대학교(미래)':
        return '제외(파일 자료 아님)'
    if n == '협성대학교':
        return '조회형 보류(입결 조회 화면은 외부 도메인이라 열지 않음, 수집 방법 보류). 입학처 안내 게시글은 ' + CONF
    if n == '중부대':
        return ('수시: ' + CONF + ' / 정시 입결: 미조사(브라우저 도구 중단으로 열어 보지 않음)')
    if n == '계명대학교':
        return ('미조사(재조사 대기: 허용 도메인 gokmu.ac.kr 추가, 작업 22). Cowork 2026-09-29 결과는 보류(허용 도메인 밖이라 열지 않음)')
    if n == '신경주대학교':
        return '재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음). Cowork 2026-09-29 결과는 보류'
    parts = [p.strip() for p in st.split(' / ')]
    main = next((p for p in parts if p.startswith('입결')), parts[0])
    m = re.sub(r'^입결\s*', '', main)
    if m == '확인':
        return CONF
    mm = re.match(r'^확인\((.*)\)$', m)
    if mm:
        return CONF + '. ' + mm.group(1)
    if m == '미확인':
        return '미확인(' + reason_from(rec) + '; Cowork 직접 열람, 2026-09-29)'
    mm = re.match(r'^미확인\((.*)\)$', m)
    if mm:
        return '미확인(' + mm.group(1) + '; Cowork 직접 열람, 2026-09-29)'
    raise ValueError('처리하지 못한 상태: %s / %s' % (n, st))


def years(s):
    return set(re.findall(r'20\d\d', s))


def urls(s):
    return set(re.findall(r'https?://[^\s)\]>]+', s))


def changes(old_url, old_year, old_stat, rec, new_stat):
    ch = []
    ou, nu = urls(old_url), urls(rec['url'])
    if ou and not all(any(u == v or v.startswith(u) or u.startswith(v) for v in nu) for u in ou):
        ch.append('게시 페이지 URL: 기존 ' + trunc(old_url) + ' → Cowork 값으로 교체')
    elif not ou and nu:
        ch.append('게시 페이지 URL: 기존 미확보 → Cowork 값')
    if rec['year'] not in ('-', '') and years(old_year) != years(rec['year']) and years(rec['year']):
        ch.append('학년도: 기존 ' + trunc(old_year, 80) + ' → ' + trunc(rec['year'], 80))
    old_stat = re.split(r' 변경:| ※', old_stat)[0].rstrip('.')   # 이전 병합이 붙인 "변경:"·비고는 뺀다
    if not old_stat.startswith('확인(Cowork'):
        ch.append('확인상태: 기존 ' + trunc(old_stat, 100) + ' → ' + label(new_stat))
    return ch


def label(stat):
    m = re.match(r'^(확인\(Cowork 직접 열람, 2026-09-\d\d\)|미확인|제외\(파일 자료 아님\)|조회형 보류|수시:|재확인 필요|미조사)', stat)
    return m.group(1) if m else trunc(stat, 30)


def note_join(stat, ch, note, extra):
    s = stat
    if ch:
        s = stat.rstrip('.') + '. 변경: ' + ' / '.join(ch) + '.'
    s += ' ※ Cowork 비고: ' + note if note else ''
    return s + extra


# ---------------------------------------------------------------- v4 파싱
def split_sections(lines):
    """### 1-N. 제목 단위 표 블록 위치를 찾는다."""
    heads = {}
    for i, l in enumerate(lines):
        m = re.match(r'^### (1-\d)\.', l)
        if m:
            heads[m.group(1)] = i
    return heads


def find_table_rows(lines, start):
    """start 이후 첫 표의 (헤더행 인덱스, [데이터 행 인덱스])"""
    i = start
    while not lines[i].startswith('| '):
        i += 1
    hdr = i
    assert lines[hdr + 1].startswith('|---')
    rows = []
    j = hdr + 2
    while j < len(lines) and lines[j].startswith('|'):
        rows.append(j)
        j += 1
    return hdr, rows


def apply_rec_7(old, rec, note_extra=''):
    """1-1~1-4 (7열): 대학명 | 지역 | 게시글 URL | 파일형식 | 지표정의 | 공개연도 | 확인상태"""
    stat = conv_status(rec)
    name, reg = (old[0], old[1]) if old else (rec['name'], NEW_REGION_7[rec['name']])
    if rec['name'] in ('신경주대학교', '계명대학교'):
        raise AssertionError('7열 대상 아님')
    fmt = rec['fmt'] if rec['fmt'] not in ('-', '') else ''
    att = rec['attach'] if rec['attach'] not in ('-', '') else ''
    if fmt == '미확인' and att.startswith('미확인'):
        fmt = ''
    fcell = '. '.join(x for x in (fmt, att) if x) or '-'
    metric = old[4] if old else '미확인'
    ch = changes(old[2], old[5], old[6], rec, stat) if old else []
    scell = note_join(stat, ch, rec['note'], note_extra)
    return [name, reg, rec['url'], fcell, metric, rec['year'], scell]


def apply_rec_8(old, rec, campus_new=None, note_extra=''):
    """1-5~1-8 (8열): 대학명 | 캠퍼스 | 자료명 | 자료 URL | 게시 페이지 URL | 학년도 | 확인일 | 비고"""
    stat = conv_status(rec)
    name, camp = (old[0], old[1]) if old else (rec['name'], campus_new)
    fmt = rec['fmt'] if rec['fmt'] not in ('-', '', '미확인') else ''
    att = rec['attach']
    aname = att + (' [형식: ' + fmt + ']' if fmt and att not in ('-',) else '')
    if att == '-':
        aname = '-'
    furl = old[3] if old else '미확보(Cowork는 파일 URL을 기록하지 않음)'
    ch = changes(old[4], old[5], old[7], rec, stat) if old else []
    return [name, camp, aname, furl, rec['url'], rec['year'], DATE, note_join(stat, ch, rec['note'], note_extra)]


NEW_REGION_7 = {'순천향대학교': '충청'}


def main():
    recs = read_cowork()
    print('Cowork 행:', len(recs), '파일:', len(set(r['file'] for r in recs)))
    unmapped = [(r['name'], r['campus']) for r in recs if (r['name'], r['campus']) not in MAP]
    assert not unmapped, unmapped
    text = rd(V4)
    lines = text.split('\n')
    heads = split_sections(lines)
    tables = {}
    for sec, st in heads.items():
        hdr, rows = find_table_rows(lines, st)
        tables[sec] = dict(hdr=hdr, rows=rows, ncol=len(cells(lines[hdr])))
    for sec in ('1-1', '1-2', '1-3', '1-4'):
        assert tables[sec]['ncol'] == 7, sec
    for sec in ('1-5', '1-6', '1-7', '1-8'):
        assert tables[sec]['ncol'] == 8, sec

    def find_row(sec, name, col2):
        hit = [i for i in tables[sec]['rows'] if cells(lines[i])[0] == name and cells(lines[i])[1] == col2]
        return hit

    replaced = {}  # 줄 번호 -> 새 줄
    inserts = {}   # 섹션 -> [새 줄]
    applied = []   # (rec, 섹션, 이름, 캠퍼스, 새로?)
    for rec in recs:
        targets = MAP[(rec['name'], rec['campus'])]
        for k, (sec, name, col2, new) in enumerate(targets):
            same = ''
            if len(targets) > 1 and k > 0:
                same = ' [입학처 공통: ' + targets[0][1] + '(' + targets[0][2] + ') 행과 같은 결과를 적용]'
            elif len(targets) > 1:
                same = ' [입학처 공통: 같은 결과를 ' + ', '.join(t[1] + '(' + t[2] + ')' for t in targets[1:]) + ' 행에도 적용]'
            if new:
                assert not find_row(sec, name, col2), ('이미 있음', sec, name, col2)
                if sec in ('1-1', '1-2', '1-3', '1-4'):
                    cs = apply_rec_7(None, rec, same)
                else:
                    cs = apply_rec_8(None, rec, campus_new=col2, note_extra=same)
                    if name == '경희대학교':
                        cs[7] = cs[7] + ' [1-5장 경희대(서울) 행과 같은 자료(Cowork 결과 한 행에 서울·국제 통합)]'
                inserts.setdefault(sec, []).append(row(cs))
                applied.append((rec, sec, name, col2, True))
                continue
            hit = find_row(sec, name, col2)
            assert len(hit) == 1, (sec, name, col2, hit)
            i = hit[0]
            old = cells(lines[i])
            if rec['name'] in ('신경주대학교', '계명대학교'):
                # 자료가 없는 보류 행: 자료 칸은 그대로 두고 비고만 갱신
                stat = conv_status(rec)
                newc = list(old)
                newc[7] = stat + ' ※ Cowork 비고: ' + rec['note'] + ' ※ 기존 비고: ' + old[7]
                newc[6] = old[6]
                replaced[i] = row(newc)
            elif sec in ('1-1', '1-2', '1-3', '1-4'):
                replaced[i] = row(apply_rec_7(old, rec, same))
            else:
                extra = same
                if rec['name'] == '경상국립대학교':
                    extra += ' [옛 경남과기대 도메인(gntech.ac.kr) 자료: 조사 안 함(통합 전 자료)]'
                newc = apply_rec_8(old, rec, note_extra=extra)
                replaced[i] = row(newc)
            applied.append((rec, sec, name, col2, False))

    # 표 안에 반영
    for i, s in replaced.items():
        lines[i] = s
    # 새 행은 표 마지막 행 뒤에 (뒤쪽 섹션부터 넣어 줄 번호가 밀리지 않게)
    for sec in sorted(inserts, key=lambda s: -tables[s]['rows'][-1]):
        last = tables[sec]['rows'][-1]
        lines[last + 1:last + 1] = inserts[sec]
    out = '\n'.join(lines)

    # ---------- 문서 보조 갱신 (표 밖 문구)
    return out, recs, applied, tables


# ---------------------------------------------------------------- 정시 파일 (작업 28)
JMAP = {'영산대학교': ['영산대학교(양산)', '영산대학교(해운대)'], '한경국립대학교': ['한경국립대학교', '한경국립대학교(평택)']}
JSKIP = ('아주대학교', '계명대학교', '신경주대학교')   # 정시 자료 없음(미조사·보류)


def jstate(cs):
    v = cs[2:5]
    if all(x == '미조사' for x in v):
        return '미조사'
    if any('미확인' in x for x in v):
        return '미확인'
    return '확인'


def update_jeongsi(recs):
    raw = rd(JS)
    assert raw.count('\r\n') == raw.count('\n')  # 이 파일은 CRLF. 그대로 유지한다
    lines = raw.replace('\r\n', '\n').split('\n')
    i0 = lines.index('## 조사 완료 대학')
    hdr = i0 + 2
    assert lines[hdr].startswith('| 대학명 |') and lines[hdr + 1].startswith('|---')
    r_idx = []
    j = hdr + 2
    while lines[j].startswith('|'):
        r_idx.append(j)
        j += 1
    before = {'미조사': 0, '미확인': 0, '확인': 0}
    for i in r_idx:
        before[jstate(cells(lines[i]))] += 1
    assert (before['미조사'], before['미확인']) == (63, 7), before  # 파일 문구는 62개(경기 32)였으나 실제 목록은 63행(경기 33, 한경국립대학교(평택) 추가 행 포함)
    # 권역 경계(표 순서): 인천은 안양대학교 (본교(제2캠퍼스)) 부터, 영남은 경남대학교 부터
    names = [(cells(lines[i])[0], cells(lines[i])[1]) for i in r_idx]
    k_inc = names.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names.index(('경남대학교', '경남대학교(마산)'))

    def region(k):
        return '경기' if k < k_inc else ('인천' if k < k_yn else '영남')

    hdr_cells = cells(lines[hdr]) + ['상태', '출처']
    lines[hdr] = row(hdr_cells)
    lines[hdr + 1] = '|' + '---|' * len(hdr_cells)
    reflected = []
    unmatched = []
    old_notes = {}
    touched = set()
    for rec in recs:
        if rec['name'] in JSKIP or rec['jurl'].startswith('미조사'):
            continue
        targets = JMAP.get(rec['name'], [rec['name']])
        hit = [k for k, i in enumerate(r_idx) if cells(lines[i])[0] in targets]
        if not hit:
            unmatched.append(rec)
            continue
        for k in hit:
            i = r_idx[k]
            cs = cells(lines[i])[:6]
            old_url, old_file = cs[3], cs[4]
            if rec['jurl'].startswith('미확인'):
                stt = '미확인'
            else:
                stt = '미확인(학년도 확인 안 됨)' if '학년도 미확인' in rec['status'] else '확인'
            if cs[2] == '미조사':
                cs[2] = '미기록(Cowork 직접 열람 시 파일 URL을 기록하지 않음)'
            cs[3] = rec['jurl']
            cs[4] = rec['jfile']
            cs[5] = DATE
            lines[i] = row(cs + [stt, 'Cowork 직접 열람'])
            touched.add(i)
            reflected.append((cs[0], cs[1], stt))
            chg = []
            if old_url not in ('미조사', '미확인'):
                chg.append('게시 페이지 URL 기존 ' + trunc(old_url) + ' → Cowork 값')
            if old_file not in ('미조사', '미확인'):
                chg.append('파일명 기존 ' + trunc(old_file, 100) + ' → Cowork 값')
            if chg and len(hit) > 1:
                chg.append('입학처 공통 결과를 같은 이름의 다른 행에도 적용')
            if chg:
                old_notes.setdefault(cs[0] + '|' + cs[1], []).extend(chg)
    for i in r_idx:
        if i not in touched:
            lines[i] = row(cells(lines[i])[:6] + ['-', '-'])
    lines[j:j] = ['', '> 상태·출처 칸은 2026-09-29 Cowork 반영 행만 채웠다. 나머지 행은 "-"이고 기존 칸 값(미조사·미확인·확인일)을 그대로 따른다.',
                  '> 2026-09-29 Cowork 직접 열람 행은 게시 페이지 URL·파일명 칸을 결과 파일 문구 그대로 옮겼다. 파일 URL은 Cowork가 기록하지 않아 "미기록"으로 뒀다.']
    # 조사 비고 표
    n0 = lines.index('## 조사 비고')
    nh = n0 + 2
    assert lines[nh].startswith('| 대학명 | 비고 |')
    nr = []
    q = nh + 2
    while lines[q].startswith('|'):
        nr.append(q)
        q += 1
    notes = {cells(lines[x])[0]: x for x in nr}
    add_rows = []
    for key, chg in old_notes.items():
        nm, camp = key.split('|')
        txt = '변경(2026-09-29 Cowork 반영): ' + ' / '.join(chg)
        if nm in notes:
            c = cells(lines[notes[nm]])
            c[1] = c[1] + ' ※ ' + txt
            lines[notes[nm]] = row(c)
        else:
            dup = sum(1 for kk in old_notes if kk.split('|')[0] == nm) > 1
            add_rows.append(row([nm + ('(' + camp + ')' if dup else ''), txt]))
    if '한경국립대학교(평택)' in notes:
        c = cells(lines[notes['한경국립대학교(평택)']])
        c[1] = c[1] + ' ※ 2026-09-29 Cowork가 안성·평택 공통 결과를 직접 열람해 확인(위 "미조사"는 지난 상태)'
        lines[notes['한경국립대학교(평택)']] = row(c)
    add_rows.append(row(['신경주대학교', '정시 요강: 미조사 유지. 재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음). Cowork 2026-09-29는 허용 도메인 밖이라 열지 않음(보류)']))
    add_rows.append(row(['아주대학교', '정시 요강: 미조사 유지. 대학 홈페이지 입학처 링크가 iajou.ac.kr로 연결됨(Cowork 2026-09-29). 허용 도메인에 추가됨(작업 22)']))
    add_rows.append(row(['계명대학교', '정시 요강: 미조사 유지. 대학 홈페이지 입학 링크가 gokmu.ac.kr로 연결됨(Cowork 2026-09-29). 허용 도메인에 추가됨(작업 22)']))
    lines[q:q] = add_rows
    # 미확인·미조사 목록은 표 상태에서 다시 계산
    rows_now = []
    j = hdr + 2
    while lines[j].startswith('|'):
        rows_now.append(cells(lines[j]))
        j += 1
    assert len(rows_now) == len(r_idx)

    def st_now(cs):
        if cs[6] != '-':
            return '미확인' if cs[6].startswith('미확인') else '확인'
        return jstate(cs[:6])

    groups = {'미조사': {'경기': [], '인천': [], '영남': []}, '미확인': {'경기': [], '인천': [], '영남': []}}
    for k, cs in enumerate(rows_now):
        st = st_now(cs)
        if st in groups:
            groups[st][region(k)].append('- %s (%s)' % (cs[0], cs[1]))
    cnt = {st: sum(len(v) for v in g.values()) for st, g in groups.items()}
    m0 = lines.index('## 미확인 대학 목록')
    tail = ['## 미확인 대학 목록', '',
            '정시 모집요강 URL을 미확인으로 둔 대학입니다. (상태 칸이 "미확인"이거나, 상태 칸이 "-"이고 기존 칸에 "미확인"이 있는 행)', '']
    for rg in ('경기', '인천', '영남'):
        tail += ['### ' + rg, ''] + (groups['미확인'][rg] or ['- 없음']) + ['']
    tail += ['## 미조사 대학 목록', '', '### 남은 대기열', '',
             '- 미조사 %d개: 아래 권역별 목록(경기 %d, 인천 %d, 영남 %d)의 대학은 아직 정시 모집요강을 확인하지 않았습니다. (2026-09-29 Cowork 반영 후)'
             % (cnt['미조사'], len(groups['미조사']['경기']), len(groups['미조사']['인천']), len(groups['미조사']['영남'])), '']
    for rg in ('경기', '인천', '영남'):
        tail += ['### ' + rg, ''] + (groups['미조사'][rg] or ['- 없음']) + ['']
    lines = lines[:m0] + tail
    while lines and lines[-1] == '':
        lines.pop()
    text = '\n'.join(lines) + '\n'
    marker = '> 관리: 2026-09-28부터 Claude Code가 관리'
    k = text.index(marker)
    text = text[:k] + ('> 2026-09-29(#0929-24 작업 28): Cowork 직접 열람 결과(cowork_results 01~15)를 해당 행에 반영하고 표에 상태·출처 칸을 추가했습니다. '
                       '파일에 행이 있는 경기·인천·영남 대학만 반영했고, 서울·충청·강원 결과는 이 파일에 행이 없어 반영하지 않았습니다.\n>\n') + text[k:]
    text = text.replace('\n', '\r\n')
    return text, dict(before=before, reflected=reflected, unmatched=unmatched, cnt=cnt, groups=groups)


# ---------------------------------------------------------------- v5 문서 정리 (표 밖 문구, 2-1·2-2·3장·5장·6장)
SEC_REGION = {'1-1': '강원', '1-2': '제주', '1-3': '서울', '1-4': '충청', '1-5': '서울', '1-6': '경기', '1-7': '인천', '1-8': '영남'}


def idx(lines, prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise KeyError(prefix)


def table_span(lines, start):
    """start 이후 첫 표의 (헤더 줄, 첫 데이터 줄, 마지막 데이터 줄 + 1)"""
    h = idx(lines, '| ', start)
    e = h + 2
    while e < len(lines) and lines[e].startswith('|'):
        e += 1
    return h, h + 2, e


def finish_v5(out, recs, applied, js):
    lines = out.split('\n')
    stats = {}
    # 제목
    old_t = '2026-09-24 기준, 누적 4차 정리본, Cowork 브라우저 확인 반영'
    assert old_t in lines[0]
    lines[0] = lines[0].replace(old_t, '2026-09-29 기준, 누적 5차 정리본, Cowork 브라우저 재조사 반영')

    # 0장 기준 문구
    k = idx(lines, '- Cowork(브라우저 도구)가 직접 열람한 행은')
    lines[k + 1:k + 1] = [
        '- 2026-09-29 Cowork 재조사(`cowork_results/cowork_20260929_01~15.md`) 행은 확인상태를 "확인(Cowork 직접 열람, 2026-09-29)"로 표기하고 확인일을 2026-09-29로 바꿨다. 이 행에서는 "학년도 스니펫 기준" 표시를 뗐다. 1-1~1-4 표는 비고 열이 없어 확인상태 칸에 함께 적는다.',
        '- 2026-09-29 반영 행의 게시글 URL·첨부 파일명·형식·학년도·비고는 Cowork 결과 파일의 칸을 스크립트(`merge_cowork_v5.py`)로 그대로 옮겼다. 학년도 판단 근거(PDF 뷰어 본문·첫 장 제목 등)는 결과 파일의 학년도·비고 문구가 그대로 들어 있다. 기존 값과 다르면 Cowork 값을 쓰고 "변경:"에 달라진 내용을 적었으며, "※ Cowork 비고:" 뒤는 결과 파일의 비고 원문이다.',
        '- 2027학년도 정시 모집요강 URL·파일명은 이 문서가 아니라 `2027_정시모집요강_URL_누적.md`에 반영했다.',
    ]

    # ---- 2-1 미확인 항목
    h2 = idx(lines, '### 2-1.')
    th, t0, t1 = table_span(lines, h2)
    drop_tokens = set()
    for rec, sec, name, col2, new in applied:
        drop_tokens.add(name)
        drop_tokens.add('%s(%s)' % (name, col2))
    kept, dropped = [], 0
    for i in range(t0, t1):
        first = cells(lines[i])[0]
        toks = first.split('·')
        hit = [t in drop_tokens for t in toks]
        assert all(hit) or not any(hit), ('2-1 행이 일부만 처리 대상', first)
        if all(hit):
            dropped += 1
        else:
            kept.append(lines[i])
    gen = []
    multi = {}
    for rec, sec, name, col2, new in applied:
        multi.setdefault((rec['name'], rec['campus']), []).append(name)
    for rec, sec, name, col2, new in applied:
        stat = conv_status(rec)
        sent = [x.strip() for x in re.split(r'(?<=\.)\s+', rec['note']) if '미확인' in x]
        special = rec['name'] in ('신경주대학교', '계명대학교')
        if stat == CONF and not sent:
            continue
        disp = name if (len(multi[(rec['name'], rec['campus'])]) == 1 or '(%s)' % col2 in name) else '%s(%s)' % (name, col2)
        if special:
            item = '전체'
        elif stat.startswith('미확인'):
            item = '입결 전체'
        elif stat.startswith(('제외', '조회형')):
            item = '입결(제외·보류 항목)'
        else:
            item = '일부 항목(확인상태·비고 참조)'
        reason = ' / '.join(x for x in ([stat] if stat != CONF else []) + [' '.join(sent)] if x)
        gen.append(row([disp, SEC_REGION[sec], item, reason]))
    lines[t0:t1] = kept + gen
    stats['2-1'] = dict(dropped=dropped, kept=len(kept), generated=len(gen))

    # ---- 2-2 확인 방식을 알 수 없는 행
    processed = {name for rec, sec, name, col2, new in applied if sec in ('1-1', '1-2', '1-3', '1-4') and not new}
    h22 = idx(lines, '### 2-2.')
    end22 = idx(lines, '- 합계 43행', h22)
    removed = {}
    remain = {}
    newl = []
    for i in range(h22, end22):
        m = re.match(r'^- (1-\d)\. (\S+) \((\d+)행\): (.*)$', lines[i])
        if not m:
            newl.append(lines[i])
            continue
        names = [x.strip() for x in m.group(4).split(',')]
        assert len(names) == int(m.group(3)), lines[i]
        keep = [x for x in names if x not in processed]
        removed[m.group(2)] = len(names) - len(keep)
        remain[m.group(2)] = keep
        if keep:
            newl.append('- %s. %s (%d행): %s' % (m.group(1), m.group(2), len(keep), ', '.join(keep)))
    n_remain = sum(len(v) for v in remain.values())
    n_removed = sum(removed.values())
    lines[h22:end22] = newl
    k = idx(lines, '- 합계 43행', h22)
    lines[k] = ('- 합계 %d행(%s). 2026-09-29 Cowork가 직접 열람해 확인 방식이 드러난 %d행(%s)은 2-2장에서 뺐다. '
                '중부대학교(금산)는 정시 입결·요강이 미조사로 남아 6장 대기열로 옮겼다. 나머지 %d행은 Cowork 결과에 없어 그대로 둠.'
                % (n_remain, ', '.join('%s %d' % (r, len(v)) for r, v in remain.items() if v), n_removed,
                   ', '.join('%s %d' % (r, c) for r, c in removed.items() if c), n_remain))
    k = idx(lines, '- 이번 채팅에서 스니펫 기준으로 고친 행:')
    lines[k] = lines[k] + ' (안양대(안양), 평택대, 한신대는 2026-09-29 Cowork가 직접 열람해 확인함)'
    stats['2-2'] = dict(remain=remain, n_remain=n_remain, n_removed=n_removed, removed=removed)

    # ---- 3-1 보류: 순천향대 해제
    h31 = idx(lines, '### 3-1.')
    th, t0, t1 = table_span(lines, h31)
    hit = [i for i in range(t0, t1) if cells(lines[i])[0] == '순천향대학교']
    assert len(hit) == 1
    del lines[hit[0]]
    t1 -= 1
    lines[t1:t1] = ['', '- 순천향대학교는 2026-09-29 Cowork가 입학처 입시결과 메뉴와 학년도별 게시글을 직접 열어 확인해 보류에서 뺐다(1-4장 행 추가).']

    # ---- 3-2 브라우저 직접 확인 필요
    h32 = idx(lines, '### 3-2.')
    h4 = idx(lines, '## 4.')
    n_done = len(applied)
    block = [
        '### 3-2. 브라우저 직접 확인 필요', '',
        '2026-09-29 Cowork 재조사(cowork_20260929_01~15.md)로 3-2장 대학을 처리했고 처리가 끝난 곳은 뺐다. 남은 곳은 아래 3곳이다.', '',
        '| 대학 | 확인할 것 |', '|---|---|',
        '| 아주대학교 | 입학처 사이트(iajou.ac.kr)의 입시결과·정시 모집요강 위치. 대학 홈페이지(www.ajou.ac.kr)의 "학부 입학(입학처)" 링크가 www.iajou.ac.kr로 연결됨(Cowork, 2026-09-29). Cowork는 당시 허용 도메인 밖이라 열지 않았고(보류), iajou.ac.kr은 작업 22(#0929-20)로 허용 도메인에 추가돼 재조사 가능 |',
        '| 계명대학교 | 입학처 사이트(gokmu.ac.kr)의 입시결과 메뉴 위치. 대학 홈페이지(www.kmu.ac.kr)의 "입학 홈페이지" 링크가 www.gokmu.ac.kr로 연결됨(Cowork, 2026-09-29). Cowork는 당시 허용 도메인 밖이라 열지 않았고(보류), gokmu.ac.kr은 작업 22로 허용 도메인에 추가돼 재조사 가능 |',
        '| 신경주대학교 | 재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음). KEDI 홈페이지 www.gu.ac.kr은 Cowork 접속 시 "Service Unavailable"(2026-09-29). sgu.ac.kr은 경상남도교육청 CSV에서 신경대학교(화성)의 홈페이지이고 신경주대의 공식 도메인으로 확인되지 않음(cowork_allowed_domains.md 7장). 공식 페이지에서 입학처로 직접 연결되는 주소를 확인해야 함 |',
        '',
    ]
    lines[h32:h4] = block

    # ---- 4-1 미조사 잔여
    k = idx(lines, '- 미조사 잔여: 용인대 학년도, 중부대(고양) 정시.')
    lines[k] = '- 미조사 잔여: 용인대 학년도, 중부대(고양) 정시, 중부대(금산) 정시 입결·요강(2026-09-29 Cowork 도구 중단으로 조사하지 못함).'

    # ---- 5장 결정 사항
    new_rows = [(rec['name'], name, col2) for rec, sec, name, col2, new in applied if new]
    upd = [1 for rec, sec, name, col2, new in applied if not new]
    k = idx(lines, '34. ')
    new_names = ', '.join('%s(%s)' % (n, c) for _, n, c in new_rows)
    add = [
        '35. Cowork 재조사 결과 01~15(2026-09-29, 파일 15개, 표 %d행)를 `merge_cowork_v5.py`로 v4에 합쳐 v5를 만듦. 기존 행 %d개 갱신, v4 표에 없던 %d개 행을 새로 만듦(%s). 표 값은 스크립트가 결과 파일의 칸을 그대로 옮김.'
        % (len(recs), len(upd), len(new_rows), new_names),
        '36. 표기: 직접 열람 행은 "확인(Cowork 직접 열람, 2026-09-29)". 미확인은 이유를 괄호에 적고, 열지 못하거나 보류한 항목은 이유와 함께 2-1장에 둠. 기존 값과 달라진 URL·학년도·확인상태는 비고(1-1~1-4는 확인상태 칸)의 "변경:"에 적음. 학년도 판단 근거는 결과 파일 문구 그대로.',
        '37. 경상국립대의 옛 경남과기대 도메인(gntech.ac.kr) 자료는 "조사 안 함(통합 전 자료)". 통합된 경남과기대 분이 gnu.ac.kr 파일에 포함되는지는 파일을 열지 않아 미확인.',
        '38. 연세대(미래)의 입시통계분석·입시결과 항목은 유튜브 영상 링크라 "제외(파일 자료 아님)". 통합자료실 1~5페이지에는 입시결과 게시글이 없음(Cowork 직접 열람).',
        '39. 협성대 입결 조회 화면(외부 도메인)은 기존대로 조회형 보류. 입학처 안내 게시글(2024~2026 수시 입시결과 확인 방법 안내)만 확인.',
        '40. 신경주대는 확인상태를 "재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음)"로 두고 3-2장·6장 대기열에 넣음.',
        '41. 아주대·계명대는 Cowork가 허용 도메인 밖이라 열지 않아 보류로 보고함. 작업 22(#0929-20)로 iajou.ac.kr·gokmu.ac.kr을 허용 도메인에 추가했으므로 재조사 대기(3-2장). 아주대는 v4 표에 행이 없고 이번에도 자료가 없어 행을 만들지 않음.',
        '42. 중부대(금산)는 cowork_20260929_15.md에 적힌 그대로 반영: 수시 입결 확인, 정시 입결·요강은 미조사(브라우저 도구 중단). 중부대(고양) 행은 이번에 조사되지 않아 손대지 않음.',
        '43. 순천향대는 Cowork가 입시결과 페이지를 확인해 3-1 보류에서 뺌. 경희대는 Cowork가 서울·국제(용인)를 한 행으로 기록해 1-5 서울 행을 갱신하고 1-6에 국제(용인) 행을 같은 자료로 새로 만듦.',
        '44. 처리가 끝난 대학은 2-2장·3-2장에서 뺐고 6장 대기열을 다시 정리함. 2-2장에서 뺀 행은 Cowork가 직접 열람해 확인 방식이 드러난 행임.',
    ]
    lines[k + 1:k + 1] = add

    # ---- 6장 남은 대기열
    h6 = idx(lines, '## 6.')
    n21 = stats['2-1']['kept'] + stats['2-1']['generated']
    cn = js['cnt']
    grp = js['groups']
    rem_names = ', '.join('%s %d' % (r, len(v)) for r, v in remain.items() if v)
    tail = [
        '## 6. 남은 대기열 한눈에 보기 (v5 기준)', '',
        '| 구분 | 규모 | 내용 |', '|---|---|---|',
        '| 3-2장 재조사 | 3곳 | 아주대학교(iajou.ac.kr 허용 도메인 추가, 재조사 대기), 계명대학교(gokmu.ac.kr 허용 도메인 추가, 재조사 대기), 신경주대학교(재확인 필요: 입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음) |',
        '| 2-1장 남은 미확인 항목 | %d행 | Cowork 처리 대학 중 남은 미확인·보류·일부 항목 %d행(2-1장 하단)과 처리하지 않은 대학 %d행. 이유는 2-1장 |' % (n21, stats['2-1']['generated'], stats['2-1']['kept']),
        '| 2-2장 확인 방식 모름 (이전 채팅 행) | %d행 | %s. 목록은 2-2장 |' % (n_remain, rem_names),
        '| 3-1장 보류 | 1곳 | 가톨릭대학교(IT 학과 소재지 좌표 미확보). 순천향대는 이번에 해제 |',
        '| 미조사 잔여 | 3건 | 용인대 학년도, 중부대(고양) 정시, 중부대(금산) 정시 입결·요강 |',
        '| 정시 모집요강 URL (별도 파일) | 미조사 %d행, 미확인 %d행 | `2027_정시모집요강_URL_누적.md` 기준. 이번에 %d행 반영. 서울·충청·강원 대학은 그 파일에 행이 없음 |' % (cn['미조사'], cn['미확인'], len(js['reflected'])),
        '| 후순위 (전문대학·교육대학·폴리텍) | 106행 | 서울 10, 경기 28, 인천 5, 영남 35, 강원 9, 제주 3, 충청 16. 목록은 4-2장 |',
        '| 호남 | 36행 | 착수하지 않음. KEDI 4년제 목록을 받은 뒤에 시작 |',
        '',
    ]
    lines[h6:] = tail
    return '\n'.join(lines), stats


# ================================================================ v6 (#0929-32)
# 위쪽은 merge_cowork_v5.py 를 그대로 복사한 코드다(v5 병합용, 이번 실행에서는 쓰지 않음).
# 아래 check_counts / update_jeongsi_v6 가 이번 지시(작업 31 사전 검사, 작업 33)를 처리한다.
# 작업 31·32(v6 문서 병합)는 대학 수 검사가 통과해야 진행한다. 검사가 실패하면 병합하지 않는다.
EXPECT_COUNT = {16: 5, 17: 4, 18: 3, 19: 5, 20: 3, 21: 5, 22: 5, 23: 5, 24: 5, 25: 5, 26: 4}   # #0929-49 작업 37 기대값
LIST4 = os.path.join(ROOT, '4yr_list_seoul_chungcheong_gangwon_jeju_honam.md')
REG_ORDER = ['경기', '인천', '영남', '서울', '충청', '강원']

# Cowork 대학 이름 -> (권역, 4년제 목록의 대학명). 캠퍼스 표기는 4년제 목록의 "연결 캠퍼스" 칸을 그대로 쓴다.
NEW6 = {
    '서울기독대학교': ('서울', '서울기독대학교'), '서울대학교': ('서울', '서울대학교'), '서울시립대학교': ('서울', '서울시립대학교'),
    '덕성여자대학교': ('서울', '덕성여자대학교'), '서경대': ('서울', '서경대학교'), '성공회대': ('서울', '성공회대학교'),
    '성신여자대': ('서울', '성신여자대학교'), '세종대': ('서울', '세종대학교'), '숙명여자대': ('서울', '숙명여자대학교'),
    '광운대학교': ('서울', '광운대학교'), '서강대학교': ('서울', '서강대학교'),
    '순천향대학교': ('충청', '순천향대학교'), '충북대': ('충청', '충북대학교'), '국립한밭대': ('충청', '국립한밭대학교'),
    '국립공주대': ('충청', '국립공주대학교'), '국립한국교통대': ('충청', '국립한국교통대학교'), '한국교원대': ('충청', '한국교원대학교'),
    '고려대': ('충청', '고려대학교(세종)'), '홍익대': ('충청', '홍익대학교'), '건국대': ('충청', '건국대학교(글로컬)'),
    '한국기술교육대': ('충청', '한국기술교육대학교'), '한서대': ('충청', '한서대학교'), '중부대': ('충청', '중부대학교'),
    '호서대': ('충청', '호서대학교'), '대전대': ('충청', '대전대학교'), '목원대': ('충청', '목원대학교'), '배재대': ('충청', '배재대학교'),
    '우송대': ('충청', '우송대학교'), '청주대': ('충청', '청주대학교'), '선문대': ('충청', '선문대학교'), '단국대': ('충청', '단국대학교'),
    '상명대': ('충청', '상명대학교'), '건양대': ('충청', '건양대학교'), '서원대': ('충청', '서원대학교'), '세명대': ('충청', '세명대학교'),
    '우석대': ('충청', '우석대학교'), '유원대': ('충청', '유원대학교'),
    '한림대학교': ('강원', '한림대학교'), '상지대학교': ('강원', '상지대학교'), '가톨릭관동대학교': ('강원', '가톨릭관동대학교'),
    '한라대학교': ('강원', '한라대학교'), '연세대학교(미래)': ('강원', '연세대학교(미래)'),
}
# 16~20번 결과를 반영할 기존 행: Cowork 이름 -> (대학명, 캠퍼스) (정시 파일 표의 앞 두 칸)
EXIST6 = {
    '아주대': ('아주대학교', '아주대학교(수원)'),
    '계명대': ('계명대학교', '계명대학교(대구)'),
    '신경주대': ('신경주대학교', '신경주대학교 (본교(제1캠퍼스))'),
    '용인대': ('용인대학교', '용인대학교(용인)'),
}
EXCLUDE6 = {'삼육대학교'}   # 정시 요강 URL 없이 미확인 -> 행을 만들지 않고 보고
STATUS6 = {'선문대': '미확인(요강 파일 링크 없음)', '신경주대': '보류(gu.ac.kr 503)', '용인대': '미확인(학년도 확인 안 됨)',
           '성공회대': '미확인(학년도 확인 안 됨)', '한서대': '미확인(학년도 확인 안 됨)'}
NOFILE = '미기록(Cowork 직접 열람 시 파일 URL을 기록하지 않음)'


def read_cowork6():
    """read_cowork 와 같지만 결과 파일 번호와 조사일(파일 머리말)을 함께 담는다."""
    recs = read_cowork()
    info = {}
    for r in recs:
        if r['file'] not in info:
            t = rd(os.path.join(ROOT, 'cowork_results', r['file']))
            m = re.search(r'^- 조사일:\s*(\d{4}-\d\d-\d\d)', t, re.M)
            assert m, r['file']
            info[r['file']] = m.group(1)
        r['date'] = info[r['file']]
        r['num'] = int(re.search(r'_(\d+)\.md$', r['file']).group(1))
    return recs


def check_counts(recs):
    got = {}
    for r in recs:
        got[r['num']] = got.get(r['num'], 0) + 1
    print('결과 파일별 대학 수 (기대):')
    ok = True
    for n in sorted(EXPECT_COUNT):
        flag = 'OK' if got.get(n) == EXPECT_COUNT[n] else '불일치'
        ok = ok and got.get(n) == EXPECT_COUNT[n]
        print('  %02d.md: %s (기대 %d) %s' % (n, got.get(n), EXPECT_COUNT[n], flag))
    return ok, got


def load_list4():
    t = rd(LIST4).split('\n')
    out = {}
    reg = None
    for l in t:
        m = re.match(r'^## (서울|충청|강원|제주|호남) \(\d+\)', l)
        if m:
            reg = m.group(1)
            continue
        if reg and l.startswith('| ') and not l.startswith('| #') and not l.startswith('|---'):
            c = cells(l)
            out.setdefault(reg, []).append((c[1], c[2]))
    return out


def update_jeongsi_v6(recs):
    raw = rd(JS)
    assert raw.count('\r\n') == raw.count('\n')
    lines = raw.replace('\r\n', '\n').split('\n')
    i0 = lines.index('## 조사 완료 대학')
    hdr = i0 + 2
    hc = cells(lines[hdr])
    assert hc[-2:] == ['상태', '출처'] and len(hc) == 8
    r_idx = []
    j = hdr + 2
    while lines[j].startswith('|'):
        r_idx.append(j)
        j += 1
    rows = [cells(lines[i]) for i in r_idx]
    n_old = len(rows)
    names = [(r[0], r[1]) for r in rows]
    k_inc = names.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names.index(('경남대학교', '경남대학교(마산)'))
    region_old = ['경기' if k < k_inc else ('인천' if k < k_yn else '영남') for k in range(n_old)]

    list4 = load_list4()
    order = {}
    for rg, items in list4.items():
        for k, (nm_, cp) in enumerate(items):
            order[(rg, nm_)] = (k, cp)

    todo_new, updated = [], []
    skipped, seen_new = [], set()
    for rec in recs:
        nm_ = rec['name']
        if nm_ == '중부대' and not rec['campus'].startswith('금산'):
            key = None   # 중부대 고양: 기존 행
        else:
            key = NEW6.get(nm_)
        has_res = not rec['jurl'].strip() in ('-', '', '미조사')
        # 기존 행 갱신: 16~20번 결과만
        target_exist = None
        if rec['num'] >= 16:
            if nm_ in EXIST6:
                target_exist = EXIST6[nm_]
            elif nm_ == '중부대' and rec['campus'].startswith('고양'):
                target_exist = ('중부대학교', '중부대학교 (본교(제2캠퍼스))')
        if target_exist:
            todo_new.append(('exist', rec, target_exist))
            continue
        if key is None:
            continue
        if not has_res:
            skipped.append((nm_, '정시 요강 결과 없음(칸이 "-")'))
            continue
        if rec['name'] in EXCLUDE6:
            skipped.append((nm_, rec['jurl'][:60]))
            continue
        rg, base = key
        if (rg, base) in seen_new:
            continue     # 같은 대학의 뒤 파일 결과가 앞선 결과를 대신하는 일은 없음
        seen_new.add((rg, base))
        todo_new.append(('new', rec, (rg, base)))
    # 같은 대학이 여러 파일에 있으면(중부대 금산: 15는 결과 없음, 20은 결과 있음) 결과 있는 쪽만 남는다

    def build(rec, dname, campus):
        if rec['name'] in STATUS6:
            st = STATUS6[rec['name']]
        else:
            st = '미확인' if rec['jurl'].startswith('미확인') else '확인'
        f2 = '미확인' if (rec['jfile'].startswith('미확인') and st.startswith(('보류', '미확인'))) else NOFILE
        return [dname, campus, f2, rec['jurl'], rec['jfile'], rec['date'], st, 'Cowork 직접 열람']

    new_rows = []
    notes = []
    for kind, rec, tgt in todo_new:
        if kind == 'exist':
            hit = [k for k, r in enumerate(rows) if (r[0], r[1]) == tgt]
            assert len(hit) == 1, tgt
            k = hit[0]
            rows[k] = build(rec, tgt[0], tgt[1])
            updated.append((tgt[0], tgt[1], rows[k][6]))
            continue
        rg, base = tgt
        kk, campus = order[(rg, base)]
        dn = base
        new_rows.append((REG_ORDER.index(rg), kk, rg, build(rec, dn, campus), rec))
    new_rows.sort(key=lambda x: (x[0], x[1]))
    # 조사 비고 후보(특별 상태)
    special = []
    for kind, rec, tgt in todo_new:
        if rec['name'] in STATUS6:
            special.append(rec)
    # 표 다시 쓰기
    for k, r in enumerate(rows):
        lines[r_idx[k]] = row(r)
    add_lines = [row(x[3]) for x in new_rows]
    lines[r_idx[-1] + 1:r_idx[-1] + 1] = add_lines
    rows_all = rows + [x[3] for x in new_rows]
    region_all = region_old + [x[2] for x in new_rows]

    # 조사 비고
    n0 = lines.index('## 조사 비고')
    nh = n0 + 2
    q = nh + 2
    nr = []
    while lines[q].startswith('|'):
        nr.append(q)
        q += 1
    notes_map = {cells(lines[x])[0]: x for x in nr}
    add_notes = []
    for nm_ in ('아주대학교', '계명대학교'):
        c = cells(lines[notes_map[nm_]])
        c[1] += ' ※ 2026-09-30 Cowork 반영(cowork_20260929_19.md)으로 위 "미조사 유지"는 지난 상태. 정시 요강 확인'
        lines[notes_map[nm_]] = row(c)
    c = cells(lines[notes_map['신경주대학교']])
    c[1] += ' ※ 2026-09-30 Cowork: 보류(gu.ac.kr 503). 위 "재확인 필요(sgu.ac.kr …)" 표시는 유지'
    lines[notes_map['신경주대학교']] = row(c)
    for rec in special:
        nm_ = rec['name']
        if nm_ == '신경주대':
            continue
        base = EXIST6.get(nm_, (None,))[0] or NEW6[nm_][1]
        add_notes.append(row([base, '정시 요강 ' + STATUS6[nm_] + ' ※ Cowork 비고: ' + rec['note']]))
    add_notes.append(row(['중부대학교', '고양·금산 입학처 공유(같은 정시 요강 URL, cowork_20260929_20.md). 표에는 경기(고양) 행과 충청(금산) 행 2개']))
    lines[q:q] = add_notes

    # 미확인·미조사·보류 목록 다시 만들기
    def st_now(cs):
        if cs[6] != '-':
            return '보류' if cs[6].startswith('보류') else ('미확인' if cs[6].startswith('미확인') else '확인')
        return jstate(cs[:6])
    groups = {s: {rg: [] for rg in REG_ORDER} for s in ('미조사', '미확인', '보류')}
    for k, cs in enumerate(rows_all):
        s = st_now(cs)
        if s in groups:
            groups[s][region_all[k]].append('- %s (%s)' % (cs[0], cs[1]))
    cnt = {s: sum(len(v) for v in g.values()) for s, g in groups.items()}
    m0 = lines.index('## 미확인 대학 목록')
    tail = ['## 미확인 대학 목록', '',
            '정시 모집요강 URL을 미확인으로 둔 대학입니다. (상태 칸이 "미확인…"이거나, 상태 칸이 "-"이고 기존 칸에 "미확인"이 있는 행)', '']
    for rg in REG_ORDER:
        tail += ['### ' + rg, ''] + (groups['미확인'][rg] or ['- 없음']) + ['']
    tail += ['## 보류 대학 목록', '', '상태 칸이 "보류…"인 행입니다.', '']
    tail += sum(([*groups['보류'][rg]] for rg in REG_ORDER), []) or ['- 없음']
    tail += ['']
    tail += ['## 미조사 대학 목록', '', '### 남은 대기열', '',
             '- 미조사 %d개: 아래 권역별 목록(%s)의 대학은 아직 정시 모집요강을 확인하지 않았습니다. (2026-09-30 Cowork 반영 후)'
             % (cnt['미조사'], ', '.join('%s %d' % (rg, len(groups['미조사'][rg])) for rg in REG_ORDER)), '']
    for rg in REG_ORDER:
        tail += ['### ' + rg, ''] + (groups['미조사'][rg] or ['- 없음']) + ['']
    lines = lines[:m0] + tail
    while lines and lines[-1] == '':
        lines.pop()
    text = '\n'.join(lines) + '\n'
    old = '서울·충청·강원 결과는 이 파일에 행이 없어 반영하지 않았습니다.'
    assert old in text
    text = text.replace(old, '서울·충청·강원 결과는 당시 이 파일에 행이 없어 반영하지 않았습니다(2026-09-30에 아래 안내대로 추가).')
    marker = '> 관리: 2026-09-28부터 Claude Code가 관리'
    k = text.index(marker)
    text = text[:k] + ('> 2026-09-30(#0929-32 작업 33): cowork_results 01~20번 중 정시 모집요강 결과가 있는 서울·충청·강원 대학 %d행을 표 끝에 추가하고(대학명·캠퍼스 표기는 `4yr_list_seoul_chungcheong_gangwon_jeju_honam.md`), 16~20번 결과를 기존 %d행에 반영했습니다. 확인일은 해당 결과 파일의 조사일입니다.\n>\n'
                       % (len(new_rows), len(updated))) + text[k:]
    text = text.replace('\n', '\r\n')
    stats = dict(added=[(x[2], x[3][0], x[3][1], x[3][6], x[3][5]) for x in new_rows], updated=updated, cnt=cnt,
                 groups=groups, skipped=skipped)
    return text, stats


# ================================================================ #0929-49 (작업 37~40)
# 위쪽은 v5·v6(#0929-32) 코드다. 아래가 이번 지시(16~26번 병합, 2-1장 정리, 정시 파일 반영)를 처리한다.
def conf(rec):
    return '확인(Cowork 직접 열람, %s)' % rec.get('date', DATE)


def conv_status6(rec):
    n = rec['name']
    C = conf(rec)
    st = rec['status'].strip()
    if n == '중부대':
        if rec['campus'].startswith('금산'):
            mm = re.match(r'^확인\((.*)\)$', st)
            return '수시: 확인(Cowork 직접 열람, 2026-09-29) / 정시: ' + C + ('. ' + mm.group(1) if mm else '')
        return '정시: ' + C
    if n == '용인대':
        return C + '. 입결 목록만 확인(게시글 미열람)'
    parts = [p.strip() for p in st.split(' / ')]
    main_ = next((p for p in parts if p.startswith('입결')), parts[0])
    m = re.sub(r'^입결\s*', '', main_)
    if m == '확인':
        return C
    mm = re.match(r'^확인\((.*)\)$', m)
    if mm:
        return C + '. ' + mm.group(1)
    raise ValueError('처리하지 못한 상태: %s / %s' % (n, st))


conv_status = conv_status6   # apply_rec_7 / apply_rec_8 이 이 이름을 쓴다

# 16~26번 중 입결 칸이 채워진 Cowork 행 -> v5 표의 행 (섹션, 대학명, 2열, 새 행 여부)
MAP6 = {
    '호서대': ('1-4', '호서대학교', '충청'), '대전대': ('1-4', '대전대학교', '충청'), '목원대': ('1-4', '목원대학교', '충청'),
    '배재대': ('1-4', '배재대학교', '충청'), '우송대': ('1-4', '우송대학교', '충청'), '청주대': ('1-4', '청주대학교', '충청'),
    '선문대': ('1-4', '선문대학교', '충청'), '단국대': ('1-4', '단국대학교(천안)', '충청'), '상명대': ('1-4', '상명대학교(천안)', '충청'),
    '건양대': ('1-4', '건양대학교', '충청'), '서원대': ('1-4', '서원대학교', '충청'), '세명대': ('1-4', '세명대학교', '충청'),
    '백석대': ('1-4', '백석대학교', '충청'), '극동대': ('1-4', '극동대학교', '충청'), '나사렛대': ('1-4', '나사렛대학교', '충청'),
    '우석대': ('1-4', '우석대학교(진천)', '충청'), '유원대': ('1-4', '유원대학교', '충청'),
    '아주대': ('1-6', '아주대학교', '수원', True), '계명대': ('1-8', '계명대학교', '대구'),
    '용인대': ('1-6', '용인대학교', '용인'),
}
MAP6_JUNGBU = {'고양': ('1-6', '중부대학교', '고양'), '금산': ('1-4', '중부대학교(금산)', '충청')}
NOTE_EXTRA6 = {
    '유원대': ' ※ 성적산출 페이지(ratio.u1.ac.kr): 열지 않음(허용 도메인 밖)',
    '선문대': ' ※ 정시 요강: 미확인(요강 파일 링크 없음, 표지 이미지 파일명만 확인)',
}
CANON = lambda n: re.sub(r'학교$', '', n)


def merge_doc6(recs):
    lines = rd(V5).split('\n')
    heads = split_sections(lines)
    tables = {}
    for sec, st in heads.items():
        hdr, rws = find_table_rows(lines, st)
        tables[sec] = dict(hdr=hdr, rows=rws, ncol=len(cells(lines[hdr])))

    def find_row(sec, name, col2):
        return [i for i in tables[sec]['rows'] if cells(lines[i])[0] == name and cells(lines[i])[1] == col2]

    replaced, inserts, applied = {}, {}, []
    sinkyung = [r for r in recs if r['name'] == '신경주대']
    for rec in recs:
        if rec['num'] < 16 or rec['url'].startswith('미조사') or rec['name'] == '신경주대':
            continue
        nm = rec['name']
        tgt = MAP6_JUNGBU[rec['campus'][:2]] if nm == '중부대' else MAP6[nm]
        sec, name, col2 = tgt[:3]
        new = len(tgt) > 3 and tgt[3]
        extra = NOTE_EXTRA6.get(nm, '')
        if new:
            assert not find_row(sec, name, col2), (sec, name)
            cs = apply_rec_8(None, rec, campus_new=col2, note_extra=extra)
            inserts.setdefault(sec, []).append(row(cs))
            applied.append((rec, sec, name, col2, True))
            continue
        hit = find_row(sec, name, col2)
        assert len(hit) == 1, (sec, name, col2, hit)
        i = hit[0]
        old = cells(lines[i])
        if tables[sec]['ncol'] == 7:
            replaced[i] = row(apply_rec_7(old, rec, extra))
        else:
            replaced[i] = row(apply_rec_8(old, rec, note_extra=extra))
        applied.append((rec, sec, name, col2, False))
    # 신경주대: 기존 재확인 표시 유지 + 보류 문구
    hit = find_row('1-8', '신경주대학교', '경주')
    assert len(hit) == 1
    old = cells(lines[hit[0]])
    n19 = next(r for r in sinkyung if r['num'] == 19)
    n21 = next(r for r in sinkyung if r['num'] == 21)
    newc = list(old)
    newc[6] = DATE30
    newc[7] = ('보류(gu.ac.kr 503, 2026-09-29·30 두 번). 재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음). '
               '※ 이전 기록: ' + old[7] + ' ※ 2026-09-30 Cowork 비고(19번): ' + n19['note'] + ' ※ 2026-09-30 Cowork 비고(21번): ' + n21['note'])
    replaced[hit[0]] = row(newc)
    applied.append((n19, '1-8', '신경주대학교', '경주', False))
    # 비고에만 덧붙이는 행
    for sec, name, col2, txt in (
            ('1-6', '국립한국교통대학교', '의왕', ' ※ 2026-09-30 Cowork 22번(정시 요강만 조사): 의왕 캠퍼스 모집단위 포함 여부 미확인'),
            ('1-7', '청운대학교', '인천', ' ※ 정시 요강: 미확인(2027 요강 미게시로 보임, 2026-09-30)')):
        h = find_row(sec, name, col2)
        assert len(h) == 1, (sec, name)
        c = cells(replaced.get(h[0], lines[h[0]]))
        c[7] = c[7] + txt
        replaced[h[0]] = row(c)
    for i, s_ in replaced.items():
        lines[i] = s_
    for sec in sorted(inserts, key=lambda s_: -tables[s_]['rows'][-1]):
        last = tables[sec]['rows'][-1]
        lines[last + 1:last + 1] = inserts[sec]
    return lines, applied


DATE30 = '2026-09-30'

KEEP_TOK = re.compile(r'전체|게시글 URL|URL 미확보|위치 미확보|미확보|미발견|메뉴 미확인|수시만 확인|입결 파일')
EXCL_TOK = re.compile(r'미열람|공유|재사용|링크만 확인|게시글 단위 미확인|링크가 JS')


def keep_2_1(item, reason):
    """입결 위치나 정시 모집요강 위치 자체를 찾지 못한 행인가."""
    if item in ('입결 전체', '입결(제외·보류 항목)', '일부 항목(확인상태·비고 참조)'):     # v5에서 Cowork 결과로 만든 행
        return item.startswith('입결 전체') or reason.startswith('제외(파일 자료 아님)')
    if EXCL_TOK.search(item + ' ' + reason):
        return False
    it = re.sub(r'첨부 URL|파일 URL', '', item)
    return bool(KEEP_TOK.search(it) or KEEP_TOK.search(reason))


REG6 = {'청운대(인천)': '인천', '대구대': '영남', '신경주대': '영남'}


def finish_v6(lines, recs, applied):
    stats = {}
    old_t = '2026-09-29 기준, 누적 5차 정리본, Cowork 브라우저 재조사 반영'
    assert old_t in lines[0]
    lines[0] = lines[0].replace(old_t, '2026-09-30 기준, 누적 6차 정리본, Cowork 브라우저 재조사 반영')
    k = idx(lines, '- 2027학년도 정시 모집요강 URL·파일명은 이 문서가 아니라')
    lines[k + 1:k + 1] = [
        '- 2026-09-30 Cowork 재조사(`cowork_results/cowork_20260929_16~20.md`, `cowork_20260930_21~26.md`)는 확인일을 결과 파일의 조사일(2026-09-30)로 적었다. 22~26번은 정시 모집요강 위치만 조사해 입결 칸이 "미조사"이므로 v5의 기존 값을 덮지 않았다(SPEC 13번).',
        '- 2-1장에는 입결 위치나 정시 모집요강 위치 자체를 찾지 못한 행만 둔다(SPEC 7번). 파일명·첨부 형식·뷰어 미로딩·캠퍼스 분리 여부처럼 위치는 찾은 경우는 해당 행의 비고에만 남겼다.',
    ]

    # ---- 2-1장
    h2 = idx(lines, '### 2-1.')
    th, t0, t1 = table_span(lines, h2)
    old_rows = [(cells(lines[i]), lines[i]) for i in range(t0, t1)]
    proc = set()
    for rec, sec, name, col2, new in applied:
        proc.add(name)
        proc.add('%s(%s)' % (name, col2))
    proc |= {'신경주대학교', '계명대학교', '용인대학교', '중부대학교(고양)'}
    kept, removed_rule, removed_proc = [], [], []
    for c, ln in old_rows:
        toks = c[0].split('·')
        if all(t in proc for t in toks):
            removed_proc.append(c[0])
            continue
        if keep_2_1(c[2], c[3]):
            kept.append(ln)
        else:
            removed_rule.append(c[0])
    gen = []
    # 요강 위치를 찾지 못한 대학(가장 나중 결과 기준)과 보류 대학
    latest = {}
    for rec in recs:
        latest[CANON(rec['name'])] = rec
    for key, rec in latest.items():
        st = rec['status']
        if st.startswith('보류'):
            gen.append(row(['신경주대학교', '영남', '입결·정시 요강 전체',
                            '보류(gu.ac.kr 503, 2026-09-29·30 두 번). 재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음)']))
        elif st.startswith('미확인') or re.search(r'요강 미확인', st):
            nm = rec['name']
            reason = '미확인(2027 요강 미게시로 보임, 2026-09-30)' if nm == '청운대(인천)' else rec['jurl']
            gen.append(row([nm if nm != '대구대' else '대구대학교', REG6.get(nm, '영남'), '정시 모집요강', reason]))
    lines[t0:t1] = kept + gen
    stats['2-1'] = dict(before=len(old_rows), removed_proc=len(removed_proc), removed_rule=len(removed_rule),
                        kept=len(kept), generated=len(gen), removed_rule_names=removed_rule, kept_names=[cells(k)[0] for k in kept],
                        gen_names=[cells(g)[0] for g in gen])
    stats['2-1']['after'] = len(kept) + len(gen)
    # 2-1 머리말 설명 (표 바로 앞)
    lines.insert(h2 + 1, '')
    lines.insert(h2 + 2, '기준(SPEC 7번): 입결 위치나 정시 모집요강 위치 자체를 찾지 못한 행만 둔다. 파일명 미확인·첨부 형식 미확인·뷰어 미로딩·캠퍼스 분리 여부 미확인, 검색·목록 미열람(미조사)은 위치를 찾았거나 시도하지 않은 경우라 뺐다. 이런 내용은 각 행의 비고에 남아 있다.')

    # ---- 2-2장: 충청 17행 모두 처리
    h22 = idx(lines, '### 2-2.')
    k = idx(lines, '- 1-4. 충청 (17행):', h22)
    del lines[k]
    k = idx(lines, '- 합계 17행', h22)
    lines[k] = '- 합계 0행. 2026-09-30 Cowork 16~21번이 충청 17행(호서대, 대전대, 목원대, 배재대, 우송대, 청주대, 선문대, 단국대(천안), 상명대(천안), 백석대, 건양대, 서원대, 세명대, 극동대, 나사렛대, 우석대(진천), 유원대)을 모두 직접 열람해 확인 방식이 드러났으므로 2-2장을 비웠다.'

    # ---- 3-2장
    h32 = idx(lines, '### 3-2.')
    h4 = idx(lines, '## 4.')
    block = [
        '### 3-2. 브라우저 직접 확인 필요', '',
        '2026-09-30 Cowork가 아주대(cowork_20260929_19.md)와 계명대(같은 파일)를 직접 열람해 처리했고(각각 1-6·1-8장 행), 두 대학은 3-2장에서 뺐다. 남은 곳은 아래 1곳이다.', '',
        '| 대학 | 확인할 것 |', '|---|---|',
        '| 신경주대학교 | 보류(gu.ac.kr 503, 2026-09-29·30 두 번). www.gu.ac.kr·gu.ac.kr 모두 "Service Unavailable"(503으로 판단). 재확인 필요(입시자료실 주소 sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음): sgu.ac.kr은 경상남도교육청 CSV에서 신경대학교(화성)의 홈페이지이고 신경주대의 공식 도메인으로 확인되지 않음(cowork_allowed_domains.md 7장). gu.ac.kr이 복구되면 재조사 |',
        '',
    ]
    lines[h32:h4] = block

    # ---- 4-1장
    k = idx(lines, '- 미조사 잔여:')
    lines[k] = '- 미조사 잔여: 없음(용인대 학년도는 입결 목록 제목까지 확인, 중부대 정시는 2026-09-30 Cowork 20번으로 해소). 다만 22~26번 대상 20곳(용인대 제외 시)은 입결 칸이 미조사라 입결 재조사는 v5 기존 값 그대로다.'

    # ---- 5장
    k = idx(lines, '44. ')
    n_up = sum(1 for a in applied if not a[4])
    n_new = sum(1 for a in applied if a[4])
    add = [
        '45. Cowork 결과 16~26번(파일 11개, 표 %d행)을 `merge_cowork_v6.py`로 v5에 합쳐 v6를 만듦. 입결 칸이 채워진 16~21번의 행을 반영(기존 행 갱신 %d, 새 행 %d(아주대)). 22~26번(정시 요강만 조사, 입결 칸 "미조사")은 v5 값을 덮지 않음.' % (len(recs), n_up, n_new),
        '46. 결과 파일의 "미조사" 값은 기존 값을 덮지 않는다(SPEC 13번). 기존 값이 없고 결과만 "미조사"인 대학(v5 표에 입결 행이 없는 22~26번 대학)은 행을 새로 만들지 않고 정시 파일에서 관리.',
        '47. 신경주대는 확인상태 "보류(gu.ac.kr 503, 2026-09-29·30 두 번)"로 두고 기존 "재확인 필요(sgu.ac.kr …)" 표시를 유지. 3-2장 남은 유일한 대학.',
        '48. 정시 요강 표기: 선문대 "미확인(요강 파일 링크 없음, 표지 이미지 파일명만 확인)", 청운대(인천) "미확인(2027 요강 미게시로 보임, 2026-09-30)". 국립한국교통대(의왕) 비고에 "의왕 캠퍼스 모집단위 포함 여부 미확인", 유원대 비고에 성적산출 페이지(ratio.u1.ac.kr) "열지 않음(허용 도메인 밖)".',
        '49. 아주대·계명대는 Cowork가 허용 도메인 추가(작업 22) 뒤 직접 열람해 확인. 아주대는 v5 표에 행이 없어 1-6장에 새 행으로 만듦.',
        '50. 2-1장 정리 기준(SPEC 7번): 입결 위치나 정시 모집요강 위치 자체를 찾지 못한 행만 둔다. 뺀 행 %d(처리 완료 %d, 위치는 찾음·미열람 %d), 남은 행 %d.'
        % (stats['2-1']['removed_proc'] + stats['2-1']['removed_rule'], stats['2-1']['removed_proc'], stats['2-1']['removed_rule'], stats['2-1']['after']),
    ]
    lines[k + 1:k + 1] = add
    return lines, stats, n_up, n_new


def sixth(lines, stats, js):
    h6 = idx(lines, '## 6.')
    a = stats['2-1']
    grp = js['groups']
    yg = ', '.join('%s %d' % (rg, len(grp['미조사'][rg])) for rg in REG_ORDER)
    tail = [
        '## 6. 남은 대기열 한눈에 보기 (v6 기준)', '',
        '| 구분 | 규모 | 내용 |', '|---|---|---|',
        '| 3-2장 재조사 | 1곳 | 신경주대학교(보류: gu.ac.kr 503, 2026-09-29·30 두 번. 재확인 필요: sgu.ac.kr이 신경대학교 도메인과 겹칠 수 있음) |',
        '| 2-1장 (입결·정시 요강 위치를 찾지 못한 행) | %d행 | %s |' % (a['after'], ', '.join(a['kept_names'] + a['gen_names'])),
        '| 2-2장 확인 방식 모름 (이전 채팅 행) | 0행 | 충청 17행 모두 2026-09-30 Cowork로 처리 |',
        '| 3-1장 보류 | 1곳 | 가톨릭대학교(IT 학과 소재지 좌표 미확보. 정시 요강은 2026-09-30 Cowork 22번으로 확인) |',
        '| 미조사 잔여 | 0건 | 용인대·중부대 항목 해소 |',
        '| 정시 모집요강 URL (별도 파일) | 미조사 %d행, 미확인 %d행, 보류 %d행 | 미조사 권역별: %s. `2027_정시모집요강_URL_누적.md` 기준 |' % (js['cnt']['미조사'], js['cnt']['미확인'], js['cnt']['보류'], yg),
        '| 후순위 (전문대학·교육대학·폴리텍) | 106행 | 서울 10, 경기 28, 인천 5, 영남 35, 강원 9, 제주 3, 충청 16. 목록은 4-2장 |',
        '| 호남 | 36행 | 착수하지 않음. KEDI 4년제 목록을 받은 뒤에 시작 |',
        '',
    ]
    lines[h6:] = tail
    return lines


# ---------------------------------------------------------------- 정시 파일 (작업 40)
NEW6.update({'백석대': ('충청', '백석대학교'), '극동대': ('충청', '극동대학교'), '나사렛대': ('충청', '나사렛대학교'), '삼육대': ('서울', '삼육대학교')})
EX40 = {
    '신경주대': ('신경주대학교', '신경주대학교 (본교(제1캠퍼스))'), '용인대': ('용인대학교', '용인대학교(용인)'),
    '가톨릭대': ('가톨릭대학교', '가톨릭대학교 (본교(제1캠퍼스))'), '강남대': ('강남대학교', '강남대학교(용인)'),
    '경동대': ('경동대학교', '경동대학교 (본교(제4캠퍼스))'), '국립한국교통대(의왕)': ('국립한국교통대학교', '국립한국교통대학교 (본교(제3캠퍼스))'),
    '대진대': ('대진대학교', '대진대학교(포천)'), '명지대': ('명지대학교', '명지대학교 (본교(제1캠퍼스))'),
    '성결대': ('성결대학교', '성결대학교(안양)'), '성균관대': ('성균관대학교', '성균관대학교 (본교(제2캠퍼스))'),
    '수원대': ('수원대학교', '수원대학교(수원)'), '예원예술대': ('예원예술대학교', '예원예술대학교 (본교(제2캠퍼스))'),
    '중앙대(안성)': ('중앙대학교', '중앙대학교(안성)'), '한국외국어대(글로벌)': ('한국외국어대학교', '한국외국어대학교 (본교(제2캠퍼스))'),
    '한세대': ('한세대학교', '한세대학교(군포)'), '한양대(ERICA)': ('한양대학교(ERICA)', '한양대학교(에리카)'),
    '연세대(송도)': ('연세대학교', '연세대학교 (본교(제2캠퍼스))'), '청운대(인천)': ('청운대학교', '청운대학교 (본교(제2캠퍼스))'),
    '국립금오공과대': ('국립금오공과대학교', '국립금오공과대학교 (본교(제1캠퍼스))'), '국립창원대': ('국립창원대학교', '국립창원대학교 (본교(제1캠퍼스))'),
    '대구한의대': ('대구한의대학교', '대구한의대학교(경산)'), '동국대(WISE)': ('동국대학교(WISE)', '동국대학교(경주)'),
    '동명대': ('동명대학교', '동명대학교(부산)'), '동아대': ('동아대학교', '동아대학교(부산)'), '동의대': ('동의대학교', '동의대학교(부산)'),
}
STATUS40 = {'청운대(인천)': '미확인(2027 요강 미게시로 보임)', '신경주대': '보류(gu.ac.kr 503)'}


def update_jeongsi_v7(recs):
    raw = rd(JS)
    assert raw.count('\r\n') == raw.count('\n')
    lines = raw.replace('\r\n', '\n').split('\n')
    i0 = lines.index('## 조사 완료 대학')
    hdr = i0 + 2
    assert len(cells(lines[hdr])) == 8
    r_idx = []
    j = hdr + 2
    while lines[j].startswith('|'):
        r_idx.append(j)
        j += 1
    rows = [cells(lines[i]) for i in r_idx]
    list4 = load_list4()
    lkey = {}
    for rg, items in list4.items():
        if rg in ('서울', '충청', '강원'):
            for k, (nm_, cp) in enumerate(items):
                lkey[(nm_, cp)] = (rg, k)
    base = [r for r in rows if (r[0], r[1]) not in lkey]      # 경기·인천·영남 (기존 순서 유지)
    outer = [r for r in rows if (r[0], r[1]) in lkey]         # 서울·충청·강원
    assert len(base) + len(outer) == len(rows) and len(base) == 79, (len(base), len(outer))
    names_b = [(r[0], r[1]) for r in base]
    k_inc = names_b.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names_b.index(('경남대학교', '경남대학교(마산)'))
    reg_base = ['경기' if k < k_inc else ('인천' if k < k_yn else '영남') for k in range(len(base))]

    def build(rec, dname, campus):
        st = STATUS40.get(rec['name']) or ('미확인' if rec['jurl'].startswith('미확인') else '확인')
        f2 = '미확인' if st.startswith(('보류', '미확인')) else NOFILE
        return [dname, campus, f2, rec['jurl'], rec['jfile'], rec['date'], st, 'Cowork 직접 열람']

    updated, added = [], []
    for rec in recs:
        if rec['num'] < 21:
            continue
        nm_ = rec['name']
        if nm_ in EX40:
            tgt = EX40[nm_]
            hit = [k for k, r in enumerate(base) if (r[0], r[1]) == tgt]
            assert len(hit) == 1, tgt
            base[hit[0]] = build(rec, tgt[0], tgt[1])
            updated.append((tgt[0], tgt[1], base[hit[0]][6]))
        elif nm_ in NEW6:
            rg, bn = NEW6[nm_]
            campus = next(cp for (n2, cp) in list4[rg] if n2 == bn)
            if (bn, campus) in [(r[0], r[1]) for r in outer]:
                raise AssertionError(('이미 있음', bn))
            outer.append(build(rec, bn, campus))
            added.append((rg, bn, campus, outer[-1][6]))
        else:
            raise KeyError(nm_)
    # 정시 파일에 없는 서울·충청·강원 조사 대상: 미조사 행 추가
    have = {(r[0], r[1]) for r in outer}
    unres = []
    for rg in ('서울', '충청', '강원'):
        for nm_, cp in list4[rg]:
            if (nm_, cp) not in have:
                outer.append([nm_, cp, '미조사', '미조사', '미조사', '-', '-', '-'])
                unres.append((rg, nm_, cp))
    outer.sort(key=lambda r: (REG_ORDER.index(lkey[(r[0], r[1])][0]), lkey[(r[0], r[1])][1]))
    reg_outer = [lkey[(r[0], r[1])][0] for r in outer]
    rows_all = base + outer
    region_all = reg_base + reg_outer
    lines[r_idx[0]:r_idx[-1] + 1] = [row(r) for r in rows_all]
    # 조사 비고
    n0 = lines.index('## 조사 비고')
    nh = n0 + 2
    q = nh + 2
    nr = []
    while lines[q].startswith('|'):
        nr.append(q)
        q += 1
    nmap = {cells(lines[x])[0]: x for x in nr}
    for nm_, txt in (('신경주대학교', ' ※ 2026-09-30 Cowork 21번: 보류(gu.ac.kr 503) 재확인(같은 503). sgu.ac.kr 재확인 필요 표시 유지'),
                     ('용인대학교', ' ※ 2026-09-30 Cowork 22번으로 요강 학년도 확인(상태 확인으로 갱신)')):
        c = cells(lines[nmap[nm_]])
        c[1] += txt
        lines[nmap[nm_]] = row(c)
    new_notes = []
    for rec in recs:
        if rec['name'] == '국립한국교통대(의왕)':
            new_notes.append(row(['국립한국교통대학교(의왕)', '정시 요강 확인. ※ Cowork 비고: ' + rec['note']]))
        if rec['name'] == '청운대(인천)':
            new_notes.append(row(['청운대학교', '정시 요강 ' + STATUS40[rec['name']] + ' ※ Cowork 비고: ' + rec['note']]))
    lines[q:q] = new_notes
    # 목록 다시 만들기
    def st_now(cs):
        if cs[6] != '-':
            return '보류' if cs[6].startswith('보류') else ('미확인' if cs[6].startswith('미확인') else '확인')
        return jstate(cs[:6])
    groups = {s_: {rg: [] for rg in REG_ORDER} for s_ in ('미조사', '미확인', '보류')}
    for k, cs in enumerate(rows_all):
        s_ = st_now(cs)
        if s_ in groups:
            groups[s_][region_all[k]].append('- %s (%s)' % (cs[0], cs[1]))
    cnt = {s_: sum(len(v) for v in g.values()) for s_, g in groups.items()}
    m0 = lines.index('## 미확인 대학 목록')
    tail = ['## 미확인 대학 목록', '',
            '정시 모집요강 URL을 미확인으로 둔 대학입니다. (상태 칸이 "미확인…"이거나, 상태 칸이 "-"이고 기존 칸에 "미확인"이 있는 행)', '']
    for rg in REG_ORDER:
        tail += ['### ' + rg, ''] + (groups['미확인'][rg] or ['- 없음']) + ['']
    tail += ['## 보류 대학 목록', '', '상태 칸이 "보류…"인 행입니다.', '']
    tail += sum(([*groups['보류'][rg]] for rg in REG_ORDER), []) or ['- 없음']
    tail += ['']
    tail += ['## 미조사 대학 목록', '', '### 남은 대기열', '',
             '- 미조사 %d개: 아래 권역별 목록(%s)의 대학은 아직 정시 모집요강을 확인하지 않았습니다. (2026-09-30 Cowork 21~26번 반영 후)'
             % (cnt['미조사'], ', '.join('%s %d' % (rg, len(groups['미조사'][rg])) for rg in REG_ORDER)), '']
    for rg in REG_ORDER:
        tail += ['### ' + rg, ''] + (groups['미조사'][rg] or ['- 없음']) + ['']
    lines = lines[:m0] + tail
    while lines and lines[-1] == '':
        lines.pop()
    text = '\n'.join(lines) + '\n'
    marker = '> 관리: 2026-09-28부터 Claude Code가 관리'
    k = text.index(marker)
    text = text[:k] + ('> 2026-09-30(#0929-49 작업 40): cowork_results 21~26번을 반영했습니다(기존 %d행 갱신, 새 행 %d개). 또한 university_master_list_v2.json 조사 대상 중 서울·충청·강원 4년제인데 이 파일에 행이 없던 %d개 대학을 상태 "-"의 미조사 행으로 추가했고, 서울·충청·강원 행은 `4yr_list_seoul_chungcheong_gangwon_jeju_honam.md` 순서로 정렬했습니다.\n>\n'
                       % (len(updated), len(added), len(unres))) + text[k:]
    text = text.replace('\n', '\r\n')
    return text, dict(updated=updated, added=added, unres=unres, cnt=cnt, groups=groups, n_rows=len(rows_all))


def master_check():
    """4년제 목록의 서울·충청·강원 대학이 master 조사 대상(byRegion)에 모두 있는지 (읽기 전용)"""
    d = json.load(open(os.path.join(ROOT, 'university_master_list_v2.json'), encoding='utf-8'))
    list4 = load_list4()
    miss = []
    for rg in ('서울', '충청', '강원'):
        names = {r['대학명'] for r in d['byRegion'][rg] if isinstance(r, dict)}
        for nm_, cp in list4[rg]:
            if nm_ not in names:
                miss.append((rg, nm_))
    extra = {}
    for rg in ('서울', '충청', '강원'):
        l4 = {n for n, _ in list4[rg]}
        extra[rg] = sorted(r['대학명'] for r in d['byRegion'][rg] if isinstance(r, dict) and r['대학명'] not in l4)
    return miss, extra


if __name__ == '__main__':
    recs = read_cowork6()
    print('Cowork 결과 행:', len(recs))
    ok, got = check_counts(recs)
    if not ok:
        print('대학 수가 기대와 달라 병합하지 않음')
        raise SystemExit(1)
    lines, applied = merge_doc6(recs)
    text_js, js = update_jeongsi_v7(recs)
    lines, st, n_up, n_new = finish_v6(lines, recs, applied)
    lines = sixth(lines, st, js)
    wr(V6, '\n'.join(lines))
    wr(JS, text_js)
    miss, extra = master_check()
    print('입결 병합: 갱신 %d, 새 행 %d' % (n_up, n_new))
    print('2-1장:', {k: v for k, v in st['2-1'].items() if k not in ('removed_rule_names', 'kept_names', 'gen_names')})
    print('2-1 남은 행:', st['2-1']['kept_names'], st['2-1']['gen_names'])
    print('2-1 규칙으로 뺀 행:', st['2-1']['removed_rule_names'])
    print('정시: 갱신 %d, Cowork 새 행 %d, 미조사 추가 %d, 표 행수 %d' % (len(js['updated']), len(js['added']), len(js['unres']), js['n_rows']))
    print('정시 남은:', js['cnt'])
    print('master 대조 - 4년제 목록에만 있음:', miss)
    print('master 조사 대상 중 4년제 목록에 없는 서울·충청·강원:', {k: len(v) for k, v in extra.items()})
