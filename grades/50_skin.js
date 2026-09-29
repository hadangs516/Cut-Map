/* ---------- 성적 관리 · 화면 테마 ----------
   테마는 html의 data-skin 속성으로만 바뀐다. 색 값은 skins.css에만 있고 여기에는 두지 않는다.
   저장은 cutmap.user와 분리된 cutmap.skin 키를 쓴다. 백업과 초기화 범위에는 넣지 않는다. */

var SKIN_KEY = 'cutmap.skin';
/* 화면에 놓이는 순서 그대로. 1줄 기본·고양이, 2줄 펭귄·벚꽃, 3줄 방안지·모노, 4줄 우주·황혼. */
var SKINS = [
  {id:'default',  name:'기본',      os:true},
  {id:'cat',      name:'고양이'},
  {id:'penguin',  name:'펭귄'},
  {id:'sakura',   name:'벚꽃'},
  {id:'grid',     name:'방안지'},
  {id:'mono',     name:'모노 잉크'},
  {id:'space',    name:'우주'},
  {id:'dusk',     name:'황혼'}
];
function skinById(id){
  for(var i = 0; i < SKINS.length; i++){ if(SKINS[i].id === id) return SKINS[i]; }
  return null;
}
/* 저장값이 손상됐거나 모르는 값이면 기본으로 본다. */
function currentSkin(){
  var v = store.get(SKIN_KEY, null);
  return (typeof v === 'string' && skinById(v)) ? v : 'default';
}
function applySkin(id){
  var s = skinById(id) ? id : 'default';
  if(s === 'default') document.documentElement.removeAttribute('data-skin');
  else document.documentElement.setAttribute('data-skin', s);
  store.set(SKIN_KEY, s);
}
function skinName(id){ var s = skinById(id); return s ? s.name : '기본'; }
/* 저장값이 손상됐으면 head 스크립트가 남겼을 수 있는 속성까지 정리한다. */
applySkin(currentSkin());

/* 미리보기 축소판. 8개 카드가 같은 마크업을 쓰고, 색은 카드에 붙은 data-skin 토큰으로만 정해진다. */
function skinPreview(id){
  var attr = id === 'default' ? ' class="sk-prev sk-prev-default"' : ' class="sk-prev" data-skin="' + id + '"';
  return '<span' + attr + ' aria-hidden="true">' +
    '<span class="sk-land sk-l1"></span><span class="sk-land sk-l2"></span><span class="sk-land sk-l3"></span>' +
    '<span class="sk-dot sk-d1"></span><span class="sk-dot sk-d2"></span><span class="sk-dot sk-d3"></span>' +
    '<span class="sk-sheet"><span class="sk-bar"></span><span class="sk-line"></span><span class="sk-line s"></span></span>' +
    '</span>';
}

function scSkin(){
  var cur = currentSkin();
  var h = '<p class="gx-lead">화면 색을 고를 수 있어요. 고르면 바로 바뀌어요.</p>';
  h += '<div class="sk-grid" role="radiogroup" aria-label="화면 테마">';
  SKINS.forEach(function(s){
    var on = s.id === cur;
    h += '<button type="button" class="sk-card" role="radio" aria-checked="' + (on ? 'true' : 'false') +
      '" tabindex="' + (on ? '0' : '-1') + '" data-skin-pick="' + s.id + '">' +
      skinPreview(s.id) +
      '<span class="sk-foot"><span class="sk-nm">' + esc(s.name) + '</span>' +
      (s.os ? '<span class="sk-os">OS 설정 따름</span>' : '') +
      '<span class="sk-chk"></span></span></button>';
  });
  h += '</div>';
  h += '<p class="gx-note">기본은 기기의 밝게·어둡게 설정을 따라가요. 나머지는 고른 색으로 고정돼요.</p>';
  return h;
}

function skinClick(e){
  var t = e.target.closest('[data-skin-pick]');
  if(!t) return false;
  applySkin(t.getAttribute('data-skin-pick'));
  gRender();
  gToast(skinName(currentSkin()) + ' 테마로 바꿨어요');
  return true;
}
/* 라디오 묶음이라 좌우·상하 키로 옮길 수 있게 한다. */
function skinKey(e){
  if(gs.screen !== 'skin') return false;
  var keys = {ArrowRight:1, ArrowDown:1, ArrowLeft:-1, ArrowUp:-1};
  var d = keys[e.key];
  if(!d) return false;
  var cards = Array.prototype.slice.call(document.querySelectorAll('[data-skin-pick]'));
  var i = cards.indexOf(document.activeElement);
  if(i < 0) return false;
  e.preventDefault();
  var next = cards[(i + d + cards.length) % cards.length];
  next.focus(); next.click();
  return true;
}
