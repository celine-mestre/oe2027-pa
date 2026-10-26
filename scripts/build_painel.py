#!/usr/bin/env python3
"""
Gera o painel HTML autónomo (docs/index.html) exclusivamente a partir de
informação publicada pela Assembleia da República:
  data/pa.json                base de dados das PA (extração automática do parlamento.pt)
  data/historico.csv          eventos detetados entre capturas (nova, substituída, retirada, estado, votação)
  data/ultima_execucao.json   metadados da última extração
  config.json                 ligações à AR e calendário oficial de apreciação (calendário COFAP)

  python scripts/build_painel.py            # docs/index.html
  python scripts/build_painel.py --dados PASTA --rotulo "TEXTO" --saida FICHEIRO   # teste com outros dados
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
    global DATA
    ap = argparse.ArgumentParser()
    ap.add_argument("--dados", default=str(RAIZ / "data"), help="pasta com pa.json, historico.csv e ultima_execucao.json")
    ap.add_argument("--rotulo", default="", help="faixa de aviso no topo")
    ap.add_argument("--saida", default=str(DOCS / "index.html"))
    args = ap.parse_args(argv)
    DATA = Path(args.dados)

    pa = ler_json("pa.json", [])
    historico = ler_csv("historico.csv")
    execucao = ler_json("ultima_execucao.json", {})
    estado_fontes = ler_json("estado_fontes.json", {})
    documentos = ler_json("documentos.json", [])

    logo_b64 = base64.b64encode((RAIZ / "assets" / "logo-sggov.png").read_bytes()).decode()
    payload = {
        "gerado_em": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rotulo": args.rotulo,
        "ppl": CONFIG["ppl"],
        "calendario": CONFIG["calendario"],
        "calendario_nota": CONFIG.get("calendario_nota", ""),
        "fontes": {k: v for k, v in CONFIG["fontes"].items() if str(v).startswith("http")},
        "execucao": execucao,
        "partidos": list(TAX["partidos"].keys()),
        "pa": pa,
        "historico": historico[-400:][::-1],
        "historico_24h": [h for h in historico if h.get("momento", "") >= (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")],
        "estado_fontes": estado_fontes,
        "documentos": documentos,
    }
    html = TEMPLATE.replace("__LOGO__", logo_b64).replace("__DADOS__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(html, encoding="utf-8")
    print(f"{args.saida}: {len(pa)} PA · {len(historico)} eventos")
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PA ao OE 2027 — Levantamento</title>
<meta name="description" content="Propostas de alteração à Proposta de Lei n.º 110/XVII/2.ª (Orçamento do Estado para 2027), a partir da informação publicada pela Assembleia da República">
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
.topo .in{max-width:1380px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:relative}
.pastilha{width:46px;height:46px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.pastilha img{width:38px;height:38px;display:block}
.topo h1{font-size:19px;font-weight:600;margin:0;line-height:1.2}
.topo .sub{font-size:12.5px;opacity:.92;font-weight:300}
.topo .org{font-size:12px;font-weight:500;letter-spacing:.03em;opacity:.95;margin-bottom:2px}
.topo .dir{margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.topo .meta{text-align:right;font-size:11.5px;opacity:.92;line-height:1.35}
.acoes{display:flex;gap:6px}
.ic{width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.08);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
.ic:hover{background:rgba(255,255,255,.22)}
.ic svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ic .i-lua{display:none}
:root[data-theme="dark"] .ic .i-sol{display:none}:root[data-theme="dark"] .ic .i-lua{display:block}
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
.kpi{position:relative}
.kpi .info{position:absolute;top:10px;right:10px;width:20px;height:20px;border-radius:50%;border:1px solid var(--linha);background:var(--card);color:var(--ink3);font:600 11px/18px Lexend,Arial,sans-serif;font-style:italic;cursor:pointer;padding:0;text-align:center}
.kpi .info:hover,.kpi .info[aria-expanded="true"]{border-color:var(--azul);color:var(--azul)}
.kpi .tip{display:none;margin-top:8px;padding-top:8px;border-top:1px solid var(--linha);font-size:11.5px;line-height:1.45;color:var(--ink2)}
.kpi.aberto .tip{display:block}
:root[data-theme="dark"] .kpi .v{color:#8cc0e0}:root[data-theme="dark"] .kpi.ok .v{color:#7fd1ad}:root[data-theme="dark"] .kpi.nok .v{color:#f08a83}:root[data-theme="dark"] .kpi.neu .v{color:#9aa7b3}
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
@media print{nav.tabs,.filtros,.acoes,.btn{display:none}section.tab{display:block!important}.tabela-wrap{max-height:none}}
@media (max-width:640px){.topo .dir{margin-left:0;align-items:flex-start}.topo .meta{text-align:left}.acoes{position:absolute;top:14px;right:16px}.barras .k{max-width:150px}}
</style>
</head>
<body>
<header class="topo"><div class="in">
  <div class="pastilha"><img src="data:image/png;base64,__LOGO__" alt="Secretaria-Geral do Governo"></div>
  <div class="tit">
    <div class="org">Secretaria-Geral do Governo · Suporte à Decisão</div>
    <h1>Propostas de alteração ao Orçamento do Estado para 2027</h1>
    <div class="sub">Proposta de Lei n.º 110/XVII/2.ª · informação publicada pela Assembleia da República</div>
  </div>
  <div class="dir">
    <div class="acoes">
      <button class="ic" id="b-tema" onclick="alternarTema()" title="Modo claro / escuro" aria-label="Modo claro / escuro">
        <svg class="i-sol" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        <svg class="i-lua" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
      </button>
      <button class="ic" onclick="expandir()" title="Ecrã inteiro" aria-label="Ecrã inteiro">
        <svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>
      </button>
      <button class="ic" onclick="window.print()" title="Imprimir" aria-label="Imprimir">
        <svg viewBox="0 0 24 24"><path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/></svg>
      </button>
    </div>
    <div class="meta" id="meta"></div>
  </div>
</div></header>
<div class="faixa-amostra" id="faixa" hidden></div>
<main>
<nav class="tabs">
  <button data-t="sintese" class="on">Síntese</button>
  <button data-t="pa">Propostas de alteração</button>
  <button data-t="votacoes">Votações</button>
  <button data-t="historico">Histórico de capturas</button>
  <button data-t="fontes">Fontes e método</button>
</nav>

<section class="tab on" id="t-sintese">
  <div class="card" id="aviso-vazio" hidden style="margin-bottom:12px"></div>
  <div class="grid kpis" id="kpis"></div>
  <div class="legenda">Estados e votações contam registos publicados pela AR: as partes de uma mesma proposta são votadas separadamente.</div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>Últimas 24 horas</h3><div class="barras" id="g-24h"></div></div>
    <div class="card"><h3>Estado das fontes da AR</h3><div id="fontes-estado" style="font-size:13px"></div></div>
  </div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>PA por proponente</h3><div class="legenda" style="margin:-6px 0 8px">Contagem por proposta (número-base); uma proposta com várias partes conta uma vez.</div><div class="barras" id="g-partido"></div></div>
    <div class="card"><h3>PA por tema (atribuído pela AR)</h3><div class="barras" id="g-tema"></div><div class="legenda">Uma proposta com vários temas conta em cada um deles.</div></div>
    <div class="card"><h3>PA por data de entrada</h3><div class="barras" id="g-data"></div><div class="legenda">Data de entrada registada pela AR, por proposta.</div></div>
    <div class="card"><h3>PA por tipo</h3><div class="barras" id="g-tipo"></div></div>
    <div class="card"><h3>Calendário de apreciação do OE 2027 na AR</h3><div class="cal" id="cal"></div><div class="legenda" id="cal-fonte"></div></div>
    <div class="card"><h3>PA por estado</h3><div class="barras" id="g-estado"></div></div>
  </div>
</section>

<section class="tab" id="t-pa">
  <div class="filtros">
    <input type="search" id="f-q" placeholder="Pesquisar no objeto, artigo, n.º da PA, deputados…">
    <select id="f-partido"><option value="">Proponente</option></select>
    <select id="f-tema"><option value="">Tema</option></select>
    <select id="f-tipo"><option value="">Tipo</option></select>
    <select id="f-incide"><option value="">Incide</option></select>
    <select id="f-estado"><option value="">Estado</option></select>
    <span class="n" id="f-n"></span>
    <button class="btn" onclick="exportarCSV()">Exportar CSV</button>
  </div>
  <div class="tabela-wrap"><table id="tab-pa"><thead><tr>
    <th data-k="n_pa">N.º</th><th data-k="data_entrada">Entrada</th><th data-k="proponente">Proponente</th><th data-k="artigo">Artigo / mapa</th><th data-k="tipo_ar">Tipo</th><th>Objeto</th><th data-k="tema_ar">Tema</th><th data-k="estado">Estado</th><th>Votação</th><th>Ligações</th>
  </tr></thead><tbody></tbody></table></div>
</section>

<section class="tab" id="t-votacoes">
  <div class="grid kpis" id="kpis-vot"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>Resultado por proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-resultado"></table></div></div>
    <div class="card"><h3>Sentido de voto por grupo parlamentar (PA votadas)</h3><div class="tabela-wrap"><table class="matriz" id="m-sentido"></table></div><div class="legenda">Tal como publicado pela AR. Inclui os deputados únicos representantes de partido.</div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Documentos de votação publicados pela COFAP</h3><div class="tabela-wrap"><table id="tab-docs"><thead><tr><th>Documento</th><th>Registado no painel</th></tr></thead><tbody></tbody></table></div><div class="legenda">Guiões, resultados de votações, textos finais e relatórios publicados na página do OE 2027 da Comissão de Orçamento, Finanças e Administração Pública.</div></div>
  <div class="card" style="margin-top:12px"><h3>PA aprovadas</h3><div class="tabela-wrap"><table id="tab-aprov"><thead><tr><th>N.º</th><th>Proponente</th><th>Artigo</th><th>Objeto</th><th>Tema</th><th>Data</th><th>Sentido de voto por grupo parlamentar</th><th>Avocação</th></tr></thead><tbody></tbody></table></div></div>
</section>

<section class="tab" id="t-historico">
  <div class="card"><h3>Eventos detetados entre capturas (mais recentes primeiro)</h3>
  <div class="tabela-wrap"><table id="tab-hist"><thead><tr><th>Momento</th><th>N.º PA</th><th>Evento</th><th>Detalhe</th><th>Fonte</th></tr></thead><tbody></tbody></table></div></div>
</section>

<section class="tab" id="t-fontes">
  <div class="grid duas">
    <div class="card"><h3>Fontes (Assembleia da República)</h3><ul id="lista-fontes" style="margin:0;padding-left:18px;font-size:13px"></ul></div>
    <div class="card"><h3>Método</h3>
      <ol style="margin:0;padding-left:18px;font-size:13px">
        <li>Toda a informação do painel é publicada pela Assembleia da República: dados abertos (categoria «Orçamento do Estado», XVII Legislatura) e, em reserva, a pesquisa de propostas de alteração e a página de detalhe de cada proposta no parlamento.pt.</li>
        <li>O painel não acrescenta classificações próprias. Tema, tipo, estado e sentido de voto são os registados pela AR.</li>
        <li>Cada captura guarda uma cópia dos dados recebidos. A base mantém a última versão de cada proposta e regista, entre capturas, entradas, substituições, retiradas, alterações de estado e votações.</li>
        <li>Uma proposta que deixe de constar da fonte é assinalada como «ausente da fonte» e deve ser confirmada no parlamento.pt.</li>
      </ol>
    </div>
  </div>
</section>
</main>
<footer><div class="filete"></div><span id="rodape"></span> · Fonte: Assembleia da República (parlamento.pt e dados abertos). Tratamento: Área de Suporte à Decisão, Secretaria-Geral do Governo.</footer>

<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtN = n => Number(n).toLocaleString('pt-PT');
const fmtData = d => d ? d.slice(0,10).split('-').reverse().join('-') : '';
const MESES = ['jan.','fev.','mar.','abr.','mai.','jun.','jul.','ago.','set.','out.','nov.','dez.'];
const diaMes = d => { const [a,m,dd] = d.slice(0,10).split('-'); return `${+dd} ${MESES[+m-1]}`; };
function expandir(){const d=document;try{if(!d.fullscreenElement){d.documentElement.requestFullscreen&&d.documentElement.requestFullscreen()}else{d.exitFullscreen&&d.exitFullscreen()}}catch(e){}}
function alternarTema(){const r=document.documentElement;const atual=r.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');const novo=atual==='dark'?'light':'dark';r.setAttribute('data-theme',novo);try{localStorage.setItem('tema',novo)}catch(e){}}
try{const t=localStorage.getItem('tema');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}
if(!document.documentElement.getAttribute('data-theme')&&matchMedia('(prefers-color-scheme: dark)').matches)document.documentElement.setAttribute('data-theme','dark');

if (D.rotulo) { $('#faixa').hidden = false; $('#faixa').textContent = D.rotulo; }
const ex = D.execucao || {};
const fonteNome = {opendata:'dados abertos da AR', scrape:'parlamento.pt (pesquisa de PA)', normalize:'ficheiro local'}[ex.comando] || '—';
$('#meta').innerHTML = `Última captura: <b>${esc(ex.momento ? ex.momento.replace('T',' ').slice(0,16) : '—')}</b><br>Fonte: ${esc(fonteNome)} · painel gerado em ${esc(D.gerado_em)}`;
$('#rodape').textContent = `PA ao OE 2027 · ${D.pa.length} registos · painel gerado em ${D.gerado_em}`;

const cont = (arr, f) => { const m = new Map(); for (const r of arr) for (const k of f(r)) m.set(k, (m.get(k)||0)+1); return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const split = s => (s||'').split(';').map(x=>x.trim()).filter(Boolean);
const temaDe = r => (r.tema_ar||'').replace(/;\s*$/,'').trim();
const estadoChip = e => { const c = {aprovada:'ok','aprovada parcialmente':'ok',rejeitada:'nok',prejudicada:'pre',retirada:'ret','não admitida':'ret'}[e]||''; return `<span class="chip ${c}">${esc(e||'—')}</span>`; };
function barras(el, pares) {
  const max = Math.max(1, ...pares.map(p=>p[1]));
  el.innerHTML = pares.map(([k,v]) => `<div class="k" title="${esc(k)}">${esc(k)}</div><div><div class="b" style="width:${(v/max*100).toFixed(1)}%"></div></div><div class="n">${fmtN(v)}</div>`).join('') || '<div class="mini">Sem dados.</div>';
}

// ----- síntese
const PA = D.pa;
const porEstado = Object.fromEntries(cont(PA, r=>[r.estado||'—']));
const nBase = new Set(PA.map(r=>r.pa_base||r.n_pa)).size;
const INFO = {
  'Propostas de alteração': 'Propostas entregues pelos grupos parlamentares e deputados para alterar a Proposta de Lei do Orçamento. Contam-se pelo número atribuído pela AR (por exemplo, 120C): uma proposta que altera vários artigos conta uma vez.',
  'Registos publicados (inclui partes)': 'Linhas publicadas pela AR. Quando uma proposta altera vários artigos ou alíneas, a AR divide-a em partes (120C-1, 120C-2), cada uma votada separadamente. Por isso há mais registos do que propostas. Os estados e as votações contam-se por registo.',
  'Em apreciação': 'Registos entregues que ainda não têm decisão: aguardam votação.',
  'Aprovadas (total ou parcialmente)': 'Registos aprovados em Comissão ou em Plenário. Inclui as aprovações parciais, em que só parte do texto proposto foi aprovada.',
  'Rejeitadas': 'Registos rejeitados em Comissão ou, depois de avocação, em Plenário.',
  'Retiradas, prejudicadas ou não admitidas': 'Retirada: o proponente desistiu da proposta. Prejudicada: deixou de poder ser votada porque uma votação anterior já decidiu a mesma matéria. Não admitida: não foi aceite para apreciação.',
  'PA votadas': 'Registos com pelo menos uma votação publicada pela AR.',
  'Prejudicadas': 'Registos que deixaram de poder ser votados porque uma votação anterior já decidiu a mesma matéria.',
  'Votadas em Plenário (avocação)': 'Registos votados em Plenário. Acontece quando um grupo parlamentar pede que a votação de uma proposta, normalmente feita na Comissão de Orçamento, Finanças e Administração Pública, seja feita (ou repetida) em Plenário.',
  'Por votar': 'Registos ainda sem votação.'
};
const kpi = ([l,v,c]) => `<div class="card kpi ${c}">${INFO[l]?`<button class="info" aria-expanded="false" aria-label="O que significa «${esc(l)}»" title="O que significa?" onclick="const k=this.parentElement;k.classList.toggle('aberto');this.setAttribute('aria-expanded',k.classList.contains('aberto'))">i</button>`:''}<div class="v">${fmtN(v)}</div><div class="l">${l}</div>${INFO[l]?`<div class="tip">${esc(INFO[l])}</div>`:''}</div>`;
if (!PA.length) {
  const av = $('#aviso-vazio'); av.hidden = false;
  av.innerHTML = `<b>Ainda não há propostas de alteração publicadas pela AR para a PPL 110/XVII/2.ª.</b><br><span class="mini">As propostas de alteração serão registadas a partir de 29 de outubro, às 9h00, data de início do prazo para a sua inserção, segundo o calendário de apreciação da AR. O painel é atualizado automaticamente a partir dessa data.</span>`;
}
$('#kpis').innerHTML = [
  ['Propostas de alteração', nBase, ''],
  ['Registos publicados (inclui partes)', PA.length, 'neu'],
  ['Em apreciação', porEstado['em apreciação']||0, 'neu'],
  ['Aprovadas (total ou parcialmente)', (porEstado['aprovada']||0)+(porEstado['aprovada parcialmente']||0), 'ok'],
  ['Rejeitadas', porEstado['rejeitada']||0, 'nok'],
  ['Retiradas, prejudicadas ou não admitidas', (porEstado['retirada']||0)+(porEstado['prejudicada']||0)+(porEstado['não admitida']||0), 'neu'],
].map(kpi).join('');
const base1 = [...new Map(PA.map(r=>[r.pa_base||r.n_pa, r])).values()];
barras($('#g-partido'), cont(base1, r=>split(r.proponente).length?split(r.proponente):['—']));
barras($('#g-tema'), cont(base1, r=>split(r.tema_ar).length?split(r.tema_ar):['—']).slice(0,16));
barras($('#g-data'), cont(base1, r=>[(r.data_entrada||'').slice(0,10)||'—']).sort((a,b)=>a[0].localeCompare(b[0])).map(([k,v])=>[fmtData(k)||'—',v]));
barras($('#g-tipo'), cont(PA, r=>[r.tipo_ar||'—']));
barras($('#g-estado'), cont(PA, r=>[r.estado||'—']));
const hoje = new Date().toISOString().slice(0,10);
$('#cal').innerHTML = D.calendario.map(c => { const cls = c.data===hoje?'hoje':(c.data<hoje?'passado':''); return `<div class="d ${cls}">${diaMes(c.data)}</div><div class="${cls}">${esc(c.momento)}</div>`; }).join('');
$('#cal-fonte').innerHTML = (D.calendario_nota ? esc(D.calendario_nota)+'<br>' : '') + (D.ppl.url_calendario ? `Fonte: <a href="${esc(D.ppl.url_calendario)}" target="_blank" rel="noopener">calendário de apreciação do OE 2027 (Assembleia da República)</a>` : '');

// ----- últimas 24 h e estado das fontes
const ev24 = cont(D.historico_24h || [], h=>[h.evento]);
barras($('#g-24h'), ev24.length ? ev24.map(([k,v])=>[({nova:'PA novas','estado alterado':'Alterações de estado',votada:'Votações registadas','ausente da fonte':'Ausentes da fonte'})[k]||k, v]) : []);
if (!ev24.length) $('#g-24h').innerHTML = '<div class="mini">Sem alterações nas últimas 24 horas.</div>';
const EF = D.estado_fontes || {};
const hm = m => m ? m.replace('T',' ').slice(0,16) : '—';
const linhaFonte = (nome, f, corpo) => `<div style="margin-bottom:10px"><b>${nome}</b><br><span class="mini">${f ? corpo(f) : 'Ainda não verificada.'}</span></div>`;
$('#fontes-estado').innerHTML =
  linhaFonte('Dados abertos (fonte principal)', EF.dados_abertos, f => f.disponivel
    ? `${fmtN(f.pa||0)} PA (${fmtN(f.registos||0)} registos) · última entrada: ${esc(hm(f.ultima_entrada))} · ficheiro atualizado pela AR: ${esc(f.ultima_modificacao_ar||'—')} · verificado: ${esc(hm(f.momento))}`
    : `Ficheiro do OE 2027 ainda não publicado · verificado: ${esc(hm(f.momento))}`) +
  linhaFonte('Página de pesquisa de PA (verificação cruzada)', EF.pesquisa, f => f.disponivel
    ? `${fmtN(f.registos||0)} registos listados · recuperados nesta verificação: ${fmtN(f.recuperados||0)} · por recuperar: <b>${fmtN(f.por_recuperar||0)}</b> · verificado: ${esc(hm(f.momento))}`
    : `Página ainda não criada pela AR · verificado: ${esc(hm(f.momento))}`);

// ----- tabela de PA
const opts = (id, vals) => { const s=$(id); for (const v of vals) { const o=document.createElement('option'); o.value=v; o.textContent=v; s.appendChild(o);} };
opts('#f-partido', cont(PA, r=>split(r.proponente)).map(p=>p[0]));
opts('#f-tema', cont(PA, r=>[temaDe(r)]).map(p=>p[0]).filter(Boolean));
opts('#f-tipo', cont(PA, r=>[r.tipo_ar||'']).map(p=>p[0]).filter(Boolean));
opts('#f-incide', cont(PA, r=>[r.incide||'']).map(p=>p[0]).filter(Boolean));
opts('#f-estado', cont(PA, r=>[r.estado||'']).map(p=>p[0]).filter(Boolean));
let ordem = {k:'n_pa', asc:true};
const numPA = s => { const m=/^(\d+)([A-Z]*)(?:-(\d+))?/.exec(s||''); return m ? [+m[1], m[2], +(m[3]||0)] : [1e9,'',0]; };
function filtrar() {
  const q=$('#f-q').value.trim().toLowerCase(), p=$('#f-partido').value, t=$('#f-tema').value, tp=$('#f-tipo').value, inc=$('#f-incide').value, e=$('#f-estado').value;
  return PA.filter(r =>
    (!q || [r.n_pa,r.objeto,r.artigo,r.proponente_deputados].join(' ').toLowerCase().includes(q)) &&
    (!p || split(r.proponente).includes(p)) && (!t || temaDe(r)===t) && (!tp || r.tipo_ar===tp) && (!inc || r.incide===inc) && (!e || r.estado===e));
}
function render() {
  const rows = filtrar().sort((x,y)=>{ let a=x[ordem.k], b=y[ordem.k]; if(ordem.k==='n_pa'){a=numPA(a);b=numPA(b); const c=a[0]-b[0]||a[1].localeCompare(b[1])||a[2]-b[2]; return ordem.asc?c:-c;} const c=String(a||'').localeCompare(String(b||''),'pt'); return ordem.asc?c:-c; });
  $('#f-n').textContent = `${fmtN(rows.length)} de ${fmtN(PA.length)} PA`;
  $('#tab-pa tbody').innerHTML = rows.map(r => `<tr>
    <td class="num"><b>${esc(r.n_pa)}</b>${r.versao==='substituição'?`<br><span class="mini">substitui ${esc(r.versao_anterior)}</span>`:''}</td>
    <td class="num">${esc(fmtData(r.data_entrada))}</td>
    <td>${split(r.proponente).map(p=>`<span class="chip">${esc(p)}</span>`).join(' ')||'—'}${r.proponente_deputados?`<br><span class="mini">${esc(r.proponente_deputados)}</span>`:''}</td>
    <td>${esc(r.artigo)||'—'}<br><span class="mini">${esc(r.incide)}${r.apresentada?' · '+esc(r.apresentada):''}</span></td>
    <td class="mini">${esc(r.tipo_ar)}</td>
    <td class="obj">${esc(r.objeto)}</td>
    <td class="mini">${esc(temaDe(r))}</td>
    <td>${estadoChip(r.estado)}<br><span class="mini">${esc(r.estado_ar)}</span></td>
    <td class="mini">${r.resultado_votacao?`${esc(r.resultado_votacao)} · ${esc(fmtData(r.data_votacao))}<br>${esc(r.votos_por_partido)}`:'—'}</td>
    <td class="mini">${r.url_detalhe?`<a href="${esc(r.url_detalhe)}" target="_blank" rel="noopener">AR</a>`:''}${r.url_pdf?` · <a href="${esc(r.url_pdf)}" target="_blank" rel="noopener">PDF</a>`:''}</td>
  </tr>`).join('') || '<tr><td colspan="10" class="mini">Sem registos.</td></tr>';
}
document.querySelectorAll('.filtros select, .filtros input').forEach(el => el.addEventListener('input', render));
document.querySelectorAll('#tab-pa th[data-k]').forEach(th => th.addEventListener('click', () => { const k=th.dataset.k; ordem = {k, asc: ordem.k===k ? !ordem.asc : true}; render(); }));
render();
function exportarCSV() {
  const cols = ['n_pa','data_entrada','versao','versao_anterior','proponente','proponente_deputados','apresentada','incide','artigo','tipo_ar','objeto','tema_ar','estado','estado_ar','data_votacao','resultado_votacao','votos_por_partido','avocacao','url_detalhe','url_pdf','primeira_captura','ultima_captura','fonte'];
  const linhas = [cols.join(';')].concat(filtrar().map(r => cols.map(c => '"'+String(r[c]??'').replace(/"/g,'""')+'"').join(';')));
  const blob = new Blob(['﻿'+linhas.join('\r\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `PA_OE2027_${D.gerado_em.slice(0,10)}.csv`; a.click();
}

// ----- votações
const votadas = PA.filter(r => r.resultado_votacao || ['aprovada','rejeitada','prejudicada'].includes(r.estado));
$('#kpis-vot').innerHTML = [['PA votadas', votadas.length,''],['Aprovadas (total ou parcialmente)', (porEstado['aprovada']||0)+(porEstado['aprovada parcialmente']||0),'ok'],['Rejeitadas', porEstado['rejeitada']||0,'nok'],['Prejudicadas', porEstado['prejudicada']||0,'neu'],['Votadas em Plenário (avocação)', PA.filter(r=>r.avocacao==='S').length,'neu'],['Por votar', porEstado['em apreciação']||0,'neu']].map(kpi).join('');
const proponentes = cont(PA, r=>split(r.proponente)).map(p=>p[0]);
const estadosV = ['aprovada','aprovada parcialmente','rejeitada','prejudicada','retirada','não admitida','em apreciação'];
$('#m-resultado').innerHTML = proponentes.length ? `<tr><th>Proponente</th>${estadosV.map(e=>`<th>${e}</th>`).join('')}<th>total</th></tr>` + proponentes.map(p => { const rs = PA.filter(r=>split(r.proponente).includes(p)); return `<tr><td style="text-align:left"><b>${esc(p)}</b></td>${estadosV.map(e=>`<td class="num">${fmtN(rs.filter(r=>r.estado===e).length)}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
const sent = {}; for (const r of votadas) for (const v of split(r.votos_por_partido)) { const [gp, s] = v.split(':').map(x=>x.trim()); if(!gp||!s) continue; sent[gp] = sent[gp]||{Favor:0,Contra:0,'Abstenção':0}; if (sent[gp][s]!==undefined) sent[gp][s]++; }
$('#m-sentido').innerHTML = Object.keys(sent).length ? `<tr><th>Grupo parlamentar</th><th>Favor</th><th>Contra</th><th>Abstenção</th></tr>` + D.partidos.concat(Object.keys(sent).filter(g=>!D.partidos.includes(g))).filter(g=>sent[g]).map(g => `<tr><td style="text-align:left"><b>${esc(g)}</b></td><td class="num f">${fmtN(sent[g].Favor)}</td><td class="num c">${fmtN(sent[g].Contra)}</td><td class="num a">${fmtN(sent[g]['Abstenção'])}</td></tr>`).join('') : '<tr><td class="mini">Ainda sem votações registadas pela AR.</td></tr>';
$('#tab-aprov tbody').innerHTML = PA.filter(r=>r.estado==='aprovada'||r.estado==='aprovada parcialmente').map(r => `<tr><td class="num"><b>${esc(r.n_pa)}</b></td><td>${esc(r.proponente)}</td><td>${esc(r.artigo)}</td><td class="obj">${esc(r.objeto)}</td><td class="mini">${esc(temaDe(r))}</td><td class="num">${esc(fmtData(r.data_votacao))}</td><td class="mini">${esc(r.votos_por_partido)}</td><td>${r.avocacao==='S'?'S':''}</td></tr>`).join('') || '<tr><td colspan="8" class="mini">Ainda sem PA aprovadas.</td></tr>';

// ----- documentos
$('#tab-docs tbody').innerHTML = (D.documentos||[]).map(d => `<tr><td><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.titulo)}</a></td><td class="num">${esc(hm(d.primeira_captura))}</td></tr>`).join('') || '<tr><td colspan="2" class="mini">Ainda sem documentos de votação publicados.</td></tr>';

// ----- histórico
$('#tab-hist tbody').innerHTML = D.historico.map(h => `<tr><td class="num">${esc((h.momento||'').replace('T',' ').slice(0,16))}</td><td class="num"><b>${esc(h.n_pa)}</b></td><td><span class="chip ${({nova:'ok','ausente da fonte':'ret'})[h.evento]||''}">${esc(h.evento)}</span></td><td>${esc(h.detalhe)}</td><td class="mini">${esc(h.fonte)}</td></tr>`).join('') || '<tr><td colspan="5" class="mini">Sem eventos.</td></tr>';

// ----- fontes
const nomes = {pesquisa_pa:'Pesquisa de propostas de alteração ao OE 2027', url_iniciativa:'Proposta de Lei n.º 110/XVII/2.ª — detalhe da iniciativa', url_texto_ppl:'Texto da proposta de lei com legislação citada', url_calendario:'Calendário de apreciação do OE 2027 (COFAP)', url_cofap:'Página do OE 2027 na Comissão de Orçamento, Finanças e Administração Pública', dados_abertos_pagina_oe:'Dados abertos — categoria Orçamento do Estado', dados_abertos_pasta_xvii:'Dados abertos — pasta XVII Legislatura', dados_abertos_json_oe2027:'Dados abertos — ficheiro do OE 2027', pesquisa_pa_oe2027:'Pesquisa de propostas de alteração ao OE 2027', detalhe_ppl_oe2027:'Detalhes da proposta de lei, artigo a artigo'};
$('#lista-fontes').innerHTML = Object.entries({...D.ppl, ...D.fontes}).filter(([k,v])=>nomes[k] && String(v).startsWith('http')).map(([k,v])=>`<li><a href="${esc(v)}" target="_blank" rel="noopener">${esc(nomes[k])}</a></li>`).join('');

document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.toggle('on', x===b)); document.querySelectorAll('section.tab').forEach(s=>s.classList.toggle('on', s.id==='t-'+b.dataset.t)); }));
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
