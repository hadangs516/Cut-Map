"""#1005-11 작업 73·74 (merge_cowork_v8.py·merge_cowork_v9.py 의 함수를 가져다 쓴다).

- 작업 73: v8 1-9장·1-10장 호남(과 서영대 파주) 행 36행의 비고를 "상태 값 + 원문: cowork_results NN번" 형식으로 바꾼다.
           상태 값 외의 설명 문장은 넣지 않는다. 상태 값(확인, 미확인, 미공개로 보임, 보류)은 바꾸지 않는다.
- 작업 74: v8 과 2027_정시모집요강_URL_누적.md 의 국립순천대 상태를 "보류(사이트 접속 실패)"로 바꾸고, v8 6장 대기열 숫자를 다시 계산한다.
"""
import re

import merge_cowork_v8 as m
import merge_cowork_v9 as m9

SUNCHON = '보류(사이트 접속 실패)'
V8 = m.V8
JS = m.JS


def shorten(lines):
    """작업 73. 반환: 바뀐 행 수"""
    n = 0
    for sec in ('### 1-9.', '### 1-10.'):
        i = m.idx(lines, sec)
        th, t0, t1 = m.table_span(lines, i)
        for k in range(t0, t1):
            c = m.cells(lines[k])
            mm = re.match(r'^(.+?Cowork 직접 열람, \d{4}-\d\d-\d\d\))', c[7])
            nn = re.search(r'원문: cowork_results ([\d·]+)번$', c[7])
            assert mm and nn, (c[0], c[7][:80])
            c[7] = '%s 원문: cowork_results %s번' % (mm.group(1), nn.group(1))
            lines[k] = m.row(c)
            n += 1
    return n


def sunchon_doc(lines):
    """작업 74 (v8 문서). 1-9장 국립순천대 행과 3-2장 행"""
    i = m.idx(lines, '### 1-9.')
    th, t0, t1 = m.table_span(lines, i)
    hit = [k for k in range(t0, t1) if m.cells(lines[k])[0] == '국립순천대학교']
    assert len(hit) == 1
    c = m.cells(lines[hit[0]])
    nn = re.search(r'원문: cowork_results ([\d·]+)번$', c[7]).group(1)
    assert c[7].startswith('미확인(')
    c[7] = '%s 원문: cowork_results %s번' % (SUNCHON, nn)
    lines[hit[0]] = m.row(c)
    i = m.idx(lines, '### 3-2.')
    th, t0, t1 = m.table_span(lines, i)
    hit = [k for k in range(t0, t1) if m.cells(lines[k])[0] == '국립순천대학교']
    assert len(hit) == 1
    c = m.cells(lines[hit[0]])
    c[1] = SUNCHON
    lines[hit[0]] = m.row(c)


def update_js():
    raw = m.rd(JS)
    assert raw.count('\r\n') == raw.count('\n')
    lines = raw.replace('\r\n', '\n').split('\n')
    i0 = lines.index('## 조사 완료 대학')
    hdr = i0 + 2
    r_idx = []
    j = hdr + 2
    while lines[j].startswith('|'):
        r_idx.append(j)
        j += 1
    rows = [m.cells(lines[i]) for i in r_idx]
    hit = [k for k, r in enumerate(rows) if r[0] == '국립순천대학교']
    assert len(hit) == 1
    assert rows[hit[0]][6] == '미확인'
    rows[hit[0]][6] = SUNCHON
    for k, r in enumerate(rows):
        lines[r_idx[k]] = m.row(r)
    n0 = lines.index('## 조사 비고')
    q = n0 + 4
    while lines[q].startswith('|'):
        c = m.cells(lines[q])
        if c[0] == '국립순천대학교':
            assert '정시 요강 미확인' in c[1]
            c[1] = c[1].replace('정시 요강 미확인', '정시 요강 ' + SUNCHON, 1)
            lines[q] = m.row(c)
        q += 1
    list4 = m.load_list4()
    lkey = {}
    for rg, items in list4.items():
        if rg in ('서울', '충청', '강원', '호남'):
            for nm_, cp in items:
                lkey[(nm_, cp)] = rg
    names_b = [(r[0], r[1]) for r in rows[:79]]
    k_inc = names_b.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names_b.index(('경남대학교', '경남대학교(마산)'))
    region_all = [('경기' if k < k_inc else ('인천' if k < k_yn else '영남')) if k < 79 else lkey[(r[0], r[1])] for k, r in enumerate(rows)]

    def st_now(cs):
        if cs[6] != '-':
            return '보류' if cs[6].startswith('보류') else ('미확인' if cs[6].startswith('미확인') else '확인')
        return m.jstate(cs[:6])
    REG7 = m9.REG7
    groups = {s_: {rg: [] for rg in REG7} for s_ in ('미조사', '미확인', '보류')}
    for k, cs in enumerate(rows):
        s_ = st_now(cs)
        if s_ in groups:
            groups[s_][region_all[k]].append('- %s (%s)' % (cs[0], cs[1]))
    cnt = {s_: sum(len(v) for v in g.values()) for s_, g in groups.items()}
    m0 = lines.index('## 미확인 대학 목록')
    tail = ['## 미확인 대학 목록', '',
            '정시 모집요강 URL을 미확인으로 둔 대학입니다. (상태 칸이 "미확인…"이거나, 상태 칸이 "-"이고 기존 칸에 "미확인"이 있는 행)', '']
    for rg in REG7:
        tail += ['### ' + rg, ''] + (groups['미확인'][rg] or ['- 없음']) + ['']
    tail += ['## 보류 대학 목록', '', '상태 칸이 "보류…"인 행입니다.', '']
    for rg in REG7:
        tail += groups['보류'][rg]
    if not cnt['보류']:
        tail += ['- 없음']
    tail += ['']
    tail += ['## 미조사 대학 목록', '', '### 남은 대기열', '',
             '- 미조사 %d개: 아래 권역별 목록(%s)의 대학은 아직 정시 모집요강을 확인하지 않았습니다. (2026-10-05 #1005-11 반영 후)'
             % (cnt['미조사'], ', '.join('%s %d' % (rg, len(groups['미조사'][rg])) for rg in REG7)), '']
    for rg in REG7:
        tail += ['### ' + rg, ''] + (groups['미조사'][rg] or ['- 없음']) + ['']
    lines = lines[:m0] + tail
    while lines and lines[-1] == '':
        lines.pop()
    text = '\n'.join(lines) + '\n'
    marker = '> 관리: 2026-09-28부터 Claude Code가 관리'
    k = text.index(marker)
    text = text[:k] + '> 2026-10-05(#1005-11 작업 74): 국립순천대학교 상태를 "%s"로 바꿨습니다.\n>\n' % SUNCHON + text[k:]
    return text.replace('\n', '\r\n'), dict(cnt=cnt, groups=groups)


def recompute_sixth(lines, js):
    """6장 대기열 숫자 다시 계산 (표 행 수는 문서에서 세고, 정시 파일 수치는 정시 파일에서 센다)"""
    def table_rows(head):
        i = m.idx(lines, head)
        th, t0, t1 = m.table_span(lines, i)
        return [m.cells(lines[k]) for k in range(t0, t1)]
    r21 = table_rows('### 2-1.')
    r32 = table_rows('### 3-2.')
    gr, cnt = js['groups'], js['cnt']

    def names(s_):
        pairs = []
        for rg in m9.REG7:
            for x in gr[s_][rg]:
                nm_, cp = x[2:].split(' (', 1)
                cp = cp[:-1]                                  # "- 이름 (캠퍼스)" 의 마지막 닫는 괄호 하나만 뺀다
                pairs.append((nm_, cp[len(nm_):].strip() if cp.startswith(nm_) else cp))
        dup = {n_ for n_, _ in pairs if sum(1 for q_, _ in pairs if q_ == n_) > 1}      # 같은 이름이 둘 이상이면 캠퍼스를 붙인다
        return ', '.join(('%s%s' % (n_, c_) if n_ in dup else n_) for n_, c_ in pairs) or '없음'
    h6 = m.idx(lines, '## 6.')
    for k in range(h6, len(lines)):
        ln = lines[k]
        if ln.startswith('| 3-2장 재조사'):
            lines[k] = ('| 3-2장 재조사 (보류·재조사 대기) | %d곳 | %s |'
                        % (len(r32), ' / '.join('%s: %s' % (c[0], c[1]) for c in r32)))
        elif ln.startswith('| 2-1장 (입결'):
            lines[k] = '| 2-1장 (입결·정시 요강 위치를 찾지 못한 행) | %d행 | %s |' % (len(r21), ', '.join(c[0] for c in r21))
        elif ln.startswith('| 정시 모집요강 URL (별도 파일'):
            lines[k] = ('| 정시 모집요강 URL (별도 파일, 경기·인천·영남·서울·충청·강원·호남 4년제) | 미조사 %d행, 미확인 %d행, 보류 %d행 | 미확인: %s / 보류: %s. 호남 전문대학·교육대학은 이 파일에 행이 없고 1-10장 비고에 요강 위치가 있음 |'
                        % (cnt['미조사'], cnt['미확인'], cnt['보류'], names('미확인'), names('보류')))
    return len(r21), len(r32)


if __name__ == '__main__':
    lines = m.rd(V8).split('\n')
    n = shorten(lines)
    sunchon_doc(lines)
    text_js, js = update_js()
    n21, n32 = recompute_sixth(lines, js)
    k = m.idx(lines, '60. ')
    lines[k + 1:k + 1] = [
        '61. 1-9장·1-10장 호남 행 %d행의 비고를 "상태 값 + 원문: cowork_results NN번" 형식으로 바꿈(상태 값 외 설명 문장 없음). 국립순천대의 상태를 "%s"로 바꾸고(1-9장, 3-2장, 정시 파일) 6장 대기열 숫자를 다시 계산함.' % (n, SUNCHON)]
    m.wr(V8, '\n'.join(lines))
    m.wr(JS, text_js)
    print('작업 73: 비고를 바꾼 행 %d' % n)
    print('작업 74: 국립순천대 상태 → %s. 6장 재계산: 2-1장 %d행, 3-2장 %d곳, 정시 파일 %s' % (SUNCHON, n21, n32, js['cnt']))
    for s_ in ('미확인', '보류'):
        print(' ', s_, {rg: [x[2:] for x in v] for rg, v in js['groups'][s_].items() if v})
