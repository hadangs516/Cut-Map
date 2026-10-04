"""#1005-06 작업 62~64 (merge_cowork_v8.py 의 함수를 가져다 쓴다. v8 파일은 고치지 않았다).

- 작업 62: 2027_정시모집요강_URL_누적.md 에 v8 1-9장 호남 4년제 21행을 새 행으로 추가한다.
           요강 URL·파일명은 cowork_results 35~43번 결과의 칸을 그대로 쓰고, 값이 없으면 "미확인".
- 작업 63: v8 1-9장·1-10장 호남(과 서영대 파주) 행의 비고를 한 줄로 줄이고 끝에 "원문: cowork_results NN번"을 붙인다. 상태 값은 그대로.
- 작업 64: v8 7장 한양대(ERICA) 행에 "ERICA 포함 여부 미확인"이 있는지 확인하고 없으면 덧붙인다.
표 값은 결과 파일의 칸을 코드가 옮긴다(사람이 옮기지 않는다).
"""
import re

import merge_cowork_v8 as m

REG7 = ['경기', '인천', '영남', '서울', '충청', '강원', '호남']
V8_DOC = m.V8
JS = m.JS


def need_note(g, status_cell):
    s = g['status']
    return (status_cell.startswith('미확인') or '불일치' in s or '학년도 미확인' in s or '초안' in g['jfile']
            or '(안)' in g['jfile'] or '부분확인' in s)


def update_js(recs):
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
    list4 = m.load_list4()
    lkey = {}
    for rg, items in list4.items():
        if rg in ('서울', '충청', '강원', '호남'):
            for k, (nm_, cp) in enumerate(items):
                lkey[(nm_, cp)] = (rg, k)
    assert not any(lkey.get((r[0], r[1]), ('',))[0] == '호남' for r in rows), '호남 행이 이미 있음'
    items, unmatched = m.classify_honam(recs)
    assert not unmatched
    four = [x for x in items if x['kind'] == '4년제']
    assert len(four) == 21, len(four)
    new_rows, notes, status_list = [], [], []
    for x in four:
        g = x['g']
        key = (x['mname'], x['link'])
        assert key in lkey and lkey[key][0] == '호남', key        # 대학명·캠퍼스는 4년제 목록(master) 표기
        jurl, jfile = g['jurl'], g['jfile']
        if jurl.startswith(('미확인', '미조사', '-')) or not jurl:
            st = '미확인'
            jurl = jurl if jurl.startswith('미확인') else '미확인'
            jfile = jfile if jfile.startswith('미확인') else '미확인'
        else:
            st = '확인'
        f2 = m.NOFILE if st == '확인' else '미확인'
        r_ = [x['mname'], x['link'], f2, jurl, jfile, g['date'], st, 'Cowork 직접 열람']
        new_rows.append((lkey[key][1], r_))
        status_list.append((x['mname'], st))
        if need_note(g, st):
            nums = '·'.join(str(n) for n in sorted(set(g['nums'])))
            notes.append(m.row([x['mname'] + ('(%s)' % x['link'].split('(')[-1].rstrip(')') if x['mname'] in ('세한대학교', '우석대학교', '예원예술대학교') else ''),
                                '정시 요강 %s ※ Cowork 상태: %s (cowork_results %s번)' % (st, g['status'], nums)]))
    new_rows.sort(key=lambda t: t[0])
    n_old = len(rows)
    rows_all = rows + [r_ for _, r_ in new_rows]
    lines[r_idx[0]:r_idx[-1] + 1] = [m.row(r_) for r_ in rows_all]
    # 조사 비고
    n0 = lines.index('## 조사 비고')
    q = n0 + 4
    while lines[q].startswith('|'):
        q += 1
    lines[q:q] = notes
    # 권역 구분(기존 행은 위치로, 서울·충청·강원·호남 행은 4년제 목록으로)
    names_b = [(r[0], r[1]) for r in rows[:79]]
    k_inc = names_b.index(('안양대학교', '안양대학교 (본교(제2캠퍼스))'))
    k_yn = names_b.index(('경남대학교', '경남대학교(마산)'))
    region_all = []
    for k, r_ in enumerate(rows_all):
        if k < 79:
            region_all.append('경기' if k < k_inc else ('인천' if k < k_yn else '영남'))
        else:
            region_all.append(lkey[(r_[0], r_[1])][0])

    def st_now(cs):
        if cs[6] != '-':
            return '보류' if cs[6].startswith('보류') else ('미확인' if cs[6].startswith('미확인') else '확인')
        return m.jstate(cs[:6])
    groups = {s_: {rg: [] for rg in REG7} for s_ in ('미조사', '미확인', '보류')}
    for k, cs in enumerate(rows_all):
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
             '- 미조사 %d개: 아래 권역별 목록(%s)의 대학은 아직 정시 모집요강을 확인하지 않았습니다. (2026-10-05 #1005-06 반영 후)'
             % (cnt['미조사'], ', '.join('%s %d' % (rg, len(groups['미조사'][rg])) for rg in REG7)), '']
    for rg in REG7:
        tail += ['### ' + rg, ''] + (groups['미조사'][rg] or ['- 없음']) + ['']
    lines = lines[:m0] + tail
    while lines and lines[-1] == '':
        lines.pop()
    text = '\n'.join(lines) + '\n'
    marker = '> 관리: 2026-09-28부터 Claude Code가 관리'
    k = text.index(marker)
    text = text[:k] + ('> 2026-10-05(#1005-06 작업 62): 컷맵_입결위치조사_20260930_v8.md 1-9장의 호남 4년제 21행을 표 끝에 새 행으로 추가했습니다(대학명·캠퍼스는 4년제 목록 표기, 요강 URL·파일명은 cowork_results 35~43번의 칸 그대로, 값이 없으면 "미확인"). 전문대학·교육대학은 추가하지 않았습니다.\n>\n') + text[k:]
    return text.replace('\n', '\r\n'), dict(n_old=n_old, added=len(new_rows), status=status_list, cnt=cnt, groups=groups, notes=len(notes))


def shorten_v8():
    lines = m.rd(V8_DOC).split('\n')
    heads = {'1-9': m.idx(lines, '### 1-9.'), '1-10': m.idx(lines, '### 1-10.')}   # split_sections 는 한 자리 번호만 찾는다
    changed = []
    for sec in ('1-9', '1-10'):
        th, rws = m.find_table_rows(lines, heads[sec])
        for i in rws:
            c = m.cells(lines[i])
            if len(c) != 8 or '※ Cowork 상태:' not in c[7]:
                continue
            label = c[7].split(' ※ Cowork 상태:')[0].strip()
            nums = sorted({int(x) for x in re.findall(r'Cowork 비고\((\d+)번\)', c[7])})
            assert nums, c[0]
            last = c[7].split('Cowork 비고(%d번): ' % nums[-1])[-1]
            first = re.split(r'(?<=[.])\s', last.strip())[0].rstrip('.')
            if len(first) > 110:
                first = first[:110] + '…'
            c[7] = '%s. %s. 원문: cowork_results %s번' % (label.rstrip('.'), first, '·'.join(str(n) for n in nums))
            lines[i] = m.row(c)
            changed.append((sec, c[0], c[7][:60]))
    return lines, changed


def check_ericas(lines):
    k = m.idx(lines, '## 7.')
    hit = [i for i in range(k, len(lines)) if lines[i].startswith('| 한양대학교(ERICA)')]
    assert len(hit) == 1
    has = 'ERICA 포함 여부 미확인' in lines[hit[0]]
    if not has:
        c = m.cells(lines[hit[0]])
        c[4] = c[4] + ' (ERICA 포함 여부 미확인)'
        lines[hit[0]] = m.row(c)
    return has


if __name__ == '__main__':
    recs = [r for r in m.read_cowork6() if 35 <= r['num'] <= 43]
    # 작업 62
    text_js, st62 = update_js(m.read_cowork6())
    # 작업 63·64
    lines, changed = shorten_v8()
    has = check_ericas(lines)
    m.wr(V8_DOC, '\n'.join(lines))
    m.wr(JS, text_js)
    print('작업 62: 새 행 %d, 조사 비고 %d행 추가, 표 행수 %d→%d' % (st62['added'], st62['notes'], st62['n_old'], st62['n_old'] + st62['added']))
    print('  상태:', st62['status'])
    print('  정시 파일 남은:', st62['cnt'])
    print('작업 63: 줄인 비고 %d행' % len(changed))
    for s_ in changed[:3]:
        print('  ', s_)
    print('작업 64: v8 7장 한양대(ERICA) 행에 "ERICA 포함 여부 미확인" 문구가 %s' % ('이미 있음' if has else '없어서 추가함'))
