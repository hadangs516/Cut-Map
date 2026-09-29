/* ---------- 지도 · "내 기준" 패널과 G 연동 ----------
   build.py가 이 파일을 template.html의 기존 IIFE 안에 넣는다. 단독 실행 파일이 아니다. */

/* ----- 성적 관리에서 오는 G ----- */
function gradeG(){
  var r = (typeof computeG === 'function') ? computeG(false) : null;
  return r ? {g:r.g, source:r.source} : null;
}
function hasG(){ return !!gradeG() || G_ASSUMED != null; }

/* 지도가 실제로 쓰는 기준값. 슬라이더로 가정한 값이 있으면 그것을 먼저 쓴다. */
function basisG(){
  if(G_ASSUMED != null) return {g:clampG(G_ASSUMED), raw:G_ASSUMED, source:'assumed'};
  var c = gradeG();
  if(c) return {g:clampG(c.g), raw:c.g, source:c.source};
  return {g:DEFAULT_G, raw:null, source:'none'};
}
/* 성적 관리에서 돌아왔을 때 등 G를 다시 맞춘다. 바뀌었으면 true. */
function syncG(){
  var b = basisG();
  if(state.G === b.g) return false;
  state.G = b.g;
  updateMe();
  refreshMarkers();
  if(state.view === 'rank') renderRank();
  return true;
}
function gSourceLabel(src){
  return src === 'confirmed' ? '확정' : (src === 'predicted' ? '예상' : (src === 'assumed' ? '가정' : '없음'));
}

/* ===== 개발 중에만 쓰는 슬라이더 묶음 =====================================
   슬라이더, 되돌리기 버튼, "가정한 기준" 배지, 임시값(G_ASSUMED) 처리는 전부 여기 있다.
   출시 전(6단계)에 이 표시 구간을 통째로 지우면 된다. RELEASE_CHECKLIST.md 1번.
   임시값은 저장하지 않는다. 앱을 다시 열면 성적 관리의 G로 돌아간다. (SPEC_대학맵.md 2-3) */
var G_ASSUMED = null;
var gRaf = 0;
function sliderHtml(){
  var b = basisG();
  var h = '<div class="sl"><div class="sl-top"><label for="gSlider">가정해서 보기 (개발용)</label>' +
    '<output id="gOut">' + b.g.toFixed(2) + '</output></div>' +
    '<input type="range" id="gSlider" min="1.5" max="4.5" step="0.05" value="' + b.g.toFixed(2) + '">' +
    '<div class="sl-scale"><span>1.5</span><span>3.0</span><span>4.5</span></div>';
  if(G_ASSUMED != null){
    h += '<div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">' +
      '<button type="button" class="btn" data-reset>성적 관리 값으로 되돌리기</button></div>';
  }
  h += '<p class="note" style="margin:10px 0 0">개발 중에만 있는 도구예요. 여기서 바꾼 값은 저장되지 않아요.</p></div>';
  return h;
}
function basisBadge(){
  var b = basisG();
  if(b.source === 'assumed') return '<span class="badge c-out">가정한 기준</span>';
  if(b.source === 'none') return '<span class="badge c-out">성적을 입력하지 않아 가정한 값이에요</span>';
  return '';
}
/* 성적 관리의 G가 슬라이더 범위 밖이면 잘린다는 것을 알린다. */
function clampNote(){
  var b = basisG();
  if(b.raw == null || Math.abs(b.raw - b.g) < 0.005) return '';
  return '<p class="note">내 기준은 ' + b.raw.toFixed(2) + '인데 지도 비교 범위(1.5~4.5) 밖이라 가장 가까운 값으로 보여줘요.</p>';
}
/* ===== 슬라이더 묶음 끝 ================================================== */

/* 구간 자체는 9등급으로 계산하고, 보여줄 때만 단위를 맞춘다. */
function bandsHtml(G){
  function b(k, a, c){ return '<div><span class="badge c-' + k + '">' + CLS_NAME[k] + '</span><span class="num">' + a + '</span><span class="note">' + c + '</span></div>'; }
  function rng(a, b2){ return showGrade(a) + ' ~ ' + showGrade(b2); }
  return b('reach', rng(G-0.8, G-0.2) + ' 미만', '합격선이 내 기준보다 높음') +
    b('fit', rng(G-0.2, G+0.3), '비슷함') +
    b('safe', showGrade(G+0.3) + ' 초과 ~ ' + showGrade(G+1.0), '내 기준보다 여유') +
    '<div class="note" style="margin-top:6px">단위: ' + scaleUnit() + '</div>';
}
/* 화면에 보여줄 대표 등급. 껐을 때는 5등급 값을 학점 가중평균한 값을 쓴다. */
function displayBasis(){
  var b = basisG();
  if(isG9()) return {v:b.g, txt:b.g.toFixed(2)};
  if(b.source === 'assumed' || b.source === 'none'){
    var c = g9to5(b.g);
    return {v:c, txt:c == null ? '–' : c.toFixed(2)};
  }
  var c5 = computeG5(false);
  var v = c5 ? c5.g : g9to5(b.g);
  return {v:v, txt:v == null ? '–' : v.toFixed(2)};
}

function renderGrade(){
  var b = basisG(), G = b.g, vt = viewType();
  var h = '<div class="sh-head"><h2>내 기준 등급</h2><p class="kicker">성적 관리에서 계산한 값으로 비교해요</p></div>';

  h += scaleSwitchHtml('mapScale');
  h += '<div class="sl" style="margin-top:0"><div class="sl-top"><label>성적 관리 기준 (' + scaleUnit() + ')</label>' +
    '<output>' + (b.source === 'none' ? '–' : displayBasis().txt) + '</output></div>' +
    '<p class="note" style="margin:4px 0 0">' +
    (b.source === 'none'
      ? '아직 넣은 성적이 없어요. 성적을 넣으면 여기 값이 생겨요.'
      : '성적 관리의 ' + (b.source === 'confirmed' ? '학기말 확정 등급' : b.source === 'predicted' ? '중간·기말 기반 예상값' : '값') + '이에요. 9등급 환산 추정치예요.') +
    '</p>' + (basisBadge() ? '<p style="margin:8px 0 0">' + basisBadge() + '</p>' : '') + clampNote() + '</div>';

  h += '<div class="gfoot" style="margin-top:12px"><button type="button" class="btn" data-goscore>성적 입력하러 가기</button></div>';

  h += '<div class="sl"><div class="sl-top"><label>지도에서 볼 전형</label></div>' +
    '<div class="seg" role="group" data-vt style="margin-top:8px">' +
    '<button type="button" data-vtv="jong" aria-pressed="' + (vt === 'jong') + '">학생부종합</button>' +
    '<button type="button" data-vtv="gyo" aria-pressed="' + (vt === 'gyo') + '">학생부교과</button>' +
    '</div><p class="note" style="margin:10px 0 0">' +
    (vt === 'gyo'
      ? '교과 입결은 일부 학과에만 있어요. 없는 학과는 "자료 없음"으로 나와요. 교과 구간 기준은 아직 정해지지 않았어요.'
      : '성적 관리 마이 탭의 "지도에서 볼 전형"과 같은 값이에요.') + '</p></div>';

  h += sliderHtml();
  h += '<div class="bands" id="bands">' + bandsHtml(G) + '</div>';
  h += '<p class="note">분류 구간은 내가 정한 기준(의견)이에요. 자세한 설명은 안내 탭에 있어요.</p>';
  h += '<p class="note">' + scaleNote() + '</p>';
  return h;
}

function setG(v){
  state.G = clampG(v);
  updateMe();
  refreshMarkers();
  if(state.view === 'rank') renderRank();
  var o = $('#gOut'); if(o) o.textContent = state.G.toFixed(2);   /* 슬라이더는 9등급 그대로 */
  var bd = $('#bands'); if(bd) bd.innerHTML = bandsHtml(state.G);
}
function setViewType(v){
  if(!user.targets || typeof user.targets !== 'object') user.targets = {};
  user.targets.viewAdmissionType = (v === 'gyo') ? 'gyo' : 'jong';
  saveUser();
  refreshMarkers();
  if(state.view === 'rank') renderRank();
  openSheet(renderGrade(), 'grade');
}

function basisClick(e){
  if(e.target.closest('[data-goscore]')){
    closeSheet();
    gOpen();                       /* 전환 로딩을 거쳐 성적 관리로 */
    return true;
  }
  var t = e.target.closest('[data-vtv]');
  if(t){ setViewType(t.getAttribute('data-vtv')); return true; }
  if(e.target.closest('[data-reset]')){
    G_ASSUMED = null;
    setG(basisG().g);
    openSheet(renderGrade(), 'grade');
    return true;
  }
  return false;
}
function basisInput(e){
  if(e.target.id !== 'gSlider') return;
  var v = parseFloat(e.target.value);
  var o = $('#gOut'); if(o) o.textContent = v.toFixed(2);
  cancelAnimationFrame(gRaf);
  gRaf = requestAnimationFrame(function(){ G_ASSUMED = v; setG(v); });
}
function basisChange(e){
  if(e.target.id !== 'gSlider') return;
  G_ASSUMED = parseFloat(e.target.value);
  setG(G_ASSUMED);
  openSheet(renderGrade(), 'grade');
}

/* ----- 성적 관리에서 돌아올 때 지도 되돌리기 (SPEC_대학맵.md 2-1) ----- */
function resetMapView(){
  closeSheet();
  state.selU = null; state.tempU = null; state.curDept = null; state.curTab = 'sum';
  state.cls = {reach:true, fit:true, safe:true};
  state.rank = {cls:'all', region:'all', field:'all', sort:'cut', out:false};
  setView('map');
  var changed = syncG();
  refreshMarkers();
  if(map) fitInitial();
  layoutMarkers();
  return changed;
}
