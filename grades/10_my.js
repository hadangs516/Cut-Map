/* ---------- 성적 관리 · 마이 탭 ---------- */

/* 화면 정의. parent가 null이면 뒤로가기 줄을 숨긴다. (SPEC 1-1) */
var MY_SCREENS = {
  home:     {title:'마이',            parent:null,       render:function(){ return scHome(); }},
  term:     {title:'내 학년·학기',     parent:'home',     render:function(){ return scTerm(); }},
  courses:  {title:'내 과목',          parent:'home',     render:function(){ return scSems(); }},
  sem:      {title:function(){ return semLabel(gs.sem); }, parent:'courses', render:function(){ return scSem(); }},
  areas:    {title:'교과 선택',        parent:'sem',      render:function(){ return scAreas(); }},
  pick:     {title:function(){ return (CM_AREA[gs.area] || {}).name || '과목 선택'; }, parent:'areas', render:function(){ return scPick(); }},
  edit:     {title:'과목 설정',        parent:'sem',      render:function(){ return scEdit(); }},
  settings: {title:'설정',             parent:'home',     render:function(){ return scSettings(); }},
  reset:    {title:'내 정보 초기화',    parent:'settings', render:function(){ return scReset(); }},
  backup:   {title:'백업 내보내기·가져오기', parent:'settings', render:function(){ return scBackup(); }},
  skin:     {title:'화면 테마',        parent:'settings', render:function(){ return scSkin(); }},
  about:    {title:'앱 정보',          parent:'settings', render:function(){ return scAbout(); }}
};

var RESET_SCOPES = [
  {id:'scores',   label:'성적',                 desc:'입력한 시험 결과와 등급'},
  {id:'courses',  label:'과목·학기',            desc:'학기별 과목 구성과 학점'},
  {id:'targets',  label:'목표 설정',            desc:'지망 전형, 목표 대학·학과'},
  {id:'schedule', label:'내가 입력한 시험 일정', desc:'학교 지필고사 등 직접 넣은 일정'},
  {id:'all',      label:'전체',                 desc:'학년·학기까지 모두 지우고 처음 상태로'}
];

function row(attrs, name, meta, tags, arrow){
  return '<button type="button" class="gx-row" ' + attrs + '><span class="gx-main">' +
    '<span class="gx-name">' + name + (tags || '') + '</span>' +
    (meta ? '<span class="gx-meta">' + meta + '</span>' : '') +
    '</span><span class="gx-arrow">' + (arrow || '›') + '</span></button>';
}
function rowOff(name, why){
  return '<button type="button" class="gx-row" disabled><span class="gx-main">' +
    '<span class="gx-name">' + esc(name) + '</span>' +
    '<span class="gx-meta"><span>' + esc(why) + '</span></span></span></button>';
}

/* ----- 마이 홈 ----- */
function scHome(){
  var p = user.profile, total = 0, semN = 0;
  SEM_IDS.forEach(function(id){ var n = semCourses(id).length; if(n){ semN++; total += n; } });
  var h = '';
  if(backupAlertDue()){
    h += '<div class="gx-alert"><span>성적을 넣은 지 꽤 됐는데 백업이 없어요. 기기를 바꾸면 사라져요.</span>' +
      '<span class="gx-alert-btns"><button type="button" class="btn" data-gnav="backup">백업하기</button>' +
      '<button type="button" class="gdel-x" data-galertoff aria-label="닫기">×</button></span></div>';
  }
  h += '<div class="gx-list">';
  h += row('data-gnav="term"', '내 학년·학기',
    '<span>' + esc(hasProfile() ? gradeTermLabel(p.currentGrade, p.currentTerm) : '아직 안 골랐어요') + '</span>');
  h += row('data-gnav="courses"', '내 과목',
    '<span>' + (total ? semN + '개 학기 · ' + total + '과목' : '등록한 과목이 없어요') + '</span>');
  var sch = user.schedule.filter(function(s){ return s.kind === 'school'; }).length;
  h += row('data-gnav="list"', '시험 일정',
    '<span>' + (sch ? '내가 넣은 학교 시험 ' + sch + '개' : '학교 시험을 넣어보세요') + '</span>');
  var tg = targets();
  h += row('data-gnav="targets"', '목표 설정',
    '<span>' + ((tg.univIds.length + tg.majorIds.length)
      ? '대학 ' + tg.univIds.length + ' · 학과 ' + tg.majorIds.length
      : '전형과 목표 대학·학과') + '</span>');
  h += rowOff('권장과목', '준비 중');
  h += row('data-gnav="settings"', '설정', '<span>초기화, 백업, 앱 정보</span>');
  h += '</div>';
  h += '<p class="gx-note">성적 입력과 성적 분석은 다음 단계에서 들어와요. 지금은 학년·학기와 과목을 넣어둘 수 있어요.</p>';
  return h;
}

/* ----- 내 학년·학기 ----- */
function scTerm(){
  var p = user.profile, first = !hasProfile();
  var h = first
    ? '<p class="gx-lead">먼저 지금 학년과 학기를 골라주세요. 나중에 언제든 바꿀 수 있어요.</p>'
    : '<p class="gx-lead">지금 학년과 학기예요. 눌러서 바꿀 수 있어요.</p>';
  h += '<div class="gx-grid">';
  GRADE_OPTS.forEach(function(o){
    var on = hasProfile() && p.currentGrade === o.g && p.currentTerm === o.t;
    h += '<button type="button" class="gx-tile' + (on ? ' on' : '') + '" data-gterm="' + o.g + ':' + o.t + '">' +
      esc(gradeTermLabel(o.g, o.t)) + (on ? '<b>지금 이걸로 저장돼 있어요</b>' : '') + '</button>';
  });
  h += '</div>';
  h += '<p class="gx-note">학기 기준은 3월 1일과 8월 1일이에요. 학교마다 개학일이 달라서 앱이 마음대로 바꾸지 않고, 날짜가 지나면 한 번 물어봐요.</p>';
  return h;
}

/* ----- 내 과목: 학기 목록 ----- */
function scSems(){
  var cur = currentSemId();
  var h = '<div class="gx-list">';
  SEM_IDS.forEach(function(id){
    var n = semCourses(id).length, isNow = (id === cur);
    h += '<button type="button" class="gx-row' + (isNow ? ' now' : '') + '" data-gsem="' + id + '">' +
      '<span class="gx-main"><span class="gx-name">' + semLabel(id) +
      (isNow ? '<span class="gx-now">현재</span>' : '') + '</span>' +
      '<span class="gx-meta"><span>' + (n ? n + '과목' : '비어 있음') + '</span></span></span>' +
      '<span class="gx-arrow">›</span></button>';
  });
  h += '</div>';
  if(!cur && user.profile.currentGrade === 'grad') h += '<p class="gx-note">졸업·N수로 저장돼 있어서 현재 학기 표시가 없어요.</p>';
  h += '<p class="gx-note">학기마다 과목과 학점을 따로 저장해요. 다른 학기를 고쳐도 지난 학기 기록은 그대로 남아요.</p>';
  return h;
}

/* ----- 내 과목: 한 학기 ----- */
function scSem(){
  var list = semCourses(gs.sem), term = gs.sem.split('-')[1], isG1 = gs.sem.charAt(0) === '1';
  var h = '<p class="gx-warn">과목 목록은 아직 <b>원자료로 검증하지 않은 임시 데이터</b>예요. 과목명·학점·등급 산출 여부가 실제와 다를 수 있어요.</p>';
  h += '<div class="gx-acts"><button type="button" class="btn" data-gadd>+ 과목 추가</button>';
  if(isG1) h += '<button type="button" class="btn" data-gcommon>' + term + '학기 공통과목 불러오기</button>';
  h += '</div>';
  if(!list.length){
    h += '<div class="gx-empty">등록한 과목이 없어요.<br>위 버튼으로 추가하세요.</div>';
    h += '<p class="gx-note">학교마다 편성이 달라서 자동으로 채워 넣지 않아요.</p>';
    return h;
  }
  h += '<div class="gx-list">';
  list.forEach(function(c, i){
    var tags = '', b = courseBadge(c);
    if(b) tags += '<span class="gx-badge">' + esc(b) + '</span>';
    if(!c.hasGrade) tags += '<span class="gx-flag">등급 없음</span>';
    if(c.isJoint) tags += '<span class="gx-flag">공동</span>';
    if(c.credits == null) tags += '<span class="gx-flag">학점 미입력</span>';
    var meta = '<span>' + esc(courseArea(c) || '교과 미지정') + '</span>' +
      '<span>' + (c.credits == null ? '학점 ?' : c.credits + '학점') + '</span>';
    if(c.customName) meta += '<span>권장과목 매칭 제외</span>';
    h += row('data-gedit="' + i + '"', esc(courseName(c)), meta, tags);
  });
  h += '</div>';
  var cr = 0, gr = 0, miss = 0;
  list.forEach(function(c){
    if(c.credits == null) miss++; else cr += Number(c.credits) || 0;
    if(c.hasGrade) gr++;
  });
  h += '<div class="gx-sum">' + list.length + '과목 · 학점 합계 ' + cr +
    (miss ? ' (학점 미입력 ' + miss + '과목 제외)' : '') + ' · 등급 산출 ' + gr + '과목</div>';
  return h;
}

/* ----- 교과 선택 ----- */
function scAreas(){
  var h = '<div class="gx-grid">';
  COURSE_MASTER.areas.forEach(function(a){
    if(a.group !== gs.group) return;
    h += '<button type="button" class="gx-tile" data-garea="' + a.id + '">' + esc(a.name) +
      '<b>' + (CM_BY_AREA[a.id] || []).length + '과목</b></button>';
  });
  if(gs.group === 'main') h += '<button type="button" class="gx-tile" data-ggroup="etc">그 외<b>체육·예술·기술가정·제2외국어·한문·교양</b></button>';
  h += '</div>';
  h += '<p class="gx-note">화면의 교과 묶음은 앱에서 쓰기 편하게 나눈 것이라 교육과정 고시의 교과(군) 구분과는 달라요.</p>';
  return h;
}

/* ----- 과목 선택 ----- */
function scPick(){
  var list = CM_BY_AREA[gs.area] || [], have = {};
  semCourses(gs.sem).forEach(function(c){ if(c.courseCode) have[c.courseCode] = 1; });
  var h = '<p class="gx-note" style="margin:0 0 12px">누르면 ' + esc(semLabel(gs.sem)) + '에 바로 추가돼요. 여러 개를 이어서 고를 수 있어요.</p>';
  h += '<div class="gx-list">';
  list.forEach(function(c){
    var added = !!have[c.code];
    var tags = '<span class="gx-badge">' + esc(CM_BADGE[c.type] || '') + '</span>';
    if(c.gradeType !== 'rank') tags += '<span class="gx-flag">등급 없음</span>';
    if(c.source !== 'spec-2-1') tags += '<span class="gx-flag">미검증</span>';
    var meta = '<span>' + (c.credits == null ? '학점 미확인' : c.credits + '학점') + '</span>' +
      (added ? '<span>추가됨</span>' : '');
    h += '<button type="button" class="gx-row" data-gpick="' + c.code + '"' + (added ? ' disabled' : '') + '>' +
      '<span class="gx-main"><span class="gx-name">' + esc(c.name) + tags + '</span>' +
      '<span class="gx-meta">' + meta + '</span></span>' +
      '<span class="gx-arrow">' + (added ? '✓' : '+') + '</span></button>';
  });
  h += '</div>';
  h += '<div class="gx-add"><input type="text" id="gxCustom" maxlength="20" placeholder="기타 (목록에 없는 과목)" aria-label="목록에 없는 과목 이름">' +
    '<button type="button" class="btn" data-gcustom>추가</button></div>';
  h += '<p class="gx-note" style="margin-top:0">기타로 넣은 과목은 권장과목 매칭에서 빠져요. "미검증"은 원자료로 확인하지 못한 과목이에요.</p>';
  return h;
}

/* ----- 과목 설정 ----- */
function scEdit(){
  var c = semCourses(gs.sem)[gs.edit];
  if(!c) return '<div class="gx-empty">과목을 찾지 못했어요.</div>';
  var b = courseBadge(c), area = courseArea(c);
  var h = '<p class="gx-lead"><b>' + esc(courseName(c)) + '</b>' +
    (b ? ' <span class="gx-badge">' + esc(b) + '</span>' : '') + (area ? ' · ' + esc(area) : '') + '</p>';
  h += '<div class="gx-field"><div><label for="gxCredits">학점</label>' +
    '<p>' + (c.credits == null ? '이 과목은 기본 학점을 확인하지 못했어요. 학교 편성표를 보고 넣어주세요.' : '일반 규칙을 적용한 기본값이에요. 학교 편성에 맞게 고치세요.') + '</p></div>' +
    '<input type="number" id="gxCredits" min="1" max="8" step="1" placeholder="미입력" value="' + (c.credits == null ? '' : c.credits) + '"></div>';
  h += '<div class="gx-field"><div><label for="gxHasGrade">등급 산출</label>' +
    '<p>석차등급이 나오는 과목이면 켜 두세요.</p></div>' +
    '<input type="checkbox" id="gxHasGrade"' + (c.hasGrade ? ' checked' : '') + '></div>';
  h += '<div class="gx-field"><div><label for="gxJoint">공동교육과정</label>' +
    '<p>켜면 등급 산출을 자동으로 꺼요. 필요하면 다시 켜세요.</p></div>' +
    '<input type="checkbox" id="gxJoint"' + (c.isJoint ? ' checked' : '') + '></div>';
  if(c.customName) h += '<p class="gx-note">직접 입력한 과목이라 나중에 권장과목과 대조할 때 빠져요.</p>';
  h += '<button type="button" class="gx-danger" data-gdel>이 학기에서 삭제</button>';
  return h;
}

/* ----- 설정 ----- */
function scSettings(){
  var formUrl = (APP_META.links || {}).feedbackForm || '';
  var h = '<div class="gx-list">';
  h += row('data-gnav="backup"', '백업 내보내기·가져오기', '<span>파일로 저장하고 되돌려요</span>');
  h += row('data-gnav="skin"', '화면 테마', '<span>' + esc(skinName(currentSkin())) + '</span>');
  h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
    '<span class="gx-name">등급 표시 단위</span>' +
    '<span class="gx-meta"><span>' + esc(scaleUnit()) + '</span></span></span>' +
    '<label class="sc-scale" style="margin:0;padding:0;border:0;background:none">' +
    '<input type="checkbox" data-scale' + (isG9() ? ' checked' : '') + ' aria-label="9등급 환산으로 보기"></label></div>';
  h += row('data-gterm-reset', '학기 전환 확인 다시 켜기',
    '<span>' + (user.profile.dismissedTermIndex == null ? '지금은 꺼둔 기록이 없어요' : '"유지"로 꺼둔 기록이 있어요') + '</span>', '', '↺');
  h += row('data-gnav="about"', '앱 정보', '<span>버전, 업데이트일, 데이터 기준일</span>');
  h += formUrl
    ? row('data-gform', '의견 보내기', '<span>오류 제보, 기능 제안</span>', '', '↗')
    : rowOff('의견 보내기', '폼 주소가 아직 없어서 준비 중이에요');
  h += row('data-ginfo', '출처·면책 안내', '<span>지도의 안내 탭으로 가요</span>', '', '↗');
  h += rowOff('개인정보처리방침·이용약관', '기능이 완성된 뒤에 씁니다');
  /* 되돌릴 수 없는 동작이라 맨 아래에 두고 위험 버튼과 같은 색 토큰을 쓴다. */
  h += row('data-gnav="reset" data-danger', '내 정보 초기화', '<span>지울 범위를 골라요</span>');
  h += '</div>';
  return h;
}

/* ----- 내 정보 초기화 ----- */
function scReset(){
  var s = gs.resetScope, all = !!s.all;
  var h = '<p class="gx-lead">지울 범위를 고르세요. 지운 자료는 되돌릴 수 없어요.</p>';
  h += '<div class="gx-acts" style="margin-bottom:12px"><button type="button" class="btn" data-gexport>먼저 백업 파일 받기</button></div>';
  RESET_SCOPES.forEach(function(sc){
    var on = sc.id === 'all' ? all : (all || !!s[sc.id]);
    h += '<div class="gx-field"><div><label for="rs-' + sc.id + '">' + esc(sc.label) + '</label>' +
      '<p>' + esc(sc.desc) + '</p></div>' +
      '<input type="checkbox" id="rs-' + sc.id + '" data-gscope="' + sc.id + '"' +
      (on ? ' checked' : '') + (all && sc.id !== 'all' ? ' disabled' : '') + '></div>';
  });
  /* 박스 없이 체크박스와 글자만. 글자를 눌러도 켜지도록 label로 감싼다. */
  h += '<label class="gx-ack"><input type="checkbox" id="rsAck"' + (gs.resetAck ? ' checked' : '') + '>' +
    '<span>되돌릴 수 없어요</span></label>';
  var any = all || RESET_SCOPES.some(function(sc){ return s[sc.id]; });
  h += '<button type="button" class="gx-danger" data-gresetrun' +
    ((gs.resetAck && any) ? '' : ' disabled') + '>고른 자료 지우기</button>';
  return h;
}

/* ----- 백업 ----- */
function scBackup(){
  var last = user.backup && user.backup.lastBackupAt;
  var h = '<p class="gx-lead">성적은 이 기기 안에만 저장돼요. 기기를 바꾸거나 브라우저 자료를 지우면 사라지니까 가끔 파일로 받아두세요.</p>';
  h += '<div class="gx-kv"><span>마지막 백업</span><span>' + esc(last ? ymdOf(last) : '아직 없어요') + '</span></div>';
  h += '<div class="gx-acts" style="margin:12px 0"><button type="button" class="btn" data-gexport>백업 파일 내보내기</button>' +
    '<button type="button" class="btn" data-gimport>백업 파일 가져오기</button></div>';
  h += '<input type="file" id="gxFile" accept="application/json,.json" hidden>';
  h += '<div class="gx-warn">이 파일에는 내 성적이 들어 있어요. 구글 드라이브 같은 내 저장 공간에만 올리고, <b>공유 링크는 만들지 마세요.</b></div>';
  h += '<p class="gx-note">가져오기를 하면 지금 기기에 있는 자료를 덮어써요. 덮어쓰기 전에 백업 시점을 보여줄게요.</p>';
  return h;
}

/* ----- 앱 정보 ----- */
function scAbout(){
  var h = '<div class="gx-kv"><span>앱 버전</span><span>' + esc(APP_META.appVersion) + '</span></div>';
  h += '<div class="gx-kv"><span>마지막 업데이트일</span><span>' + esc(APP_META.buildDate || '알 수 없음') + '</span></div>';
  h += '<div class="gx-kv"><span>데이터 기준일</span><span>' + esc(APP_META.dataAsOf || '알 수 없음') + '</span></div>';
  h += '<p class="gx-note">마지막 업데이트일은 앱을 만든 날이고, 데이터 기준일은 입결 같은 자료를 정리한 날이에요. 둘은 다를 수 있어요.</p>';
  return h;
}

/* ----- 과목 추가·삭제 ----- */
function addCourse(code){
  var m = CM_BY_CODE[code]; if(!m) return;
  var s = ensureSem(gs.sem);
  for(var i = 0; i < s.courses.length; i++){ if(s.courses[i].courseCode === code) return; }
  s.courses.push(courseFromMaster(m));
  saveUser(); gRender();
}
function addCustomCourse(){
  var el = $('#gxCustom'); if(!el) return;
  var nm = (el.value || '').trim();
  if(!nm){ el.focus(); return; }
  var s = ensureSem(gs.sem);
  s.courses.push({courseCode:null, customName:nm, nameSnapshot:nm, area:gs.area,
    credits:4, hasGrade:true, isJoint:false});
  saveUser(); gRender();
}
/* 공통과목은 이름 끝의 1·2로 학기를 가른다. (SPEC 2-1) */
function addCommonCourses(){
  var term = gs.sem.split('-')[1];
  var s = ensureSem(gs.sem), have = {}, added = 0;
  s.courses.forEach(function(c){ if(c.courseCode) have[c.courseCode] = 1; });
  COURSE_MASTER.courses.forEach(function(m){
    if(m.type !== 'common' || have[m.code]) return;
    if(m.name.slice(-1) !== term) return;
    s.courses.push(courseFromMaster(m));
    added++;
  });
  saveUser(); gRender();
  gToast(added ? added + '개 과목을 추가했어요' : '더 추가할 공통과목이 없어요');
}
function delCourse(){
  var s = findSem(gs.sem); if(!s) return;
  var c = s.courses[gs.edit]; if(!c) return;
  gModal({
    title: '이 과목을 지울까요?',
    body: '<p><b>' + esc(courseName(c)) + '</b>을(를) ' + esc(semLabel(gs.sem)) + '에서 지워요.</p>',
    buttons: [
      {label:'지우기', main:true, run:function(){
        s.courses.splice(gs.edit, 1);
        saveUser(); gModalClose();
        gs.edit = null; gGo('sem');
      }},
      {label:'취소', run:gModalClose}
    ]
  });
}

/* ----- 초기화 실행 ----- */
function runReset(){
  var s = gs.resetScope;
  var body = s.all
    ? '<p>학년·학기를 포함해 <b>모든 자료</b>를 지워요. 지우고 나면 처음 실행한 상태가 돼요.</p>'
    : '<p>고른 자료를 지워요: <b>' + esc(RESET_SCOPES.filter(function(sc){ return s[sc.id]; })
        .map(function(sc){ return sc.label; }).join(', ')) + '</b></p>';
  gModal({
    title: '정말 지울까요?',
    body: body + '<p>되돌릴 수 없어요.</p>',
    buttons: [
      {label:'지우기', main:true, run:function(){
        if(s.all){
          user.profile = {}; user.semesters = []; user.exams = [];
          user.schedule = []; user.targets = {}; user.backup = {};
        }else{
          if(s.scores) user.exams = [];
          if(s.courses) user.semesters = [];
          if(s.targets) user.targets = {};
          if(s.schedule) user.schedule = [];
        }
        saveUser(); gModalClose();
        gs.resetScope = {}; gs.resetAck = false;
        gs.screen = hasProfile() ? 'settings' : 'term';
        gRender(); gToast('지웠어요');
      }},
      {label:'취소', run:gModalClose}
    ]
  });
}

/* ----- 이벤트 ----- */
function myClick(e){
  var t;
  if((t = e.target.closest('[data-gnav]'))){ gGo(t.getAttribute('data-gnav')); return; }
  if((t = e.target.closest('[data-gterm]'))){
    var v = t.getAttribute('data-gterm').split(':');
    var g = v[0] === 'grad' ? 'grad' : Number(v[0]);
    setProfile(g, Number(v[1]));
    gGo('home');
    gToast(gradeTermLabel(g, Number(v[1])) + '로 저장했어요');
    return;
  }
  if((t = e.target.closest('[data-gsem]'))){ gs.sem = t.getAttribute('data-gsem'); gGo('sem'); return; }
  if(e.target.closest('[data-gadd]')){ gs.group = 'main'; gGo('areas'); return; }
  if(e.target.closest('[data-gcommon]')){ addCommonCourses(); return; }
  if((t = e.target.closest('[data-ggroup]'))){ gs.group = t.getAttribute('data-ggroup'); gRender(); return; }
  if((t = e.target.closest('[data-garea]'))){ gs.area = t.getAttribute('data-garea'); gGo('pick'); return; }
  if((t = e.target.closest('[data-gpick]'))){ addCourse(t.getAttribute('data-gpick')); return; }
  if(e.target.closest('[data-gcustom]')){ addCustomCourse(); return; }
  if((t = e.target.closest('[data-gedit]'))){ gs.edit = Number(t.getAttribute('data-gedit')); gGo('edit'); return; }
  if(e.target.closest('[data-gdel]')){ delCourse(); return; }
  if(e.target.closest('[data-gterm-reset]')){
    user.profile.dismissedTermIndex = null; saveUser(); gRender();
    gToast('학기 전환 확인을 다시 켰어요');
    return;
  }
  if(e.target.closest('[data-galertoff]')){
    user.backup.dismissedAt = new Date().toISOString(); saveUser(); gRender(); return;
  }
  if(e.target.closest('[data-gexport]')){ exportBackup(); gRender(); return; }
  if(e.target.closest('[data-gimport]')){ var f = $('#gxFile'); if(f) f.click(); return; }
  if(e.target.closest('[data-gresetrun]')){ runReset(); return; }
  if(e.target.closest('[data-gform]')){
    var url = (APP_META.links || {}).feedbackForm;
    if(url) window.open(url, '_blank', 'noopener');
    return;
  }
  if(e.target.closest('[data-ginfo]')){ gExit('info'); return; }
}

function myChange(e){
  var id = e.target.id, t;
  if(id === 'gxFile'){
    if(e.target.files && e.target.files[0]) importBackupFile(e.target.files[0]);
    e.target.value = '';
    return;
  }
  if((t = e.target.closest('[data-gscope]'))){
    var k = t.getAttribute('data-gscope');
    gs.resetScope[k] = t.checked;
    gRender();
    return;
  }
  if(id === 'rsAck'){ gs.resetAck = e.target.checked; gRender(); return; }
  if(gs.screen !== 'edit') return;
  var c = semCourses(gs.sem)[gs.edit]; if(!c) return;
  if(id === 'gxCredits'){
    var raw = e.target.value.trim();
    if(raw === ''){ c.credits = null; }
    else{
      var v = Math.round(Number(raw));
      if(!(v >= 1 && v <= 8)) v = (c.credits == null ? 4 : c.credits);
      c.credits = v; e.target.value = v;
    }
    saveUser(); return;
  }
  if(id === 'gxHasGrade'){ c.hasGrade = e.target.checked; saveUser(); return; }
  if(id === 'gxJoint'){
    c.isJoint = e.target.checked;
    if(c.isJoint && c.hasGrade){
      c.hasGrade = false;
      var g = $('#gxHasGrade'); if(g) g.checked = false;
    }
    saveUser();
  }
}
