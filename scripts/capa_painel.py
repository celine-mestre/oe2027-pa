"""
Capa de abertura do painel (ecrã inteiro, com movimento), na linha da capa do Radar de Notícias.
Mostra só dados da AR da edição ativa: número de PA, estados, proponentes, mosaico por ordem de entrada,
últimas entradas e marcos do calendário. Não aparece quando se chega por uma ligação direta (#oe2027/…).
Importado por build_painel.py: CSS, HTML e JS são inseridos no TEMPLATE.
"""

CSS = r"""
/* ============ CAPA ============ */
body.cp-aberta{overflow:hidden}
.cp{position:fixed;inset:0;z-index:500;color:#fff;overflow-y:auto;overflow-x:hidden;font-family:Lexend,Arial,sans-serif;
  background:linear-gradient(120deg,#275673 0%,#266B73 52%,#1F735B 100%);border-bottom:4px solid #D02117;
  transition:opacity .55s ease,visibility .55s}
.cp.saiu{opacity:0;visibility:hidden}
.cp *{box-sizing:border-box}
.cp-deco{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
.cp-deco .a1{transform-origin:1180px 170px;animation:cp-rodar 90s linear infinite}
.cp-deco .a2{transform-origin:150px 780px;animation:cp-rodar 140s linear infinite reverse}
@keyframes cp-rodar{to{transform:rotate(360deg)}}
.cp-in{position:relative;z-index:2;max-width:1200px;margin:0 auto;min-height:100%;padding:3.2vh clamp(1rem,3vw,2.5rem) 2.4vh;display:flex;flex-direction:column;gap:2.6vh}
.cp-grelha{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);gap:clamp(1.5rem,3vw,3rem);align-items:center;flex:1}
.cp-e{opacity:0;transform:translateY(16px);animation:cp-subir .7s cubic-bezier(.2,.8,.3,1) forwards}
@keyframes cp-subir{to{opacity:1;transform:none}}
.cp-marca{display:flex;align-items:center;gap:.9rem}
.cp-pastilha{width:74px;height:74px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 24px rgba(0,0,0,.28);flex:none}
.cp-pastilha img{width:70px;height:70px;object-fit:contain}
.cp-org{font-size:.74rem;letter-spacing:.18em;text-transform:uppercase;opacity:.88;font-weight:500;line-height:1.6}
.cp-org b{display:block;font-weight:600;letter-spacing:.12em}
.cp h1{font-size:clamp(2rem,3.9vw,3.15rem);font-weight:600;letter-spacing:-.03em;line-height:1.08;margin:1.6rem 0 .9rem;color:#fff}
.cp h1 em{font-style:normal;color:#FFD200}
.cp-sub{font-size:1rem;font-weight:300;opacity:.93;line-height:1.6;max-width:52ch;margin:0}
.cp-vivo{margin-top:1.3rem;display:inline-flex;align-items:center;gap:.6rem;padding:.45rem .95rem .45rem .7rem;border-radius:999px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.28);font-size:.82rem}
.cp-pulso{width:10px;height:10px;border-radius:50%;background:#7CF0A8;position:relative;flex:none}
.cp-pulso::after{content:"";position:absolute;inset:-6px;border-radius:50%;border:2px solid #7CF0A8;animation:cp-pulso 1.8s ease-out infinite}
.cp-pulso.parado{background:#FFD200}.cp-pulso.parado::after{display:none}
@keyframes cp-pulso{from{transform:scale(.4);opacity:1}to{transform:scale(1.5);opacity:0}}
.cp-vivo b{font-weight:600}
.cp-cont{margin-top:1.6rem;display:flex;align-items:flex-end;gap:1rem;flex-wrap:wrap}
.cp-num{font-size:clamp(3.6rem,7.5vw,5.6rem);font-weight:700;line-height:.9;letter-spacing:-.04em;font-variant-numeric:tabular-nums}
.cp-rot{padding-bottom:.45rem;font-size:.95rem;line-height:1.35}
.cp-rot small{display:block;font-size:.76rem;opacity:.78;font-weight:300}
.cp-estados{margin-top:1.1rem;max-width:480px}
.cp-barra{display:flex;height:10px;border-radius:999px;overflow:hidden;background:rgba(255,255,255,.14)}
.cp-barra span{display:block;height:100%;width:0;transition:width 1.4s cubic-bezier(.2,.8,.3,1)}
.cp-leg{display:flex;flex-wrap:wrap;gap:.4rem 1.1rem;margin-top:.55rem;font-size:.76rem;opacity:.92}
.cp-leg i,.cp-leg2 i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:.35rem;vertical-align:-1px}
.cp-botoes{margin-top:1.8rem;display:flex;gap:.7rem;flex-wrap:wrap}
.cp-btn{display:inline-flex;align-items:center;gap:.55rem;padding:.85rem 1.7rem;border-radius:999px;font:600 .95rem Lexend,Arial,sans-serif;cursor:pointer;transition:.2s}
.cp-btn svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.cp-btn.pri{background:#fff;color:#275673;border:1px solid #fff;box-shadow:0 8px 24px rgba(0,0,0,.18)}
.cp-btn.pri:hover{transform:translateY(-2px)}
.cp-btn.sec{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.45)}
.cp-btn.sec:hover{background:rgba(255,255,255,.18)}
.cp-btn:focus-visible{outline:3px solid #FFD200;outline-offset:2px}
.cp-cartao{min-width:0;background:rgba(9,32,44,.28);border:1px solid rgba(255,255,255,.18);border-radius:18px;padding:1.2rem 1.25rem 1.1rem;box-shadow:0 18px 50px rgba(0,0,0,.18)}
.cp-cartao h2{margin:0 0 .2rem;font-size:.72rem;letter-spacing:.16em;text-transform:uppercase;font-weight:600;opacity:.9;color:#fff}
.cp-nota{font-size:.76rem;opacity:.75;margin:0 0 .9rem;font-weight:300}
.cp-mosaico{display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--q,20px),1fr));gap:var(--g,4px)}
.cp-q{aspect-ratio:1;border-radius:4px;box-shadow:inset 0 0 0 1px rgba(255,255,255,.38);opacity:0;transform:scale(.3);transition:opacity .35s,transform .35s cubic-bezier(.3,1.6,.5,1);position:relative}
.cp-q.on{opacity:1;transform:none}
.cp-q.na.on{opacity:.55;background-image:repeating-linear-gradient(135deg,rgba(255,255,255,.75) 0 2px,transparent 2px 5px)!important}
.cp-q.nova::after{content:"";position:absolute;inset:-3px;border-radius:6px;border:2px solid #FFD200;animation:cp-piscar 1.6s ease-in-out infinite}
@keyframes cp-piscar{50%{opacity:.15}}
.cp-vazio{font-size:.85rem;opacity:.8;padding:1rem 0}
.cp-leg2{display:flex;flex-wrap:wrap;gap:.35rem 1rem;margin-top:.85rem;font-size:.76rem}
.cp-ult{margin-top:1rem;border-top:1px solid rgba(255,255,255,.16);padding-top:.8rem}
.cp-ult h3{margin:0 0 .5rem;font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;font-weight:600;opacity:.85;color:#fff}
.cp-fita{height:calc(3 * 2.55rem);overflow:hidden;-webkit-mask-image:linear-gradient(#000 70%,transparent);mask-image:linear-gradient(#000 70%,transparent)}
.cp-fita ul{list-style:none;margin:0;padding:0;transition:transform .8s cubic-bezier(.4,0,.2,1)}
.cp-fita li{height:2.55rem;display:flex;align-items:center;gap:.6rem;font-size:.8rem;white-space:nowrap}
.cp-fita .n{font-weight:600;min-width:2.8rem}
.cp-fita .gp{font-size:.68rem;font-weight:600;padding:.1rem .45rem;border-radius:999px;color:#fff;flex:none;box-shadow:inset 0 0 0 1px rgba(255,255,255,.45)}
.cp-fita .h{opacity:.7;font-size:.72rem;flex:none}
.cp-fita .t{min-width:0;overflow:hidden;text-overflow:ellipsis;font-weight:300}
.cp-linha{position:relative;padding:1.4rem 0 .2rem}
.cp-eixo,.cp-feito{position:absolute;left:0;top:calc(1.4rem + 7px);height:2px;border-radius:2px}
.cp-eixo{right:0;background:rgba(255,255,255,.22)}
.cp-feito{width:0;background:#FFD200;transition:width 1.8s cubic-bezier(.2,.8,.3,1) .6s}
.cp-marcos{position:relative;display:grid;grid-template-columns:repeat(var(--m,5),1fr)}
.cp-marco{font-size:.74rem;line-height:1.35;padding-right:.6rem}
.cp-marco .p{width:16px;height:16px;border-radius:50%;background:#173f54;border:2px solid rgba(255,255,255,.55);margin-bottom:.55rem}
.cp-marco.passou .p{background:#FFD200;border-color:#FFD200}
.cp-marco.agora .p{background:#FFD200;border-color:#fff;animation:cp-anel 2s infinite}
@keyframes cp-anel{0%{box-shadow:0 0 0 0 rgba(255,210,0,.6)}70%,100%{box-shadow:0 0 0 10px rgba(255,210,0,0)}}
.cp-marco b{display:block;font-weight:600;font-size:.8rem}
.cp-marco span{opacity:.78;font-weight:300}
.cp-hoje{position:absolute;top:0;font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;font-weight:600;color:#FFD200;transform:translateX(-50%);white-space:nowrap;opacity:0;transition:opacity .4s 2.2s}
.cp-hoje.on{opacity:1}
.cp-rodape{font-size:.72rem;opacity:.72;line-height:1.7;display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;border-top:1px solid rgba(255,255,255,.14);padding-top:.8rem}
.cp-rodape a{color:#fff}
@media(max-width:900px){
  .cp-grelha{grid-template-columns:minmax(0,1fr)}
  .cp-marcos{grid-template-columns:1fr;gap:.7rem}
  .cp-eixo,.cp-feito,.cp-hoje{display:none}
  .cp-marco{display:grid;grid-template-columns:24px 1fr;align-items:start}
  .cp-marco .p{margin:2px 0 0}
}
@media(max-width:560px){
  .cp-pastilha{width:56px;height:56px}.cp-pastilha img{width:52px;height:52px}
  .cp h1{font-size:1.85rem;margin-top:1.1rem}
  .cp-sub{font-size:.92rem}
  .cp-btn{width:100%;justify-content:center}
  .cp-fita .h{display:none}
}
@media (prefers-reduced-motion:reduce){
  .cp *,.cp *::before,.cp *::after{animation:none!important;transition:none!important}
  .cp-e,.cp-q{opacity:1;transform:none}
}
@media print{.cp{display:none!important}body.cp-aberta{overflow:visible}}
"""

HTML = r"""
<div class="cp" id="capa" role="dialog" aria-modal="true" aria-labelledby="cp-titulo" hidden>
  <svg class="cp-deco" viewBox="0 0 1400 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs><pattern id="cp-pt" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.4" fill="#fff" opacity=".35"/></pattern></defs>
    <rect width="1400" height="900" fill="url(#cp-pt)" opacity=".55"/>
    <g class="a1" fill="none" stroke="#fff" stroke-opacity=".16">
      <circle cx="1180" cy="170" r="270"/><circle cx="1180" cy="170" r="190"/>
      <ellipse cx="1180" cy="170" rx="270" ry="95"/><ellipse cx="1180" cy="170" rx="95" ry="270"/>
      <circle cx="1450" cy="170" r="5" fill="#fff" fill-opacity=".5"/>
    </g>
    <g class="a2" fill="none" stroke="#fff" stroke-opacity=".12">
      <circle cx="150" cy="780" r="320"/><circle cx="150" cy="780" r="220"/>
      <circle cx="370" cy="780" r="4" fill="#fff" fill-opacity=".5"/>
    </g>
  </svg>
  <div class="cp-in">
    <div class="cp-grelha">
      <div>
        <div class="cp-marca cp-e" style="animation-delay:.05s">
          <div class="cp-pastilha"><img src="data:image/png;base64,__LOGO__" alt="Secretaria-Geral do Governo"></div>
          <div class="cp-org"><b>Secretaria-Geral do Governo</b>Suporte à Decisão</div>
        </div>
        <h1 id="cp-titulo" class="cp-e" style="animation-delay:.15s"></h1>
        <p class="cp-sub cp-e" id="cp-sub" style="animation-delay:.25s"></p>
        <div class="cp-vivo cp-e" style="animation-delay:.35s"><span class="cp-pulso" id="cp-pulso"></span><span id="cp-prazo"></span></div>
        <div class="cp-cont cp-e" style="animation-delay:.45s">
          <div class="cp-num" id="cp-num">0</div>
          <div class="cp-rot">propostas de alteração registadas<small id="cp-subnum"></small></div>
        </div>
        <div class="cp-estados cp-e" style="animation-delay:.55s"><div class="cp-barra" id="cp-barra"></div><div class="cp-leg" id="cp-leg"></div></div>
        <div class="cp-botoes cp-e" style="animation-delay:.65s">
          <button class="cp-btn pri" id="cp-entrar">Entrar no painel <svg viewBox="0 0 24 24"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg></button>
          <button class="cp-btn sec" id="cp-outra" hidden></button>
        </div>
      </div>
      <div class="cp-cartao cp-e" style="animation-delay:.4s">
        <h2>Cada quadrado é uma proposta</h2>
        <p class="cp-nota">Por ordem de entrada, com a cor do proponente. As mais recentes piscam.</p>
        <div class="cp-mosaico" id="cp-mosaico"></div>
        <div class="cp-leg2" id="cp-leg2"></div>
        <div class="cp-ult"><h3>Últimas entradas</h3><div class="cp-fita"><ul id="cp-fita"></ul></div></div>
      </div>
    </div>
    <div class="cp-linha cp-e" style="animation-delay:.75s">
      <div class="cp-eixo"></div><div class="cp-feito" id="cp-feito"></div><div class="cp-hoje" id="cp-hoje">hoje</div>
      <div class="cp-marcos" id="cp-marcos"></div>
    </div>
    <div class="cp-rodape cp-e" style="animation-delay:.85s">
      <span>Fonte: <a id="cp-fonte" target="_blank" rel="noopener">dados abertos da Assembleia da República</a> · última captura <span id="cp-captura">—</span></span>
      <span>Direção de Serviços de Suporte à Decisão · Unidade de Pesquisa e Estatísticas</span>
    </div>
  </div>
</div>
"""

JS = r"""
// ----- capa de abertura (só na edição ativa; não aparece em ligações diretas com #)
(function capa(){
  const C = $('#capa'); if (!C) return;
  const ATV = D.edicao_ativa, EA = D.edicoes[ATV];
  if (HASH_INICIAL || !EA || EA.estado === 'concluído') return;
  C.hidden = false; document.body.classList.add('cp-aberta');
  const meses = ['jan.','fev.','mar.','abr.','mai.','jun.','jul.','ago.','set.','out.','nov.','dez.'];
  const dia = s => `${+s.slice(8,10)} ${meses[+s.slice(5,7)-1]}`;
  const hora = s => `${+s.slice(11,13)}h${s.slice(14,16)}`;
  const corP = p => { const g = String(p||'').split(/;\s*/).filter(Boolean); const c = x => (D.cores||{})[x] || '#9aa7b0';
    return g.length > 1 ? `linear-gradient(135deg, ${c(g[0])} 50%, ${c(g[1])} 50%)` : c(g[0]); };
  const nomeP = p => String(p||'—').replace(/;\s*/g,'/');
  const num = s => { const m = String(s||'').match(/^(\d+)/); return m ? +m[1] : 1e9; };
  const PAc = [...(EA.pa||[])].sort((a,b) => (a.data_entrada||'').localeCompare(b.data_entrada||'') || num(a.n_pa) - num(b.n_pa) || String(a.n_pa).localeCompare(String(b.n_pa)));
  const N = PAc.length;

  $('#cp-titulo').innerHTML = `Propostas de alteração<br><em>ao Orçamento do Estado para ${esc(ATV)}</em>`;
  $('#cp-sub').textContent = `${EA.designacao}. Todas as propostas publicadas pela Assembleia da República, acompanhadas desde a entrada até à votação.`;
  $('#cp-fonte').href = (D.fontes||{}).dados_abertos_pagina_oe || '#';

  // prazo de entrega (só a data: o calendário da AR não fixa a hora)
  const hoje = new Date(), hojeD = hoje.toISOString().slice(0,10);
  const fim = EA.fim_prazo || '';
  const dias = fim ? Math.round((Date.parse(fim+'T00:00:00Z') - Date.parse(hojeD+'T00:00:00Z'))/864e5) : null;
  const fimTxt = fim ? `${+fim.slice(8,10)} de ${['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'][+fim.slice(5,7)-1]}` : '';
  if (dias === null) $('#cp-prazo').textContent = 'Em curso';
  else if (dias > 1) $('#cp-prazo').innerHTML = `Prazo de entrega a decorrer · termina a <b>${fimTxt}</b> · faltam <b>${dias} dias</b>`;
  else if (dias === 1) $('#cp-prazo').innerHTML = `Prazo de entrega a decorrer · termina amanhã, <b>${fimTxt}</b>`;
  else if (dias === 0) $('#cp-prazo').innerHTML = `<b>Último dia</b> do prazo de entrega de propostas`;
  else { $('#cp-prazo').innerHTML = `Prazo de entrega terminado a <b>${fimTxt}</b> · apreciação na especialidade`; $('#cp-pulso').classList.add('parado'); }

  // contador
  const gps = new Set(PAc.flatMap(r => String(r.proponente||'').split(/;\s*/).filter(Boolean)));
  const ult = PAc[N-1];
  $('#cp-subnum').textContent = N ? `${gps.size} ${gps.size === 1 ? 'grupo parlamentar proponente' : 'grupos parlamentares proponentes'} · última entrada a ${dia(ult.data_entrada)}, ${hora(ult.data_entrada)}` : 'Ainda sem propostas publicadas pela AR';
  const reduzir = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const elN = $('#cp-num');
  if (reduzir) elN.textContent = fmtN(N);
  else setTimeout(() => { const t0 = performance.now(); (function f(t){ const k = Math.min(1,(t-t0)/1600); elN.textContent = fmtN(Math.round(N*(1-Math.pow(1-k,3)))); if (k<1) requestAnimationFrame(f); })(t0); }, 500);

  // estados publicados pela AR
  const cont = {}; PAc.forEach(r => cont[r.estado_ar||'—'] = (cont[r.estado_ar||'—']||0) + 1);
  const ordemE = [['Admitida','admitidas','#7CF0A8'],['Entrada (via IPA)','em entrada','rgba(255,255,255,.6)'],['Não Admitida','não admitidas','#FFD200'],['Retirado(a)','retiradas','#F5A3A3']];
  const conhecidos = new Set(ordemE.map(x => x[0]));
  const outros = Object.entries(cont).filter(([k]) => !conhecidos.has(k)).reduce((s,[,n]) => s+n, 0);
  const est = ordemE.filter(([k]) => cont[k]).map(([k,l,c]) => [cont[k],l,c]).concat(outros ? [[outros,'outros estados','#9ec5d6']] : []);
  $('#cp-barra').innerHTML = est.map(([n,,c]) => `<span style="background:${c}" data-w="${N ? 100*n/N : 0}"></span>`).join('');
  $('#cp-leg').innerHTML = est.map(([n,l,c]) => `<span><i style="background:${c}"></i><b>${fmtN(n)}</b> ${l}</span>`).join('');
  setTimeout(() => document.querySelectorAll('#cp-barra span').forEach(s => s.style.width = s.dataset.w + '%'), reduzir ? 0 : 900);

  // mosaico: um quadrado por registo, por ordem de entrada
  const M = $('#cp-mosaico');
  M.style.setProperty('--q', N > 1500 ? '7px' : N > 700 ? '9px' : N > 300 ? '13px' : '20px');
  M.style.setProperty('--g', N > 700 ? '2px' : '4px');
  if (!N) M.innerHTML = '<div class="cp-vazio">A capa mostra as propostas à medida que a AR as publica.</div>';
  const recentes = new Set(PAc.slice(-3).map(r => r.n_pa));
  const passo = Math.min(18, 1800 / Math.max(N,1));
  PAc.forEach((r,i) => {
    const q = document.createElement('div');
    q.className = 'cp-q' + (r.estado_ar === 'Não Admitida' ? ' na' : '') + (recentes.has(r.n_pa) ? ' nova' : '');
    q.style.background = corP(r.proponente);
    q.title = `${r.n_pa} · ${nomeP(r.proponente)} · ${dia(r.data_entrada||'')} ${hora(r.data_entrada||'')} · ${r.estado_ar||''}\n${r.objeto||''}`;
    M.appendChild(q);
    if (reduzir) q.classList.add('on'); else setTimeout(() => q.classList.add('on'), 700 + i * passo);
  });
  const porP = {}; PAc.forEach(r => porP[r.proponente||'—'] = (porP[r.proponente||'—']||0) + 1);
  $('#cp-leg2').innerHTML = Object.entries(porP).sort((a,b) => b[1]-a[1]).map(([p,n]) => `<span><i style="background:${corP(p)}"></i>${esc(nomeP(p))} <b>${fmtN(n)}</b></span>`).join('')
    + (cont['Não Admitida'] ? '<span><i style="background:repeating-linear-gradient(135deg,#fff 0 2px,transparent 2px 4px);box-shadow:inset 0 0 0 1px rgba(255,255,255,.6)"></i>não admitida</span>' : '');

  // fita das últimas entradas (títulos tal como a AR os publica)
  const ultimas = PAc.slice(-8).reverse();
  $('#cp-fita').innerHTML = ultimas.map(r => `<li><span class="n">${esc(r.n_pa)}</span><span class="gp" style="background:${corP(r.proponente)}">${esc(nomeP(r.proponente))}</span><span class="h">${esc(dia(r.data_entrada||''))} ${esc(hora(r.data_entrada||''))}</span><span class="t">${esc(r.objeto)}</span></li>`).join('');
  let pos = 0;
  const rodar = !reduzir && ultimas.length > 3 ? setInterval(() => { pos = (pos+1) % (ultimas.length-2); $('#cp-fita').style.transform = `translateY(${-pos*2.55}rem)`; }, 3200) : null;

  // marcos do calendário
  const MC = EA.marcos_capa || [];
  $('#cp-marcos').style.setProperty('--m', Math.max(MC.length,1));
  let idx = -1; MC.forEach((m,i) => { if (m.data <= hojeD) idx = i; });
  $('#cp-marcos').innerHTML = MC.map((m,i) => `<div class="cp-marco ${i<idx?'passou':i===idx?'agora':''}"><div class="p"></div><div><b>${esc(m.rotulo)}</b><span>${esc(m.texto)}</span></div></div>`).join('');
  if (MC.length) {
    let frac = 0;
    if (idx >= 0 && idx < MC.length-1) { const a = Date.parse(MC[idx].data), b = Date.parse(MC[idx+1].data); frac = Math.min(1, Math.max(0, (hoje - a)/(b - a))); }
    const pct = idx < 0 ? 0 : Math.min(100, (idx + frac) * 100 / MC.length + 0.6);
    setTimeout(() => { $('#cp-feito').style.width = pct + '%'; $('#cp-hoje').style.left = pct + '%'; $('#cp-hoje').classList.add('on'); }, 50);
  }
  const m = (EA.estado_fontes||{}).dados_abertos?.momento || (EA.execucao||{}).momento || '';
  if (m) $('#cp-captura').textContent = `${dia(m)} ${m.slice(0,4)}, ${hora(m)}`;

  // outra edição (concluída)
  const outra = Object.keys(D.edicoes).filter(a => a !== ATV).sort().pop();
  if (outra) { const b = $('#cp-outra'); b.hidden = false; b.textContent = `OE ${outra}${D.edicoes[outra].estado === 'concluído' ? ' · processo concluído' : ''}`;
    b.addEventListener('click', () => { const x = document.querySelector(`#edicoes button[data-ano="${outra}"]`); if (x) x.click(); fechar(); }); }

  function fechar(){ C.classList.add('saiu'); document.body.classList.remove('cp-aberta'); if (rodar) clearInterval(rodar); setTimeout(() => { C.hidden = true; }, 600); }
  $('#cp-entrar').addEventListener('click', fechar);
  document.addEventListener('keydown', e => { if (!C.hidden && !C.classList.contains('saiu') && e.key === 'Escape') fechar(); });
})();
"""
