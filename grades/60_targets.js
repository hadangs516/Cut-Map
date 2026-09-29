/* ---------- 성적 관리 · 목표 설정과 검색 ----------
   카탈로그(catalog.json)는 용량이 커서 앱을 켤 때가 아니라
   이 화면을 처음 열 때 불러온다. (SPEC_대학맵.md 5-1) */

var CATALOG = null, CAT_STATE = 'idle';   /* idle | loading | ready | error */
var SYNONYMS = /*__SYNONYMS__*/null;

function loadCatalog(then){
  if(CAT_STATE === 'ready'){ then && then(); return; }
  if(CAT_STATE === 'loading') return;
  CAT_STATE = 'loading';
  gRender();
  fetch('catalog.json').then(function(r){
    if(!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then(function(j){
    CATALOG = j; CAT_STATE = 'ready';
    then && then();
    gRender();
  }).catch(function(){
    CAT_STATE = 'error';
    gRender();
  });
}

/* ----- 목표(별표) ----- */
function targets(){
  if(!user.targets || typeof user.targets !== 'object') user.targets = {};
  if(!Array.isArray(user.targets.univIds)) user.targets.univIds = [];
  if(!Array.isArray(user.targets.majorIds)) user.targets.majorIds = [];
  if(!Array.isArray(user.targets.admissionTypes)) user.targets.admissionTypes = [];
  return user.targets;
}
function majorId(univ, name){ return univ + '|' + name; }
function isStarUniv(name){ return targets().univIds.indexOf(name) >= 0; }
function isStarMajor(id){ return targets().majorIds.indexOf(id) >= 0; }
function toggleStarUniv(name){
  var t = targets(), i = t.univIds.indexOf(name);
  if(i >= 0) t.univIds.splice(i, 1); else t.univIds.push(name);
  saveUser();
  refreshMarkers();
  if(state.view === 'rank') renderRank();
}
function toggleStarMajor(id){
  var t = targets(), i = t.majorIds.indexOf(id);
  if(i >= 0) t.majorIds.splice(i, 1); else t.majorIds.push(id);
  saveUser();
  if(state.view === 'rank') renderRank();
}
/* 목록 탭 분야 기본값에 쓸 내 희망 학과의 계열. (SPEC 3-2) */
function targetSeries(){
  if(CAT_STATE !== 'ready') return [];
  var want = {}, out = [];
  targets().majorIds.forEach(function(id){ want[id] = 1; });
  CATALOG.depts.forEach(function(d){
    if(want[majorId(d.univ, d.name)] && out.indexOf(d.series) < 0) out.push(d.series);
  });
  return out;
}

/* ----- 검색 (SPEC 5-3) -----
   학과명에 글자가 없어도 별칭·주요교과목·관련직업으로 걸린다.
   결과마다 왜 나왔는지 적는다. 순서는 학과명 > 별칭 > 교과목·직업. */
function expandQuery(q){
  var words = [q], syn = SYNONYMS || {};
  var key = q.replace(/\s+/g, '');
  ['major', 'univ'].forEach(function(g){
    var m = syn[g] || {};
    Object.keys(m).forEach(function(k){
      if(k.toUpperCase() === key.toUpperCase()) m[k].forEach(function(w){ if(words.indexOf(w) < 0) words.push(w); });
    });
  });
  return words;
}
function searchCatalog(q){
  if(CAT_STATE !== 'ready' || !q) return [];
  var words = expandQuery(q), first = words[0], alias = words.slice(1), out = [], seen = {};
  /* 짧은 줄임말을 그대로 찾으면 엉뚱하게 걸린다("의대"가 "한의대학교"에 맞는 식).
     별칭이 있는 줄임말은 별칭을 먼저 쓰고, 글자 그대로의 매칭은 3글자 이상일 때만 본다. */
  var literalOk = first.length >= 3 || !alias.length;
  CATALOG.depts.forEach(function(d){
    var why = null, rank = 99, i, hit;
    if(literalOk && d.name.indexOf(first) >= 0){ rank = 0; }
    if(rank === 99){
      for(i = 0; i < alias.length; i++){
        if(d.name.indexOf(alias[i]) >= 0){ why = '"' + q + '"과 관련: ' + alias[i]; rank = 1; break; }
      }
    }
    if(rank === 99 && literalOk && d.univ.indexOf(first) >= 0){ why = '대학 이름'; rank = 2; }
    if(rank === 99){
      for(i = 0; i < alias.length; i++){
        if(d.univ.indexOf(alias[i]) >= 0){ why = '대학 이름: ' + alias[i]; rank = 3; break; }
      }
    }
    if(rank === 99){
      hit = d.subjects.filter(function(s){ return words.some(function(w){ return s.indexOf(w) >= 0; }); })[0];
      if(hit){ why = '주요교과목: ' + hit; rank = 4; }
    }
    if(rank === 99){
      hit = d.jobs.filter(function(s){ return words.some(function(w){ return s.indexOf(w) >= 0; }); })[0];
      if(hit){ why = '관련직업: ' + hit; rank = 5; }
    }
    if(rank === 99) return;
    var id = majorId(d.univ, d.name);
    if(seen[id]) return;
    seen[id] = 1;
    out.push({d:d, why:why, rank:rank});
  });
  out.sort(function(a, b){
    if(a.rank !== b.rank) return a.rank - b.rank;
    if(a.d.univ !== b.d.univ) return a.d.univ < b.d.univ ? -1 : 1;
    return a.d.name < b.d.name ? -1 : 1;
  });
  return out.slice(0, 120);
}

/* ----- 화면 ----- */
var TARGET_SCREENS = {
  targets: {title:'목표 설정', parent:'home', render:function(){ return scTargets(); }},
  tsearch: {title:'목표 대학·학과 고르기', parent:'targets', render:function(){ return scTargetSearch(); }}
};

var ADMISSION_TYPES = [
  {id:'jeongsi', name:'정시'}, {id:'jonghap', name:'학생부종합'},
  {id:'gyogwa', name:'학생부교과'}, {id:'nonsul', name:'논술'}
];

function scTargets(){
  var t = targets(), vt = viewType();
  var h = '<h3 class="gx-h">지도에서 볼 전형</h3>';
  h += '<div class="seg" role="group" style="margin-bottom:4px">' +
    '<button type="button" data-vtv="jong" aria-pressed="' + (vt === 'jong') + '">학생부종합</button>' +
    '<button type="button" data-vtv="gyo" aria-pressed="' + (vt === 'gyo') + '">학생부교과</button>' +
    '</div><p class="gx-note">지도의 "내 기준" 패널과 같은 값이에요. 정시·논술은 준비 중이에요.</p>';

  h += '<h3 class="gx-h">지망 전형 (기록용)</h3><div class="gx-grid">';
  ADMISSION_TYPES.forEach(function(a){
    var on = t.admissionTypes.indexOf(a.id) >= 0;
    h += '<button type="button" class="gx-tile' + (on ? ' on' : '') + '" data-atype="' + a.id + '">' + esc(a.name) + '</button>';
  });
  h += '</div><p class="gx-note">여러 개 고를 수 있어요. 지도 분류에는 위의 "지도에서 볼 전형"만 써요.</p>';

  h += '<h3 class="gx-h">목표 대학·학과</h3>';
  h += '<div class="gx-acts" style="margin-bottom:10px"><button type="button" class="btn" data-gnav="tsearch">+ 찾아서 추가</button></div>';
  if(!t.univIds.length && !t.majorIds.length){
    h += '<div class="gx-empty">아직 고른 목표가 없어요.<br>안 골라도 지도와 목록은 그대로 써요.</div>';
  }else{
    if(t.univIds.length){
      h += '<div class="gx-list">';
      t.univIds.forEach(function(n){
        h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
          '<span class="gx-name">' + esc(n) + '<span class="gx-badge">대학</span></span>' +
          '<span class="gx-meta"><span>지도에서 항상 보여요</span></span></span>' +
          '<button type="button" class="gdel-x" data-unstar-u="' + esc(n) + '" aria-label="목표에서 빼기">×</button></div>';
      });
      h += '</div>';
    }
    if(t.majorIds.length){
      h += '<div class="gx-list">';
      t.majorIds.forEach(function(id){
        var p = id.split('|');
        h += '<div class="gx-row" style="cursor:default"><span class="gx-main">' +
          '<span class="gx-name">' + esc(p[1] || id) + '</span>' +
          '<span class="gx-meta"><span>' + esc(p[0] || '') + '</span></span></span>' +
          '<button type="button" class="gdel-x" data-unstar-m="' + esc(id) + '" aria-label="목표에서 빼기">×</button></div>';
      });
      h += '</div>';
    }
  }
  h += '<p class="gx-note">전부 선택 사항이에요. 목표를 안 골라도 앱은 그대로 동작해요.</p>';
  return h;
}

function scTargetSearch(){
  if(CAT_STATE === 'idle'){ loadCatalog(); }
  if(CAT_STATE === 'loading') return '<div class="gx-empty">전국 학과 목록을 불러오는 중이에요…</div>';
  if(CAT_STATE === 'error'){
    return '<div class="gx-empty">학과 목록 파일(catalog.json)을 불러오지 못했어요.<br>' +
      'it-major-map.html과 같은 폴더에 두고 웹서버로 열어야 해요.</div>';
  }
  var q = gs.tq || '';
  var h = '<div class="gx-add"><input type="text" id="tqInput" value="' + esc(q) + '" placeholder="학과, 대학, 직업으로 찾기 (예: IT, 컴공, 간호)" aria-label="검색어">' +
    '<button type="button" class="btn" data-tsearch>찾기</button></div>';
  h += '<p class="gx-note" style="margin-top:0">학과 이름에 없는 말이어도 관련 있으면 나와요. ' +
    '전국 ' + CATALOG.univs.length + '개 학교, ' + CATALOG.depts.length + '개 학과에서 찾아요.</p>';
  if(CATALOG.incomplete) h += '<p class="gx-warn" style="margin-top:10px">원본 파일이 잘려 있어서 빠진 학교와 학과가 있어요. 기준 연도 ' + CATALOG.baseYear + '.</p>';
  if(!q) return h;

  var res = searchCatalog(q);
  if(!res.length) return h + '<div class="gx-empty">"' + esc(q) + '"에 맞는 학과가 없어요.</div>';
  h += '<div class="gx-list">';
  res.forEach(function(x){
    var d = x.d, id = majorId(d.univ, d.name), on = isStarMajor(id);
    h += '<button type="button" class="gx-row" data-star-m="' + esc(id) + '">' +
      '<span class="gx-main"><span class="gx-name">' + esc(d.name) +
      '<span class="gx-badge">' + esc(d.series) + '</span>' +
      (d.isDivision ? '<span class="gx-flag">학부</span>' : '') + '</span>' +
      '<span class="gx-meta"><span>' + esc(d.univ) + '</span>' +
      (x.why ? '<span>' + esc(x.why) + '</span>' : '') + '</span></span>' +
      '<span class="gx-arrow">' + (on ? '★' : '☆') + '</span></button>';
  });
  h += '</div>';
  h += '<p class="gx-note">별을 누르면 목표에 담겨요. 학교 전체를 목표로 하려면 아래에서 고르세요.</p>';
  var unames = [];
  res.forEach(function(x){ if(unames.indexOf(x.d.univ) < 0) unames.push(x.d.univ); });
  h += '<div class="gx-list">';
  unames.slice(0, 12).forEach(function(n){
    h += '<button type="button" class="gx-row" data-star-u="' + esc(n) + '">' +
      '<span class="gx-main"><span class="gx-name">' + esc(n) + '<span class="gx-badge">대학</span></span></span>' +
      '<span class="gx-arrow">' + (isStarUniv(n) ? '★' : '☆') + '</span></button>';
  });
  h += '</div>';
  return h;
}

function targetsClick(e){
  var t;
  if((t = e.target.closest('[data-atype]'))){
    var id = t.getAttribute('data-atype'), arr = targets().admissionTypes, i = arr.indexOf(id);
    if(i >= 0) arr.splice(i, 1); else arr.push(id);
    saveUser(); gRender();
    return true;
  }
  if((t = e.target.closest('[data-star-m]'))){ toggleStarMajor(t.getAttribute('data-star-m')); gRender(); return true; }
  if((t = e.target.closest('[data-star-u]'))){ toggleStarUniv(t.getAttribute('data-star-u')); gRender(); return true; }
  if((t = e.target.closest('[data-unstar-m]'))){ toggleStarMajor(t.getAttribute('data-unstar-m')); gRender(); return true; }
  if((t = e.target.closest('[data-unstar-u]'))){ toggleStarUniv(t.getAttribute('data-unstar-u')); gRender(); return true; }
  if(e.target.closest('[data-tsearch]')){
    var el = $('#tqInput'); gs.tq = el ? el.value.trim() : '';
    gRender();
    return true;
  }
  if((t = e.target.closest('[data-vtv]'))){ setViewType(t.getAttribute('data-vtv')); gRender(); return true; }
  return false;
}
function targetsKey(e){
  if(e.key === 'Enter' && e.target.id === 'tqInput'){
    e.preventDefault();
    gs.tq = e.target.value.trim();
    gRender();
    return true;
  }
  return false;
}
