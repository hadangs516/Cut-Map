/* ---------- 성적 관리 · 시험 일정과 D-day ----------
   앱이 기본으로 제공하는 일정은 exam_schedule.json에 있는 것만 쓴다.
   파일에 없는 일정은 지어내지 않고 사용자가 직접 넣게 한다. (SPEC 2-2) */

var EXAM_SCHEDULE = /*__EXAM_SCHEDULE__*/null;

var PART_LABEL = {midterm:'중간고사', final:'기말고사'};

function todayYmd(){ return ymd(new Date()); }
function daysUntil(dateStr){
  var a = new Date(dateStr + 'T00:00:00'), b = new Date(todayYmd() + 'T00:00:00');
  return Math.round((a - b) / 86400000);
}
function gradeForSchedule(){
  var g = user.profile.currentGrade;
  return g === 'grad' ? 3 : g;      /* 졸업·N수는 고3 일정을 본다. */
}

function scheduleOverride(ref){
  for(var i = 0; i < user.schedule.length; i++){
    var s = user.schedule[i];
    if(s.kind === 'override' && s.ref === ref) return s;
  }
  return null;
}
function schoolExams(){
  return user.schedule.filter(function(s){ return s.kind === 'school'; });
}
function schoolExamLabel(s){
  return semLabel(s.sem) + ' ' + (PART_LABEL[s.part] || s.part);
}

/* 기본 제공 일정(모의고사·수능) 중 내 학년에 해당하는 것. 사용자가 고친 날짜와 숨김을 반영한다. */
function providedExams(){
  var g = gradeForSchedule();
  return (EXAM_SCHEDULE.exams || []).filter(function(e){
    return (e.grades || []).indexOf(g) >= 0;
  }).map(function(e){
    var ov = scheduleOverride(e.id);
    return {id:e.id, name:e.name, date:(ov && ov.date) || e.date, kind:e.kind,
      host:e.host, note:e.note, dday:e.dday !== false, hidden:!!(ov && ov.hidden),
      moved:!!(ov && ov.date && ov.date !== e.date), origDate:e.date};
  });
}
/* 입시 일정은 학년과 무관하게 보여준다. (사용자 결정) */
function admissionItems(){
  var a = EXAM_SCHEDULE.admission_2029 || {};
  return (a.items || []).map(function(it){
    return {id:'adm-' + (it.date || it.date_start), name:it.name,
      date:it.date || it.date_start, kind:'admission', note:it.note, dday:true, hidden:false};
  });
}

/* D-day 후보: 내가 넣은 학교 시험 + 기본 제공 모의고사 + 입시 일정. 지난 것은 뺀다. */
function ddayList(){
  var out = [];
  schoolExams().forEach(function(s){
    out.push({id:s.id, name:schoolExamLabel(s), date:s.date, kind:'school', dday:true});
  });
  providedExams().forEach(function(e){ if(!e.hidden && e.dday) out.push(e); });
  admissionItems().forEach(function(e){ out.push(e); });
  return out.filter(function(e){ return e.date && daysUntil(e.date) >= 0; })
    .sort(function(a, b){ return a.date < b.date ? -1 : (a.date > b.date ? 1 : 0); });
}

function renderDday(){
  var el = $('#gvDday'); if(!el) return;
  var list = ddayList();
  if(!list.length){
    el.innerHTML = '<span class="gd-none">다가오는 시험이 없어요. 마이 탭에서 학교 시험을 넣어보세요.</span>';
    el.disabled = true;
    return;
  }
  el.disabled = false;
  var n = list[0], d = daysUntil(n.date);
  el.innerHTML = '<span class="gd-num">' + (d === 0 ? 'D-DAY' : 'D-' + d) + '</span>' +
    '<span class="gd-name">' + esc(n.name) + '</span>' +
    '<span class="gd-date">' + esc(n.date) + '</span>' +
    '<span class="gd-more">전체 일정 ›</span>';
}
function showDdayList(){
  var list = ddayList();
  var h = list.map(function(e){
    var d = daysUntil(e.date);
    return '<div class="gd-row"><span>' + esc(e.name) + '</span>' +
      '<span>' + esc(e.date) + ' · ' + (d === 0 ? '오늘' : 'D-' + d) + '</span></div>';
  }).join('');
  gModal({
    title: '다가오는 일정',
    body: (h || '<p>남은 일정이 없어요.</p>') +
      '<p class="gx-note">학력평가 일정은 시행 전에 바뀔 수 있어요. 학교 공지를 확인하세요.</p>',
    buttons: [{label:'닫기', main:true, run:gModalClose}]
  });
}

/* ----- 시험 일정 화면 ----- */
var EXAM_SCREENS = {
  list: {title:'시험 일정', parent:'home', render:function(){ return scExams(); }},
  add:  {title:'학교 시험 넣기', parent:'list', render:function(){ return scExamAdd(); }}
};

function scExams(){
  var mine = schoolExams().slice().sort(function(a, b){ return a.date < b.date ? -1 : 1; });
  var h = '<h3 class="gx-h">내가 넣은 학교 시험</h3>';
  h += '<div class="gx-acts" style="margin-bottom:10px"><button type="button" class="btn" data-gexadd>+ 학교 시험 넣기</button></div>';
  if(!mine.length){
    h += '<div class="gx-empty">넣은 학교 시험이 없어요.<br>중간·기말고사 날짜를 넣으면 D-day에 나와요.</div>';
  }else{
    h += '<div class="gx-list">';
    mine.forEach(function(s){
      var d = daysUntil(s.date);
      h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
        '<span class="gx-name">' + esc(schoolExamLabel(s)) + '</span>' +
        '<span class="gx-meta"><span>' + esc(s.date) + '</span><span>' +
        (d >= 0 ? (d === 0 ? '오늘' : 'D-' + d) : '지남') + '</span></span></span>' +
        '<button type="button" class="gdel-x" data-gexdel="' + esc(s.id) + '" aria-label="삭제">×</button></div>';
    });
    h += '</div>';
  }

  h += '<h3 class="gx-h">앱이 넣어둔 일정</h3>';
  var prov = providedExams();
  if(!prov.length){
    h += '<p class="gx-note">지금 학년에 해당하는 일정이 파일에 없어요.</p>';
  }else{
    h += '<div class="gx-list">';
    prov.forEach(function(e){
      var d = daysUntil(e.date);
      h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
        '<span class="gx-name">' + esc(e.name) +
        (e.hidden ? '<span class="gx-flag">숨김</span>' : '') +
        (e.moved ? '<span class="gx-flag">날짜 고침</span>' : '') + '</span>' +
        '<span class="gx-meta"><span>' + esc(e.date) + '</span>' +
        '<span>' + (d >= 0 ? (d === 0 ? '오늘' : 'D-' + d) : '지남') + '</span>' +
        (e.host ? '<span>' + esc(e.host) + '</span>' : '') + '</span></span>' +
        '<button type="button" class="gdel-x" data-gexedit="' + esc(e.id) + '" aria-label="고치기">⋯</button></div>';
    });
    h += '</div>';
  }
  h += '<p class="gx-note">학력평가 일정은 시행 전에 바뀔 수 있어요. 학교 공지를 확인하세요. 파일에 없는 일정은 앱이 만들지 않아요.</p>';

  var adm = admissionItems();
  if(adm.length){
    h += '<h3 class="gx-h">입시 일정</h3><div class="gx-list">';
    adm.forEach(function(e){
      var d = daysUntil(e.date);
      h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
        '<span class="gx-name">' + esc(e.name) + '</span>' +
        '<span class="gx-meta"><span>' + esc(e.date) + '</span><span>' +
        (d >= 0 ? 'D-' + d : '지남') + '</span></span></span></div>';
    });
    h += '</div>';
    h += '<p class="gx-note">' + esc((EXAM_SCHEDULE.admission_2029 || {}).audience || '') + ' 기준이에요.</p>';
  }
  return h;
}

function scExamAdd(){
  var f = gs.examForm || {};
  var h = '<p class="gx-lead">학교 지필고사는 학교마다 달라서 직접 넣어야 해요.</p>';
  h += '<div class="gx-field"><div><label for="exSem">학기</label></div>' +
    '<select id="exSem" class="gx-sel">' + SEM_IDS.map(function(id){
      return '<option value="' + id + '"' + (f.sem === id ? ' selected' : '') + '>' + semLabel(id) + '</option>';
    }).join('') + '</select></div>';
  h += '<div class="gx-field"><div><label for="exPart">구분</label></div>' +
    '<select id="exPart" class="gx-sel">' +
    '<option value="midterm"' + (f.part === 'midterm' ? ' selected' : '') + '>중간고사</option>' +
    '<option value="final"' + (f.part === 'final' ? ' selected' : '') + '>기말고사</option></select></div>';
  h += '<div class="gx-field"><div><label for="exDate">날짜</label><p>시험 첫날로 넣으면 돼요.</p></div>' +
    '<input type="date" id="exDate" class="gx-sel" value="' + esc(f.date || '') + '"></div>';
  h += '<div class="gx-acts" style="margin-top:12px"><button type="button" class="btn" data-gexsave>넣기</button></div>';
  return h;
}

function saveSchoolExam(){
  var sem = $('#exSem').value, part = $('#exPart').value, date = $('#exDate').value;
  if(!date){ gToast('날짜를 넣어주세요'); return; }
  var dup = schoolExams().filter(function(s){ return s.sem === sem && s.part === part; })[0];
  if(dup){ dup.date = date; }
  else{
    user.schedule.push({id:'sch-' + Date.now(), kind:'school', sem:sem, part:part, date:date});
  }
  saveUser();
  gs.examForm = null;
  gGo('list'); renderDday();
  gToast(dup ? '날짜를 고쳤어요' : '넣었어요');
}
function delSchoolExam(id){
  user.schedule = user.schedule.filter(function(s){ return s.id !== id; });
  saveUser(); gRender(); renderDday();
}
function editProvided(ref){
  var e = providedExams().filter(function(x){ return x.id === ref; })[0];
  if(!e) return;
  gModal({
    title: e.name,
    body: '<p>앱이 넣어둔 일정이에요. 학교 공지와 다르면 날짜를 고치거나 숨길 수 있어요.</p>' +
      '<p class="gx-note">파일 기준 날짜: ' + esc(e.origDate) + '</p>' +
      '<div class="gx-field"><div><label for="ovDate">날짜</label></div>' +
      '<input type="date" id="ovDate" class="gx-sel" value="' + esc(e.date) + '"></div>',
    buttons: [
      {label:'저장', main:true, run:function(){
        var v = $('#ovDate').value;
        setOverride(ref, {date:v || null, hidden:false});
        gModalClose(); gRender(); renderDday(); gToast('고쳤어요');
      }},
      {label: e.hidden ? '다시 보이기' : '숨기기', run:function(){
        setOverride(ref, {hidden:!e.hidden});
        gModalClose(); gRender(); renderDday();
      }},
      {label:'되돌리기', run:function(){
        user.schedule = user.schedule.filter(function(s){ return !(s.kind === 'override' && s.ref === ref); });
        saveUser(); gModalClose(); gRender(); renderDday(); gToast('파일 기준으로 되돌렸어요');
      }}
    ]
  });
}
function setOverride(ref, patch){
  var ov = scheduleOverride(ref);
  if(!ov){ ov = {id:'ovr-' + ref, kind:'override', ref:ref}; user.schedule.push(ov); }
  if(patch.date !== undefined) ov.date = patch.date;
  if(patch.hidden !== undefined) ov.hidden = patch.hidden;
  saveUser();
}

function examsClick(e){
  var t;
  if(e.target.closest('[data-gexadd]')){ gs.examForm = {sem:currentSemId() || '1-1', part:'midterm', date:''}; gGo('add'); return true; }
  if(e.target.closest('[data-gexsave]')){ saveSchoolExam(); return true; }
  if((t = e.target.closest('[data-gexdel]'))){ delSchoolExam(t.getAttribute('data-gexdel')); return true; }
  if((t = e.target.closest('[data-gexedit]'))){ editProvided(t.getAttribute('data-gexedit')); return true; }
  return false;
}
