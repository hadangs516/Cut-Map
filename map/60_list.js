/* ---------- 지도 · 목록 탭 (정렬·필터·별표) ----------
   SPEC_대학맵.md 3-1(정렬 8가지), 3-2(분야), 3-3(필터).
   분야 버튼은 하드코딩하지 않고 지금 들어 있는 데이터에서 만든다. */

var SORTS = [
  {id:'near',    name:'내 성적과 가까운 순'},
  {id:'cutHigh', name:'합격선 높은 순'},
  {id:'cutLow',  name:'합격선 낮은 순'},
  {id:'compHigh',name:'경쟁률 높은 순'},
  {id:'compLow', name:'경쟁률 낮은 순'},
  {id:'n',       name:'모집인원 많은 순'},
  {id:'add',     name:'추합 많은 순'},
  {id:'name',    name:'대학명 가나다순'}
];

/* 데이터에 실제로 있는 분야만 버튼으로 만든다. */
function fieldOptions(){
  var groups = {}, subs = {};
  UNIS.forEach(function(u){
    u.ds.forEach(function(d){
      var g = FIELD_GROUP[d.f];
      if(g) groups[g] = (groups[g] || 0) + 1;
      if(d.f) subs[d.f] = (subs[d.f] || 0) + 1;
    });
  });
  var GNAME = {csw:'컴퓨터·SW', aid:'AI·데이터'};
  var out = [['all', '전체 분야']];
  Object.keys(groups).forEach(function(g){ out.push([g, GNAME[g] || g]); });
  return out;
}
function regionOptions(){
  var seen = {};
  UNIS.forEach(function(u){ seen[u.rg] = 1; });
  var out = [['all', '전체 지역']];
  if(seen['서울']) out.push(['seoul', '서울']);
  if(Object.keys(seen).some(function(k){ return k !== '서울'; })) out.push(['metro', '서울 밖']);
  return out;
}
function ownerOptions(){
  var seen = {};
  UNIS.forEach(function(u){ if(u.ty) seen[u.ty] = 1; });
  var out = [['all', '국공립·사립']];
  if(seen['국립'] || seen['공립']) out.push(['pub', '국공립']);
  if(seen['사립']) out.push(['pri', '사립']);
  return out;
}
function segs(){
  return [
    ['sort', SORTS.map(function(s){ return [s.id, s.name]; })],
    ['cls', [['all','전체'],['reach','상향'],['fit','적정'],['safe','안정']]],
    ['region', regionOptions()],
    ['owner', ownerOptions()],
    ['field', fieldOptions()]
  ];
}
/* 분야 기본값은 내 희망 학과의 분야. 없으면 전체. (SPEC 3-2) */
function defaultField(){
  var s = (typeof targetSeries === 'function') ? targetSeries() : [];
  if(!s.length) return 'all';
  if(s.indexOf('공학') >= 0) return 'csw';
  return 'all';
}
function renderFilters(){
  if(state.rank.sort === 'cut') state.rank.sort = hasG() ? 'near' : 'name';
  if(state.rank.field == null) state.rank.field = defaultField();
  var h = segs().map(function(s){
    return '<div class="seg" role="group" data-seg="' + s[0] + '">' + s[1].map(function(o){
      return '<button type="button" data-v="' + o[0] + '" aria-pressed="' + (state.rank[s[0]] === o[0]) + '">' + esc(o[1]) + '</button>';
    }).join('') + '</div>';
  }).join('');
  h += '<div class="tgs"><label><input type="checkbox" id="tgWomen"' + (state.women ? ' checked' : '') + '> 여대 포함</label>' +
    '<label><input type="checkbox" id="tgOut"' + (state.rank.out ? ' checked' : '') + '> 범위 밖 학과도 보기</label>' +
    '<label><input type="checkbox" id="tgStar"' + (state.rank.star ? ' checked' : '') + '> 목표만 보기</label></div>';
  $('#filters').innerHTML = h;
}

function starOnly(u, d){
  if(!state.rank.star) return true;
  if(typeof isStarUniv !== 'function') return true;
  return isStarUniv(u.nm) || isStarMajor(majorId(u.nm, d.nm));
}
function renderRank(){
  var R = state.rank, items = [];
  UNIS.forEach(function(u){
    if(!state.women && u.w) return;
    if(R.region === 'seoul' && u.rg !== '서울') return;
    if(R.region === 'metro' && u.rg === '서울') return;
    if(R.owner === 'pub' && !(u.ty === '국립' || u.ty === '공립')) return;
    if(R.owner === 'pri' && u.ty !== '사립') return;
    u.ds.forEach(function(d){
      var r = curRow(d);
      if(!r) return;
      if(R.field !== 'all' && FIELD_GROUP[d.f] !== R.field) return;
      if(!starOnly(u, d)) return;
      var e = evalDept(d);
      var inr = !!IN[e.cls];
      if(!inr && !R.out) return;
      if(R.cls !== 'all' && e.cls !== R.cls) return;
      items.push({u:u, d:d, r:r, e:e, inr:inr});
    });
  });

  /* 정렬 기준 값이 없는 항목은 항상 맨 아래. (SPEC 3-1) */
  function val(it){
    var r = it.r;
    switch(R.sort){
      case 'near':     return hasG() ? Math.abs(r.cut - state.G) : null;
      case 'cutHigh':  return num(r.cut) ? r.cut : null;
      case 'cutLow':   return num(r.cut) ? -r.cut : null;
      case 'compHigh': return num(r.comp) ? -r.comp : null;
      case 'compLow':  return num(r.comp) ? r.comp : null;
      case 'n':        return num(r.n) ? -r.n : null;
      case 'add':      return num(r.add) ? -r.add : null;
      default:         return null;
    }
  }
  items.forEach(function(it){ it._v = val(it); });
  items.sort(function(a, b){
    if(R.sort === 'name'){
      if(a.u.nm !== b.u.nm) return a.u.nm < b.u.nm ? -1 : 1;
      return a.d.nm < b.d.nm ? -1 : 1;
    }
    var av = a._v, bv = b._v;
    if(av == null && bv == null) return a.u.nm < b.u.nm ? -1 : 1;
    if(av == null) return 1;
    if(bv == null) return -1;
    if(av !== bv) return av - bv;
    return a.u.nm < b.u.nm ? -1 : 1;
  });

  var sortName = (SORTS.filter(function(s){ return s.id === R.sort; })[0] || {}).name || '';
  $('#rcount').textContent = items.length + '개 학과 · ' + sortName +
    ' · 내 기준 ' + displayBasis().txt + ' (' + scaleUnit() + ')';
  if(!items.length){
    $('#rankList').innerHTML = '<li class="empty">조건에 맞는 학과가 없어요. 필터를 넓혀 보세요.</li>';
    return;
  }
  $('#rankList').innerHTML = items.map(function(it, i){
    var r = it.r, meta = '<span>' + esc(r.t) + '</span><span>' + (r.cy || '') + '학년도</span>';
    if(R.sort === 'compHigh' || R.sort === 'compLow') meta += '<span>경쟁률 ' + fcomp(r.comp) + '</span>';
    if(R.sort === 'n') meta += '<span>모집 ' + (num(r.n) ? r.n + '명' : '자료 없음') + '</span>';
    if(R.sort === 'add') meta += '<span>추합 ' + (num(r.add) ? r.add + '명' : '자료 없음') + '</span>';
    if(it._v == null && R.sort !== 'name') meta += '<span>자료 없음</span>';
    if(r.cy === 2024) meta += '<span class="mk">2024 자료</span>';
    if(it.e.flags.length) meta += '<span class="mk">보정됨</span>';
    var mid = (typeof majorId === 'function') ? majorId(it.u.nm, it.d.nm) : '';
    var starred = (typeof isStarMajor === 'function') && isStarMajor(mid);
    return '<li><div class="rrow-wrap"><button type="button" class="rrow' + (it.inr ? '' : ' oor') + '" data-go="' + it.d.id + '">' +
      '<span class="rn">' + (i + 1) + '</span>' +
      '<span class="rm"><span class="ru">' + esc(it.u.sh) + '</span><span class="rd">' + esc(it.d.nm) + '</span><span class="rt">' + meta + '</span></span>' +
      '<span class="rc"><span class="rv">' + showGrade(r.cut) + '</span><span class="badge c-' + it.e.cls + '">' + CLS_NAME[it.e.cls] + '</span></span>' +
      '</button><button type="button" class="rstar' + (starred ? ' on' : '') + '" data-star="' + esc(mid) + '" aria-label="목표에 넣기">' +
      (starred ? '★' : '☆') + '</button></div></li>';
  }).join('');
}
