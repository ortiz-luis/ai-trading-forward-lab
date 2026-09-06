const eur=value=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value??0);
const usd=value=>value==null?'—':`$${new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(value)}`;
const pct=value=>value==null?'—':`${Number(value).toFixed(2)}%`;
const dayFmt=value=>value?new Intl.DateTimeFormat('es-ES',{dateStyle:'medium'}).format(new Date(`${value}T12:00:00Z`)):'—';
const dateFmt=value=>value?new Intl.DateTimeFormat('es-ES',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)):'—';
const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const setText=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value;};
const pnlClass=value=>value>0?'positive':value<0?'negative':'neutral';
const unlock=id=>{const el=document.getElementById(id);if(el)el.classList.remove('locked-step');};
const SELL_THRESHOLD=80;

let replayData=null;
let currentReplay=null;
let visibleRange='1M';
let scanned=false;
let asked=false;
let applied=false;
let timelineVisible=0;
let proChart=null;
let candleSeries=null;
let volumeSeries=null;
let confidenceSeries=null;
let smaSeries=[];

function switchMode(mode){
  const replay=mode==='replay';
  document.getElementById('replayPanel').classList.toggle('hidden',!replay);
  document.getElementById('livePanel').classList.toggle('hidden',replay);
  document.getElementById('replayModeButton').classList.toggle('active',replay);
  document.getElementById('liveModeButton').classList.toggle('active',!replay);
}
document.getElementById('replayModeButton').addEventListener('click',()=>switchMode('replay'));
document.getElementById('liveModeButton').addEventListener('click',()=>switchMode('live'));

function destroyProfessionalChart(){
  if(proChart){proChart.remove();proChart=null;candleSeries=null;volumeSeries=null;confidenceSeries=null;smaSeries=[];}
  const host=document.getElementById('professionalChart');if(host)host.innerHTML='';
}

function smaData(rows,period){
  const out=[];let sum=0;
  rows.forEach((row,i)=>{sum+=row.close;if(i>=period)sum-=rows[i-period].close;if(i>=period-1)out.push({time:row.date,value:sum/period});});
  return out;
}

function sellConfidence(row){
  const c=Math.max(0,Math.min(1,Number(row?.confidence??0)));
  return Math.round((row?.action==='SELL'?c:1-c)*1000)/10;
}

function initialSellConfidence(){
  const d=currentReplay?.decision||{};
  if(d.action!=='BUY')return null;
  return Math.round((1-Math.max(0,Math.min(1,Number(d.confidence??0))))*1000)/10;
}

function futureRows(){
  const c=currentReplay?.chart||{};
  return (c.candles_after_cutoff?.length?c.candles_after_cutoff:c.spy_after_cutoff)||[];
}

function chartRows(){
  if(!currentReplay)return{before:[],after:[],all:[]};
  const c=currentReplay.chart||{};
  const before=(c.candles_before_cutoff?.length?c.candles_before_cutoff:c.spy_before_cutoff)||[];
  const after=futureRows().slice(0,timelineVisible);
  return {before,after,all:[...before,...after]};
}

function rangeSessions(){return {'1W':5,'1M':22,'3M':66,'1Y':252,'2Y':520}[visibleRange]||22;}

function visibleLifecycle(){
  const latest=futureRows()[Math.max(0,timelineVisible-1)]?.date;
  if(!latest)return[];
  return (currentReplay?.lifecycle||[]).filter(r=>r.date<=latest);
}

function saleAssessment(){
  return visibleLifecycle().find(r=>sellConfidence(r)>=SELL_THRESHOLD)||null;
}

function exitReached(){
  const exit=currentReplay?.result?.exit_day;
  const latest=futureRows()[Math.max(0,timelineVisible-1)]?.date;
  return Boolean(exit&&latest&&latest>=exit);
}

function renderProfessionalChart(){
  if(!currentReplay||!scanned)return;
  const host=document.getElementById('professionalChart');if(!host)return;
  destroyProfessionalChart();
  const {before,after,all}=chartRows();
  if(!all.length){host.innerHTML='<div class="small-muted" style="padding:20px">No hay velas disponibles.</div>';return;}
  if(!window.LightweightCharts){host.innerHTML='<div class="small-muted" style="padding:20px">No se pudo cargar el motor de gráficos.</div>';return;}

  proChart=LightweightCharts.createChart(host,{width:host.clientWidth,height:host.clientHeight,layout:{background:{color:'#fff'},textColor:'#596673'},grid:{vertLines:{color:'#f1f3f5'},horzLines:{color:'#f1f3f5'}},rightPriceScale:{borderColor:'#e5e9ed'},timeScale:{borderColor:'#e5e9ed',rightOffset:2},crosshair:{mode:LightweightCharts.CrosshairMode.Normal}});
  candleSeries=proChart.addCandlestickSeries({upColor:'#18794e',downColor:'#b42318',borderVisible:false,wickUpColor:'#18794e',wickDownColor:'#b42318',priceScaleId:'right'});
  candleSeries.setData(all.map(r=>({time:r.date,open:r.open,high:r.high,low:r.low,close:r.close})));
  volumeSeries=proChart.addHistogramSeries({priceFormat:{type:'volume'},priceScaleId:'volume'});
  volumeSeries.setData(all.map(r=>({time:r.date,value:r.volume,color:r.close>=r.open?'rgba(24,121,78,.30)':'rgba(180,35,24,.26)'})));
  proChart.priceScale('volume').applyOptions({scaleMargins:{top:.82,bottom:0}});

  [20,50,200].forEach(period=>{const data=smaData(before,period);if(!data.length)return;const line=proChart.addLineSeries({lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});line.setData(data);smaSeries.push(line);});

  const o=currentReplay.chart?.overlays||{};
  (o.support_levels||[]).forEach((price,i)=>candleSeries.createPriceLine({price,color:'#18794e',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`Soporte ${i+1}`}));
  (o.resistance_levels||[]).forEach((price,i)=>candleSeries.createPriceLine({price,color:'#b42318',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`Resistencia ${i+1}`}));
  if(o.target_price)candleSeries.createPriceLine({price:o.target_price,color:'#344054',lineWidth:1,lineStyle:1,axisLabelVisible:true,title:'Objetivo'});
  if(applied&&currentReplay.result?.entry_price)candleSeries.createPriceLine({price:currentReplay.result.entry_price,color:'#17202a',lineWidth:2,lineStyle:0,axisLabelVisible:true,title:'Entrada'});

  const lifecycle=visibleLifecycle();
  const conf=[];
  const init=initialSellConfidence();
  if(init!=null&&before.length)conf.push({time:before[before.length-1].date,value:init});
  lifecycle.forEach(r=>conf.push({time:r.date,value:sellConfidence(r)}));
  if(conf.length){
    confidenceSeries=proChart.addLineSeries({priceScaleId:'sellConfidence',lineWidth:3,lineType:0,priceLineVisible:false,lastValueVisible:true,crosshairMarkerVisible:true,priceFormat:{type:'custom',formatter:v=>`${Math.round(v)}%`},autoscaleInfoProvider:()=>({priceRange:{minValue:0,maxValue:100}})});
    confidenceSeries.setData(conf);
    confidenceSeries.createPriceLine({price:SELL_THRESHOLD,color:'#b42318',lineWidth:2,lineStyle:2,axisLabelVisible:true,title:'Venta 80%'});
    proChart.priceScale('sellConfidence').applyOptions({borderVisible:true,borderColor:'#d0d5dd',scaleMargins:{top:.06,bottom:.20}});
  }

  const markers=[];
  if(before.length)markers.push({time:before[before.length-1].date,position:'aboveBar',color:'#7a5b00',shape:'circle',text:'Cutoff'});
  if(applied&&timelineVisible>0&&currentReplay.result?.entry_day)markers.push({time:currentReplay.result.entry_day,position:'belowBar',color:'#17202a',shape:'arrowUp',text:'Entrada'});
  const sold=saleAssessment();
  if(sold)markers.push({time:sold.date,position:'aboveBar',color:'#b42318',shape:'arrowDown',text:`VENTA ${Math.round(sellConfidence(sold))}%`});
  else if(exitReached()&&currentReplay.result?.exit_day)markers.push({time:currentReplay.result.exit_day,position:'aboveBar',color:'#65717d',shape:'arrowDown',text:'Salida por horizonte'});
  if(after.length)markers.push({time:after[after.length-1].date,position:'aboveBar',color:'#344054',shape:'circle',text:'Ahora'});
  candleSeries.setMarkers(markers.filter(m=>all.some(r=>r.date===m.time)));

  const n=rangeSessions();const from=Math.max(0,all.length-n);proChart.timeScale().setVisibleLogicalRange({from,to:all.length+1});
  const phase=sold||exitReached()?'ANÁLISIS RETROSPECTIVO':timelineVisible?'GESTIÓN DE LA POSICIÓN':'FUTURO BLOQUEADO';
  setText('chartRevealState',timelineVisible?`${phase} · ${timelineVisible} sesión(es) revelada(s)`:'Sólo datos conocidos al cutoff');
  const symbol=currentReplay.chart?.symbol||'SPY';
  const latest=after[after.length-1]?.date||currentReplay.cutoff_date;
  setText('professionalChartTitle',`${symbol} · presente simulado: ${dayFmt(latest)}`);
  const scope=currentReplay.analysis_scope||{};
  setText('chartContextNote',`Vista ${visibleRange}; la IA analizó ${scope.daily_history_target||'histórico amplio'}. La curva secundaria es convicción de venta; 80% activa la venta simulada.`);

  const levels=[];
  if(o.sma20)levels.push(`SMA20 ${usd(o.sma20)}`);if(o.sma50)levels.push(`SMA50 ${usd(o.sma50)}`);if(o.sma200)levels.push(`SMA200 ${usd(o.sma200)}`);
  (o.support_levels||[]).forEach(v=>levels.push(`Soporte ${usd(v)}`));(o.resistance_levels||[]).forEach(v=>levels.push(`Resistencia ${usd(v)}`));if(o.target_price)levels.push(`Objetivo ${usd(o.target_price)}`);
  levels.push(`Threshold venta ${SELL_THRESHOLD}%`);
  document.getElementById('chartLevels').innerHTML=levels.map(x=>`<span class="level-chip">${esc(x)}</span>`).join('');
}

window.addEventListener('resize',()=>{if(proChart){const host=document.getElementById('professionalChart');proChart.applyOptions({width:host.clientWidth,height:host.clientHeight});}});
document.querySelectorAll('[data-range]').forEach(btn=>btn.addEventListener('click',()=>{visibleRange=btn.dataset.range;document.querySelectorAll('[data-range]').forEach(b=>b.classList.toggle('active',b===btn));renderProfessionalChart();}));

function resetReplay(){
  scanned=false;asked=false;applied=false;timelineVisible=0;
  ['decisionCard','applyCard','followCard','revealCard'].forEach(id=>document.getElementById(id).classList.add('locked-step'));
  ['scanResult','decisionShort','applyResult','followResult','revealResult','lessonCard','professionalChartCard','timelineControls','timelineStatus'].forEach(id=>document.getElementById(id).classList.add('hidden'));
  ['askDecision','applyDecision','revealFuture'].forEach(id=>{const el=document.getElementById(id);el.classList.add('hidden');el.disabled=false;});
  ['advanceDay','advanceWeek','advanceMonth'].forEach(id=>{const el=document.getElementById(id);el.disabled=false;});
  setText('timelinePhaseTitle','Gestión de la posición');setText('timelinePhaseCopy','Cada avance revela sólo nuevas sesiones ya ocurridas. ChatGPT reevalúa la tesis y su convicción de vender queda dibujada sobre el mismo gráfico.');
  const scan=document.getElementById('scanMarket');scan.disabled=false;scan.textContent='Explorar mercado';
  destroyProfessionalChart();
}

function loadReplay(id){currentReplay=replayData.sessions.find(s=>s.replay_id===id)||replayData.sessions[0];const scope=currentReplay.analysis_scope||{};setText('analysisScope',`ChatGPT comparó ${scope.universe_size||18} acciones, ${scope.daily_history_target||'histórico amplio'}, horizontes ${(scope.technical_horizons||[]).join(', ')} y noticias cutoff-safe.`);resetReplay();}
function renderReplayData(data){replayData=data;const select=document.getElementById('replayDate');select.innerHTML=[...data.sessions].reverse().map(s=>`<option value="${esc(s.replay_id)}">${dayFmt(s.cutoff_date)}</option>`).join('');const first=[...data.sessions].reverse()[0];select.value=first.replay_id;loadReplay(first.replay_id);}
document.getElementById('replayDate').addEventListener('change',e=>loadReplay(e.target.value));

document.getElementById('scanMarket').addEventListener('click',()=>{
  if(!currentReplay)return;scanned=true;const s=currentReplay.selection||{};const selected=s.selected_symbol;
  const rows=(s.shortlist||[]).map(r=>`<div class="scan-row"><strong>${esc(r.symbol)}</strong><span class="score-pill">${Math.round((r.score||0)*100)}%</span><span>${esc(r.reason)}</span></div>`).join('');
  document.getElementById('scanResult').innerHTML=`<div class="short-decision"><strong>${selected?`Foco: ${esc(selected)}`:'Hoy no hay un candidato claro'}</strong><span>${esc(s.selection_summary||'')}</span></div>${rows?`<div class="scan-shortlist">${rows}</div>`:''}`;
  document.getElementById('scanResult').classList.remove('hidden');document.getElementById('professionalChartCard').classList.remove('hidden');unlock('decisionCard');document.getElementById('askDecision').classList.remove('hidden');const btn=document.getElementById('scanMarket');btn.disabled=true;btn.textContent='Mercado explorado';renderProfessionalChart();
});

function renderEvidence(){const list=document.getElementById('evidenceList');const rows=currentReplay.evidence||[];if(!rows.length){list.innerHTML='<div class="small-muted">No hubo noticias cutoff-safe suficientemente relevantes.</div>';return;}list.innerHTML=rows.map(row=>`<div class="evidence-item"><a href="${esc(row.url)}" target="_blank" rel="noopener noreferrer">${esc(row.headline||row.source||row.url)}</a><span>${esc(row.summary||'')}</span><span class="evidence-meta">${esc(row.source||'')} · ${dateFmt(row.published_at)}</span></div>`).join('');}

document.getElementById('askDecision').addEventListener('click',()=>{
  if(!currentReplay)return;asked=true;const d=currentReplay.decision||{};const title=d.action==='BUY'?`BUY ${d.symbol}`:'NO TRADE';
  document.getElementById('decisionShort').innerHTML=`<div class="short-decision"><strong>${esc(title)}</strong><span>${d.notional_eur?`${eur(d.notional_eur)} · `:''}confianza ${Math.round((d.confidence||0)*100)}%${d.horizon_days?` · ${d.horizon_days} días`:''}</span><p>${esc(d.short_answer||d.thesis||'')}</p></div>`;
  document.getElementById('decisionShort').classList.remove('hidden');setText('lessonSelection',currentReplay.selection?.selection_summary||'');setText('lessonChart',d.chart_reading||'');setText('lessonNews',d.news_reading||'');setText('lessonRisk',`${d.counter_thesis||''}\n\n${d.risk_lesson||''}`);renderEvidence();document.getElementById('lessonCard').classList.remove('hidden');unlock('applyCard');document.getElementById('applyDecision').classList.remove('hidden');const btn=document.getElementById('askDecision');btn.disabled=true;btn.textContent='Respuesta revelada';renderProfessionalChart();
});

document.getElementById('applyDecision').addEventListener('click',()=>{
  if(!currentReplay)return;applied=true;const d=currentReplay.decision||{};const r=currentReplay.result||{};
  if(d.action!=='BUY')document.getElementById('applyResult').innerHTML='<div class="apply-ticket"><strong>No se abrió posición.</strong><span>La IA conservó los €1.000 ficticios en cash.</span></div>';
  else if(r.available)document.getElementById('applyResult').innerHTML=`<div class="apply-ticket"><div class="ticket-row"><span>Activo</span><strong>${esc(d.symbol)}</strong></div><div class="ticket-row"><span>Capital asignado</span><strong>${eur(d.notional_eur)}</strong></div><div class="ticket-row"><span>Entrada simulada</span><strong>${usd(r.entry_price)}</strong></div><div class="ticket-row"><span>Convicción inicial de venta</span><strong>${initialSellConfidence()}%</strong></div></div>`;
  else document.getElementById('applyResult').textContent='La entrada todavía no existe en este replay.';
  document.getElementById('applyResult').classList.remove('hidden');unlock('followCard');document.getElementById('timelineControls').classList.remove('hidden');document.getElementById('timelineStatus').classList.remove('hidden');document.getElementById('applyDecision').disabled=true;updateTimelineUI();renderProfessionalChart();
});

function renderLifecycle(){
  const rows=visibleLifecycle();
  if(!rows.length){document.getElementById('followResult').classList.add('hidden');return;}
  const body=rows.map(r=>`<tr><td>${dayFmt(r.date)}</td><td><strong>${esc(r.action)}</strong></td><td>${sellConfidence(r)}%</td><td>${esc(r.thesis_status||'')}</td></tr>`).join('');
  document.getElementById('followResult').innerHTML=`<div class="follow-table"><table><thead><tr><th>Fecha</th><th>Lectura</th><th>Convicción de venta</th><th>Tesis</th></tr></thead><tbody>${body}</tbody></table></div>`;
  document.getElementById('followResult').classList.remove('hidden');
}

function updateTimelineUI(){
  const total=futureRows().length;const rows=visibleLifecycle();const sold=saleAssessment();const exited=exitReached();const latest=futureRows()[Math.max(0,timelineVisible-1)]?.date;
  let status=timelineVisible?`Presente simulado: ${dayFmt(latest)} · ${timelineVisible}/${total} sesiones futuras reveladas.`:'Presente simulado todavía en el cutoff.';
  if(rows.length){const last=rows[rows.length-1];status+=` Convicción de venta: ${sellConfidence(last)}%.`;}
  if(sold){status+=` Threshold cruzado el ${dayFmt(sold.date)}: venta simulada.`;setText('timelinePhaseTitle','Análisis retrospectivo');setText('timelinePhaseCopy','La venta ya quedó fijada. Seguir avanzando sólo sirve para juzgar retrospectivamente si fue temprana, tardía o razonable.');unlock('revealCard');document.getElementById('revealFuture').classList.remove('hidden');}
  else if(exited){status+=` La posición ya terminó por la regla de horizonte del protocolo.`;setText('timelinePhaseTitle','Análisis retrospectivo');setText('timelinePhaseCopy','La salida ya quedó fijada por el protocolo. Lo que revelemos ahora es únicamente retrospectivo.');unlock('revealCard');document.getElementById('revealFuture').classList.remove('hidden');}
  else{setText('timelinePhaseTitle','Gestión de la posición');}
  setText('timelineStatus',status);
  const done=timelineVisible>=total;['advanceDay','advanceWeek','advanceMonth'].forEach(id=>document.getElementById(id).disabled=done);
  renderLifecycle();renderProfessionalChart();
}

function advanceBy(n){if(!applied)return;timelineVisible=Math.min(futureRows().length,timelineVisible+n);updateTimelineUI();}
document.getElementById('advanceDay').addEventListener('click',()=>advanceBy(1));
document.getElementById('advanceWeek').addEventListener('click',()=>advanceBy(5));
document.getElementById('advanceMonth').addEventListener('click',()=>advanceBy(22));

document.getElementById('revealFuture').addEventListener('click',()=>{
  timelineVisible=futureRows().length;updateTimelineUI();const d=currentReplay.decision||{};const r=currentReplay.result||{};const future=futureRows();let hindsight='';
  if(d.action==='BUY'&&r.available&&future.length){const afterExit=future.filter(x=>r.exit_day&&x.date>r.exit_day);if(afterExit.length){const maxHigh=Math.max(...afterExit.map(x=>x.high));const minLow=Math.min(...afterExit.map(x=>x.low));hindsight=`<div class="ticket-row"><span>Máximo después de salir</span><strong>${usd(maxHigh)}</strong></div><div class="ticket-row"><span>Mínimo después de salir</span><strong>${usd(minLow)}</strong></div>`;}}
  if(d.action!=='BUY')document.getElementById('revealResult').innerHTML='<div class="result-ticket"><strong>NO TRADE</strong><span>Todo lo posterior es diagnóstico retrospectivo.</span></div>';
  else if(r.available)document.getElementById('revealResult').innerHTML=`<div class="result-ticket"><div class="ticket-row"><span>Entrada</span><strong>${usd(r.entry_price)} · ${dayFmt(r.entry_day)}</strong></div><div class="ticket-row"><span>Salida fijada</span><strong>${usd(r.exit_price)} · ${dayFmt(r.exit_day)}</strong></div><div class="ticket-row"><span>P/L</span><strong class="${pnlClass(r.net_pnl_eur)}">${eur(r.net_pnl_eur)}</strong></div><div class="ticket-row"><span>SPY mismo intervalo</span><strong>${pct(r.spy_return_pct)}</strong></div>${hindsight}<p class="small-muted">Esta parte es hindsight-only y jamás modifica la decisión histórica.</p></div>`;
  document.getElementById('revealResult').classList.remove('hidden');document.getElementById('revealFuture').disabled=true;
});

function drawEquity(series){const svg=document.getElementById('equityChart');if(!svg||!series?.length)return;const vals=series.map(x=>x.equity_eur);const min=Math.min(...vals),max=Math.max(...vals),span=Math.max(max-min,1);const pts=series.map((p,i)=>`${10+(i/Math.max(1,series.length-1))*780},${240-((p.equity_eur-min)/span)*210}`).join(' ');svg.innerHTML=`<polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>`;}
function renderLive(data){setText('startingCapital',eur(data.starting_capital_eur));setText('currentEquity',eur(data.current_equity_eur));const pnl=document.getElementById('totalPnl');pnl.textContent=eur(data.total_net_pnl_eur);pnl.className=pnlClass(data.total_net_pnl_eur);setText('wins',data.counts?.wins??0);setText('losses',data.counts?.losses??0);setText('noTrades',data.counts?.no_trades??0);setText('decisions',data.counts?.decisions??0);const latest=data.latest_decision;if(latest){setText('latestTitle',latest.action==='NO_TRADE'?'Hoy decidió no hacer nada':`${latest.action} ${latest.symbol??''}`.trim());setText('latestThesis',latest.thesis);const badge=document.getElementById('latestBadge');badge.textContent=latest.action;badge.className='decision-badge '+(latest.action==='BUY'?'badge-win':latest.action==='SELL'?'badge-loss':'badge-neutral');document.getElementById('latestMeta').innerHTML=`<span>${dateFmt(latest.decision_at)}</span><span>Confianza ${Math.round((latest.confidence??0)*100)}%</span>`;}const positions=document.getElementById('positions');if(data.open_positions?.length){positions.classList.remove('empty');positions.innerHTML=data.open_positions.map(p=>`<div class="stack-item"><strong>${esc(p.symbol)}</strong><span>${eur(p.notional_eur)}</span></div>`).join('');}const away=document.getElementById('whileAway');if(data.while_away?.length){away.classList.remove('empty');away.innerHTML=[...data.while_away].reverse().map(r=>`<div class="stack-item"><div><strong>${esc(r.action)}${r.symbol?' '+esc(r.symbol):''}</strong><div class="neutral">${dateFmt(r.decision_at)}</div></div><span>${r.net_pnl_eur==null?esc(r.result):eur(r.net_pnl_eur)}</span></div>`).join('');}const tbody=document.getElementById('historyBody');if(data.history?.length){tbody.innerHTML=[...data.history].reverse().map(r=>`<tr><td>${dateFmt(r.decision_at)}</td><td>${esc(r.symbol??'—')}</td><td>${esc(r.action)}</td><td>${esc(r.result)}</td><td>${r.net_pnl_eur==null?'—':eur(r.net_pnl_eur)}</td></tr>`).join('');}drawEquity(data.equity_series);const health=data.health||{};setText('statusPill',health.last_error_kind?`Atención: ${health.last_error_kind}`:'SIMULACIÓN · €0 real');}

Promise.all([fetch('./data/replay-v2.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`replay-v2 ${r.status}`);return r.json();}),fetch('./data/dashboard.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`dashboard ${r.status}`);return r.json();})]).then(([replays,live])=>{renderReplayData(replays);renderLive(live);setText('lastUpdated',`Replay generado ${dateFmt(replays.generated_at)}`);}).catch(err=>{document.getElementById('scanResult').classList.remove('hidden');document.getElementById('scanResult').innerHTML=`<div class="small-muted">El Replay todavía se está generando o publicando. ${esc(err.message)}</div>`;setText('statusPill','Preparando Replay');});
