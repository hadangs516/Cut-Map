/* ---------- 등급 표시 단위 (9등급 환산 켜기/끄기) ----------
   판정(상향·적정·안정)은 언제나 9등급 값으로 계산한다. 여기서 바꾸는 건 화면에 보이는 숫자뿐이다.
   그래서 스위치를 켜고 꺼도 마커 색과 분류 결과는 같다.
   저장은 화면 테마와 같은 방식(별도 키, 백업·초기화 대상 아님). */

var SCALE_KEY = 'cutmap.scale';
function scaleMode(){
  var v = store.get(SCALE_KEY, null);
  return v === 'g5' ? 'g5' : 'g9';      /* 모르는 값이면 기본 '9등급 환산' */
}
function isG9(){ return scaleMode() === 'g9'; }
function setScale(m){
  store.set(SCALE_KEY, m === 'g5' ? 'g5' : 'g9');
}
function scaleUnit(){ return isG9() ? '9등급 환산' : '5등급 기준'; }

/* 5등급 -> 9등급 기대값. 균등분포 가정의 [추정]값이며 SPEC 4장과 같은 표다. */
var G5_TO_G9 = {1:1.60, 2:3.42, 3:5.00, 4:6.58, 5:8.40};
var G5_ANCHOR = [[1, 1.60], [2, 3.42], [3, 5.00], [4, 6.58], [5, 8.40]];

/* 9등급 -> 5등급 역환산. 위 표를 기준점으로 구간 선형 보간한다.
   표 바깥은 1.00과 5.00으로 자른다. 왕복 오차는 스크립트로 확인했다. */
function g9to5(v9){
  if(v9 == null || !isFinite(v9)) return null;
  if(v9 <= G5_ANCHOR[0][1]) return 1;
  var last = G5_ANCHOR[G5_ANCHOR.length - 1];
  if(v9 >= last[1]) return 5;
  for(var i = 0; i < G5_ANCHOR.length - 1; i++){
    var a = G5_ANCHOR[i], b = G5_ANCHOR[i + 1];
    if(v9 >= a[1] && v9 <= b[1]){
      var t = (v9 - a[1]) / (b[1] - a[1]);
      return Math.min(5, Math.max(1, a[0] + t * (b[0] - a[0])));
    }
  }
  return null;
}
function g5to9(v5){
  if(v5 == null || !isFinite(v5)) return null;
  if(v5 <= 1) return G5_ANCHOR[0][1];
  if(v5 >= 5) return G5_ANCHOR[4][1];
  for(var i = 0; i < G5_ANCHOR.length - 1; i++){
    var a = G5_ANCHOR[i], b = G5_ANCHOR[i + 1];
    if(v5 >= a[0] && v5 <= b[0]){
      var t = (v5 - a[0]) / (b[0] - a[0]);
      return a[1] + t * (b[1] - a[1]);
    }
  }
  return null;
}

/* 화면에 쓰는 값. 내부 계산은 항상 9등급이고 여기서만 바꾼다. */
function showGrade(v9, digits){
  if(v9 == null || !isFinite(v9)) return '–';
  var d = digits == null ? 2 : digits;
  return (isG9() ? v9 : g9to5(v9)).toFixed(d);
}
/* 차이(±)는 등급 차라서 같은 축으로 바꿔서 보여준다. */
function showDiff(d9, base9){
  if(d9 == null || !isFinite(d9)) return '–';
  if(isG9()) return (d9 > 0 ? '+' : '') + d9.toFixed(2);
  var a = g9to5(base9), b = g9to5(base9 + d9);
  if(a == null || b == null) return '–';
  var d5 = b - a;
  return (d5 > 0 ? '+' : '') + d5.toFixed(2);
}
function scaleNote(){
  return isG9()
    ? '9등급 환산은 5등급 구간을 9등급 척도로 바꾼 추정치예요. 공식 환산표가 아니에요.'
    : '입결은 9등급 자료라서 5등급으로 되돌려 보여줘요. 되돌린 값은 근사값이라 실제와 다를 수 있어요.';
}
function scaleSwitchHtml(id){
  return '<label class="sc-scale"><input type="checkbox" data-scale id="' + (id || 'scScale') + '"' +
    (isG9() ? ' checked' : '') + '><span>9등급 환산으로 보기</span></label>';
}
/* 스위치는 설정·성적 분석·지도 "내 기준" 패널 세 곳에 있고 같은 값을 쓴다. */
function toggleScale(on){
  setScale(on ? 'g9' : 'g5');
  updateMe();
  refreshMarkers();
  if(state.view === 'rank') renderRank();
  if(state.sheetMode === 'grade') openSheet(renderGrade(), 'grade');
  else if(state.sheetMode === 'dept' && state.curDept) openSheet(renderDept(state.curDept, state.curTab), 'dept');
  renderInfo();
  if(!gvEl.hidden) gRender();
}
function scaleClick(e){
  return false;
}
function scaleChange(e){
  if(!e.target.hasAttribute || !e.target.hasAttribute('data-scale')) return false;
  toggleScale(e.target.checked);
  return true;
}
