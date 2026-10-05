"""#1005-20 작업 81 (merge_cowork_v8·v9·v10 의 함수를 가져다 쓴다).

v8 의 광양보건대 상태를 "보류(사이트 접속 실패)"로 바꾸고(1-10장 비고, 3-2장 상태) 6장 숫자를 다시 계산한다.
2027_정시모집요강_URL_누적.md 에는 광양보건대 행이 없다(전문대학은 정시 파일 대상이 아님). 그래서 정시 파일은 건드리지 않고 6장 수치만 그 파일에서 다시 센다.
"""
import re

import merge_cowork_v8 as m
import merge_cowork_v9 as m9
import merge_cowork_v10 as m10

STATUS = '보류(사이트 접속 실패)'


def js_stats():
    """정시 파일(변경 없음)에서 상태별 대학 수와 목록을 센다."""
    raw = m.rd(m.JS)
    lines = raw.replace('\r\n', '\n').split('\n')
    i0 = lines.index('## 조사 완료 대학')
    j = i0 + 4
    rows = []
    while lines[j].startswith('|'):
        rows.append(m.cells(lines[j]))
        j += 1
    list4 = m.load_list4()
    lkey = {}
    for rg, items in list4.items():
        if rg in ('서울', '충청', '강원', '호남'):
            for nm_, cp in items:
                lkey[(nm_, cp)] = rg
    names_b = [(r[0], r[1]) for r in rows[:79]]
    k_inc = names_b.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names_b.index(('경남대학교', '경남대학교(마산)'))
    groups = {s_: {rg: [] for rg in m9.REG7} for s_ in ('미조사', '미확인', '보류')}
    for k, cs in enumerate(rows):
        rg = ('경기' if k < k_inc else ('인천' if k < k_yn else '영남')) if k < 79 else lkey[(cs[0], cs[1])]
        if cs[6] != '-':
            s_ = '보류' if cs[6].startswith('보류') else ('미확인' if cs[6].startswith('미확인') else '확인')
        else:
            s_ = m.jstate(cs[:6])
        if s_ in groups:
            groups[s_][rg].append('- %s (%s)' % (cs[0], cs[1]))
    return dict(groups=groups, cnt={s_: sum(len(v) for v in g.values()) for s_, g in groups.items()})


if __name__ == '__main__':
    lines = m.rd(m.V8).split('\n')
    i = m.idx(lines, '### 1-10.')
    th, t0, t1 = m.table_span(lines, i)
    hit = [k for k in range(t0, t1) if m.cells(lines[k])[0] == '광양보건대학교']
    assert len(hit) == 1
    c = m.cells(lines[hit[0]])
    nn = re.search(r'원문: cowork_results ([\d·]+)번$', c[7]).group(1)
    assert c[7].startswith('미확인(')
    c[7] = '%s 원문: cowork_results %s번' % (STATUS, nn)
    lines[hit[0]] = m.row(c)
    i = m.idx(lines, '### 3-2.')
    th, t0, t1 = m.table_span(lines, i)
    hit = [k for k in range(t0, t1) if m.cells(lines[k])[0] == '광양보건대학교']
    assert len(hit) == 1
    c = m.cells(lines[hit[0]])
    c[1] = STATUS
    lines[hit[0]] = m.row(c)
    js = js_stats()
    n21, n32 = m10.recompute_sixth(lines, js)
    k = m.idx(lines, '61. ')
    lines[k + 1:k + 1] = ['62. 광양보건대의 상태를 "%s"로 바꿈(1-10장, 3-2장). 정시 파일에는 광양보건대 행이 없음(전문대학). 6장 대기열 숫자를 다시 계산함.' % STATUS]
    m.wr(m.V8, '\n'.join(lines))
    print('작업 81: 광양보건대 상태 → %s. 6장 재계산: 2-1장 %d행, 3-2장 %d곳, 정시 파일 %s' % (STATUS, n21, n32, js['cnt']))
