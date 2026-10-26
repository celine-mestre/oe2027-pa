#!/usr/bin/env python3
"""
Gera o painel HTML autónomo (docs/index.html) a partir de:
  data/pa.json                  base de dados das PA (extração automática)
  data/classificacao_manual.csv classificação da DACDP (natureza, área, relevância, impacto, ...)
  data/medidas_anunciadas.csv   levantamento ex ante
  data/historico.csv            eventos (nova, substituída, retirada, estado alterado, votada)
  data/ultima_execucao.json     metadados da última extração

  python scripts/build_painel.py            # docs/index.html
  python scripts/build_painel.py --amostra  # assinala no painel que os dados são uma amostra sintética
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
DOCS = RAIZ / "docs"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
TAX = json.loads((DATA / "taxonomia.json").read_text(encoding="utf-8"))


def ler_csv(nome: str) -> list[dict]:
    f = DATA / nome
    if not f.exists():
        return []
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=";")]


def ler_json(nome: str, default):
    f = DATA / nome
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--amostra", action="store_true")
    ap.add_argument("--saida", default=str(DOCS / "index.html"))
    args = ap.parse_args(argv)

    pa = ler_json("pa.json", [])
    manual = {r["n_pa"].strip(): r for r in ler_csv("classificacao_manual.csv") if r.get("n_pa", "").strip()}
    medidas = ler_csv("medidas_anunciadas.csv")
    historico = ler_csv("historico.csv")
    execucao = ler_json("ultima_execucao.json", {})

    # juntar a classificação manual (prevalece sobre as sugestões automáticas)
    for r in pa:
        m = manual.get(r["n_pa"], {})
        r["natureza"] = m.get("natureza") or ""
        r["area_governativa"] = m.get("area_governativa") or ""
        r["descricao_sumaria"] = m.get("descricao_sumaria") or ""
        r["impacto_orcamental_eur"] = m.get("impacto_orcamental_eur") or ""
        r["fonte_impacto"] = m.get("fonte_impacto") or ""
        r["anunciada_previamente"] = m.get("anunciada_previamente") or ""
        r["id_medida"] = m.get("id_medida") or ""
        r["relevancia"] = m.get("relevancia") or ""
        r["justificacao_relevancia"] = m.get("justificacao_relevancia") or ""
        r["cavaleiro_orcamental"] = m.get("cavaleiro_orcamental") or ""
        r["observacoes"] = m.get("observacoes") or ""
        r["classificada"] = "S" if m else "N"

    logo_b64 = base64.b64encode((RAIZ / "assets" / "logo-sggov.png").read_bytes()).decode()
    payload = {
        "gerado_em": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "amostra": bool(args.amostra),
        "ppl": CONFIG["ppl"],
        "calendario": CONFIG["calendario"],
        "fontes": {k: v for k, v in CONFIG["fontes"].items() if not str(v).startswith("A_PREENCHER")},
        "execucao": execucao,
        "taxonomia": {"partidos": list(TAX["partidos"].keys()), "areas": TAX["areas_governativas"],
                      "natureza": TAX["natureza"]["valores"], "relevancia": TAX["relevancia"]["valores"]},
        "pa": pa,
        "medidas": medidas,
        "historico": historico[-400:][::-1],
    }
    html = TEMPLATE.replace("__LOGO__", logo_b64).replace("__DADOS__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(html, encoding="utf-8")
    print(f"{args.saida}: {len(pa)} PA · {len(medidas)} medidas anunciadas · {len(historico)} eventos")
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PA ao OE 2027 — Levantamento</title>
<meta name="description" content="Levantamento das propostas de alteração à Proposta de Lei n.º 110/XVII/2.ª (Orçamento do Estado para 2027) — DSSD, Secretaria-Geral do Governo">
<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{
  --azul:#275673;--teal:#266B73;--verde:#1F735B;--dourado:#F2B705;--vermelho:#D02117;--verde-logo:#0E7433;
  --bg:#f4f6f8;--card:#ffffff;--ink:#1c2630;--ink2:#4b5a68;--ink3:#7a8794;--linha:#dde3e9;--chip:#eef2f5;
  --ok:#1F735B;--nok:#D02117;--neutro:#7a8794;--aviso:#B07A00;
}
:root:not([data-theme="light"]){@media (prefers-color-scheme: dark){
  --bg:#0f1519;--card:#16202a;--ink:#e8edf2;--ink2:#b5c0cb;--ink3:#86939f;--linha:#2a3744;--chip:#1f2b36;}}
:root[data-theme="dark"]{--bg:#0f1519;--card:#16202a;--ink:#e8edf2;--ink2:#b5c0cb;--ink3:#86939f;--linha:#2a3744;--chip:#1f2b36;}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:Lexend,Arial,sans-serif;font-size:14px;line-height:1.45}
a{color:var(--azul)}
header.topo{background:linear-gradient(90deg,var(--azul) 0%,var(--teal) 55%,var(--verde) 100%);color:#fff;border-bottom:4px solid var(--vermelho)}
.topo .in{max-width:1380px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.pastilha{width:46px;height:46px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.pastilha img{width:38px;height:38px;display:block}
.topo h1{font-size:19px;font-weight:600;margin:0;line-height:1.2}
.topo .sub{font-size:12.5px;opacity:.92;font-weight:300}
.topo .dir{margin-left:auto;text-align:right;font-size:12px;opacity:.95;line-height:1.35}
.faixa-amostra{background:var(--dourado);color:#1c2630;font-weight:600;text-align:center;padding:8px 16px;font-size:13px}
main{max-width:1380px;margin:0 auto;padding:16px}
nav.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 14px}
nav.tabs button{background:var(--card);border:1px solid var(--linha);color:var(--ink2);padding:8px 14px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer}
nav.tabs button.on{background:var(--azul);border-color:var(--azul);color:#fff;font-weight:500}
section.tab{display:none}section.tab.on{display:block}
.grid{display:grid;gap:12px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.card{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:14px 16px}
.card h3{margin:0 0 10px;font-size:13px;font-weight:600;color:var(--ink2);text-transform:uppercase;letter-spacing:.04em}
.kpi .v{font-size:28px;font-weight:600;color:var(--azul);line-height:1.1}
.kpi .l{font-size:12px;color:var(--ink3);margin-top:4px}
.kpi.ok .v{color:var(--ok)}.kpi.nok .v{color:var(--nok)}.kpi.neu .v{color:var(--neutro)}
.duas{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.barras{display:grid;grid-template-columns:max-content 1fr max-content;gap:6px 10px;align-items:center;font-size:13px}
.barras .b{height:12px;background:var(--azul);border-radius:0 4px 4px 0;min-width:2px}
.barras .b.sug{background:var(--teal);opacity:.55}
.barras .n{color:var(--ink2);text-align:right;font-variant-numeric:tabular-nums}
.barras .k{color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px}
.legenda{font-size:11.5px;color:var(--ink3);margin-top:8px}
.filtros{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
.filtros select,.filtros input{font:inherit;font-size:13px;padding:7px 9px;border:1px solid var(--linha);border-radius:8px;background:var(--card);color:var(--ink)}
.filtros input[type=search]{min-width:260px;flex:1}
.filtros .n{color:var(--ink3);font-size:12.5px;margin-left:auto}
.btn{font:inherit;font-size:12.5px;padding:7px 12px;border-radius:8px;border:1px solid var(--azul);background:var(--card);color:var(--azul);cursor:pointer}
.btn:hover{background:var(--azul);color:#fff}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--linha);border-radius:12px;overflow:hidden;font-size:12.5px}
th,td{padding:8px 9px;border-bottom:1px solid var(--linha);vertical-align:top;text-align:left}
th{background:var(--chip);color:var(--ink2);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;white-space:nowrap;position:sticky;top:0}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--chip);color:var(--ink2);font-size:11.5px;white-space:nowrap}
.chip.ok{background:#e3f1ea;color:#145a44}.chip.nok{background:#f9e3e1;color:#8a1711}.chip.pre{background:#eee;color:#555}.chip.ret{background:#fdf1d6;color:#7a5200}
.chip.alta{background:#f9e3e1;color:#8a1711}.chip.media{background:#fdf1d6;color:#7a5200}.chip.baixa{background:#e3f1ea;color:#145a44}
.chip.sug{border:1px dashed var(--ink3);background:transparent;color:var(--ink3)}
:root[data-theme="dark"] .chip.ok,:root[data-theme="dark"] .chip.baixa{background:#1b3a30;color:#9fdcc2}
:root[data-theme="dark"] .chip.nok,:root[data-theme="dark"] .chip.alta{background:#4a1b18;color:#f5b3ad}
:root[data-theme="dark"] .chip.ret,:root[data-theme="dark"] .chip.media{background:#4a3a12;color:#f3d27a}
.tabela-wrap{overflow:auto;max-height:70vh;border-radius:12px}
.cal{display:grid;grid-template-columns:max-content 1fr;gap:4px 12px;font-size:13px}
.cal .d{font-variant-numeric:tabular-nums;color:var(--ink2);white-space:nowrap}
.cal .hoje{color:var(--vermelho);font-weight:600}
.cal .passado{color:var(--ink3)}
.matriz td,.matriz th{text-align:center}
.matriz td.f{background:#e3f1ea}.matriz td.c{background:#f9e3e1}.matriz td.a{background:#fdf1d6}
:root[data-theme="dark"] .matriz td.f{background:#1b3a30}:root[data-theme="dark"] .matriz td.c{background:#4a1b18}:root[data-theme="dark"] .matriz td.a{background:#4a3a12}
.mini{font-size:11.5px;color:var(--ink3)}
#tab-pa{min-width:1640px}.obj{min-width:340px;max-width:460px}#tab-pa td:nth-child(7){max-width:150px}#tab-pa td:nth-child(8){max-width:190px}#tab-pa td:nth-child(8) .chip,#tab-pa td:nth-child(9) .chip{white-space:normal}
details summary{cursor:pointer;color:var(--azul);font-size:12.5px}
footer{max-width:1380px;margin:10px auto 24px;padding:0 16px;font-size:11.5px;color:var(--ink3)}
footer .filete{height:3px;background:linear-gradient(90deg,var(--azul),var(--teal),var(--verde));border-bottom:2px solid var(--vermelho);margin-bottom:10px;border-radius:2px}
.tema-btn{margin-left:8px;background:transparent;border:1px solid rgba(255,255,255,.6);color:#fff;border-radius:999px;padding:4px 10px;font:inherit;font-size:11.5px;cursor:pointer}
@media print{nav.tabs,.filtros,.tema-btn,.btn{display:none}section.tab{display:block!important}.tabela-wrap{max-height:none}}
@media (max-width:640px){.topo .dir{margin-left:0;text-align:left}.barras .k{max-width:150px}}
</style>
</head>
<body>
<header class="topo"><div class="in">
  <div class="pastilha"><img src="data:image/png;base64,__LOGO__" alt="Secretaria-Geral do Governo"></div>
  <div>
    <h1>Propostas de alteração ao Orçamento do Estado para 2027</h1>
    <div class="sub">Proposta de Lei n.º 110/XVII/2.ª · levantamento ex ante e ex post · Direção de Serviços de Suporte à Decisão</div>
  </div>
  <div class="dir" id="meta"></div>
  <button class="tema-btn" onclick="alternarTema()">claro / escuro</button>
</div></header>
<div class="faixa-amostra" id="faixa" hidden>AMOSTRA SINTÉTICA — os registos abaixo são fictícios e servem apenas para testar o painel. Não existem ainda propostas de alteração à PPL 110/XVII/2.ª.</div>
<main>
<nav class="tabs">
  <button data-t="sintese" class="on">Síntese</button>
  <button data-t="pa">Propostas de alteração</button>
  <button data-t="votacoes">Votações</button>
  <button data-t="exante">Medidas anunciadas</button>
  <button data-t="historico">Histórico de capturas</button>
  <button data-t="fontes">Fontes e método</button>
</nav>

<section class="tab on" id="t-sintese">
  <div class="grid kpis" id="kpis"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>PA por proponente</h3><div class="barras" id="g-partido"></div></div>
    <div class="card"><h3>PA por tema (comissão)</h3><div class="barras" id="g-tema"></div></div>
    <div class="card"><h3>PA por área governativa</h3><div class="barras" id="g-area"></div><div class="legenda">Barras claras: sugestão automática a partir do tema da AR, ainda não validada pela DACDP.</div></div>
    <div class="card"><h3>PA por natureza</h3><div class="barras" id="g-natureza"></div><div class="legenda">Barras claras: sugestão automática por palavras-chave, ainda não validada.</div></div>
    <div class="card"><h3>Calendário parlamentar</h3><div class="cal" id="cal"></div></div>
    <div class="card"><h3>Estado da classificação</h3><div class="barras" id="g-classif"></div><div class="legenda">Relevância e natureza são atribuídas manualmente na folha <code>classificacao_manual.csv</code>.</div></div>
  </div>
</section>

<section class="tab" id="t-pa">
  <div class="filtros">
    <input type="search" id="f-q" placeholder="Pesquisar no objeto, artigo, n.º da PA…">
    <select id="f-partido"><option value="">Proponente</option></select>
    <select id="f-tema"><option value="">Tema</option></select>
    <select id="f-area"><option value="">Área governativa</option></select>
    <select id="f-natureza"><option value="">Natureza</option></select>
    <select id="f-estado"><option value="">Estado</option></select>
    <select id="f-relev"><option value="">Relevância</option></select>
    <select id="f-tipo"><option value="">Tipo (AR)</option></select>
    <span class="n" id="f-n"></span>
    <button class="btn" onclick="exportarCSV()">Exportar CSV</button>
  </div>
  <div class="tabela-wrap"><table id="tab-pa"><thead><tr>
    <th data-k="n_pa">N.º</th><th data-k="data_entrada">Entrada</th><th data-k="proponente">Prop.</th><th data-k="artigo">Artigo / mapa</th><th data-k="tipo_ar">Tipo (AR)</th><th>Objeto</th><th data-k="tema_ar">Tema</th><th>Área gov.</th><th>Natureza</th><th>Relev.</th><th data-k="estado">Estado</th><th>Votação</th><th>Ligações</th>
  </tr></thead><tbody></tbody></table></div>
</section>

<section class="tab" id="t-votacoes">
  <div class="grid kpis" id="kpis-vot"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>Resultado por proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-resultado"></table></div></div>
    <div class="card"><h3>Sentido de voto por partido (todas as PA votadas)</h3><div class="tabela-wrap"><table class="matriz" id="m-sentido"></table></div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>PA aprovadas</h3><div class="tabela-wrap"><table id="tab-aprov"><thead><tr><th>N.º</th><th>Prop.</th><th>Artigo</th><th>Objeto</th><th>Área gov.</th><th>Impacto (EUR)</th><th>Data</th><th>Votos</th><th>Avoc.</th></tr></thead><tbody></tbody></table></div></div>
</section>

<section class="tab" id="t-exante">
  <div class="card"><h3>Medidas anunciadas pelos partidos (levantamento ex ante)</h3>
  <div class="tabela-wrap"><table id="tab-ma"><thead><tr><th>ID</th><th>Partido</th><th>Data</th><th>Medida</th><th>Custo anunciado</th><th>Área gov.</th><th>Fonte</th><th>Entregue como PA</th><th>N.º PA</th><th>Obs.</th></tr></thead><tbody></tbody></table></div>
  <div class="legenda">Fonte de cada linha indicada na coluna "Fonte". As linhas provenientes do plano de ação de 23 de outubro de 2026 são um levantamento inicial a confirmar com fonte primária (Fase 1).</div></div>
</section>

<section class="tab" id="t-historico">
  <div class="card"><h3>Eventos registados pelo pipeline (mais recentes primeiro)</h3>
  <div class="tabela-wrap"><table id="tab-hist"><thead><tr><th>Momento</th><th>N.º PA</th><th>Evento</th><th>Detalhe</th><th>Fonte</th></tr></thead><tbody></tbody></table></div></div>
</section>

<section class="tab" id="t-fontes">
  <div class="grid duas">
    <div class="card"><h3>Fontes primárias</h3><ul id="lista-fontes" style="margin:0;padding-left:18px;font-size:13px"></ul></div>
    <div class="card"><h3>Método</h3>
      <ol style="margin:0;padding-left:18px;font-size:13px">
        <li>Extração automática das PA a partir dos dados abertos da Assembleia da República (categoria "Orçamento do Estado", XVII Legislatura), com reserva na página de pesquisa de PA da PPL 110/XVII/2.ª.</li>
        <li>Cada execução guarda um snapshot bruto; a base de dados mantém a última versão de cada PA e um histórico de eventos (entrada, substituição, retirada, alteração de estado, votação).</li>
        <li>Área governativa e natureza são sugeridas automaticamente (tema da AR e palavras-chave) e substituídas pela classificação manual da DACDP quando existe.</li>
        <li>Relevância, impacto orçamental e ligação a medidas anunciadas são registados manualmente, com fonte, na folha de classificação.</li>
        <li>Registo factual e neutro: o painel não contém juízos de mérito político.</li>
      </ol>
    </div>
  </div>
</section>
</main>
<footer><div class="filete"></div><span id="rodape"></span> · Fonte dos dados: Assembleia da República (dados abertos e parlamento.pt). Classificação: Direção de Serviços de Suporte à Decisão, Secretaria-Geral do Governo.</footer>

<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtN = n => Number(n).toLocaleString('pt-PT');
function alternarTema(){const r=document.documentElement;const atual=r.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');const novo=atual==='dark'?'light':'dark';r.setAttribute('data-theme',novo);try{localStorage.setItem('tema',novo)}catch(e){}}
try{const t=localStorage.getItem('tema');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}

if (D.amostra) $('#faixa').hidden = false;
const ex = D.execucao || {};
$('#meta').innerHTML = `Última extração: <b>${esc(ex.momento ? ex.momento.replace('T',' ').slice(0,16) : '—')}</b><br>Fonte: ${esc({opendata:'dados abertos da AR',scrape:'parlamento.pt (pesquisa de PA)',normalize:'ficheiro local'}[ex.comando] || '—')}${D.amostra?' (amostra sintética)':''} · Painel gerado em ${esc(D.gerado_em)}`;
$('#rodape').textContent = `PA ao OE 2027 · ${D.pa.length} registos · painel gerado em ${D.gerado_em}`;

// ----- helpers de agregação
const cont = (arr, f) => { const m = new Map(); for (const r of arr) { for (const k of f(r)) m.set(k, (m.get(k)||0)+1); } return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const split = s => (s||'').split(';').map(x=>x.trim()).filter(Boolean);
const areaDe = r => r.area_governativa ? split(r.area_governativa) : split(r.area_governativa_sug);
const natDe = r => r.natureza || r.natureza_sug || '';
const estadoChip = e => { const c = {aprovada:'ok',rejeitada:'nok',prejudicada:'pre',retirada:'ret','substituída':'ret'}[e]||''; return `<span class="chip ${c}">${esc(e||'—')}</span>`; };
const relevChip = r => r ? `<span class="chip ${esc(r.normalize('NFD').replace(/[̀-ͯ]/g,''))}">${esc(r)}</span>` : '<span class="mini">—</span>';

function barras(el, pares, opts={}) {
  const max = Math.max(1, ...pares.map(p=>p[1]));
  el.innerHTML = pares.map(([k,v,sug]) => `<div class="k" title="${esc(k)}">${esc(k)}</div><div><div class="b ${sug?'sug':''}" style="width:${(v/max*100).toFixed(1)}%"></div></div><div class="n">${fmtN(v)}</div>`).join('') || '<div class="mini">Sem dados.</div>';
}

// ----- síntese
const PA = D.pa;
const porEstado = Object.fromEntries(cont(PA, r=>[r.estado||'—']));
const ult = ex.momento ? ex.momento.slice(0,10) : '—';
$('#kpis').innerHTML = [
  ['PA registadas', PA.length, ''],
  ['Em apreciação', porEstado['em apreciação']||0, 'neu'],
  ['Aprovadas', porEstado['aprovada']||0, 'ok'],
  ['Rejeitadas', porEstado['rejeitada']||0, 'nok'],
  ['Prejudicadas', porEstado['prejudicada']||0, 'neu'],
  ['Retiradas / substituídas', (porEstado['retirada']||0)+(porEstado['substituída']||0), 'neu'],
  ['Classificadas pela DACDP', PA.filter(r=>r.classificada==='S').length, ''],
  ['Relevância alta', PA.filter(r=>r.relevancia==='alta').length, 'nok'],
].map(([l,v,c])=>`<div class="card kpi ${c}"><div class="v">${fmtN(v)}</div><div class="l">${l}</div></div>`).join('');
barras($('#g-partido'), cont(PA, r=>split(r.proponente).length?split(r.proponente):['—']));
barras($('#g-tema'), cont(PA, r=>[ (r.tema_ar||'—').replace(/;$/,'') ]).slice(0,16));
barras($('#g-area'), (()=>{ const m=new Map(); for(const r of PA){ const sug=!r.area_governativa; for(const a of (areaDe(r).length?areaDe(r):['—'])){ const k=a; const e=m.get(k)||[0,0]; e[sug?1:0]++; m.set(k,e);} } return [...m.entries()].sort((a,b)=>(b[1][0]+b[1][1])-(a[1][0]+a[1][1])).flatMap(([k,[v,s]])=>{const out=[]; if(v) out.push([k,v,false]); if(s) out.push([k+' (sugestão)',s,true]); return out;}); })());
barras($('#g-natureza'), (()=>{ const m=new Map(); for(const r of PA){ const sug=!r.natureza; const k=natDe(r)||'—'; const e=m.get(k)||[0,0]; e[sug?1:0]++; m.set(k,e);} return [...m.entries()].sort((a,b)=>(b[1][0]+b[1][1])-(a[1][0]+a[1][1])).flatMap(([k,[v,s]])=>{const out=[]; if(v) out.push([k,v,false]); if(s) out.push([k+' (sugestão)',s,true]); return out;}); })());
barras($('#g-classif'), [['Natureza validada', PA.filter(r=>r.natureza).length], ['Área governativa validada', PA.filter(r=>r.area_governativa).length], ['Relevância atribuída', PA.filter(r=>r.relevancia).length], ['Impacto registado', PA.filter(r=>r.impacto_orcamental_eur).length], ['Ligadas a medida anunciada', PA.filter(r=>r.id_medida).length], ['Por classificar', PA.filter(r=>r.classificada!=='S').length]]);
const hoje = new Date().toISOString().slice(0,10);
$('#cal').innerHTML = D.calendario.map(c => { const cls = c.data===hoje?'hoje':(c.data<hoje?'passado':''); return `<div class="d ${cls}">${c.data.split('-').reverse().join('-')}</div><div class="${cls}">${esc(c.momento)}</div>`; }).join('') + `<div class="d mini">nota</div><div class="mini">Nos dois últimos orçamentos o prazo das PA foi prorrogado para o fim de semana seguinte; prever captura até 8–9 de novembro.</div>`;

// ----- tabela de PA
const opts = (id, vals) => { const s=$(id); for (const v of vals) { const o=document.createElement('option'); o.value=v; o.textContent=v; s.appendChild(o);} };
opts('#f-partido', cont(PA, r=>split(r.proponente)).map(p=>p[0]));
opts('#f-tema', cont(PA, r=>[(r.tema_ar||'').replace(/;$/,'')]).map(p=>p[0]).filter(Boolean));
opts('#f-area', D.taxonomia.areas);
opts('#f-natureza', D.taxonomia.natureza);
opts('#f-estado', ['em apreciação','aprovada','rejeitada','prejudicada','retirada','substituída']);
opts('#f-relev', D.taxonomia.relevancia.concat(['(sem relevância)']));
opts('#f-tipo', cont(PA, r=>[r.tipo_ar||'']).map(p=>p[0]).filter(Boolean));
let ordem = {k:'n_pa', asc:true};
const numPA = s => { const m=/^(\d+)([A-Z]*)(?:-(\d+))?/.exec(s||''); return m ? [+m[1], m[2], +(m[3]||0)] : [1e9,'',0]; };
function filtrar() {
  const q = $('#f-q').value.trim().toLowerCase(), p=$('#f-partido').value, t=$('#f-tema').value, a=$('#f-area').value, n=$('#f-natureza').value, e=$('#f-estado').value, rl=$('#f-relev').value, tp=$('#f-tipo').value;
  return PA.filter(r =>
    (!q || [r.n_pa,r.objeto,r.artigo,r.descricao_sumaria,r.proponente_deputados].join(' ').toLowerCase().includes(q)) &&
    (!p || split(r.proponente).includes(p)) && (!t || (r.tema_ar||'').replace(/;$/,'')===t) && (!a || areaDe(r).includes(a)) &&
    (!n || natDe(r)===n) && (!e || r.estado===e) && (!rl || (rl==='(sem relevância)' ? !r.relevancia : r.relevancia===rl)) && (!tp || r.tipo_ar===tp));
}
function render() {
  const rows = filtrar().sort((x,y)=>{ let a=x[ordem.k], b=y[ordem.k]; if(ordem.k==='n_pa'){a=numPA(a);b=numPA(b); const c=a[0]-b[0]||a[1].localeCompare(b[1])||a[2]-b[2]; return ordem.asc?c:-c;} const c=String(a||'').localeCompare(String(b||''),'pt'); return ordem.asc?c:-c; });
  $('#f-n').textContent = `${fmtN(rows.length)} de ${fmtN(PA.length)} PA`;
  $('#tab-pa tbody').innerHTML = rows.map(r => `<tr>
    <td class="num"><b>${esc(r.n_pa)}</b>${r.versao==='substituição'?`<br><span class="mini">subst. ${esc(r.versao_anterior)}</span>`:''}</td>
    <td class="num">${esc(r.data_entrada)}</td>
    <td>${split(r.proponente).map(p=>`<span class="chip">${esc(p)}</span>`).join(' ')||'—'}</td>
    <td>${esc(r.artigo)||'—'}<br><span class="mini">${esc(r.incide)}</span></td>
    <td class="mini">${esc(r.tipo_ar)}</td>
    <td class="obj">${esc(r.descricao_sumaria||r.objeto)}${r.descricao_sumaria?`<br><span class="mini">${esc(r.objeto)}</span>`:''}${r.anunciada_previamente==='S'?`<br><span class="chip">anunciada previamente${r.id_medida?' · '+esc(r.id_medida):''}</span>`:''}</td>
    <td class="mini">${esc((r.tema_ar||'').replace(/;$/,''))}</td>
    <td>${r.area_governativa?esc(r.area_governativa):(r.area_governativa_sug?`<span class="chip sug" title="sugestão automática">${esc(r.area_governativa_sug)}</span>`:'—')}</td>
    <td>${r.natureza?esc(r.natureza):(r.natureza_sug?`<span class="chip sug" title="sugestão automática">${esc(r.natureza_sug)}</span>`:'—')}${r.cavaleiro_orcamental==='S'?'<br><span class="chip nok">cavaleiro orçamental</span>':''}</td>
    <td>${relevChip(r.relevancia)}${r.impacto_orcamental_eur?`<br><span class="mini">${esc(r.impacto_orcamental_eur)} EUR<br>${esc(r.fonte_impacto)}</span>`:''}</td>
    <td>${estadoChip(r.estado)}<br><span class="mini">${esc(r.estado_ar)}</span></td>
    <td class="mini">${r.resultado_votacao?`${esc(r.resultado_votacao)} · ${esc(r.data_votacao)}<br>${esc(r.votos_por_partido)}${r.avocacao==='S'?'<br><b>avocada a Plenário</b>':''}`:'—'}</td>
    <td class="mini">${r.url_detalhe?`<a href="${esc(r.url_detalhe)}" target="_blank" rel="noopener">AR</a>`:''} ${r.url_pdf?`· <a href="${esc(r.url_pdf)}" target="_blank" rel="noopener">PDF</a>`:''}</td>
  </tr>`).join('') || '<tr><td colspan="13" class="mini">Sem registos para os filtros escolhidos.</td></tr>';
}
document.querySelectorAll('.filtros select, .filtros input').forEach(el => el.addEventListener('input', render));
document.querySelectorAll('#tab-pa th[data-k]').forEach(th => th.addEventListener('click', () => { const k=th.dataset.k; ordem = {k, asc: ordem.k===k ? !ordem.asc : true}; render(); }));
render();
function exportarCSV() {
  const cols = ['n_pa','data_entrada','versao','versao_anterior','proponente','proponente_deputados','apresentada','incide','artigo','tipo_ar','objeto','tema_ar','area_governativa','area_governativa_sug','natureza','natureza_sug','descricao_sumaria','impacto_orcamental_eur','fonte_impacto','anunciada_previamente','id_medida','relevancia','justificacao_relevancia','cavaleiro_orcamental','estado','estado_ar','data_votacao','resultado_votacao','votos_por_partido','avocacao','observacoes','url_detalhe','url_pdf'];
  const linhas = [cols.join(';')].concat(filtrar().map(r => cols.map(c => '"'+String(r[c]??'').replace(/"/g,'""')+'"').join(';')));
  const blob = new Blob(['﻿'+linhas.join('\r\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `PA_OE2027_${D.gerado_em.slice(0,10)}.csv`; a.click();
}

// ----- votações
const votadas = PA.filter(r => r.resultado_votacao || ['aprovada','rejeitada','prejudicada'].includes(r.estado));
$('#kpis-vot').innerHTML = [['PA votadas', votadas.length,''],['Aprovadas', porEstado['aprovada']||0,'ok'],['Rejeitadas', porEstado['rejeitada']||0,'nok'],['Prejudicadas', porEstado['prejudicada']||0,'neu'],['Avocadas a Plenário', PA.filter(r=>r.avocacao==='S').length,'neu'],['Por votar', porEstado['em apreciação']||0,'neu']].map(([l,v,c])=>`<div class="card kpi ${c}"><div class="v">${fmtN(v)}</div><div class="l">${l}</div></div>`).join('');
const partidos = cont(PA, r=>split(r.proponente)).map(p=>p[0]);
const estadosV = ['aprovada','rejeitada','prejudicada','retirada','em apreciação'];
$('#m-resultado').innerHTML = `<tr><th>Proponente</th>${estadosV.map(e=>`<th>${e}</th>`).join('')}<th>total</th></tr>` + partidos.map(p => { const rs = PA.filter(r=>split(r.proponente).includes(p)); return `<tr><td style="text-align:left"><b>${esc(p)}</b></td>${estadosV.map(e=>`<td class="num">${fmtN(rs.filter(r=>r.estado===e).length)}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('');
const gps = D.taxonomia.partidos;
const sent = {}; for (const r of votadas) for (const v of split(r.votos_por_partido)) { const [gp, s] = v.split(':').map(x=>x.trim()); if(!gp||!s) continue; sent[gp] = sent[gp]||{Favor:0,Contra:0,Abstenção:0}; if (sent[gp][s]!==undefined) sent[gp][s]++; }
$('#m-sentido').innerHTML = `<tr><th>Partido</th><th>Favor</th><th>Contra</th><th>Abstenção</th></tr>` + gps.filter(g=>sent[g]).map(g => `<tr><td style="text-align:left"><b>${esc(g)}</b></td><td class="num f">${fmtN(sent[g].Favor)}</td><td class="num c">${fmtN(sent[g].Contra)}</td><td class="num a">${fmtN(sent[g].Abstenção)}</td></tr>`).join('') || '<tr><td class="mini">Ainda sem votações registadas.</td></tr>';
$('#tab-aprov tbody').innerHTML = PA.filter(r=>r.estado==='aprovada').map(r => `<tr><td class="num"><b>${esc(r.n_pa)}</b></td><td>${esc(r.proponente)}</td><td>${esc(r.artigo)}</td><td class="obj">${esc(r.descricao_sumaria||r.objeto)}</td><td>${esc(r.area_governativa||r.area_governativa_sug)}</td><td class="num">${esc(r.impacto_orcamental_eur||'não quantificado')}</td><td class="num">${esc(r.data_votacao)}</td><td class="mini">${esc(r.votos_por_partido)}</td><td>${r.avocacao==='S'?'S':''}</td></tr>`).join('') || '<tr><td colspan="9" class="mini">Ainda sem PA aprovadas.</td></tr>';

// ----- medidas anunciadas
$('#tab-ma tbody').innerHTML = D.medidas.map(m => `<tr><td class="num">${esc(m.id_medida)}</td><td><span class="chip">${esc(m.partido)}</span></td><td class="num">${esc((m.data||'').trim())}</td><td class="obj">${esc(m.descricao)}</td><td class="num">${esc(m.custo_anunciado_eur)||'—'}</td><td>${esc(m.area_governativa)||'—'}</td><td class="mini">${m.url_fonte?`<a href="${esc(m.url_fonte)}" target="_blank" rel="noopener">${esc(m.fonte)}</a>`:esc(m.fonte)}</td><td>${m.entregue_como_pa==='S'?'<span class="chip ok">S</span>':'<span class="chip">N</span>'}</td><td class="num">${esc(m.n_pa)}</td><td class="mini">${esc(m.observacoes)}</td></tr>`).join('') || '<tr><td colspan="10" class="mini">Sem medidas registadas.</td></tr>';

// ----- histórico
$('#tab-hist tbody').innerHTML = D.historico.map(h => `<tr><td class="num">${esc((h.momento||'').replace('T',' ').slice(0,16))}</td><td class="num"><b>${esc(h.n_pa)}</b></td><td><span class="chip ${({nova:'ok','votada':'',retirada:'ret','substituída':'ret','estado alterado':''})[h.evento]||''}">${esc(h.evento)}</span></td><td>${esc(h.detalhe)}</td><td class="mini">${esc(h.fonte)}</td></tr>`).join('') || '<tr><td colspan="5" class="mini">Sem eventos.</td></tr>';

// ----- fontes
const nomes = {url_iniciativa:'Página da PPL 110/XVII/2.ª (detalhe da iniciativa)', url_texto_ppl:'Texto da PPL com legislação citada', url_calendario:'Calendário de apreciação (COFAP)', url_cofap:'Página do OE 2027 na Comissão de Orçamento, Finanças e Administração Pública', dados_abertos_pagina_oe:'Dados abertos da AR — categoria Orçamento do Estado', dados_abertos_pasta_xvii:'Dados abertos — pasta XVII Legislatura', pesquisa_pa_oe2027:'Pesquisa de propostas de alteração ao OE 2027', detalhe_ppl_oe2027:'Detalhes da PPL (artigo a artigo, com PA e votações)', pesquisa_pa_oe2026:'Pesquisa de PA ao OE 2026 (referência para calibração)'};
$('#lista-fontes').innerHTML = Object.entries({...D.ppl, ...D.fontes}).filter(([k,v])=>nomes[k] && String(v).startsWith('http')).map(([k,v])=>`<li><a href="${esc(v)}" target="_blank" rel="noopener">${esc(nomes[k])}</a></li>`).join('') + '<li>UTAO — pareceres e notas sobre a proposta e sobre as PA (ligações a registar na classificação manual)</li>';

// ----- tabs
document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.toggle('on', x===b)); document.querySelectorAll('section.tab').forEach(s=>s.classList.toggle('on', s.id==='t-'+b.dataset.t)); }));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
