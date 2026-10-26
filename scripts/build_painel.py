#!/usr/bin/env python3
"""
Gera o painel HTML autónomo (docs/index.html) com todas as edições configuradas em config.json
(OE 2027 em curso e OE 2026 concluído), a partir de:
  data/oe<ano>/pa.json               base de dados das PA (informação publicada pela AR)
  data/oe<ano>/historico.csv         eventos detetados entre capturas
  data/oe<ano>/ultima_execucao.json  metadados da última extração
  data/oe<ano>/estado_fontes.json    estado das fontes da AR
  data/oe<ano>/documentos.json       documentos publicados pela COFAP
  config.json                        ligações à AR e calendário oficial de apreciação

  python scripts/build_painel.py                       # docs/index.html
  python scripts/build_painel.py --rotulo "TEXTO" --saida FICHEIRO --pasta-2026 PASTA   # testes
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
TAX = json.loads((RAIZ / "data" / "taxonomia.json").read_text(encoding="utf-8"))


def ler_csv(f: Path) -> list[dict]:
    if not f.exists():
        return []
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=";")]


def ler_json(f: Path, default):
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def carregar_edicao(ano: str, ed: dict, pasta: Path) -> dict:
    pa = ler_json(pasta / "pa.json", [])
    historico = ler_csv(pasta / "historico.csv")
    agora = dt.datetime.now(dt.timezone.utc)
    return {
        "ano": ano,
        "designacao": ed["designacao"],
        "estado": ed.get("estado", ""),
        "nota": ed.get("_nota", ""),
        "inicio_registo": ed.get("inicio_registo", ""),
        "urls": {k: v for k, v in ed.items() if k.startswith("url_")},
        "calendario": ed.get("calendario", []),
        "calendario_nota": ed.get("calendario_nota", ""),
        "execucao": ler_json(pasta / "ultima_execucao.json", {}),
        "pa": pa,
        "historico": historico[-400:][::-1],
        "historico_24h": [h for h in historico if h.get("momento", "") >= (agora - dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")],
        "estado_fontes": ler_json(pasta / "estado_fontes.json", {}),
        "documentos": ler_json(pasta / "documentos.json", []),
        "excel": f"Registo_PA_OE{ano}.xlsx" if (DOCS / f"Registo_PA_OE{ano}.xlsx").exists() else "",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rotulo", default="", help="faixa de aviso no topo")
    ap.add_argument("--saida", default=str(DOCS / "index.html"))
    for ano in CONFIG["edicoes"]:
        ap.add_argument(f"--pasta-{ano}", default="", help=f"outra pasta de dados para o OE {ano} (testes)")
    args = ap.parse_args(argv)

    edicoes = {}
    for ano, ed in CONFIG["edicoes"].items():
        pasta = Path(getattr(args, f"pasta_{ano}") or RAIZ / ed["pasta"])
        edicoes[ano] = carregar_edicao(ano, ed, pasta)
    logo_b64 = base64.b64encode((RAIZ / "assets" / "logo-sggov.png").read_bytes()).decode()
    payload = {
        "gerado_em": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rotulo": args.rotulo,
        "edicao_ativa": CONFIG["edicao_ativa"],
        "edicoes": edicoes,
        "fontes": {k: v for k, v in CONFIG["fontes"].items() if str(v).startswith("http")},
        "partidos": list(TAX["partidos"].keys()),
    }
    html = TEMPLATE.replace("__LOGO__", logo_b64).replace("__DADOS__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(html, encoding="utf-8")
    print(f"{args.saida}: " + " · ".join(f"OE {a}: {len(e['pa'])} registos" for a, e in edicoes.items()))
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PA ao Orçamento do Estado — Levantamento</title>
<meta name="description" content="Propostas de alteração às propostas de lei do Orçamento do Estado (OE 2027 em curso e OE 2026 concluído), exclusivamente a partir dos dados abertos da Assembleia da República">
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
.acoes{display:flex;gap:6px;align-items:center}
.edicoes{display:flex;border:1px solid rgba(255,255,255,.55);border-radius:999px;overflow:hidden;margin-right:6px}
.edicoes button{font:inherit;font-size:12.5px;font-weight:500;padding:6px 12px;border:0;background:transparent;color:#fff;cursor:pointer}
.edicoes button.on{background:#fff;color:var(--azul)}
.ic{width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.08);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
.ic:hover{background:rgba(255,255,255,.22)}
.ic svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ic .i-sol{display:none}
:root[data-theme="dark"] .ic .i-lua{display:none}:root[data-theme="dark"] .ic .i-sol{display:block}
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
.seg{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
.seg button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:999px;border:1px solid var(--linha);background:var(--card);color:var(--ink2);cursor:pointer}
.seg button.on{background:var(--azul);border-color:var(--azul);color:#fff}
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
.aviso{background:#fdf1d6;color:#5a3d00;border:1px solid #f2d58a;border-radius:10px;padding:8px 12px;font-size:12.5px;margin:0 0 12px}
:root[data-theme="dark"] .aviso{background:#4a3a12;color:#f3d27a;border-color:#6b5420}
.filtros{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
.filtros select,.filtros input{font:inherit;font-size:13px;padding:7px 9px;border:1px solid var(--linha);border-radius:8px;background:var(--card);color:var(--ink)}
.filtros input[type=search]{min-width:260px;flex:1}
.filtros .n{color:var(--ink3);font-size:12.5px;margin-left:auto}
.btn{font:inherit;font-size:12.5px;padding:7px 12px;border-radius:8px;border:1px solid var(--azul);background:var(--card);color:var(--azul);cursor:pointer;text-decoration:none;display:inline-block}
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
.calor td.q{color:#1c2630;font-variant-numeric:tabular-nums;min-width:62px}
.calor td.q small{display:block;font-size:10px;opacity:.75}
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
    <h1 id="titulo">Propostas de alteração ao Orçamento do Estado</h1>
    <div class="sub" id="subtitulo">informação publicada pela Assembleia da República</div>
  </div>
  <div class="dir">
    <div class="acoes">
      <div class="edicoes" id="edicoes" role="tablist" aria-label="Edição do Orçamento"></div>
      <button class="ic" id="b-tema" onclick="alternarTema()" title="Mudar para modo escuro / claro" aria-label="Mudar para modo escuro / claro">
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
  <button data-t="temas">Por tema</button>
  <button data-t="votacoes">Votações</button>
  <button data-t="historico">Histórico de capturas</button>
  <button data-t="fontes">Fontes e método</button>
</nav>

<section class="tab on" id="t-sintese">
  <div class="card" id="aviso-vazio" hidden style="margin-bottom:12px"></div>
  <div class="grid kpis" id="kpis"></div>
  <div class="legenda">Estados e votações contam registos publicados pela AR: as partes de uma mesma proposta são votadas separadamente.</div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3 id="h-24h">Últimas 24 horas</h3><div class="barras" id="g-24h"></div></div>
    <div class="card"><h3>Estado das fontes da AR</h3><div id="fontes-estado" style="font-size:13px"></div></div>
  </div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>PA por proponente</h3><div class="legenda" style="margin:-6px 0 8px">Contagem por proposta (número-base); uma proposta com várias partes conta uma vez.</div><div class="barras" id="g-partido"></div></div>
    <div class="card"><h3>PA por tema (atribuído pela AR)</h3><div class="barras" id="g-tema"></div><div class="legenda">Uma proposta com vários temas conta em cada um deles.</div></div>
    <div class="card"><h3>PA por data de entrada</h3><div class="barras" id="g-data"></div><div class="legenda">Data de entrada registada pela AR, por proposta.</div></div>
    <div class="card"><h3>PA por tipo</h3><div class="barras" id="g-tipo"></div></div>
    <div class="card"><h3 id="h-cal">Calendário de apreciação na AR</h3><div class="cal" id="cal"></div><div class="legenda" id="cal-fonte"></div></div>
    <div class="card"><h3>PA por estado</h3><div class="barras" id="g-estado"></div></div>
  </div>
</section>

<section class="tab" id="t-pa">
  <div class="filtros">
    <input type="search" id="f-q" placeholder="Pesquisar no objeto, artigo, n.º da PA, deputados…">
    <select id="f-partido"><option value="">Proponente</option></select>
    <select id="f-tema"><option value="">Tema (AR)</option></select>
    <select id="f-tipo"><option value="">Tipo</option></select>
    <select id="f-incide"><option value="">Incide</option></select>
    <select id="f-estado"><option value="">Estado</option></select>
    <span class="n" id="f-n"></span>
    <button class="btn" onclick="exportarCSV()">Exportar CSV</button>
    <a class="btn" id="b-excel" hidden download>Excel (modelo DACDP)</a>
  </div>
  <div class="tabela-wrap"><table id="tab-pa"><thead><tr>
    <th data-k="n_pa">N.º</th><th data-k="data_entrada">Entrada</th><th data-k="proponente">Proponente</th><th data-k="artigo">Artigo / mapa</th><th data-k="tipo_ar">Tipo</th><th>Objeto</th><th data-k="tema_ar">Tema (AR)</th><th data-k="estado">Estado</th><th>Votação</th><th>Ligações</th>
  </tr></thead><tbody></tbody></table></div>
</section>

<section class="tab" id="t-temas">
  <div class="legenda" style="margin:0 0 12px">Tema atribuído pela AR a cada proposta. Uma proposta com vários temas conta em cada um deles. Contagens por proposta (número-base), salvo indicação em contrário.</div>
  <div class="grid kpis" id="kpis-temas"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>PA por tema</h3><div class="barras" id="g-tema-2"></div><div class="legenda">Clique num tema para filtrar a tabela abaixo.</div></div>
    <div class="card"><h3>Resultado por tema</h3><div class="tabela-wrap"><table class="matriz" id="m-tema-res"></table></div><div class="legenda">Por registo publicado pela AR.</div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>PA por tema e proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-tema-prop"></table></div></div>
  <div class="card" style="margin-top:12px"><h3>Posição dos grupos parlamentares por tema</h3>
    <div class="filtros"><label class="mini" for="f-pos-prop">PA apresentadas por</label><select id="f-pos-prop"><option value="">todos os proponentes</option></select><span class="mini">Percentagem de votos a favor de cada grupo parlamentar nas PA votadas de cada tema; por baixo, favor · contra · abstenção.</span></div>
    <div class="tabela-wrap"><table class="matriz calor" id="m-posicao"></table></div>
    <div class="legenda">Indicador histórico calculado a partir dos temas e dos sentidos de voto publicados pela AR. Não é uma previsão. Inclui os deputados únicos representantes de partido.</div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Registos por tema</h3>
    <div class="filtros"><select id="f-t-tema"><option value="">Tema</option></select><select id="f-t-estado"><option value="">Estado</option></select><span class="n" id="f-t-n"></span></div>
    <div class="tabela-wrap"><table id="tab-temas"><thead><tr><th>N.º</th><th>Entrada</th><th>Proponente</th><th>Artigo / mapa</th><th>Objeto</th><th>Tema (AR)</th><th>Estado</th><th>Votação</th></tr></thead><tbody></tbody></table></div>
  </div>
</section>

<section class="tab" id="t-votacoes">
  <div class="grid kpis" id="kpis-vot"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>Resultado por proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-resultado"></table></div></div>
    <div class="card"><h3>Sentido de voto por grupo parlamentar (PA votadas)</h3><div class="tabela-wrap"><table class="matriz" id="m-sentido"></table></div><div class="legenda">Tal como publicado pela AR. Inclui os deputados únicos representantes de partido.</div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Como vota cada grupo parlamentar nas PA de cada proponente</h3><div class="tabela-wrap"><table class="matriz calor" id="m-cruzado"></table></div><div class="legenda">Linhas: proponente da PA. Colunas: grupo parlamentar que vota. Percentagem de votos a favor nas PA votadas; por baixo, favor · contra · abstenção.</div></div>
  <div class="card" style="margin-top:12px"><h3 id="h-docs">Documentos publicados pela COFAP</h3><div class="tabela-wrap"><table id="tab-docs"><thead><tr><th>Documento</th><th>Registado no painel</th></tr></thead><tbody></tbody></table></div><div class="legenda">Guiões e resultados de votações, textos finais, relatórios e pareceres (por exemplo, da UTAO e do Conselho das Finanças Públicas) publicados na página do OE da Comissão de Orçamento, Finanças e Administração Pública. Não inclui os contributos de entidades e cidadãos.</div></div>
  <div class="card" style="margin-top:12px"><h3>Detalhe das votações</h3>
    <div class="seg" id="seg-res"></div>
    <div class="tabela-wrap"><table id="tab-res"><thead><tr><th>N.º</th><th>Proponente</th><th>Artigo</th><th>Objeto</th><th>Tema</th><th>Resultado</th><th>Data</th><th>Sentido de voto por grupo parlamentar</th></tr></thead><tbody></tbody></table></div>
    <div class="legenda">Por registo publicado pela AR. «Em Plenário» assinala as votações feitas em Plenário por avocação.</div>
  </div>
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
        <li>Toda a informação do painel é publicada pela Assembleia da República: dados abertos (categoria «Orçamento do Estado», XVII Legislatura) e, em reserva, a página de detalhe de cada proposta no parlamento.pt.</li>
        <li>O painel não acrescenta classificações próprias. Tema, tipo, estado e sentido de voto são os registados pela AR. O tema é o atribuído pelos serviços da AR a cada proposta (em 2026, corresponde à comissão parlamentar competente).</li>
        <li>Cada captura guarda uma cópia dos dados recebidos. A base mantém a última versão de cada proposta e regista, entre capturas, entradas, alterações de estado e votações.</li>
        <li>Uma proposta que deixe de constar da fonte é assinalada como «ausente da fonte» e deve ser confirmada no parlamento.pt.</li>
        <li>O OE 2026 (processo concluído) serve de base de comparação e de calibração: é a única edição completa da XVII Legislatura, com a mesma composição parlamentar.</li>
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

const cont = (arr, f) => { const m = new Map(); for (const r of arr) for (const k of f(r)) m.set(k, (m.get(k)||0)+1); return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const split = s => (s||'').split(';').map(x=>x.trim()).filter(Boolean);
const temaDe = r => (r.tema_ar||'').replace(/;\s*$/,'').trim();
const estadoChip = e => { const c = {aprovada:'ok','aprovada parcialmente':'ok',rejeitada:'nok',prejudicada:'pre',retirada:'ret','não admitida':'ret'}[e]||''; return `<span class="chip ${c}">${esc(e||'—')}</span>`; };
const numPA = s => { const m=/^(\d+)([A-Z]*)(?:-(\d+))?/.exec(s||''); return m ? [+m[1], m[2], +(m[3]||0)] : [1e9,'',0]; };
const ordemPA = (x,y) => { const a=numPA(x.n_pa),b=numPA(y.n_pa); return a[0]-b[0]||a[1].localeCompare(b[1])||a[2]-b[2]; };
const hm = m => m ? m.replace('T',' ').slice(0,16) : '—';
function barras(el, pares, onclick) {
  const max = Math.max(1, ...pares.map(p=>p[1]));
  el.innerHTML = pares.map(([k,v]) => `<div class="k" title="${esc(k)}" ${onclick?`style="cursor:pointer" data-k="${esc(k)}"`:''}>${esc(k)}</div><div><div class="b" style="width:${(v/max*100).toFixed(1)}%"></div></div><div class="n">${fmtN(v)}</div>`).join('') || '<div class="mini">Sem dados.</div>';
  if (onclick) el.querySelectorAll('.k').forEach(k => k.addEventListener('click', () => onclick(k.dataset.k)));
}
const opts = (id, vals, manter=1) => { const s=$(id); while (s.options.length>manter) s.remove(manter); for (const v of vals) { const o=document.createElement('option'); o.value=v; o.textContent=v; s.appendChild(o);} };
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
  'Por votar': 'Registos ainda sem votação.',
  'Temas atribuídos pela AR': 'Temas distintos que os serviços da AR atribuíram às propostas desta edição. Em 2026 correspondem às comissões parlamentares competentes.',
  'PA com tema': 'Propostas (número-base) com pelo menos um tema atribuído pela AR.',
  'PA com mais de um tema': 'Propostas a que a AR atribuiu vários temas. Contam em cada um deles.',
  'PA sem tema': 'Propostas publicadas sem tema. Aparecem como «—».',
  'Registos votados': 'Registos com sentido de voto publicado, base da matriz de posições por tema.'
};
const kpi = ([l,v,c]) => `<div class="card kpi ${c}">${INFO[l]?`<button class="info" aria-expanded="false" aria-label="O que significa «${esc(l)}»" title="O que significa?" onclick="const k=this.parentElement;k.classList.toggle('aberto');this.setAttribute('aria-expanded',k.classList.contains('aberto'))">i</button>`:''}<div class="v">${fmtN(v)}</div><div class="l">${l}</div>${INFO[l]?`<div class="tip">${esc(INFO[l])}</div>`:''}</div>`;
const matrizCalor = (el, linhas, colunas, celula, vazio) => {
  if (!linhas.length) { el.innerHTML = `<tr><td class="mini">${vazio}</td></tr>`; return; }
  el.innerHTML = `<tr><th></th>${colunas.map(c=>`<th>${esc(c)}</th>`).join('')}</tr>` + linhas.map(l => `<tr><td style="text-align:left"><b>${esc(l)}</b></td>${colunas.map(c => { const s = celula(l,c); if (!s || !(s.F+s.C+s.A)) return '<td class="q mini">—</td>'; const n=s.F+s.C+s.A, p=s.F/n; const cor = `hsl(${Math.round(p*120)},55%,${82-Math.round(p*10)}%)`; return `<td class="q" style="background:${cor}" title="${esc(c)} nas PA de ${esc(l)}: ${s.F} a favor, ${s.C} contra, ${s.A} abstenções">${Math.round(p*100)}%<small>${s.F} · ${s.C} · ${s.A}</small></td>`; }).join('')}</tr>`).join('');
};
const sentidos = (regs, chaveLinha) => { const m = {}; for (const r of regs) { if (!r.votos_por_partido) continue; for (const l of chaveLinha(r)) { m[l] = m[l]||{}; for (const v of split(r.votos_por_partido)) { const [gp,s]=v.split(':').map(x=>x.trim()); const k={Favor:'F',Contra:'C','Abstenção':'A'}[s]; if(!gp||!k) continue; m[l][gp]=m[l][gp]||{F:0,C:0,A:0}; m[l][gp][k]++; } } } return m; };

let ANO = D.edicao_ativa, E = D.edicoes[ANO], PA = [], ordem = {k:'n_pa', asc:true}, segAtivo = 0;
$('#edicoes').innerHTML = Object.keys(D.edicoes).sort((a,b)=>b.localeCompare(a)).map(a => `<button role="tab" data-ano="${a}" class="${a===ANO?'on':''}">OE ${a}</button>`).join('');
$('#edicoes').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { ANO = b.dataset.ano; E = D.edicoes[ANO]; $('#edicoes').querySelectorAll('button').forEach(x=>x.classList.toggle('on', x===b)); montar(); }));

function montar() {
  PA = E.pa;
  const concluido = E.estado === 'concluído';
  const ex = E.execucao || {};
  const fonteNome = {opendata:'dados abertos da AR', scrape:'parlamento.pt (página de cada PA)', normalize:'ficheiro local'}[ex.comando] || '—';
  $('#titulo').textContent = `Propostas de alteração ao Orçamento do Estado para ${ANO}`;
  $('#subtitulo').textContent = `${E.designacao} · informação publicada pela Assembleia da República` + (concluido ? ' · processo concluído' : '');
  $('#meta').innerHTML = `Última captura: <b>${esc(ex.momento ? ex.momento.replace('T',' ').slice(0,16) : '—')}</b><br>Fonte: <a href="${esc(D.fontes.dados_abertos_pagina_oe)}" target="_blank" rel="noopener" style="color:#fff">${esc(fonteNome)}</a> · painel gerado em ${esc(D.gerado_em)}`;
  $('#rodape').textContent = `PA ao OE ${ANO} · ${fmtN(PA.length)} registos · painel gerado em ${D.gerado_em}`;
  $('#h-cal').textContent = `Calendário de apreciação do OE ${ANO} na AR`;
  $('#h-docs').textContent = `Documentos publicados pela COFAP sobre o OE ${ANO}`;

  // ----- síntese
  const porEstado = Object.fromEntries(cont(PA, r=>[r.estado||'—']));
  const nBase = new Set(PA.map(r=>r.pa_base||r.n_pa)).size;
  const av = $('#aviso-vazio'); av.hidden = true;
  if (!PA.length) {
    av.hidden = false;
    av.innerHTML = concluido ? `<b>Sem dados carregados para o OE ${ANO}.</b>` : `<b>Ainda não há propostas de alteração publicadas pela AR para a ${esc(E.designacao)}.</b><br><span class="mini">As propostas de alteração serão registadas a partir de ${E.inicio_registo ? fmtData(E.inicio_registo)+', às '+E.inicio_registo.slice(11,16).replace(':','h') : '29 de outubro, às 9h00'}, data de início do prazo para a sua inserção, segundo o calendário de apreciação da AR. O painel é atualizado automaticamente a partir dessa data. Use o seletor «OE 2026» no canto superior direito para ver o processo anterior, concluído.</span>`;
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
  let cal = E.calendario || [];
  if (!cal.length && PA.length) {  // edição concluída sem calendário transcrito: marcos derivados dos próprios dados da AR
    const entradas = PA.map(r=>r.data_entrada).filter(Boolean).sort(), vot = PA.map(r=>r.data_votacao).filter(Boolean).sort(), plen = PA.filter(r=>r.sede_votacao==='Plenário').map(r=>r.data_votacao).filter(Boolean).sort();
    cal = [{data:entradas[0], momento:'primeira PA registada pela AR'}, {data:entradas[entradas.length-1], momento:`última PA registada pela AR (${entradas[entradas.length-1].slice(11,16).replace(':','h')})`}];
    if (vot.length) cal.push({data:vot[0], momento:'primeira votação publicada'}, {data:vot[vot.length-1], momento:'última votação publicada'});
    if (plen.length) cal.push({data:plen[plen.length-1], momento:'última votação em Plenário (avocações)'});
    cal.sort((a,b)=>a.data.localeCompare(b.data));
  }
  $('#cal').innerHTML = cal.map(c => { const cls = c.data.slice(0,10)===hoje?'hoje':(c.data.slice(0,10)<hoje?'passado':''); return `<div class="d ${cls}">${diaMes(c.data)}${concluido?' '+c.data.slice(0,4):''}</div><div class="${cls}">${esc(c.momento)}</div>`; }).join('') || '<div class="mini">Sem calendário.</div>';
  $('#cal-fonte').innerHTML = (E.calendario_nota ? esc(E.calendario_nota)+'<br>' : '') + (E.urls.url_calendario ? `Fonte: <a href="${esc(E.urls.url_calendario)}" target="_blank" rel="noopener">calendário de apreciação do OE ${ANO} (Assembleia da República)</a>` : (concluido ? 'Marcos derivados das datas de entrada e de votação publicadas pela AR.' : ''));

  // ----- últimas 24 h e estado das fontes
  if (concluido) {
    $('#h-24h').textContent = 'Processo concluído';
    $('#g-24h').innerHTML = `<div class="mini" style="grid-column:1/-1">${esc(E.nota || 'Processo concluído.')}</div>`;
  } else {
    $('#h-24h').textContent = 'Últimas 24 horas';
    const ev24 = cont(E.historico_24h || [], h=>[h.evento]);
    barras($('#g-24h'), ev24.length ? ev24.map(([k,v])=>[({nova:'PA novas','estado alterado':'Alterações de estado',votada:'Votações registadas','ausente da fonte':'Ausentes da fonte'})[k]||k, v]) : []);
    if (!ev24.length) $('#g-24h').innerHTML = '<div class="mini">Sem alterações nas últimas 24 horas.</div>';
  }
  const EF = E.estado_fontes || {};
  const linhaFonte = (nome, f, corpo) => `<div style="margin-bottom:10px"><b>${nome}</b><br><span class="mini">${f ? corpo(f) : 'Ainda não verificada.'}</span></div>`;
  const ligDA = `<a href="${esc(D.fontes.dados_abertos_pagina_oe)}" target="_blank" rel="noopener">dados abertos da AR, categoria «Orçamento do Estado»</a> · <a href="${esc(D.fontes.dados_abertos_pasta_xvii)}" target="_blank" rel="noopener">pasta «XVII Legislatura»</a> · ficheiro <code>OEPropostasAlteracao${ANO}Or_json.txt</code> (também em XML)`;
  $('#fontes-estado').innerHTML =
    `<div style="margin-bottom:10px"><b>De onde vêm os dados</b><br><span class="mini">${ligDA}. Um registo por PA (ou parte de PA): número, data e hora de entrada, título, artigo, tema, tipo, incidência, estado, proponentes e todas as votações com o sentido de voto de cada grupo parlamentar.</span></div>` +
    linhaFonte('Estado dos dados abertos (fonte principal)', EF.dados_abertos, f => f.disponivel
      ? `${fmtN(f.pa||0)} PA (${fmtN(f.registos||0)} registos) · última entrada: ${esc(hm(f.ultima_entrada))} · ficheiro atualizado pela AR: ${esc(f.ultima_modificacao_ar||'—')} · verificado: ${esc(hm(f.momento))}`
      : `Ficheiro do OE ${ANO} ainda não publicado · verificado: ${esc(hm(f.momento))}`) +
    (concluido ? '' : linhaFonte('Portal da AR, página de cada proposta (reserva)', EF.portal, f =>
      `PA novas nesta verificação: ${fmtN(f.novos||0)} · atualizadas: ${fmtN(f.relidos||0)} · identificadores verificados: ${esc(f.primeiro_id_testado)}–${esc(f.ultimo_id_testado)}${f.erro?` · <b>erro: ${esc(f.erro)}</b>`:''} · verificado: ${esc(hm(f.momento))}`));

  // ----- tabela de PA
  opts('#f-partido', cont(PA, r=>split(r.proponente)).map(p=>p[0]));
  opts('#f-tema', cont(PA, r=>[temaDe(r)]).map(p=>p[0]).filter(Boolean));
  opts('#f-tipo', cont(PA, r=>[r.tipo_ar||'']).map(p=>p[0]).filter(Boolean));
  opts('#f-incide', cont(PA, r=>[r.incide||'']).map(p=>p[0]).filter(Boolean));
  opts('#f-estado', cont(PA, r=>[r.estado||'']).map(p=>p[0]).filter(Boolean));
  $('#f-q').value = ''; ['#f-partido','#f-tema','#f-tipo','#f-incide','#f-estado'].forEach(s=>$(s).value='');
  const bx = $('#b-excel'); bx.hidden = !E.excel; if (E.excel) bx.href = E.excel;
  render();

  const estadosV = ['aprovada','aprovada parcialmente','rejeitada','prejudicada','retirada','não admitida','em apreciação'];
  const proponentes = cont(PA, r=>split(r.proponente)).map(p=>p[0]);
  opts('#f-pos-prop', proponentes); $('#f-pos-prop').value = '';
  renderPosicao();

  // ----- por tema (atribuído pela AR)
  const temasPA = r => split(r.tema_ar).length ? split(r.tema_ar) : ['—'];
  const temasLista = cont(base1, temasPA).map(p=>p[0]);
  const votadasT = PA.filter(r => r.votos_por_partido);
  $('#kpis-temas').innerHTML = [
    ['Temas atribuídos pela AR', temasLista.filter(x=>x!=='—').length, ''],
    ['PA com tema', base1.filter(r=>split(r.tema_ar).length).length, 'neu'],
    ['PA com mais de um tema', base1.filter(r=>split(r.tema_ar).length>1).length, 'neu'],
    ['PA sem tema', base1.filter(r=>!split(r.tema_ar).length).length, 'neu'],
    ['Registos votados', votadasT.length, 'ok'],
  ].map(kpi).join('');
  barras($('#g-tema-2'), cont(base1, temasPA), tm => { $('#f-t-tema').value = tm; renderTemas(); document.getElementById('tab-temas').scrollIntoView({behavior:'smooth', block:'start'}); });
  $('#m-tema-res').innerHTML = temasLista.length ? `<tr><th>Tema</th>${estadosV.map(e=>`<th>${e}</th>`).join('')}<th>total</th></tr>` + temasLista.map(tm => { const rs = PA.filter(r=>temasPA(r).includes(tm)); return `<tr><td style="text-align:left"><b>${esc(tm)}</b></td>${estadosV.map(e=>`<td class="num">${fmtN(rs.filter(r=>r.estado===e).length)}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  $('#m-tema-prop').innerHTML = temasLista.length ? `<tr><th>Tema</th>${proponentes.map(p=>`<th>${esc(p)}</th>`).join('')}<th>total</th></tr>` + temasLista.map(tm => { const rs = base1.filter(r=>temasPA(r).includes(tm)); return `<tr><td style="text-align:left"><b>${esc(tm)}</b></td>${proponentes.map(p=>`<td class="num">${fmtN(rs.filter(r=>split(r.proponente).includes(p)).length)||'<span class="mini">·</span>'}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  opts('#f-t-tema', temasLista); opts('#f-t-estado', cont(PA, r=>[r.estado||'']).map(p=>p[0]).filter(Boolean)); $('#f-t-tema').value = ''; $('#f-t-estado').value = '';
  renderTemas();

  // ----- votações
  const votadas = PA.filter(r => r.resultado_votacao || ['aprovada','rejeitada','prejudicada'].includes(r.estado));
  $('#kpis-vot').innerHTML = [['PA votadas', votadas.length,''],['Aprovadas (total ou parcialmente)', (porEstado['aprovada']||0)+(porEstado['aprovada parcialmente']||0),'ok'],['Rejeitadas', porEstado['rejeitada']||0,'nok'],['Prejudicadas', porEstado['prejudicada']||0,'neu'],['Votadas em Plenário (avocação)', PA.filter(r=>r.avocacao==='S').length,'neu'],['Por votar', porEstado['em apreciação']||0,'neu']].map(kpi).join('');
  $('#m-resultado').innerHTML = proponentes.length ? `<tr><th>Proponente</th>${estadosV.map(e=>`<th>${e}</th>`).join('')}<th>total</th></tr>` + proponentes.map(p => { const rs = PA.filter(r=>split(r.proponente).includes(p)); return `<tr><td style="text-align:left"><b>${esc(p)}</b></td>${estadosV.map(e=>`<td class="num">${fmtN(rs.filter(r=>r.estado===e).length)}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  const sent = {}; for (const r of votadas) for (const v of split(r.votos_por_partido)) { const [gp, s] = v.split(':').map(x=>x.trim()); if(!gp||!s) continue; sent[gp] = sent[gp]||{Favor:0,Contra:0,'Abstenção':0}; if (sent[gp][s]!==undefined) sent[gp][s]++; }
  const gpsVot = D.partidos.concat(Object.keys(sent).filter(g=>!D.partidos.includes(g))).filter(g=>sent[g]);
  $('#m-sentido').innerHTML = gpsVot.length ? `<tr><th>Grupo parlamentar</th><th>Favor</th><th>Contra</th><th>Abstenção</th></tr>` + gpsVot.map(g => `<tr><td style="text-align:left"><b>${esc(g)}</b></td><td class="num f">${fmtN(sent[g].Favor)}</td><td class="num c">${fmtN(sent[g].Contra)}</td><td class="num a">${fmtN(sent[g]['Abstenção'])}</td></tr>`).join('') : '<tr><td class="mini">Ainda sem votações registadas pela AR.</td></tr>';
  const cruz = sentidos(votadas, r=>split(r.proponente));
  matrizCalor($('#m-cruzado'), proponentes.filter(p=>cruz[p]), gpsVot, (l,c)=>cruz[l]&&cruz[l][c], 'Ainda sem votações registadas pela AR.');
  segAtivo = 0; renderRes();

  // ----- documentos, histórico, fontes
  $('#tab-docs tbody').innerHTML = (E.documentos||[]).map(d => `<tr><td><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.titulo)}</a></td><td class="num">${esc(hm(d.primeira_captura))}</td></tr>`).join('') || '<tr><td colspan="2" class="mini">Ainda sem documentos publicados.</td></tr>';
  $('#tab-hist tbody').innerHTML = E.historico.map(h => `<tr><td class="num">${esc((h.momento||'').replace('T',' ').slice(0,16))}</td><td class="num"><b>${esc(h.n_pa)}</b></td><td><span class="chip ${({nova:'ok','ausente da fonte':'ret'})[h.evento]||''}">${esc(h.evento)}</span></td><td>${esc(h.detalhe)}</td><td class="mini">${esc(h.fonte)}</td></tr>`).join('') || '<tr><td colspan="5" class="mini">Sem eventos.</td></tr>';
  const nomes = {pesquisa_pa:'Pesquisa de propostas de alteração', url_iniciativa:`${E.designacao} — detalhe da iniciativa`, url_texto_ppl:'Texto da proposta de lei com legislação citada', url_calendario:`Calendário de apreciação do OE ${ANO} (COFAP)`, url_cofap:`Página do OE ${ANO} na Comissão de Orçamento, Finanças e Administração Pública`, dados_abertos_pagina_oe:'Dados abertos — categoria Orçamento do Estado', dados_abertos_pasta_xvii:'Dados abertos — pasta XVII Legislatura'};
  $('#lista-fontes').innerHTML = `<li><b>Fonte principal:</b> ${ligDA}.</li>` + Object.entries({...D.fontes, ...E.urls}).filter(([k,v])=>nomes[k] && String(v).startsWith('http')).map(([k,v])=>`<li><a href="${esc(v)}" target="_blank" rel="noopener">${esc(nomes[k])}</a></li>`).join('') + (E.excel ? `<li><a href="${esc(E.excel)}" download>Registo das PA no modelo da DACDP (Excel), gerado em cada captura</a></li>` : '');
}

function filtrar() {
  const q=$('#f-q').value.trim().toLowerCase(), p=$('#f-partido').value, t=$('#f-tema').value, tp=$('#f-tipo').value, inc=$('#f-incide').value, e=$('#f-estado').value;
  return PA.filter(r =>
    (!q || [r.n_pa,r.objeto,r.artigo,r.proponente_deputados].join(' ').toLowerCase().includes(q)) &&
    (!p || split(r.proponente).includes(p)) && (!t || temaDe(r)===t) && (!tp || r.tipo_ar===tp) && (!inc || r.incide===inc) && (!e || r.estado===e));
}
function render() {
  const rows = filtrar().sort((x,y)=>{ if(ordem.k==='n_pa'){ const c=ordemPA(x,y); return ordem.asc?c:-c; } const c=String(x[ordem.k]||'').localeCompare(String(y[ordem.k]||''),'pt'); return ordem.asc?c:-c; });
  $('#f-n').textContent = `${fmtN(rows.length)} de ${fmtN(PA.length)} registos`;
  $('#tab-pa tbody').innerHTML = rows.slice(0,3000).map(r => `<tr>
    <td class="num"><b>${esc(r.n_pa)}</b></td>
    <td class="num">${esc(fmtData(r.data_entrada))}</td>
    <td>${split(r.proponente).map(p=>`<span class="chip">${esc(p)}</span>`).join(' ')||'—'}${r.proponente_deputados?`<br><span class="mini">${esc(r.proponente_deputados)}</span>`:''}</td>
    <td>${esc(r.artigo)||'—'}<br><span class="mini">${esc(r.incide)}${r.apresentada?' · '+esc(r.apresentada):''}</span></td>
    <td class="mini">${esc(r.tipo_ar)}</td>
    <td class="obj">${esc(r.objeto)}</td>
    <td class="mini">${esc(temaDe(r))}</td>
    <td>${estadoChip(r.estado)}<br><span class="mini">${esc(r.estado_ar)}</span></td>
    <td class="mini">${r.resultado_votacao?`${esc(r.resultado_votacao)} · ${esc(fmtData(r.data_votacao))}<br>${esc(r.votos_por_partido)}`:'—'}</td>
    <td class="mini">${r.url_detalhe?`<a href="${esc(r.url_detalhe)}" target="_blank" rel="noopener">AR</a>`:''}${r.url_pdf?` · <a href="${esc(r.url_pdf)}" target="_blank" rel="noopener">PDF</a>`:''}</td>
  </tr>`).join('') + (rows.length>3000?`<tr><td colspan="10" class="mini">Mostram-se 3 000 de ${fmtN(rows.length)} registos. Afine os filtros ou exporte.</td></tr>`:'') || '<tr><td colspan="10" class="mini">Sem registos.</td></tr>';
}
document.querySelectorAll('#t-pa .filtros select, #t-pa .filtros input').forEach(el => el.addEventListener('input', render));
document.querySelectorAll('#tab-pa th[data-k]').forEach(th => th.addEventListener('click', () => { const k=th.dataset.k; ordem = {k, asc: ordem.k===k ? !ordem.asc : true}; render(); }));
function exportarCSV() {
  const cols = ['n_pa','data_entrada','proponente','proponente_deputados','apresentada','incide','artigo','tipo_ar','objeto','tema_ar','estado','estado_ar','data_votacao','resultado_votacao','votos_por_partido','avocacao','url_detalhe','url_pdf','primeira_captura','ultima_captura','fonte'];
  const linhas = [cols.join(';')].concat(filtrar().map(r => cols.map(c => '"'+String(r[c]??'').replace(/"/g,'""')+'"').join(';')));
  const blob = new Blob(['﻿'+linhas.join('\r\n')], {type:'text/csv;charset=utf-8'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `PA_OE${ANO}_${D.gerado_em.slice(0,10)}.csv`; a.click();
}

function renderPosicao() {
  const p = $('#f-pos-prop').value;
  const votadas = PA.filter(r => r.votos_por_partido && (!p || split(r.proponente).includes(p)));
  const m = sentidos(votadas, r=>split(r.tema_ar).length?split(r.tema_ar):['—']);
  const gps = D.partidos.filter(g => Object.values(m).some(l=>l[g]));
  const temas = Object.keys(m).sort((a,b)=>Object.values(m[b]).reduce((s,x)=>s+x.F+x.C+x.A,0)-Object.values(m[a]).reduce((s,x)=>s+x.F+x.C+x.A,0));
  matrizCalor($('#m-posicao'), temas, gps, (l,c)=>m[l]&&m[l][c], 'Ainda sem votações registadas pela AR.');
}
$('#f-pos-prop').addEventListener('input', renderPosicao);
function renderTemas() {
  const tm=$('#f-t-tema').value, e=$('#f-t-estado').value;
  const rows = PA.filter(r => (!tm || split(r.tema_ar).includes(tm)) && (!e || r.estado===e)).sort(ordemPA);
  $('#f-t-n').textContent = `${fmtN(rows.length)} registos`;
  $('#tab-temas tbody').innerHTML = rows.slice(0,1500).map(r => `<tr><td class="num"><b>${esc(r.n_pa)}</b></td><td class="num">${esc(fmtData(r.data_entrada))}</td><td>${esc(r.proponente)}</td><td>${esc(r.artigo)||'—'}<br><span class="mini">${esc(r.incide)}</span></td><td class="obj">${esc(r.objeto)}</td><td class="mini">${esc(temaDe(r))}</td><td>${estadoChip(r.estado)}</td><td class="mini">${r.resultado_votacao?`${esc(fmtData(r.data_votacao))}<br>${esc(r.votos_por_partido)}`:'—'}</td></tr>`).join('')
    + (rows.length>1500?`<tr><td colspan="8" class="mini">Mostram-se 1 500 de ${fmtN(rows.length)} registos. Use o separador «Propostas de alteração» para filtrar e exportar.</td></tr>`:'') || '<tr><td colspan="8" class="mini">Sem registos.</td></tr>';
}
$('#f-t-tema').addEventListener('input', renderTemas); $('#f-t-estado').addEventListener('input', renderTemas);

const GRUPOS_RES = [
  ['Aprovadas', r=>r.estado==='aprovada'||r.estado==='aprovada parcialmente'],
  ['Rejeitadas', r=>r.estado==='rejeitada'],
  ['Prejudicadas', r=>r.estado==='prejudicada'],
  ['Retiradas ou não admitidas', r=>r.estado==='retirada'||r.estado==='não admitida'],
  ['Votadas em Plenário (avocação)', r=>r.avocacao==='S'],
  ['Por votar', r=>r.estado==='em apreciação'],
  ['Todas', r=>true]
];
function renderRes() {
  $('#seg-res').innerHTML = GRUPOS_RES.map(([l,f],i)=>`<button class="${i===segAtivo?'on':''}" onclick="segAtivo=${i};renderRes()">${esc(l)} (${fmtN(PA.filter(f).length)})</button>`).join('');
  const rows = PA.filter(GRUPOS_RES[segAtivo][1]).sort(ordemPA);
  $('#tab-res tbody').innerHTML = rows.slice(0,1500).map(r => `<tr><td class="num"><b>${esc(r.n_pa)}</b></td><td>${esc(r.proponente)}</td><td>${esc(r.artigo)}</td><td class="obj">${esc(r.objeto)}</td><td class="mini">${esc(temaDe(r))}</td><td>${estadoChip(r.estado)}${r.sede_votacao==='Plenário'?'<br><span class="mini">em Plenário</span>':''}</td><td class="num">${esc(fmtData(r.data_votacao))}</td><td class="mini">${esc(r.votos_por_partido)||'—'}</td></tr>`).join('')
    + (rows.length>1500?`<tr><td colspan="8" class="mini">Mostram-se 1 500 de ${fmtN(rows.length)} registos. Use o separador «Propostas de alteração» para filtrar e exportar.</td></tr>`:'')
    || `<tr><td colspan="8" class="mini">Sem registos neste grupo.</td></tr>`;
}
document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => { document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.toggle('on', x===b)); document.querySelectorAll('section.tab').forEach(s=>s.classList.toggle('on', s.id==='t-'+b.dataset.t)); }));
montar();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
