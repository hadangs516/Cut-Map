/* ---------- 성적 관리 · 성적 분석 탭 ---------- */

/* 등수와 수강자 수가 있으면 상위 %로 바로 환산해서 오차를 줄인다.
   없으면 5등급 구간 기대값(G5_TO_G9)을 쓴다. 두 경우 모두 추정치다. */
function resultTo9(r, exam){
  var n = r.studentCount || (exam && exam.studentCount), rank = r.rank;
  if(!r.gradeManual && n > 0 && rank > 0 && rank <= n){
    var t = Math.max(1, Number(r.tiedCount) || 1);
    return {v:g9From((rank + (t - 1) / 2) / n * 100), exact:true};
  }
  if(r.grade5 != null) return {v:G5_TO_G9[r.grade5], exact:false};
  return null;
}

var CORE_AREAS = {korean:1, math:1, english:1, social:1, history:1, science:1};

function courseOf(semId, code){
  var list = semCourses(semId);
  for(var i = 0; i < list.length; i++){ if(list[i].courseCode === code) return list[i]; }
  return null;
}
function examsOfType(types){
  return user.exams.filter(function(e){ return types.indexOf(e.type) >= 0; });
}
/* 학점 가중평균. to9가 true면 9등급 환산값, false면 5등급 값 그대로 평균한다. */
function weighted(exams, coreOnly, to9){
  var sum = 0, w = 0, exact = 0, all = 0, noCredit = 0;
  exams.forEach(function(e){
    e.results.forEach(function(r){
      if(!r.courseCode) return;
      var c = courseOf(e.sem, r.courseCode);
      if(!c || !c.hasGrade) return;
      if(coreOnly && !CORE_AREAS[c.area]) return;
      var v, ex = false;
      if(to9){ var g = resultTo9(r, e); if(!g) return; v = g.v; ex = g.exact; }
      else { if(r.grade5 == null) return; v = r.grade5; }
      all++;
      if(c.credits == null){ noCredit++; return; }
      sum += v * c.credits; w += c.credits;
      if(ex) exact++;
    });
  });
  return w > 0 ? {g:Math.round(sum / w * 100) / 100, n:all, exact:exact, noCredit:noCredit} : null;
}
/* 대표 등급 G(9등급). 지도 분류에 쓰는 값이라 스위치와 무관하게 항상 9등급으로 낸다. */
function computeG(coreOnly){
  var c = weighted(examsOfType(['semesterConfirmed']), coreOnly, true);
  if(c){ c.source = 'confirmed'; return c; }
  var p = weighted(examsOfType(['final', 'midterm']), coreOnly, true);
  if(p){ p.source = 'predicted'; return p; }
  return null;
}
/* 스위치를 껐을 때 보여줄 5등급 가중평균. 9등급을 되돌린 값이 아니라 원래 5등급 값으로 계산한다. */
function computeG5(coreOnly){
  var c = weighted(examsOfType(['semesterConfirmed']), coreOnly, false);
  if(c){ c.source = 'confirmed'; return c; }
  var p = weighted(examsOfType(['final', 'midterm']), coreOnly, false);
  if(p){ p.source = 'predicted'; return p; }
  return null;
}
/* 학기별 평균. to9에 따라 축이 달라진다. */
function semAverages(to9){
  var rows = [];
  SEM_IDS.forEach(function(id){
    var conf = user.exams.filter(function(e){ return e.sem === id && e.type === 'semesterConfirmed'; });
    var pred = user.exams.filter(function(e){ return e.sem === id && (e.type === 'final' || e.type === 'midterm'); });
    var use = conf.length ? conf : pred;
    if(!use.length) return;
    var r = weighted(use, false, to9);
    if(r) rows.push({id:id, g:r.g, confirmed:conf.length > 0});
  });
  return rows;
}

function bar(g, max){
  var pct = Math.max(4, Math.min(100, (1 - (g - 1) / (max - 1)) * 100));
  return '<span class="an-bar"><i style="width:' + pct.toFixed(0) + '%"></i></span>';
}
function axisMax(){ return isG9() ? 9 : 5; }

var ANALYSIS_SCREENS = {
  home: {title:'성적 분석', parent:null, render:function(){ return scAnalysis(); }}
};

function scAnalysis(){
  var view = gs.anaView || 'exam';
  var h = scaleSwitchHtml('anScale');
  h += '<div class="an-seg">' +
    [['exam','시험별'],['subject','과목별'],['all','전체'],['graph','그래프']].map(function(o){
      return '<button type="button" data-anav="' + o[0] + '"' + (view === o[0] ? ' class="on"' : '') + '>' + o[1] + '</button>';
    }).join('') + '</div>';

  var on = isG9();
  var G = on ? computeG(!!gs.anaCore) : computeG5(!!gs.anaCore);
  h += '<div class="an-g">' +
    '<div class="an-g-top"><span>대표 등급 (' + scaleUnit() + ')</span>' +
    '<label class="an-core"><input type="checkbox" id="anCore"' + (gs.anaCore ? ' checked' : '') + '> 국영수사과만</label></div>';
  if(G){
    h += '<div class="an-g-v">' + G.g.toFixed(2) + '</div>' +
      '<div class="an-g-m">' + (G.source === 'confirmed' ? '학기말 확정 등급 기준' : '중간·기말 기반 <b>예상값</b>') +
      ' · 학점 가중평균' + (on ? ' · 환산 추정치' : '') + '</div>';
    if(on && G.exact < G.n) h += '<p class="gx-note" style="margin-top:6px">등수를 안 넣은 과목은 구간 평균으로 환산해서 오차가 커요.</p>';
    if(G.noCredit) h += '<p class="gx-note" style="margin-top:6px">학점을 안 넣은 과목 ' + G.noCredit + '개는 평균에서 빠졌어요.</p>';
  }else{
    h += '<div class="an-g-v off">–</div><div class="an-g-m">성적을 넣으면 여기에 나와요.</div>';
  }
  h += '</div>';

  if(view === 'exam') h += anaByExam();
  else if(view === 'subject') h += anaBySubject();
  else if(view === 'graph') h += anaGraph();
  else h += anaAll();
  h += '<p class="gx-note">' + scaleNote() + '</p>';
  return h;
}

function anaByExam(){
  var list = user.exams.filter(function(e){ return e.results.some(function(r){ return r.grade5 != null || r.grade != null; }); });
  if(!list.length) return '<div class="gx-empty">아직 넣은 성적이 없어요.</div>';
  var cur = gs.anaExam && list.filter(function(e){ return e.id === gs.anaExam; })[0] ? gs.anaExam : list[0].id;
  var h = '<div class="an-pick">' + list.map(function(e){
    return '<button type="button" data-anexam="' + esc(e.id) + '"' + (e.id === cur ? ' class="on"' : '') + '>' + esc(e.name) + '</button>';
  }).join('') + '</div>';
  var e = list.filter(function(x){ return x.id === cur; })[0];
  h += '<div class="an-rows">';
  e.results.forEach(function(r){
    if(r.area){
      /* 모의고사는 원래 9등급이라 변환하지 않는다. */
      if(r.grade == null) return;
      h += '<div class="an-row"><span class="an-nm">' + esc(r.area) + '</span>' + bar(r.grade, 9) +
        '<span class="an-v">' + r.grade + '등급 <b>9등급</b></span></div>';
      return;
    }
    if(r.grade5 == null) return;
    var c = courseOf(e.sem, r.courseCode);
    var g9 = resultTo9(r, e);
    h += '<div class="an-row"><span class="an-nm">' + esc(c ? courseName(c) : r.courseCode) +
      (r.gradeManual ? ' <span class="gx-flag">수정됨</span>' : '') + '</span>' + bar(r.grade5, 5) +
      '<span class="an-v">' + r.grade5 + '등급' + (isG9() && g9 ? ' <b>' + g9.v.toFixed(2) + '</b>' : '') + '</span></div>';
  });
  h += '</div>';
  if(isG9()) h += '<p class="gx-note">왼쪽은 학교 5등급, 굵은 숫자는 9등급 환산이에요.</p>';
  return h;
}

function subjectSeries(){
  var byCode = {};
  user.exams.forEach(function(e){
    if(e.type === 'mock') return;
    e.results.forEach(function(r){
      if(!r.courseCode || r.grade5 == null) return;
      (byCode[r.courseCode] = byCode[r.courseCode] || []).push({e:e, r:r});
    });
  });
  return byCode;
}
function anaBySubject(){
  var byCode = subjectSeries(), codes = Object.keys(byCode);
  if(!codes.length) return '<div class="gx-empty">아직 넣은 지필고사 성적이 없어요.</div>';
  var cur = gs.anaCourse && byCode[gs.anaCourse] ? gs.anaCourse : codes[0];
  var h = '<div class="an-pick">' + codes.map(function(code){
    var any = byCode[code][0], c = courseOf(any.e.sem, code);
    return '<button type="button" data-ancourse="' + esc(code) + '"' + (code === cur ? ' class="on"' : '') + '>' +
      esc(c ? courseName(c) : code) + '</button>';
  }).join('') + '</div><div class="an-rows">';
  byCode[cur].forEach(function(x){
    h += '<div class="an-row"><span class="an-nm">' + esc(x.e.name) + '</span>' + bar(x.r.grade5, 5) +
      '<span class="an-v">' + x.r.grade5 + '등급</span></div>';
  });
  h += '</div>';
  return h;
}

function anaAll(){
  var rows = semAverages(isG9());
  if(!rows.length) return '<div class="gx-empty">학기 평균을 낼 성적이 아직 없어요.</div>';
  var run = 0, h = '<div class="an-rows">';
  rows.forEach(function(r, i){
    run += r.g;
    h += '<div class="an-row"><span class="an-nm">' + semLabel(r.id) +
      (r.confirmed ? '' : ' <span class="gx-flag">예상</span>') + '</span>' + bar(r.g, axisMax()) +
      '<span class="an-v">' + r.g.toFixed(2) + ' <b>누적 ' + (run / (i + 1)).toFixed(2) + '</b></span></div>';
  });
  h += '</div><p class="gx-note">학기 평균은 학점 가중평균이고, 누적은 학기 평균을 다시 평균한 값이에요. 단위는 ' + scaleUnit() + '이에요.</p>';
  return h;
}

/* ----- 그래프 (인라인 SVG) -----
   등급은 숫자가 작을수록 좋아서 위쪽이 1등급이다. 색은 전부 테마 토큰으로만 칠한다.
   모의고사는 9등급이라 내신 그래프에 섞지 않는다. */
var AG = {w:320, h:180, l:30, r:10, t:12, b:24};
function agX(i, n){
  if(n <= 1) return AG.l + (AG.w - AG.l - AG.r) / 2;
  return AG.l + (AG.w - AG.l - AG.r) * i / (n - 1);
}
function agY(v){
  var max = axisMax();
  return AG.t + (AG.h - AG.t - AG.b) * (v - 1) / (max - 1);
}
function agFrame(labels){
  var max = axisMax(), h = '';
  var ticks = max === 9 ? [1,3,5,7,9] : [1,2,3,4,5];
  ticks.forEach(function(v){
    var y = agY(v).toFixed(1);
    h += '<line class="ag-grid" x1="' + AG.l + '" y1="' + y + '" x2="' + (AG.w - AG.r) + '" y2="' + y + '"/>';
    h += '<text class="ag-label" x="' + (AG.l - 6) + '" y="' + (Number(y) + 3.5).toFixed(1) + '" text-anchor="end">' + v + '</text>';
  });
  labels.forEach(function(t, i){
    h += '<text class="ag-label" x="' + agX(i, labels.length).toFixed(1) + '" y="' + (AG.h - 6) + '" text-anchor="middle">' + esc(t) + '</text>';
  });
  return h;
}
function agSeries(vals, cls){
  var n = vals.length, h = '';
  if(n > 1){
    var pts = vals.map(function(v, i){ return agX(i, n).toFixed(1) + ',' + agY(v.g).toFixed(1); }).join(' ');
    h += '<polyline class="ag-line ' + cls + '" points="' + pts + '"/>';
  }
  vals.forEach(function(v, i){
    var x = agX(i, n).toFixed(1), y = agY(v.g).toFixed(1);
    /* 확정은 채운 동그라미, 예상은 속 빈 네모로 구분한다. */
    if(v.confirmed === false){
      h += '<rect class="ag-dot pred ' + cls + '" x="' + (x - 3.2) + '" y="' + (y - 3.2) + '" width="6.4" height="6.4"/>';
    }else{
      h += '<circle class="ag-dot ' + cls + '" cx="' + x + '" cy="' + y + '" r="3.4"/>';
    }
  });
  return h;
}
function agSvg(inner){
  return '<svg class="ag" viewBox="0 0 ' + AG.w + ' ' + AG.h + '" role="img" preserveAspectRatio="xMidYMid meet">' + inner + '</svg>';
}
function anaGraph(){
  var rows = semAverages(isG9());
  var h = '<h3 class="gx-h">학기 평균과 누적 평균</h3>';
  if(!rows.length){
    h += '<div class="gx-empty">학기 평균을 낼 성적이 아직 없어요.</div>';
  }else{
    var run = 0, cum = rows.map(function(r, i){ run += r.g; return {g:run / (i + 1), confirmed:true}; });
    var labels = rows.map(function(r){ return r.id; });
    h += agSvg(agFrame(labels) + agSeries(rows, 's1') + agSeries(cum, 's2'));
    h += '<div class="ag-leg"><span class="ag-key s1"></span>학기 평균<span class="ag-key s2"></span>누적 평균' +
      '<span class="ag-key pred"></span>예상값</div>';
    if(rows.length === 1) h += '<p class="gx-note">학기가 하나뿐이라 점 하나만 찍혀요. 학기가 늘면 선으로 이어져요.</p>';
  }

  h += '<h3 class="gx-h">과목별 추이</h3>';
  var byCode = subjectSeries(), codes = Object.keys(byCode);
  if(!codes.length){
    h += '<div class="gx-empty">아직 넣은 지필고사 성적이 없어요.</div>';
    return h;
  }
  var cur = gs.anaCourse && byCode[gs.anaCourse] ? gs.anaCourse : codes[0];
  h += '<div class="an-pick">' + codes.map(function(code){
    var any = byCode[code][0], c = courseOf(any.e.sem, code);
    return '<button type="button" data-ancourse="' + esc(code) + '"' + (code === cur ? ' class="on"' : '') + '>' +
      esc(c ? courseName(c) : code) + '</button>';
  }).join('') + '</div>';
  var series = byCode[cur].map(function(x){
    var v = isG9() ? (resultTo9(x.r, x.e) || {v:null}).v : x.r.grade5;
    return {g:v, confirmed: x.e.type === 'semesterConfirmed', name:x.e.name};
  }).filter(function(x){ return x.g != null; });
  if(!series.length){
    h += '<div class="gx-empty">이 과목은 그릴 값이 없어요.</div>';
    return h;
  }
  h += agSvg(agFrame(series.map(function(s, i){ return String(i + 1); })) + agSeries(series, 's1'));
  h += '<p class="gx-note">가로축은 시험 순서예요: ' + esc(series.map(function(s, i){ return (i + 1) + '. ' + s.name; }).join(' / ')) + '</p>';
  if(series.length === 1) h += '<p class="gx-note">시험이 하나뿐이라 점 하나만 찍혀요.</p>';
  h += '<p class="gx-note">세로축은 ' + scaleUnit() + '이고 위쪽이 1등급이에요. 모의고사는 9등급이라 이 그래프에 넣지 않았어요.</p>';
  return h;
}

function analysisClick(e){
  var t;
  if((t = e.target.closest('[data-anav]'))){ gs.anaView = t.getAttribute('data-anav'); gRender(); return true; }
  if((t = e.target.closest('[data-anexam]'))){ gs.anaExam = t.getAttribute('data-anexam'); gRender(); return true; }
  if((t = e.target.closest('[data-ancourse]'))){ gs.anaCourse = t.getAttribute('data-ancourse'); gRender(); return true; }
  return false;
}
function analysisChange(e){
  if(scaleChange(e)) return true;
  if(e.target.id === 'anCore'){ gs.anaCore = e.target.checked; gRender(); return true; }
  return false;
}
