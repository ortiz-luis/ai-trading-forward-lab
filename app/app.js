const eur = value => new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(value ?? 0);
const dateFmt = value => value ? new Intl.DateTimeFormat('es-ES',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)) : '—';

function setText(id, value){ const el=document.getElementById(id); if(el) el.textContent=value; }
function pnlClass(value){ return value>0?'positive':value<0?'negative':'neutral'; }

function drawEquity(series){
  const svg=document.getElementById('equityChart');
  if(!series?.length){ svg.innerHTML=''; return; }
  const values=series.map(p=>p.equity_eur);
  const min=Math.min(...values), max=Math.max(...values);
  const span=Math.max(max-min,1);
  const pts=series.map((p,i)=>{
    const x=series.length===1?400:(i/(series.length-1))*780+10;
    const y=240-((p.equity_eur-min)/span)*210;
    return `${x},${y}`;
  }).join(' ');
  svg.innerHTML=`<line x1="10" y1="240" x2="790" y2="240" stroke="currentColor" opacity=".12"/><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="4" vector-effect="non-scaling-stroke"/>`;
}

function render(data){
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
}

fetch('../data/public/dashboard.json',{cache:'no-store'})
  .then(r=>{if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json();})
  .then(render)
  .catch(()=>{
    document.getElementById('statusPill').textContent='Aún sin datos públicos';
  });
