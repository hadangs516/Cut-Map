/* ---------- 성적 관리 · 성적 입력 탭 ---------- */

/* 5등급 상대평가 누적 비율. (SPEC 3-3) */
var CUM5 = [10, 34, 66, 90, 100];
function grade5From(pct){
  for(var i = 0; i < CUM5.length; i++){ if(pct <= CUM5[i]) return i + 1; }
  return 5;
}
/* 동점자가 있으면 중간석차로 계산한다. 학교 처리와 다를 수 있어 사용자가 등급을 고칠 수 있게 해둔다. */
function calcGrade5(rank, tied, count){
  var r = Number(rank), n = Number(count), t = Math.max(1, Number(tied) || 1);
  if(!(n > 0) || !(r > 0) || r > n) return null;
  var eff = r + (t - 1) / 2;
  return grade5From(eff / n * 100);
}

var EXAM_TYPE_LABEL = {midterm:'중간고사', final:'기말고사', semesterConfirmed:'학기말 확정', mock:'모의고사'};
/* 모의고사 영역은 학년·연도에 따라 달라서 고정하지 않는다. 기본 줄만 주고 사용자가 고친다. */
var MOCK_AREAS_DEFAULT = ['국어', '수학', '영어', '한국사', '탐구'];

function examKey(type, sem, refId){
  return type === 'mock' ? ('mock:' + refId) : ('sem:' + sem + ':' + type);
}
function findExam(key){
  for(var i = 0; i < user.exams.length; i++){ if(user.exams[i].id === key) return user.exams[i]; }
  return null;
}
function ensureExam(key, base){
  var e = findExam(key);
  if(!e){
    e = {id:key, type:base.type, sem:base.sem || null, refId:base.refId || null,
      name:base.name, date:base.date || null, studentCount:null, results:[]};
    user.exams.push(e);
  }
  if(!Array.isArray(e.results)) e.results = [];
  return e;
}
function examResult(e, key){
  for(var i = 0; i < e.results.length; i++){
    if(e.results[i].courseCode === key || e.results[i].area === key) return e.results[i];
  }
  return null;
}
function markFirstEntry(){
  if(!user.backup.firstEntryAt) user.backup.firstEntryAt = new Date().toISOString();
}

/* ----- 시험 목록 순서 (A-3-2) -----
   기본 순서: 3모, 1학기 중간, 5모, 6모, 1학기 기말, 7모, 1학기 학기말,
             9모, 2학기 중간, 10모, 2학기 기말, 2학기 학기말, 수능. 학년마다 반복한다.
   날짜가 있는 시험은 날짜순으로 다시 놓고, 날짜가 없는 시험은 기본 자리를 지킨다. */
var SLOT_ORDER = [
  {kind:'mock', month:3},
  {kind:'exam', term:1, part:'midterm'},
  {kind:'mock', month:5},
  {kind:'mock', month:6},
  {kind:'exam', term:1, part:'final'},
  {kind:'mock', month:7},
  {kind:'exam', term:1, part:'semesterConfirmed'},
  {kind:'mock', month:9},
  {kind:'exam', term:2, part:'midterm'},
  {kind:'mock', month:10},
  {kind:'exam', term:2, part:'final'},
  {kind:'exam', term:2, part:'semesterConfirmed'},
  {kind:'csat'}
];
var PART_RANK = {midterm:0, final:1, semesterConfirmed:2};

function gradesWithCourses(){
  var set = {};
  SEM_IDS.forEach(function(id){ if(semCourses(id).length) set[id.charAt(0)] = 1; });
  var cur = user.profile.currentGrade;
  if(cur && cur !== 'grad') set[String(cur)] = 1;
  return Object.keys(set).sort();
}
/* 이미 본 모의고사만. 숨긴 것과 아직 안 본 것은 뺀다. 파일에 없는 시험은 만들지 않는다. */
function pastMocks(){
  return providedExams().filter(function(e){
    return !e.hidden && e.date && daysUntil(e.date) <= 0 && e.kind !== 'result';
  });
}
function examCandidates(){
  var mocks = pastMocks(), used = {}, items = [], base = 0;
  var curGrade = String(user.profile.currentGrade || '');

  gradesWithCourses().forEach(function(g){
    SLOT_ORDER.forEach(function(slot){
      if(slot.kind === 'exam'){
        var sem = g + '-' + slot.term;
        if(!semCourses(sem).length) return;
        var sch = schoolExams().filter(function(s){ return s.sem === sem && s.part === slot.part; })[0];
        items.push({key:examKey(slot.part, sem), type:slot.part, sem:sem, grade:g,
          name:semLabel(sem) + ' ' + EXAM_TYPE_LABEL[slot.part],
          date:(slot.part === 'semesterConfirmed' || !sch) ? null : sch.date,
          base:base++, kindTag:'exam', partRank:PART_RANK[slot.part]});
        return;
      }
      /* 모의고사는 앱 일정 파일에 있는 것만. 지금 학년 자리에만 넣는다. */
      if(g !== curGrade) return;
      var m = null;
      mocks.forEach(function(x){
        if(used[x.id]) return;
        if(slot.kind === 'csat'){ if(x.kind === 'csat') m = m || x; return; }
        if(x.kind === 'csat') return;
        if(Number(x.date.slice(5, 7)) === slot.month) m = m || x;
      });
      if(!m) return;
      used[m.id] = 1;
      items.push({key:examKey('mock', null, m.id), type:'mock', refId:m.id, grade:g,
        name:m.name, date:m.date, base:base++, kindTag:'mock'});
    });
  });
  /* 기본 순서에 자리가 없는 모의고사는 날짜순으로 맨 뒤에 붙인다. */
  mocks.filter(function(x){ return !used[x.id]; })
    .sort(function(a, b){ return a.date < b.date ? -1 : 1; })
    .forEach(function(m){
      items.push({key:examKey('mock', null, m.id), type:'mock', refId:m.id, grade:curGrade,
        name:m.name, date:m.date, base:1000 + base++, kindTag:'mock', tail:true});
    });

  return orderExams(items);
}
/* 날짜 없는 시험은 기본 순서에서 바로 앞 시험의 날짜를 물려받는다. 앞이 없으면 뒤 시험 날짜의 하루 전.
   그 뒤 (날짜, 기본순서)로 정렬하고, 같은 학기 안에서는 중간·기말·학기말 확정 순서를 강제한다. */
function orderExams(items){
  var n = items.length, key = new Array(n);
  for(var i = 0; i < n; i++) key[i] = items[i].date || null;
  for(i = 0; i < n; i++){
    if(key[i]) continue;
    for(var a = i - 1; a >= 0; a--){ if(key[a]){ key[i] = key[a]; break; } }
  }
  for(i = n - 1; i >= 0; i--){
    if(key[i]) continue;
    for(var b = i + 1; b < n; b++){
      if(key[b]){ var d = new Date(key[b] + 'T00:00:00'); d.setDate(d.getDate() - 1); key[i] = ymd(d); break; }
    }
  }
  var idx = items.map(function(it, i){ return {it:it, k:key[i] || '', i:i}; });
  idx.sort(function(x, y){
    if(x.k !== y.k) return x.k < y.k ? -1 : 1;
    return x.it.base - y.it.base;
  });
  var out = idx.map(function(x){ return x.it; });
  /* 같은 학기의 중간 → 기말 → 학기말 확정 순서를 지킨다. */
  for(var pass = 0; pass < 3; pass++){
    var moved = false;
    for(i = 0; i < out.length - 1; i++){
      var p = out[i], q = out[i + 1];
      if(p.sem && p.sem === q.sem && p.partRank > q.partRank){
        out[i] = q; out[i + 1] = p; moved = true;
      }
    }
    if(!moved) break;
  }
  return out;
}

var SCORE_SCREENS = {
  home:  {title:'성적 입력', parent:null,   render:function(){ return scScoreHome(); }},
  entry: {title:function(){ return (gs.examMeta && gs.examMeta.name) || '성적 입력'; },
          parent:'home', render:function(){ return scScoreEntry(); }}
};

function scScoreHome(){
  var list = examCandidates();
  if(!list.length){
    return '<div class="gx-empty">먼저 마이 탭에서 과목을 넣어주세요.<br>과목이 있어야 성적을 넣을 수 있어요.</div>';
  }
  var h = '<p class="gx-lead">시험을 고르면 성적을 넣을 수 있어요. 학교 시험은 날짜를 넣으면 그 순서로 놓여요.</p><div class="gx-list">';
  list.forEach(function(c){
    var e = findExam(c.key);
    var n = e ? e.results.filter(function(r){ return r.grade5 != null || r.grade != null; }).length : 0;
    var meta = '<span>' + (c.date ? c.date : '날짜 미입력') + '</span>' +
      '<span>' + (n ? n + '개 입력됨' : '아직 안 넣음') + '</span>';
    var tags = c.type === 'semesterConfirmed' ? '<span class="gx-badge">확정</span>' : '';
    h += '<button type="button" class="gx-row" data-kind="' + c.kindTag + '" data-gexam="' + esc(c.key) + '">' +
      '<span class="gx-main"><span class="gx-name">' + esc(c.name) + tags + '</span>' +
      '<span class="gx-meta">' + meta + '</span></span><span class="gx-arrow">›</span></button>';
  });
  h += '</div><p class="gx-note">중간·기말로 계산한 등급은 예상값이에요. 내신에 들어가는 건 학기말 확정 등급이라 따로 넣어요. 모의고사는 앱 일정 파일에 있는 것만 나와요.</p>';
  return h;
}

/* ----- 입력 중에는 저장하지 않고 초안(draft)에 담는다. 저장 버튼을 눌러야 반영된다. ----- */
function loadDraft(meta){
  var e = ensureExam(meta.key, meta);
  var d = {key:meta.key, studentCount:e.studentCount, results:{}};
  e.results.forEach(function(r){
    if(!r.courseCode) return;
    d.results[r.courseCode] = {rank:r.rank, tiedCount:r.tiedCount, studentCount:r.studentCount,
      manual:r.gradeManual ? r.grade5 : null, original:r.gradeOriginal};
  });
  gs.draft = d;
  gs.dirty = false;
}
function draftRow(code){
  var d = gs.draft;
  if(!d.results[code]) d.results[code] = {rank:null, tiedCount:null, studentCount:null, manual:null};
  return d.results[code];
}
function draftCount(code){
  var d = gs.draft, r = d.results[code];
  return (r && r.studentCount != null) ? r.studentCount : d.studentCount;
}
function draftGrade(code){
  var r = draftRow(code), calc = calcGrade5(r.rank, r.tiedCount, draftCount(code));
  return r.manual != null ? {g:r.manual, manual:true, calc:calc} : {g:calc, manual:false, calc:calc};
}
function saveDraft(){
  var d = gs.draft, e = ensureExam(gs.examMeta.key, gs.examMeta);
  e.studentCount = d.studentCount;
  Object.keys(d.results).forEach(function(code){
    var src = d.results[code];
    var r = examResult(e, code);
    if(!r){ r = {courseCode:code}; e.results.push(r); }
    var calc = calcGrade5(src.rank, src.tiedCount, src.studentCount != null ? src.studentCount : d.studentCount);
    r.rank = src.rank; r.tiedCount = src.tiedCount; r.studentCount = src.studentCount;
    if(src.manual != null){ r.gradeManual = true; r.gradeOriginal = calc; r.grade5 = src.manual; }
    else { r.gradeManual = false; r.gradeOriginal = null; r.grade5 = calc; }
  });
  markFirstEntry();
  saveUser();
  gs.dirty = false;
}

function scScoreEntry(){
  var meta = gs.examMeta; if(!meta) return '<div class="gx-empty">시험을 찾지 못했어요.</div>';
  if(!gs.draft || gs.draft.key !== meta.key) loadDraft(meta);
  if(meta.type === 'mock') return scMockEntry(ensureExam(meta.key, meta));

  var d = gs.draft;
  var list = semCourses(meta.sem).filter(function(c){ return c.hasGrade; });
  var skipped = semCourses(meta.sem).length - list.length;
  var h = '';
  if(meta.type === 'semesterConfirmed') h += '<p class="gx-warn">학기말에 나온 <b>확정 석차등급</b>을 넣는 곳이에요. 수행평가까지 반영된 최종 등급이에요.</p>';
  h += '<div class="gx-field"><div><label for="scCount">수강자 수</label>' +
    '<p>시험 전체 기준이에요. 과목마다 다르면 아래 카드에서 그 과목만 고치세요.</p></div>' +
    '<input type="number" id="scCount" min="1" step="1" placeholder="예: 210" value="' +
    (d.studentCount == null ? '' : d.studentCount) + '"></div>';
  if(!list.length){
    h += '<div class="gx-empty">이 학기에 등급이 나오는 과목이 없어요.</div>';
    return h;
  }
  h += '<div class="sc-list">';
  list.forEach(function(c){
    var code = c.courseCode || '', r = draftRow(code), g = draftGrade(code);
    h += '<div class="sc-card" data-sc="' + esc(code) + '">' +
      '<div class="sc-top"><span class="sc-nm">' + esc(courseName(c)) + '</span>' +
      '<span class="sc-g' + (g.g == null ? ' off' : '') + '">' + (g.g == null ? '–' : g.g + '등급') + '</span>' +
      '<span class="sc-man"' + (g.manual ? '' : ' hidden') + '><span class="gx-flag">수정됨</span></span></div>' +
      '<div class="sc-grid">' +
      '<label>석차<input type="number" min="1" step="1" data-scf="rank" placeholder="등수" value="' + (r.rank == null ? '' : r.rank) + '"></label>' +
      '<label>동석차<input type="number" min="1" step="1" data-scf="tiedCount" placeholder="없을 시 빈칸" value="' + (r.tiedCount == null ? '' : r.tiedCount) + '"></label>' +
      '<label>수강자<input type="number" min="1" step="1" data-scf="studentCount" placeholder="시험 기준" value="' + (draftCount(code) == null ? '' : draftCount(code)) + '"></label>' +
      '<label>등급 직접<select data-scf="manual"><option value="">자동</option>' +
      [1,2,3,4,5].map(function(n){
        return '<option value="' + n + '"' + (r.manual === n ? ' selected' : '') + '>' + n + '등급</option>';
      }).join('') + '</select></label>' +
      '</div>' +
      '<p class="sc-orig"' + (g.manual && g.calc != null ? '' : ' hidden') + '>계산값은 ' + (g.calc == null ? '–' : g.calc) + '등급이었어요.</p>' +
      '</div>';
  });
  h += '</div>';
  if(skipped) h += '<p class="gx-note">등급이 안 나오는 과목 ' + skipped + '개는 뺐어요.</p>';
  h += '<p class="gx-note">석차를 모르면 "등급 직접"에서 고르면 돼요. 학생부에는 등수가 안 적혀서 모를 수 있어요.</p>';
  h += '<div class="sc-save"><button type="button" class="btn sc-savebtn" data-scsave>저장</button>' +
    '<span class="gx-note" id="scDirty"' + (gs.dirty ? '' : ' hidden') + '>저장하지 않은 입력이 있어요</span></div>';
  return h;
}

/* 입력 중에는 화면을 다시 그리지 않는다. 다시 그리면 스크롤이 맨 위로 튄다. */
function refreshCard(code){
  var card = document.querySelector('.sc-card[data-sc="' + code + '"]');
  if(!card) return;
  var g = draftGrade(code), el = card.querySelector('.sc-g');
  el.textContent = g.g == null ? '–' : g.g + '등급';
  el.classList.toggle('off', g.g == null);
  card.querySelector('.sc-man').hidden = !g.manual;
  var o = card.querySelector('.sc-orig');
  o.hidden = !(g.manual && g.calc != null);
  o.textContent = '계산값은 ' + (g.calc == null ? '–' : g.calc) + '등급이었어요.';
}
function markDirty(){
  gs.dirty = true;
  var el = $('#scDirty'); if(el) el.hidden = false;
}
/* 시험 단위 수강자 수를 바꾸면, 따로 고치지 않은 카드의 칸도 같이 바뀐다. */
function applyCountToCards(){
  var d = gs.draft;
  document.querySelectorAll('.sc-card').forEach(function(card){
    var code = card.getAttribute('data-sc'), r = d.results[code];
    if(r && r.studentCount != null) return;
    var inp = card.querySelector('[data-scf="studentCount"]');
    if(inp) inp.value = d.studentCount == null ? '' : d.studentCount;
    refreshCard(code);
  });
}

function scMockEntry(e){
  if(!Array.isArray(e.areas) || !e.areas.length) e.areas = MOCK_AREAS_DEFAULT.slice();
  var h = '<p class="gx-lead">영역별 등급을 넣어주세요. 원점수와 백분위는 넣어도 되고 안 넣어도 돼요.</p>';
  h += '<div class="sc-list">';
  e.areas.forEach(function(a, i){
    var r = examResult(e, a) || {};
    h += '<div class="sc-card" data-sca="' + esc(a) + '">' +
      '<div class="sc-top"><input class="sc-anm" type="text" data-scaname="' + i + '" value="' + esc(a) + '" maxlength="10" aria-label="영역 이름">' +
      '<button type="button" class="gdel-x" data-scadel="' + i + '" aria-label="영역 삭제">×</button></div>' +
      '<div class="sc-grid">' +
      '<label>등급<select data-scf="grade"><option value="">–</option>' +
      [1,2,3,4,5,6,7,8,9].map(function(n){
        return '<option value="' + n + '"' + (r.grade === n ? ' selected' : '') + '>' + n + '</option>';
      }).join('') + '</select></label>' +
      '<label>원점수<input type="number" min="0" step="1" data-scf="raw" placeholder="선택" value="' + (r.raw == null ? '' : r.raw) + '"></label>' +
      '<label>백분위<input type="number" min="0" max="100" step="1" data-scf="pct" placeholder="선택" value="' + (r.pct == null ? '' : r.pct) + '"></label>' +
      '</div></div>';
  });
  h += '</div>';
  h += '<div class="gx-add"><input type="text" id="scAreaNew" maxlength="10" placeholder="영역 추가 (예: 통합사회)" aria-label="영역 추가">' +
    '<button type="button" class="btn" data-scaadd>추가</button></div>';
  h += '<p class="gx-note">모의고사는 9등급이에요. 영역 구성은 학년과 연도에 따라 다르니 시험지 기준으로 고치세요. 모의고사 등급은 환산하지 않고 그대로 써요.</p>';
  return h;
}
function mockSetField(area, field, value){
  var e = ensureExam(gs.examMeta.key, gs.examMeta);
  var r = examResult(e, area);
  if(!r){ r = {area:area}; e.results.push(r); }
  r[field] = value === '' ? null : Number(value);
  markFirstEntry();
  saveUser();
}

function scoreClick(e){
  var t;
  if((t = e.target.closest('[data-gexam]'))){
    var key = t.getAttribute('data-gexam');
    gs.examMeta = examCandidates().filter(function(c){ return c.key === key; })[0] || null;
    gs.draft = null;
    gGo('entry');
    return true;
  }
  if(e.target.closest('[data-scsave]')){
    saveDraft();
    var el = $('#scDirty'); if(el) el.hidden = true;
    gToast('저장했어요');
    return true;
  }
  if(e.target.closest('[data-scaadd]')){
    var el2 = $('#scAreaNew'), nm = (el2.value || '').trim();
    if(!nm) return true;
    var ex = ensureExam(gs.examMeta.key, gs.examMeta);
    if(!Array.isArray(ex.areas)) ex.areas = MOCK_AREAS_DEFAULT.slice();
    if(ex.areas.indexOf(nm) < 0) ex.areas.push(nm);
    saveUser(); gRender();
    return true;
  }
  if((t = e.target.closest('[data-scadel]'))){
    var ex2 = ensureExam(gs.examMeta.key, gs.examMeta);
    var idx = Number(t.getAttribute('data-scadel')), nm2 = ex2.areas[idx];
    ex2.areas.splice(idx, 1);
    ex2.results = ex2.results.filter(function(r){ return r.area !== nm2; });
    saveUser(); gRender();
    return true;
  }
  return false;
}

/* 지필 입력은 input으로 받아서 그 카드만 고친다. change로 다시 그리지 않는다. */
function scoreInput(e){
  if(gs.tab !== 'score' || gs.screen !== 'entry' || !gs.draft) return false;
  var el = e.target;
  if(el.id === 'scCount'){
    var v = el.value.trim();
    gs.draft.studentCount = v === '' ? null : Math.round(Number(v));
    if(!(gs.draft.studentCount > 0)) gs.draft.studentCount = null;
    applyCountToCards();
    markDirty();
    return true;
  }
  var card = el.closest('[data-sc]');
  if(!card) return false;
  var code = card.getAttribute('data-sc'), f = el.getAttribute('data-scf');
  if(!f) return false;
  var r = draftRow(code), raw = el.value.trim();
  if(f === 'manual'){
    r.manual = raw === '' ? null : Number(raw);
  }else{
    var n = raw === '' ? null : Math.round(Number(raw));
    if(n != null && !(n > 0)) n = null;
    /* 카드 값이 시험 단위 값과 같으면 별도 값으로 저장하지 않는다. */
    if(f === 'studentCount' && n != null && n === gs.draft.studentCount) n = null;
    r[f] = n;
  }
  refreshCard(code);
  markDirty();
  return true;
}
function scoreChange(e){
  if(gs.tab !== 'score') return false;
  var el = e.target;
  if(el.hasAttribute('data-scaname')){
    var ex = ensureExam(gs.examMeta.key, gs.examMeta);
    var i = Number(el.getAttribute('data-scaname')), old = ex.areas[i], nv = el.value.trim();
    if(nv && nv !== old){
      ex.areas[i] = nv;
      ex.results.forEach(function(r){ if(r.area === old) r.area = nv; });
      saveUser(); gRender();
    }
    return true;
  }
  var mcard = el.closest('[data-sca]');
  if(mcard){ mockSetField(mcard.getAttribute('data-sca'), el.getAttribute('data-scf'), el.value.trim()); return true; }
  return scoreInput(e);       /* select는 change로만 오므로 같은 처리를 태운다. */
}
