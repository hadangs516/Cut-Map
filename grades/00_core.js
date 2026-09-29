/* ---------- 성적 관리 · 공통 ----------
   build.py가 grades/ 폴더의 js를 번호 순서대로 template.html의 기존 IIFE 안에 넣는다.
   그래서 $, esc, store, reduceMotion 같은 지도 쪽 헬퍼를 그대로 쓴다. 단독 실행 파일이 아니다. */

var APP_META = /*__APP_META__*/null;
var COURSE_MASTER = /*__COURSES__*/null;

/* ----- 과목 마스터 색인 ----- */
var CM_AREA = {}, CM_BADGE = {}, CM_BY_CODE = {}, CM_BY_AREA = {};
COURSE_MASTER.areas.forEach(function(a){ CM_AREA[a.id] = a; CM_BY_AREA[a.id] = []; });
COURSE_MASTER.types.forEach(function(t){ CM_BADGE[t.id] = t.badge; });
COURSE_MASTER.courses.forEach(function(c){
  CM_BY_CODE[c.code] = c;
  if(CM_BY_AREA[c.area]) CM_BY_AREA[c.area].push(c);
});

/* ----- 학년·학기 ----- */
var SEM_IDS = ['1-1','1-2','2-1','2-2','3-1','3-2'];
var GRADE_OPTS = [
  {g:1, t:1}, {g:1, t:2}, {g:2, t:1}, {g:2, t:2}, {g:3, t:1}, {g:3, t:2}, {g:'grad', t:2}
];
function semLabel(id){ var p = String(id).split('-'); return p[0] + '학년 ' + p[1] + '학기'; }
function gradeTermLabel(g, t){ return g === 'grad' ? '졸업·N수' : (g + '학년 ' + t + '학기'); }

/* 학년도는 3월 1일에 시작한다. 3~12월은 그 해, 1~2월은 전년도. (SPEC 2-0) */
function schoolYearOf(d){ return (d.getMonth() + 1) >= 3 ? d.getFullYear() : d.getFullYear() - 1; }
/* 학기 기준일은 8월 1일. 3~7월 1학기, 8~12월 2학기, 1~2월은 지난 학년도의 2학기. */
function expectedTerm(d){
  var m = d.getMonth() + 1;
  return {schoolYear: schoolYearOf(d), term: (m >= 3 && m <= 7) ? 1 : 2};
}
function termIndex(schoolYear, term){ return schoolYear * 2 + (term - 1); }
/* 저장된 학년·학기에서 steps 학기만큼 진행한 값. 3학년 2학기를 넘으면 졸업·N수. */
function advanceTerm(grade, term, steps){
  var g = grade, t = term;
  for(var i = 0; i < steps; i++){
    if(g === 'grad') break;
    if(t === 1){ t = 2; } else { t = 1; g = g + 1; }
    if(g > 3){ g = 'grad'; t = 2; break; }
  }
  return {grade:g, term:t};
}

/* ----- 저장 (SPEC 5장 구조) ----- */
var USER_KEY = 'cutmap.user', USER_SCHEMA = 1;
var user = (function(){
  var u = store.get(USER_KEY, null);
  if(!u || typeof u !== 'object' || Array.isArray(u)) u = {};
  if(!u.profile || typeof u.profile !== 'object') u.profile = {};
  if(!Array.isArray(u.semesters)) u.semesters = [];
  if(!Array.isArray(u.exams)) u.exams = [];
  if(!Array.isArray(u.schedule)) u.schedule = [];
  if(!u.targets || typeof u.targets !== 'object') u.targets = {};
  if(!u.backup || typeof u.backup !== 'object') u.backup = {};
  u.v = USER_SCHEMA;
  return u;
})();
function saveUser(){ store.set(USER_KEY, user); }
function hasProfile(){ return !!user.profile && user.profile.currentGrade != null; }
function currentSemId(){
  var p = user.profile;
  if(!p || p.currentGrade == null || p.currentGrade === 'grad') return null;
  return p.currentGrade + '-' + p.currentTerm;
}
function setProfile(grade, term, opts){
  var exp = expectedTerm(new Date());
  var p = user.profile;
  p.currentGrade = grade;
  p.currentTerm = term;
  p.schoolYear = exp.schoolYear;
  /* 직접 고른 값이 예상 학기와 다를 수 있다. 바로 다시 묻지 않도록 이번 예상 학기는 넘긴 것으로 둔다. */
  if(!opts || opts.dismiss !== false) p.dismissedTermIndex = termIndex(exp.schoolYear, exp.term);
  saveUser();
}
function findSem(id){
  for(var i = 0; i < user.semesters.length; i++){ if(user.semesters[i].id === id) return user.semesters[i]; }
  return null;
}
function semCourses(id){ var s = findSem(id); return (s && Array.isArray(s.courses)) ? s.courses : []; }
function ensureSem(id){
  var s = findSem(id);
  if(!s){ s = {id:id, courses:[]}; user.semesters.push(s); }
  if(!Array.isArray(s.courses)) s.courses = [];
  return s;
}
/* 과목 마스터가 실제 데이터로 교체되면 courseCode가 안 맞을 수 있어서 이름을 같이 저장해 둔다. */
function courseName(c){
  if(c.customName) return c.customName;
  var m = CM_BY_CODE[c.courseCode];
  return (m && m.name) || c.nameSnapshot || '이름 없는 과목';
}
function courseBadge(c){
  if(c.customName) return '기타';
  var m = CM_BY_CODE[c.courseCode];
  return m ? (CM_BADGE[m.type] || '') : '';
}
function courseArea(c){ var a = CM_AREA[c.area]; return a ? a.name : ''; }
function courseFromMaster(m){
  return {courseCode:m.code, customName:null, nameSnapshot:m.name, area:m.area,
    credits:(m.credits == null ? null : m.credits), hasGrade:m.gradeType === 'rank', isJoint:false};
}

/* ----- 시스템 전환 연출 -----
   지도와 성적 관리가 서로 다른 시스템이라는 것을 느끼게 하려고 일부러 넣은 연출이다.
   빠르게 만들려다 뺀 것이 아니라 의도한 것이므로 지우지 말 것. (SPEC_성적관리시스템.md 0-2)
   길이는 0.5~1.5초 범위. 아래 상수 하나만 고치면 된다. 끄는 옵션은 두지 않는다. */
var TRANSITION_MS = 1000;
var TRANSITION_MIN = 500, TRANSITION_MAX = 1500;
function transitionMs(){ return Math.min(TRANSITION_MAX, Math.max(TRANSITION_MIN, TRANSITION_MS)); }

var gBusy = false;
function gTransition(dir, mid){
  if(gBusy) return;           /* 전환 중에는 입력을 막아 중복 이동을 방지한다. */
  gBusy = true;
  var box = $('#gxLoad'), msg = $('#gxLoadMsg');
  msg.textContent = (dir === 'toGrades') ? '성적 관리로 이동 중…' : '지도로 돌아가는 중…';
  box.hidden = false;
  var fade = reduceMotion ? 0 : 220;
  requestAnimationFrame(function(){ box.classList.add('on'); });
  setTimeout(function(){
    try{ mid(); }finally{
      box.classList.remove('on');
      setTimeout(function(){ box.hidden = true; gBusy = false; }, fade);
    }
  }, transitionMs());
}

/* ----- 저장하지 않은 입력 지키기 -----
   성적 입력은 저장 버튼을 눌러야 반영된다. 저장 없이 화면을 떠나려 하면 먼저 물어본다. */
function leaveGuard(go){
  if(!gs.dirty){ go(); return; }
  gModal({
    title: '저장하지 않은 입력이 있어요',
    body: '<p>지금 나가면 방금 넣은 값이 사라져요.</p>',
    buttons: [
      {label:'저장하고 나가기', main:true, run:function(){ saveDraft(); gModalClose(); gToast('저장했어요'); go(); }},
      {label:'그냥 나가기', run:function(){ gs.dirty = false; gModalClose(); go(); }},
      {label:'취소', run:gModalClose}
    ]
  });
}

/* ----- 확인 대화창 ----- */
var gModalOnKey = null;
function gModal(opt){
  var box = $('#gxModal');
  $('#gxModalTitle').textContent = opt.title || '';
  $('#gxModalBody').innerHTML = opt.body || '';
  var btns = $('#gxModalBtns');
  btns.innerHTML = (opt.buttons || []).map(function(b, i){
    return '<button type="button" data-gm="' + i + '"' + (b.main ? ' class="main"' : '') +
      (b.disabled ? ' disabled' : '') + '>' + esc(b.label) + '</button>';
  }).join('');
  gModalOnKey = opt.buttons || [];
  box.hidden = false;
  if(opt.onOpen) opt.onOpen(box);
  var f = btns.querySelector('button:not([disabled])'); if(f) f.focus();
}
function gModalClose(){ $('#gxModal').hidden = true; gModalOnKey = null; }

/* ----- 알림 한 줄 ----- */
var gToastT = 0;
function gToast(text){
  var el = document.getElementById('gxToast');
  if(!el){
    el = document.createElement('div');
    el.id = 'gxToast'; el.className = 'gx-toast'; el.setAttribute('aria-live', 'polite');
    document.body.appendChild(el);
  }
  el.textContent = text;
  el.hidden = false;
  clearTimeout(gToastT);
  gToastT = setTimeout(function(){ el.hidden = true; }, 2200);
}

/* ----- 화면 골격 ----- */
var gs = {tab:'my', screen:'home', sem:null, area:null, group:'main', edit:null, resetScope:{}, resetAck:false};
var gvEl = $('#gradesView');

/* 탭마다 화면 묶음이 따로 있다. 마이 탭은 시험 일정 화면까지 합쳐서 쓴다. */
function gScreens(){
  if(gs.tab === 'score') return SCORE_SCREENS;
  if(gs.tab === 'analysis') return ANALYSIS_SCREENS;
  var m = {};
  for(var k in MY_SCREENS) m[k] = MY_SCREENS[k];
  for(var j in EXAM_SCREENS) m[j] = EXAM_SCREENS[j];
  for(var k2 in TARGET_SCREENS) m[k2] = TARGET_SCREENS[k2];
  return m;
}
function gSetTab(tab){
  if(gs.tab === tab) return;
  gs.tab = tab;
  gs.screen = 'home';
  document.querySelectorAll('.gv-tabs button[data-gtab]').forEach(function(b){
    b.setAttribute('aria-selected', b.getAttribute('data-gtab') === tab ? 'true' : 'false');
  });
  gRender();
}
function gRender(){
  if(!gvEl) return;
  var defs = gScreens(), def = defs[gs.screen];
  if(!def){ gs.screen = 'home'; def = defs.home; }
  var title = typeof def.title === 'function' ? def.title() : def.title;
  var sub = $('#gvSub');
  /* 첫 실행의 학년·학기 화면은 되돌아갈 곳이 없으므로 뒤로가기를 숨긴다. */
  if(def.parent == null || (gs.screen === 'term' && !hasProfile())){
    sub.hidden = true;
  }else{
    sub.hidden = false;
    $('#gvCrumb').textContent = title;
  }
  var body = $('#gvBody');
  body.innerHTML = def.render();
  body.scrollTop = 0;
}
function gGo(screen){ gs.screen = screen; gRender(); }
function gBack(){
  var defs = gScreens(), def = defs[gs.screen];
  /* 교과 선택은 '그 외'를 펼친 상태에서 한 단계 되돌린다. */
  if(gs.screen === 'areas' && gs.group === 'etc'){ gs.group = 'main'; gRender(); return; }
  if(!def || def.parent == null) return;
  if(gs.screen === 'pick'){ gs.group = (CM_AREA[gs.area] || {}).group || 'main'; }
  gGo(def.parent);
}

function gEnter(){
  /* 처음 들어오면 학년·학기부터 받는다. (SPEC 2-0) */
  gs.tab = 'my';
  gs.screen = hasProfile() ? 'home' : 'term';
  gs.sem = null; gs.area = null; gs.group = 'main'; gs.edit = null;
  document.querySelectorAll('.gv-tabs button[data-gtab]').forEach(function(b){
    b.setAttribute('aria-selected', b.getAttribute('data-gtab') === 'my' ? 'true' : 'false');
  });
  gvEl.hidden = false;
  renderDday();
  gRender();
  if(hasProfile()) checkTermChange();
  var c = gvEl.querySelector('[data-gexit]'); if(c) c.focus();
}
function gOpen(){
  gTransition('toGrades', gEnter);
}
function gExit(toView){
  gTransition('toMap', function(){
    gvEl.hidden = true;
    /* 지도는 맨 처음 들어왔을 때의 화면으로 되돌린다. 저장한 자료는 그대로 둔다. */
    var changed = resetMapView();
    if(toView) setView(toView);
    var b = $('#gradesBtn'); if(b) b.focus();
    if(changed && !toView) gToast('내 성적이 반영됐어요');
  });
}

/* ----- 학기 전환 확인 (SPEC 2-0) ----- */
function checkTermChange(){
  var p = user.profile;
  if(p.currentGrade === 'grad') return;
  var exp = expectedTerm(new Date());
  var expIdx = termIndex(exp.schoolYear, exp.term);
  var curIdx = termIndex(p.schoolYear, p.currentTerm);
  if(expIdx <= curIdx) return;
  if(p.dismissedTermIndex === expIdx) return;
  var next = advanceTerm(p.currentGrade, p.currentTerm, expIdx - curIdx);
  gModal({
    title: '학기가 바뀌었나요?',
    body: '<p>지금 저장된 건 <b>' + esc(gradeTermLabel(p.currentGrade, p.currentTerm)) + '</b>이에요.' +
      ' 날짜로 보면 <b>' + esc(gradeTermLabel(next.grade, next.term)) + '</b>일 것 같아요.</p>' +
      '<p class="gx-note" style="margin:8px 0 0">학교마다 개학일이 달라서 앱이 마음대로 바꾸지 않아요.' +
      ' 바꿔도 지난 학기 기록은 그대로 남아요.</p>',
    buttons: [
      {label:'바꾸기', main:true, run:function(){
        setProfile(next.grade, next.term);
        gModalClose(); gRender();
        gToast(gradeTermLabel(next.grade, next.term) + '로 바꿨어요');
      }},
      {label:'유지', run:function(){
        p.dismissedTermIndex = expIdx; saveUser(); gModalClose();
      }},
      {label:'직접 선택', run:function(){ gModalClose(); gGo('term'); }}
    ]
  });
}

/* ----- 백업 (SPEC 6장) ----- */
/* 저장은 ISO(UTC)로 하되 화면에는 기기 시간대 날짜를 보여준다. 그냥 자르면 하루가 밀린다. */
function ymd(d){
  if(!(d instanceof Date) || isNaN(d)) return '';
  return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
}
function ymdOf(iso){ return iso ? ymd(new Date(iso)) : ''; }
/* 성적을 넣은 뒤 14일이 지나도록 백업이 없으면 알린다. 닫으면 7일 뒤에 다시. (SPEC 6장) */
var BACKUP_ALERT_DAYS = 14, BACKUP_SNOOZE_DAYS = 7;
function daysSince(iso){ return iso ? (Date.now() - new Date(iso).getTime()) / 86400000 : null; }
function backupAlertDue(){
  var b = user.backup;
  if(!b.firstEntryAt) return false;
  var since = daysSince(b.lastBackupAt || b.firstEntryAt);
  if(since == null || since < BACKUP_ALERT_DAYS) return false;
  var snoozed = daysSince(b.dismissedAt);
  return snoozed == null || snoozed >= BACKUP_SNOOZE_DAYS;
}
function backupPayload(){
  return {app:'cutmap', kind:'backup', schema:USER_SCHEMA,
    appVersion:APP_META.appVersion, exportedAt:new Date().toISOString(), user:user};
}
function exportBackup(){
  var txt = JSON.stringify(backupPayload(), null, 1);
  var name = 'cutmap-backup-' + ymd(new Date()).replace(/-/g, '') + '.json';
  var url = URL.createObjectURL(new Blob([txt], {type:'application/json'}));
  var a = document.createElement('a');
  a.href = url; a.download = name;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
  user.backup.lastBackupAt = new Date().toISOString();
  saveUser();
  gToast('백업 파일을 내려받았어요');
}
function importBackupFile(file){
  var r = new FileReader();
  r.onload = function(){
    var data;
    try{ data = JSON.parse(r.result); }catch(e){ gToast('읽을 수 없는 파일이에요'); return; }
    if(!data || data.app !== 'cutmap' || !data.user){ gToast('컷맵 백업 파일이 아니에요'); return; }
    var when = ymdOf(data.exportedAt) || '알 수 없음';
    gModal({
      title: '이 백업으로 덮어쓸까요?',
      body: '<p>백업 시점 <b>' + esc(when) + '</b> · 앱 버전 ' + esc(data.appVersion || '알 수 없음') + '</p>' +
        '<p>지금 기기에 있는 성적·과목·목표가 <b>모두 사라지고</b> 백업 내용으로 바뀌어요. 되돌릴 수 없어요.</p>',
      buttons: [
        {label:'덮어쓰기', main:true, run:function(){
          var u = data.user;
          user.profile = (u.profile && typeof u.profile === 'object') ? u.profile : {};
          user.semesters = Array.isArray(u.semesters) ? u.semesters : [];
          user.exams = Array.isArray(u.exams) ? u.exams : [];
          user.schedule = Array.isArray(u.schedule) ? u.schedule : [];
          user.targets = (u.targets && typeof u.targets === 'object') ? u.targets : {};
          user.backup = (u.backup && typeof u.backup === 'object') ? u.backup : {};
          saveUser(); gModalClose();
          gs.screen = hasProfile() ? 'home' : 'term';
          gRender(); gToast('백업을 불러왔어요');
        }},
        {label:'취소', run:gModalClose}
      ]
    });
  };
  r.readAsText(file);
}

/* ----- 이벤트 ----- */
if(gvEl){
  gvEl.addEventListener('click', function(e){
    if(gBusy) return;
    var t;
    if(e.target.closest('[data-gexit]')){ leaveGuard(function(){ gExit(); }); return; }
    if(e.target.closest('#gvBack')){ leaveGuard(gBack); return; }
    if((t = e.target.closest('[data-gtab]'))){
      var tab = t.getAttribute('data-gtab');
      leaveGuard(function(){ gSetTab(tab); });
      return;
    }
    if(e.target.closest('[data-gdday]')){ showDdayList(); return; }
    if(gs.tab === 'score'){ if(scoreClick(e)) return; }
    if(gs.tab === 'analysis'){ if(analysisClick(e)) return; }
    if(skinClick(e)) return;
    if(targetsClick(e)) return;
    if(examsClick(e)) return;
    myClick(e);
  });
  gvEl.addEventListener('input', function(e){
    if(gs.tab === 'score') scoreInput(e);
  });
  gvEl.addEventListener('change', function(e){
    if(scaleChange(e)) return;          /* 등급 단위 스위치는 어느 탭에서나 같은 값 */
    if(gs.tab === 'score'){ if(scoreChange(e)) return; }
    if(gs.tab === 'analysis'){ if(analysisChange(e)) return; }
    myChange(e);
  });
  gvEl.addEventListener('keydown', function(e){
    if(e.key === 'Enter' && e.target.id === 'gxCustom'){ e.preventDefault(); addCustomCourse(); return; }
    if(targetsKey(e)) return;
    skinKey(e);
  });

  $('#gxModal').addEventListener('click', function(e){
    var b = e.target.closest('[data-gm]');
    if(!b || !gModalOnKey) return;
    var def = gModalOnKey[Number(b.getAttribute('data-gm'))];
    if(def && def.run) def.run();
  });

  document.addEventListener('keydown', function(e){
    if(e.key !== 'Escape' || gBusy) return;
    if(!$('#gxModal').hidden) return;          /* 확인 대화창은 버튼으로만 닫는다. */
    if(!gvEl.hidden) leaveGuard(gBack);
  });
  /* 탭을 닫거나 새로고침할 때도 저장 안 된 입력을 알린다. */
  window.addEventListener('beforeunload', function(e){
    if(!gs.dirty) return;
    e.preventDefault();
    e.returnValue = '';
  });

  /* 지도 탭바의 '성적 관리'는 지도 탭 전환(setView)을 타면 안 된다.
     기존 핸들러보다 먼저 도는 캡처 단계에서 가로채 전체 화면으로 연다. */
  var viewsNav = document.querySelector('.views');
  if(viewsNav) viewsNav.addEventListener('click', function(e){
    if(!e.target.closest('button[data-view="grades"]')) return;
    e.stopPropagation();
    gOpen();
  }, true);

  var verEl = $('#appVer');
  if(verEl) verEl.textContent = 'v' + APP_META.appVersion;
}
