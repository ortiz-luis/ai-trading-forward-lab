const eur = value => new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value ?? 0);
const num = value => new Intl.NumberFormat('es-ES',{maximumFractionDigits:4}).format(value ?? 0);
const pct = value => `${(value ?? 0).toFixed(2)}%`;
const dateFmt = value => value ? new Intl.DateTimeFormat('es-ES',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)) : '—';
const dayFmt = value => value ? new Intl.DateTimeFormat('es-ES',{dateStyle:'medium'}).format(new Date(`${value}T12:00:00Z`)) : '—';

function setText(id, value){ const el=document.getElementById(id); if(el) el.textContent=value; }
function pnlClass(value){ return value>0?'positive':value<0?'negative':'neutral'; }
function unlock(id){ const el=document.getElementById(id); if(el){el.classList.remove('locked-step');el.classList.add('unlocked-step');} }

let replayData=null;
let currentReplay=null;
let replayRange='1M';
let replayStage=0;

function switchMode(mode){
  const replay=mode==='replay';
  document.getElementById('replayPanel').classList.toggle('hidden',!replay);
  document.getElementById('livePanel').classList.toggle('hidden',replay);
  document.getElementById('replayModeButton').classList.toggle('active',replay);
  document.getElementById('liveModeButton').classList.toggle('active',!replay);
}

document.getElementById('replayModeButton').addEventListener('click',()=>switchMode('replay'));
document.getElementById('liveModeButton').addEventListener('click',()=>switchMode('live'));

function drawLineChart(svgId, points, {futurePoints=[]}={}){
  const svg=document.getElementById(svgId);
  if(!svg || !points?.length){ if(svg) svg.innerHTML=''; return; }
  const all=[...points,...futurePoints];
  const values=all.map(p=>p.value);
  const min=Math.min(...values), max=Math.max(...values);
  const span=Math.max(max-min,0.0001);
  const xFor=i=>all.length===1?400:(i/(all.length-1))*760+20;
  const yFor=v=>235-((v-min)/span)*190;
  const pastPts=points.map((p,i)=>`${xFor(i)},${yFor(p.value)}`).join(' ');
  let html=`<line x1="20" y1="235" x2="780" y2="235" stroke="currentColor" opacity=".10"/><polyline points="${pastPts}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>`;
  if(futurePoints.length){
    const joined=[points[points.length-1],...futurePoints];
    const offset=points.length-1;
    const futPts=joined.map((p,j)=>`${xFor(offset+j)},${yFor(p.value)}`).join(' ');
    html+=`<polyline points="${futPts}" fill="none" stroke="#b42318" stroke-width="4" vector-effect="non-scaling-stroke"/>`;
  }
  const labels=[all[0],all[all.length-1]];
  html+=labels.map((p,idx)=>`<text x="${idx?780:20}" y="255" text-anchor="${idx?'end':'start'}" font-size="11" fill="currentColor" opacity=".55">${p.label}</text>`).join('');
  svg.innerHTML=html;
}

function drawEquity(series){
  const svg=document.getElementById('equityChart');
  if(!svg || !series?.length){ if(svg) svg.innerHTML=''; return; }
  const values=series.map(p=>p.equity_eur);
  const min=Math.min(...values), max=Math.max(...values);
  const span=Math.max(max-min,1);
  const coords=series.map((p,i)=>({...p,x:series.length===1?400:(i/(series.length-1))*780+10,y:240-((p.equity_eur-min)/span)*210}));
  const pre=coords.filter(p=>p.phase==='PREHISTORY');
  const fwd=coords.filter(p=>p.phase==='FORWARD');
  const prePts=pre.map(p=>`${p.x},${p.y}`).join(' ');
  const joinedFwd=(fwd.length && pre.length ? [pre[pre.length-1],...fwd] : fwd).map(p=>`${p.x},${p.y}`).join(' ');
  const boundary=fwd.length ? fwd[0].x : null;
  svg.innerHTML=`<line x1="10" y1="240" x2="790" y2="240" stroke="currentColor" opacity=".12"/>${pre.length>1?`<polyline points="${prePts}" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="9 9" opacity=".35" vector-effect="non-scaling-stroke"/>`:''}${joinedFwd?`<polyline points="${joinedFwd}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>`:''}${boundary!==null?`<line x1="${boundary}" y1="18" x2="${boundary}" y2="245" stroke="currentColor" stroke-width="2" stroke-dasharray="4 6" opacity=".45"/><text x="${Math.min(boundary+8,650)}" y="28" fill="currentColor" opacity=".7" font-size="14">Inicio forward</text>`:`<text x="20" y="28" fill="currentColor" opacity=".65" font-size="14">Prehistoria visual · €1.000, sin decisiones</text>`}`;
}

function replayChartPoints(){
  if(!currentReplay) return {past:[],future:[]};
  const symbol=document.getElementById('replaySymbol').value || 'SPY';
  let rows=currentReplay.charts?.[symbol] || [];
  if(replayRange==='1W') rows=rows.slice(-5);
  const past=rows.map(r=>({label:r.date,value:r.close}));
  const future=[];
  const result=currentReplay.result_next_session;
  if(replayStage>=2 && result?.available && result.action==='BUY' && symbol===currentReplay.decision.symbol && result.entry){
    future.push({label:`${result.session_date} open`,value:result.raw_open ?? result.entry});
  }
  if(replayStage>=3 && result?.available && result.action==='BUY' && symbol===currentReplay.decision.symbol && result.close){
    future.push({label:`${result.session_date} close`,value:result.close});
  }
  return {past,future};
}

function renderReplayChart(){
  if(!currentReplay) return;
  const symbol=document.getElementById('replaySymbol').value || 'SPY';
  setText('replayChartTitle',`${symbol} · datos disponibles hasta ${dayFmt(currentReplay.cutoff_date)}`);
  setText('replayCutoff',`Cutoff ${dateFmt(currentReplay.cutoff_at)}`);
  const {past,future}=replayChartPoints();
  drawLineChart('replayChart',past,{futurePoints:future});
  document.getElementById('futureLegend').classList.toggle('hidden',!future.length);
}

function resetReplaySteps(){
  replayStage=0;
  ['decisionStep','applyStep','resultStep'].forEach(id=>{const el=document.getElementById(id);el.classList.add('locked-step');el.classList.remove('unlocked-step');});
  setText('replayDecisionTitle','Esperando consulta');
  document.getElementById('replayDecisionBody').textContent='Todavía no sabes qué eligió.';
  setText('replayApplyTitle','Aún no aplicada');
  document.getElementById('replayApplyBody').textContent='El precio de apertura sigue oculto.';
  setText('replayResultTitle','Futuro oculto');
  document.getElementById('replayResultBody').textContent='Aquí aparecerá el cierre siguiente y cuánto habría cambiado el capital.';
  const apply=document.getElementById('applyReplay');apply.classList.add('hidden');apply.disabled=false;
  const reveal=document.getElementById('revealReplay');reveal.classList.add('hidden');reveal.disabled=false;
  const ask=document.getElementById('askReplay');ask.disabled=false;ask.textContent='Consultar a ChatGPT';
  renderReplayChart();
}

function loadReplaySession(replayId){
  currentReplay=replayData.sessions.find(s=>s.replay_id===replayId) || replayData.sessions[0];
  const symbolSelect=document.getElementById('replaySymbol');
  const symbols=Object.keys(currentReplay.charts||{}).sort((a,b)=>a==='SPY'?-1:b==='SPY'?1:a.localeCompare(b));
  symbolSelect.innerHTML=symbols.map(s=>`<option value="${s}">${s}</option>`).join('');
  symbolSelect.value='SPY';
  resetReplaySteps();
}

function renderReplayData(data){
  replayData=data;
  const select=document.getElementById('replayDate');
  select.innerHTML=[...data.sessions].reverse().map(s=>`<option value="${s.replay_id}">${dayFmt(s.cutoff_date)}${s.result_next_session?.available?'':' · futuro aún no ocurrido'}</option>`).join('');
  const first=[...data.sessions].reverse().find(s=>s.result_next_session?.available) || data.sessions[data.sessions.length-1];
  select.value=first.replay_id;
  loadReplaySession(first.replay_id);
}

document.getElementById('replayDate').addEventListener('change',e=>loadReplaySession(e.target.value));
document.getElementById('replaySymbol').addEventListener('change',renderReplayChart);
document.getElementById('range1w').addEventListener('click',()=>{replayRange='1W';document.getElementById('range1w').classList.add('active');document.getElementById('range1m').classList.remove('active');renderReplayChart();});
document.getElementById('range1m').addEventListener('click',()=>{replayRange='1M';document.getElementById('range1m').classList.add('active');document.getElementById('range1w').classList.remove('active');renderReplayChart();});

document.getElementById('askReplay').addEventListener('click',()=>{
  if(!currentReplay) return;
  replayStage=1;
  const d=currentReplay.decision;
  unlock('decisionStep');
  setText('replayDecisionTitle',d.action==='NO_TRADE'?'ChatGPT decidió esperar':`${d.action} ${d.symbol}`);
  document.getElementById('replayDecisionBody').innerHTML=`<div class="decision-summary"><strong>${d.action}${d.symbol?` ${d.symbol}`:''}</strong><span>Confianza ${Math.round((d.confidence??0)*100)}%${d.notional_eur?` · ${eur(d.notional_eur)}`:''}${d.horizon_days?` · horizonte ${d.horizon_days} días`:''}</span><div class="reason-box"><b>Por qué:</b> ${d.thesis}</div><div class="reason-box"><b>Qué podría salir mal:</b> ${d.counter_thesis}</div></div>`;
  document.getElementById('applyReplay').classList.remove('hidden');
  const ask=document.getElementById('askReplay');ask.disabled=true;ask.textContent='Respuesta revelada';
  if(d.symbol && currentReplay.charts?.[d.symbol]) document.getElementById('replaySymbol').value=d.symbol;
  renderReplayChart();
});

document.getElementById('applyReplay').addEventListener('click',()=>{
  if(!currentReplay) return;
  replayStage=2;
  const d=currentReplay.decision;
  const r=currentReplay.result_next_session;
  unlock('applyStep');
  if(d.action==='NO_TRADE'){
    setText('replayApplyTitle','No se abrió posición');
    document.getElementById('replayApplyBody').innerHTML='<div class="apply-ticket"><span>ChatGPT prefirió conservar los €1.000 ficticios en cash.</span></div>';
  } else if(r?.available){
    setText('replayApplyTitle',`${d.symbol} comprado en la apertura`);
    document.getElementById('replayApplyBody').innerHTML=`<div class="apply-ticket"><div class="ticket-row"><span>Fecha</span><strong>${dayFmt(r.session_date)}</strong></div><div class="ticket-row"><span>Capital asignado</span><strong>${eur(d.notional_eur)}</strong></div><div class="ticket-row"><span>Precio simulado de entrada</span><strong>$${num(r.entry)}</strong></div><div class="ticket-row"><span>Acciones simuladas</span><strong>${num(r.shares_simulated)}</strong></div></div>`;
  } else {
    setText('replayApplyTitle','La apertura siguiente aún no ocurrió');
    document.getElementById('replayApplyBody').textContent='Este replay llegó al borde del presente. No revelaremos un precio futuro inexistente.';
  }
  document.getElementById('revealReplay').classList.remove('hidden');
  document.getElementById('applyReplay').disabled=true;
  renderReplayChart();
});

document.getElementById('revealReplay').addEventListener('click',()=>{
  if(!currentReplay) return;
  replayStage=3;
  const d=currentReplay.decision;
  const r=currentReplay.result_next_session;
  unlock('resultStep');
  if(!r?.available){
    setText('replayResultTitle','Todavía no existe el resultado');
    document.getElementById('replayResultBody').textContent='La siguiente sesión todavía no ha ocurrido. Este es exactamente el comportamiento que tendrá el modo en vivo.';
  } else if(d.action==='NO_TRADE'){
    setText('replayResultTitle','Capital intacto');
    document.getElementById('replayResultBody').innerHTML=`<div class="result-ticket"><div class="ticket-row"><span>P/L de la decisión</span><strong class="neutral">${eur(0)}</strong></div><div class="ticket-row"><span>SPY ese día</span><strong>${pct(r.benchmark_return_pct)}</strong></div><span>ChatGPT decidió no exponerse y conservó los €1.000 ficticios.</span></div>`;
  } else {
    const after=1000+r.net_pnl_eur;
    setText('replayResultTitle',r.net_pnl_eur>0?'La idea habría ganado':r.net_pnl_eur<0?'La idea habría perdido':'Resultado plano');
    document.getElementById('replayResultBody').innerHTML=`<div class="result-ticket"><div class="ticket-row"><span>Cierre siguiente</span><strong>$${num(r.close)}</strong></div><div class="ticket-row"><span>Resultado</span><strong class="${pnlClass(r.net_pnl_eur)}">${eur(r.net_pnl_eur)}</strong></div><div class="ticket-row"><span>Capital después</span><strong>${eur(after)}</strong></div><div class="ticket-row"><span>Retorno sobre lo asignado</span><strong>${pct(r.return_pct)}</strong></div><div class="ticket-row"><span>SPY ese día</span><strong>${pct(r.benchmark_return_pct)}</strong></div></div>`;
  }
  document.getElementById('revealReplay').disabled=true;
  renderReplayChart();
});

function renderLive(data){
  setText('startingCapital',eur(data.starting_capital_eur));
  setText('currentEquity',eur(data.current_equity_eur));
  const pnl=document.getElementById('totalPnl'); pnl.textContent=eur(data.total_net_pnl_eur); pnl.className=pnlClass(data.total_net_pnl_eur);
  setText('wins',data.counts?.wins ?? 0); setText('losses',data.counts?.losses ?? 0); setText('noTrades',data.counts?.no_trades ?? 0); setText('decisions',data.counts?.decisions ?? 0);
  const latest=data.latest_decision;
  if(latest){
    setText('latestTitle',latest.action==='NO_TRADE'?'Hoy decidió no hacer nada':`${latest.action} ${latest.symbol ?? ''}`.trim());
    setText('latestThesis',latest.thesis);
    const badge=document.getElementById('latestBadge'); badge.textContent=latest.action; badge.className='decision-badge '+(latest.action==='BUY'?'badge-win':latest.action==='SELL'?'badge-loss':'badge-neutral');
    document.getElementById('latestMeta').innerHTML=`<span>${dateFmt(latest.decision_at)}</span><span>Confianza ${Math.round((latest.confidence??0)*100)}%</span><span>${latest.notional_eur?eur(latest.notional_eur):'Sin capital asignado'}</span>`;
  }
  const positions=document.getElementById('positions');
  if(data.open_positions?.length){ positions.classList.remove('empty'); positions.innerHTML=data.open_positions.map(p=>`<div class="stack-item"><strong>${p.symbol}</strong><span>${eur(p.notional_eur)}</span></div>`).join(''); }
  const away=document.getElementById('whileAway');
  if(data.while_away?.length){ away.classList.remove('empty'); away.innerHTML=[...data.while_away].reverse().map(r=>`<div class="stack-item"><div><strong>${r.action}${r.symbol?' '+r.symbol:''}</strong><div class="neutral">${dateFmt(r.decision_at)}</div></div><span class="${pnlClass(r.net_pnl_eur)}">${r.net_pnl_eur==null?r.result:eur(r.net_pnl_eur)}</span></div>`).join(''); }
  const tbody=document.getElementById('historyBody');
  if(data.history?.length){ tbody.innerHTML=[...data.history].reverse().map(r=>`<tr><td>${dateFmt(r.decision_at)}</td><td>${r.symbol??'—'}</td><td>${r.action}</td><td>${r.result}</td><td class="${pnlClass(r.net_pnl_eur)}">${r.net_pnl_eur==null?'—':eur(r.net_pnl_eur)}</td></tr>`).join(''); }
  drawEquity(data.equity_series);
  const a=data.advanced??{};
  document.getElementById('advanced').innerHTML=`<div><span class="label">Drawdown máximo</span><strong>${(a.max_drawdown_pct??0).toFixed(2)}%</strong></div><div><span class="label">Benchmark medio</span><strong>${(a.benchmark_return_pct_mean??0).toFixed(2)}%</strong></div><div><span class="label">Puntos</span><strong>${a.score_points??0}</strong></div>`;
  const health=data.health??{};
  const pill=document.getElementById('statusPill');
  if(health.last_error_kind){ pill.textContent=`Atención: ${health.last_error_kind}`; }
  else { pill.textContent=data.simulation_only?'SIMULACIÓN · €0 real':'Estado disponible'; }
  setText('lastUpdated', health.updated_at ? `Actualizado ${dateFmt(health.updated_at)}` : 'Página lista · esperando primera sesión live');
}

Promise.allSettled([
  fetch('./data/dashboard.json',{cache:'no-store'}).then(r=>{if(!r.ok) throw new Error(`dashboard HTTP ${r.status}`); return r.json();}),
  fetch('./data/replay/index.json',{cache:'no-store'}).then(r=>{if(!r.ok) throw new Error(`replay HTTP ${r.status}`); return r.json();})
]).then(([dashboard,replay])=>{
  if(dashboard.status==='fulfilled') renderLive(dashboard.value);
  if(replay.status==='fulfilled' && replay.value?.sessions?.length){renderReplayData(replay.value);switchMode('replay');}
  else {switchMode('live');}
}).catch(()=>{document.getElementById('statusPill').textContent='Aún sin datos públicos';});
