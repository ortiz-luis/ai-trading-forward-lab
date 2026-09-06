const eur=value=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value??0);
const usd=value=>value==null?'—':`$${new Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(value)}`;
const pct=value=>value==null?'—':`${Number(value).toFixed(2)}%`;
const dayFmt=value=>value?new Intl.DateTimeFormat('es-ES',{dateStyle:'medium'}).format(new Date(`${value}T12:00:00Z`)):'—';
const dateFmt=value=>value?new Intl.DateTimeFormat('es-ES',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)):'—';
const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const setText=(id,value)=>{const el=document.getElementById(id);if(el)el.textContent=value;};
const pnlClass=value=>value>0?'positive':value<0?'negative':'neutral';
const unlock=id=>{const el=document.getElementById(id);if(el)el.classList.remove('locked-step');};

let replayData=null;
let currentReplay=null;
let visibleRange='1M';
let scanned=false;
let asked=false;
let applied=false;
let revealed=false;
let followVisible=0;
let proChart=null;
let candleSeries=null;
let volumeSeries=null;
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
  if(proChart){proChart.remove();proChart=null;candleSeries=null;volumeSeries=null;smaSeries=[];}
  const host=document.getElementById('professionalChart');
  if(host)host.innerHTML='';
}

function smaData(rows,period){
  const out=[];let sum=0;
  rows.forEach((row,i)=>{
    sum+=row.close;
    if(i>=period)sum-=rows[i-period].close;
    if(i>=period-1)out.push({time:row.date,value:sum/period});
  });
  return out;
}

function chartRows(){
  if(!currentReplay)return[];
  const c=currentReplay.chart||{};
  const before=(c.candles_before_cutoff?.length?c.candles_before_cutoff:c.spy_before_cutoff)||[];
  const after=revealed?((c.candles_after_cutoff?.length?c.candles_after_cutoff:c.spy_after_cutoff)||[]):[];
  return {before,after,all:[...before,...after]};
}

function rangeSessions(){return {'1W':5,'1M':22,'3M':66,'1Y':252,'2Y':520}[visibleRange]||22;}

function renderProfessionalChart(){
  if(!currentReplay||!scanned)return;
  const host=document.getElementById('professionalChart');
  if(!host)return;
  destroyProfessionalChart();
  const {before,after,all}=chartRows();
  if(!all.length){host.innerHTML='<div class="small-muted" style="padding:20px">No hay velas disponibles para este replay.</div>';return;}
  if(!window.LightweightCharts){host.innerHTML='<div class="small-muted" style="padding:20px">No se pudo cargar el motor de gráficos.</div>';return;}

  proChart=LightweightCharts.createChart(host,{
    width:host.clientWidth,
    height:host.clientHeight,
    layout:{background:{color:'#ffffff'},textColor:'#596673'},
    grid:{vertLines:{color:'#f1f3f5'},horzLines:{color:'#f1f3f5'}},
    rightPriceScale:{borderColor:'#e5e9ed'},
    timeScale:{borderColor:'#e5e9ed',timeVisible:false,rightOffset:2},
    crosshair:{mode:LightweightCharts.CrosshairMode.Normal},
  });
  candleSeries=proChart.addCandlestickSeries({
    upColor:'#18794e',downColor:'#b42318',borderVisible:false,wickUpColor:'#18794e',wickDownColor:'#b42318',
    priceScaleId:'right',
  });
  candleSeries.setData(all.map(r=>({time:r.date,open:r.open,high:r.high,low:r.low,close:r.close})));
  volumeSeries=proChart.addHistogramSeries({priceFormat:{type:'volume'},priceScaleId:'volume',scaleMargins:{top:0.80,bottom:0}});
  volumeSeries.setData(all.map(r=>({time:r.date,value:r.volume,color:r.close>=r.open?'rgba(24,121,78,.32)':'rgba(180,35,24,.28)'})));
  proChart.priceScale('volume').applyOptions({scaleMargins:{top:.82,bottom:0}});

  [20,50,200].forEach(period=>{
    const data=smaData(before,period);
    if(!data.length)return;
    const line=proChart.addLineSeries({lineWidth:1,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
    line.setData(data);
    smaSeries.push(line);
  });

  const o=currentReplay.chart?.overlays||{};
  const lines=[];
  (o.support_levels||[]).forEach((price,i)=>lines.push({price,color:'#18794e',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`Soporte ${i+1}`}));
  (o.resistance_levels||[]).forEach((price,i)=>lines.push({price,color:'#b42318',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`Resistencia ${i+1}`}));
  if(o.target_price)lines.push({price:o.target_price,color:'#344054',lineWidth:1,lineStyle:1,axisLabelVisible:true,title:'Objetivo'});
  if(applied&&currentReplay.result?.entry_price)lines.push({price:currentReplay.result.entry_price,color:'#17202a',lineWidth:2,lineStyle:0,axisLabelVisible:true,title:'Entrada'});
  lines.forEach(line=>candleSeries.createPriceLine(line));

  const markers=[];
  if(before.length)markers.push({time:before[before.length-1].date,position:'aboveBar',color:'#7a5b00',shape:'circle',text:'Cutoff'});
  if(applied&&currentReplay.result?.entry_day)markers.push({time:currentReplay.result.entry_day,position:'belowBar',color:'#17202a',shape:'arrowUp',text:'Entrada'});
  if(revealed&&currentReplay.result?.exit_day)markers.push({time:currentReplay.result.exit_day,position:'aboveBar',color:'#17202a',shape:'arrowDown',text:'Salida'});
  if(revealed){
    (currentReplay.lifecycle||[]).forEach(row=>markers.push({time:row.date,position:row.action==='SELL'?'aboveBar':'belowBar',color:row.action==='SELL'?'#b42318':'#65717d',shape:row.action==='SELL'?'arrowDown':'circle',text:row.action}));
  }
  candleSeries.setMarkers(markers.filter(m=>all.some(r=>r.date===m.time)));

  const n=rangeSessions();
  const from=Math.max(0,all.length-n);
  proChart.timeScale().setVisibleLogicalRange({from,to:all.length+1});
  setText('chartRevealState',revealed?'Futuro revelado · velas posteriores visibles':'Sólo datos conocidos al cutoff');
  const symbol=currentReplay.chart?.symbol||'SPY';
  setText('professionalChartTitle',`${symbol} · velas diarias hasta ${dayFmt(currentReplay.cutoff_date)}`);
  const scope=currentReplay.analysis_scope||{};
  setText('chartContextNote',`Vista ${visibleRange}; la IA analizó ${scope.daily_history_target||'histórico amplio'} y horizontes ${(scope.technical_horizons||[]).join(' / ')}.`);

  const levels=[];
  if(o.sma20)levels.push(`SMA20 ${usd(o.sma20)}`);
  if(o.sma50)levels.push(`SMA50 ${usd(o.sma50)}`);
  if(o.sma200)levels.push(`SMA200 ${usd(o.sma200)}`);
  (o.support_levels||[]).forEach(v=>levels.push(`Soporte ${usd(v)}`));
  (o.resistance_levels||[]).forEach(v=>levels.push(`Resistencia ${usd(v)}`));
  if(o.target_price)levels.push(`Objetivo ${usd(o.target_price)}`);
  document.getElementById('chartLevels').innerHTML=levels.map(x=>`<span class="level-chip">${esc(x)}</span>`).join('');
}

window.addEventListener('resize',()=>{if(proChart){const host=document.getElementById('professionalChart');proChart.applyOptions({width:host.clientWidth,height:host.clientHeight});}});

document.querySelectorAll('[data-range]').forEach(btn=>btn.addEventListener('click',()=>{
  visibleRange=btn.dataset.range;
  document.querySelectorAll('[data-range]').forEach(b=>b.classList.toggle('active',b===btn));
  renderProfessionalChart();
}));

function resetReplay(){
  scanned=false;asked=false;applied=false;revealed=false;followVisible=0;
  ['decisionCard','applyCard','followCard','revealCard'].forEach(id=>document.getElementById(id).classList.add('locked-step'));
  ['scanResult','decisionShort','applyResult','followResult','revealResult','lessonCard','professionalChartCard'].forEach(id=>document.getElementById(id).classList.add('hidden'));
  ['askDecision','applyDecision','advanceDay','revealFuture'].forEach(id=>{const el=document.getElementById(id);el.classList.add('hidden');el.disabled=false;});
  const scan=document.getElementById('scanMarket');scan.disabled=false;scan.textContent='Explorar mercado';
  destroyProfessionalChart();
}

function loadReplay(id){
  currentReplay=replayData.sessions.find(s=>s.replay_id===id)||replayData.sessions[0];
  const scope=currentReplay.analysis_scope||{};
  setText('analysisScope',`ChatGPT comparó ${scope.universe_size||18} acciones, ${scope.daily_history_target||'histórico amplio'}, horizontes ${(scope.technical_horizons||[]).join(', ')} y noticias cutoff-safe.`);
  resetReplay();
}

function renderReplayData(data){
  replayData=data;
  const select=document.getElementById('replayDate');
  select.innerHTML=[...data.sessions].reverse().map(s=>`<option value="${esc(s.replay_id)}">${dayFmt(s.cutoff_date)}</option>`).join('');
  const first=[...data.sessions].reverse()[0];
  select.value=first.replay_id;
  loadReplay(first.replay_id);
}

document.getElementById('replayDate').addEventListener('change',e=>loadReplay(e.target.value));

document.getElementById('scanMarket').addEventListener('click',()=>{
  if(!currentReplay)return;
  scanned=true;
  const s=currentReplay.selection||{};
  const selected=s.selected_symbol;
  const rows=(s.shortlist||[]).map(r=>`<div class="scan-row"><strong>${esc(r.symbol)}</strong><span class="score-pill">${Math.round((r.score||0)*100)}%</span><span>${esc(r.reason)}</span></div>`).join('');
  document.getElementById('scanResult').innerHTML=`<div class="short-decision"><strong>${selected?`Foco: ${esc(selected)}`:'Hoy no hay un candidato claro'}</strong><span>${esc(s.selection_summary||'')}</span></div>${rows?`<div class="scan-shortlist">${rows}</div>`:''}<p class="small-muted">Por qué no las demás: ${esc(s.why_not_others||'')}</p>`;
  document.getElementById('scanResult').classList.remove('hidden');
  document.getElementById('professionalChartCard').classList.remove('hidden');
  unlock('decisionCard');
  document.getElementById('askDecision').classList.remove('hidden');
  const btn=document.getElementById('scanMarket');btn.disabled=true;btn.textContent='Mercado explorado';
  renderProfessionalChart();
});

function renderEvidence(){
  const list=document.getElementById('evidenceList');
  const rows=currentReplay.evidence||[];
  if(!rows.length){list.innerHTML='<div class="small-muted">No hubo noticias cutoff-safe suficientemente relevantes para este replay.</div>';return;}
  list.innerHTML=rows.map(row=>`<div class="evidence-item"><a href="${esc(row.url)}" target="_blank" rel="noopener noreferrer">${esc(row.headline||row.source||row.url)}</a><span>${esc(row.summary||'')}</span><span class="evidence-meta">${esc(row.source||'')} · ${dateFmt(row.published_at)}</span></div>`).join('');
}

document.getElementById('askDecision').addEventListener('click',()=>{
  if(!currentReplay)return;
  asked=true;
  const d=currentReplay.decision||{};
  const title=d.action==='BUY'?`BUY ${d.symbol}`:'NO TRADE';
  document.getElementById('decisionShort').innerHTML=`<div class="short-decision"><strong>${esc(title)}</strong><span>${d.notional_eur?`${eur(d.notional_eur)} · `:''}confianza ${Math.round((d.confidence||0)*100)}%${d.horizon_days?` · ${d.horizon_days} días`:''}${d.stop_pct?` · stop ${pct(d.stop_pct*100)}`:''}${d.target_price?` · objetivo ${usd(d.target_price)}`:''}</span><p>${esc(d.short_answer||d.thesis||'')}</p></div>`;
  document.getElementById('decisionShort').classList.remove('hidden');
  setText('lessonSelection',currentReplay.selection?.selection_summary||'');
  setText('lessonChart',d.chart_reading||'');
  setText('lessonNews',d.news_reading||'');
  setText('lessonRisk',`${d.counter_thesis||''}\n\n${d.risk_lesson||''}`);
  renderEvidence();
  document.getElementById('lessonCard').classList.remove('hidden');
  unlock('applyCard');
  document.getElementById('applyDecision').classList.remove('hidden');
  const btn=document.getElementById('askDecision');btn.disabled=true;btn.textContent='Respuesta revelada';
  renderProfessionalChart();
});

document.getElementById('applyDecision').addEventListener('click',()=>{
  if(!currentReplay)return;
  applied=true;
  const d=currentReplay.decision||{};
  const r=currentReplay.result||{};
  if(d.action!=='BUY'){
    document.getElementById('applyResult').innerHTML='<div class="apply-ticket"><strong>No se abrió posición.</strong><span>La IA conservó los €1.000 ficticios en cash.</span></div>';
  }else if(r.available){
    document.getElementById('applyResult').innerHTML=`<div class="apply-ticket"><div class="ticket-row"><span>Activo</span><strong>${esc(d.symbol)}</strong></div><div class="ticket-row"><span>Capital asignado</span><strong>${eur(d.notional_eur)}</strong></div><div class="ticket-row"><span>Entrada simulada</span><strong>${usd(r.entry_price)}</strong></div><div class="ticket-row"><span>Primera sesión</span><strong>${dayFmt(r.entry_day)}</strong></div></div>`;
  }else{
    document.getElementById('applyResult').textContent='La entrada todavía no existe en este replay.';
  }
  document.getElementById('applyResult').classList.remove('hidden');
  unlock('followCard');
  const lifecycle=currentReplay.lifecycle||[];
  if(lifecycle.length)document.getElementById('advanceDay').classList.remove('hidden');
  else{unlock('revealCard');document.getElementById('revealFuture').classList.remove('hidden');}
  document.getElementById('applyDecision').disabled=true;
  renderProfessionalChart();
});

function renderLifecycle(){
  const rows=(currentReplay.lifecycle||[]).slice(0,followVisible);
  const body=rows.map(r=>`<tr><td>${dayFmt(r.date)}</td><td><strong>${esc(r.action)}</strong></td><td>${Math.round((r.confidence||0)*100)}%</td><td>${esc(r.new_information)}</td><td>${esc(r.reason)}</td></tr>`).join('');
  document.getElementById('followResult').innerHTML=`<div class="follow-table"><table><thead><tr><th>Fecha</th><th>Qué haría</th><th>Confianza</th><th>Nueva información</th><th>Por qué</th></tr></thead><tbody>${body}</tbody></table></div>`;
  document.getElementById('followResult').classList.remove('hidden');
}

document.getElementById('advanceDay').addEventListener('click',()=>{
  const lifecycle=currentReplay.lifecycle||[];
  if(followVisible<lifecycle.length)followVisible+=1;
  renderLifecycle();
  const done=followVisible>=lifecycle.length||lifecycle[followVisible-1]?.action==='SELL';
  if(done){
    document.getElementById('advanceDay').disabled=true;
    document.getElementById('advanceDay').textContent=lifecycle[followVisible-1]?.action==='SELL'?'La IA decidió salir':'Seguimiento completado';
    unlock('revealCard');
    document.getElementById('revealFuture').classList.remove('hidden');
  }
});

document.getElementById('revealFuture').addEventListener('click',()=>{
  revealed=true;
  const d=currentReplay.decision||{};
  const r=currentReplay.result||{};
  const future=currentReplay.chart?.candles_after_cutoff||[];
  let hindsight='';
  if(d.action==='BUY'&&r.available&&future.length){
    const afterExit=future.filter(x=>r.exit_day&&x.date>r.exit_day);
    if(afterExit.length){
      const maxHigh=Math.max(...afterExit.map(x=>x.high));
      hindsight=`<div class="ticket-row"><span>Máximo posterior a la salida</span><strong>${usd(maxHigh)}</strong></div>`;
    }
  }
  if(d.action!=='BUY'){
    document.getElementById('revealResult').innerHTML='<div class="result-ticket"><strong>NO TRADE</strong><span>El capital habría permanecido en €1.000. Las velas posteriores se muestran sólo como diagnóstico retrospectivo.</span></div>';
  }else if(r.available){
    document.getElementById('revealResult').innerHTML=`<div class="result-ticket"><div class="ticket-row"><span>Entrada</span><strong>${usd(r.entry_price)} · ${dayFmt(r.entry_day)}</strong></div><div class="ticket-row"><span>Salida siguiendo a la IA</span><strong>${usd(r.exit_price)} · ${dayFmt(r.exit_day)}</strong></div><div class="ticket-row"><span>P/L</span><strong class="${pnlClass(r.net_pnl_eur)}">${eur(r.net_pnl_eur)}</strong></div><div class="ticket-row"><span>Capital final</span><strong>${eur(r.capital_after_eur)}</strong></div><div class="ticket-row"><span>Retorno sobre lo asignado</span><strong>${pct(r.return_pct)}</strong></div><div class="ticket-row"><span>SPY mismo intervalo</span><strong>${pct(r.spy_return_pct)}</strong></div>${hindsight}<p class="small-muted">La comparación posterior es hindsight-only: nunca fue entregada a la IA durante el replay.</p></div>`;
  }else{
    document.getElementById('revealResult').textContent='Aún no existe un resultado posterior.';
  }
  document.getElementById('revealResult').classList.remove('hidden');
  document.getElementById('revealFuture').disabled=true;
  renderProfessionalChart();
});

function drawEquity(series){
  const svg=document.getElementById('equityChart');
  if(!svg||!series?.length)return;
  const vals=series.map(x=>x.equity_eur);const min=Math.min(...vals),max=Math.max(...vals),span=Math.max(max-min,1);
  const pts=series.map((p,i)=>`${10+(i/Math.max(1,series.length-1))*780},${240-((p.equity_eur-min)/span)*210}`).join(' ');
  svg.innerHTML=`<polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>`;
}

function renderLive(data){
  setText('startingCapital',eur(data.starting_capital_eur));setText('currentEquity',eur(data.current_equity_eur));
  const pnl=document.getElementById('totalPnl');pnl.textContent=eur(data.total_net_pnl_eur);pnl.className=pnlClass(data.total_net_pnl_eur);
  setText('wins',data.counts?.wins??0);setText('losses',data.counts?.losses??0);setText('noTrades',data.counts?.no_trades??0);setText('decisions',data.counts?.decisions??0);
  const latest=data.latest_decision;if(latest){setText('latestTitle',latest.action==='NO_TRADE'?'Hoy decidió no hacer nada':`${latest.action} ${latest.symbol??''}`.trim());setText('latestThesis',latest.thesis);const badge=document.getElementById('latestBadge');badge.textContent=latest.action;badge.className='decision-badge '+(latest.action==='BUY'?'badge-win':latest.action==='SELL'?'badge-loss':'badge-neutral');document.getElementById('latestMeta').innerHTML=`<span>${dateFmt(latest.decision_at)}</span><span>Confianza ${Math.round((latest.confidence??0)*100)}%</span><span>${latest.notional_eur?eur(latest.notional_eur):'Sin capital asignado'}</span>`;}
  const positions=document.getElementById('positions');if(data.open_positions?.length){positions.classList.remove('empty');positions.innerHTML=data.open_positions.map(p=>`<div class="stack-item"><strong>${esc(p.symbol)}</strong><span>${eur(p.notional_eur)}</span></div>`).join('');}
  const away=document.getElementById('whileAway');if(data.while_away?.length){away.classList.remove('empty');away.innerHTML=[...data.while_away].reverse().map(r=>`<div class="stack-item"><div><strong>${esc(r.action)}${r.symbol?' '+esc(r.symbol):''}</strong><div class="neutral">${dateFmt(r.decision_at)}</div></div><span class="${pnlClass(r.net_pnl_eur)}">${r.net_pnl_eur==null?esc(r.result):eur(r.net_pnl_eur)}</span></div>`).join('');}
  const tbody=document.getElementById('historyBody');if(data.history?.length){tbody.innerHTML=[...data.history].reverse().map(r=>`<tr><td>${dateFmt(r.decision_at)}</td><td>${esc(r.symbol??'—')}</td><td>${esc(r.action)}</td><td>${esc(r.result)}</td><td class="${pnlClass(r.net_pnl_eur)}">${r.net_pnl_eur==null?'—':eur(r.net_pnl_eur)}</td></tr>`).join('');}
  drawEquity(data.equity_series);
  const health=data.health||{};const pill=document.getElementById('statusPill');pill.textContent=health.last_error_kind?`Atención: ${health.last_error_kind}`:'SIMULACIÓN · €0 real';
}

Promise.all([
  fetch('./data/replay-v2.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`replay-v2 ${r.status}`);return r.json();}),
  fetch('./data/dashboard.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`dashboard ${r.status}`);return r.json();}),
]).then(([replays,live])=>{renderReplayData(replays);renderLive(live);setText('lastUpdated',`Replay v2 generado ${dateFmt(replays.generated_at)}`);}).catch(err=>{
  document.getElementById('scanResult').classList.remove('hidden');
  document.getElementById('scanResult').innerHTML=`<div class="small-muted">El Professional Replay v2 todavía se está generando o publicando. ${esc(err.message)}</div>`;
  setText('statusPill','Preparando Replay v2');
});
