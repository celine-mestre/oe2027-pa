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
        "excel": f"PA_OE{ano}_dados_AR.xlsx" if (DOCS / f"PA_OE{ano}_dados_AR.xlsx").exists() else "",
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
        "cores": TAX.get("cores", {}),
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
  --bg:#f4f6f8;--card:#ffffff;--ink:#1c2630;--ink2:#4b5a68;--ink3:#7a8794;--linha:#dde3e9;--chip:#eef2f5;--sombra:0 1px 2px rgba(20,30,40,.06);
  --ok:#1F735B;--ok2:#6fb59a;--nok:#D02117;--neutro:#7a8794;--aviso:#B07A00;--pend:#b7c3cc;--ret:#e0b24c;
}
:root:not([data-theme="light"]){@media (prefers-color-scheme: dark){
  --bg:#0f1519;--card:#16202a;--ink:#e8edf2;--ink2:#b5c0cb;--ink3:#86939f;--linha:#2a3744;--chip:#1f2b36;--sombra:none;--pend:#3a4a58;}}
:root[data-theme="dark"]{--bg:#0f1519;--card:#16202a;--ink:#e8edf2;--ink2:#b5c0cb;--ink3:#86939f;--linha:#2a3744;--chip:#1f2b36;--sombra:none;--pend:#3a4a58}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:Lexend,Arial,sans-serif;font-size:14px;line-height:1.45}
a{color:var(--azul)}
code{font-family:ui-monospace,Consolas,monospace;font-size:12px;background:var(--chip);padding:1px 5px;border-radius:4px}
header.topo{background:linear-gradient(90deg,var(--azul) 0%,var(--teal) 55%,var(--verde) 100%);color:#fff;border-bottom:4px solid var(--vermelho)}
.topo .in{max-width:1380px;margin:0 auto;padding:14px 16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:relative}
.pastilha{width:46px;height:46px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none}
.pastilha img{width:38px;height:38px;display:block}
.topo h1{font-size:19px;font-weight:600;margin:0;line-height:1.2}
.topo .sub{font-size:12.5px;opacity:.92;font-weight:300}
.topo .sub a{color:#fff}
.topo .org{font-size:12px;font-weight:500;letter-spacing:.03em;opacity:.95;margin-bottom:2px}
.topo .dir{margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.topo .meta{text-align:right;font-size:11.5px;opacity:.92;line-height:1.35}
.topo .meta a{color:#fff}
.acoes{display:flex;gap:6px;align-items:center}
.segm{display:flex;border:1px solid rgba(255,255,255,.55);border-radius:999px;overflow:hidden}
.segm button{font:inherit;font-size:12.5px;font-weight:500;padding:6px 12px;border:0;background:transparent;color:#fff;cursor:pointer;display:flex;align-items:center;gap:5px}
.segm button.on{background:#fff;color:var(--azul)}
.segm button svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ic{width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.55);background:rgba(255,255,255,.08);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0}
.ic:hover{background:rgba(255,255,255,.22)}
.ic svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
#b-tema .i-sol{display:none}
:root[data-theme="dark"] #b-tema .i-lua{display:none}:root[data-theme="dark"] #b-tema .i-sol{display:block}
.faixa-amostra{background:var(--dourado);color:#1c2630;font-weight:600;text-align:center;padding:8px 16px;font-size:13px}
nav.tabs{position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--linha);box-shadow:0 2px 6px rgba(20,30,40,.06)}
nav.tabs .in{max-width:1380px;margin:0 auto;padding:8px 16px;display:flex;gap:6px;flex-wrap:wrap;align-items:center}
nav.tabs button{background:var(--card);border:1px solid var(--linha);color:var(--ink2);padding:7px 13px;border-radius:999px;font:inherit;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:7px}
nav.tabs button svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
nav.tabs button .n{font-size:11px;background:var(--chip);color:var(--ink2);border-radius:999px;padding:1px 7px;font-variant-numeric:tabular-nums}
nav.tabs button.on{background:var(--azul);border-color:var(--azul);color:#fff;font-weight:500}
nav.tabs button.on .n{background:rgba(255,255,255,.22);color:#fff}
nav.tabs button[hidden]{display:none}
nav.tabs .ed{margin-left:auto;font-size:12px;color:var(--ink3)}
main{max-width:1380px;margin:0 auto;padding:16px}
section.tab{display:none}section.tab.on{display:block}
section.tab.oculta{display:none!important}
.grid{display:grid;gap:12px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
.card{background:var(--card);border:1px solid var(--linha);border-radius:12px;padding:14px 16px;box-shadow:var(--sombra)}
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
.hero{display:grid;grid-template-columns:minmax(220px,1fr) 2fr;gap:18px;align-items:center}
.hero .big{font-size:44px;font-weight:600;color:var(--azul);line-height:1}
:root[data-theme="dark"] .hero .big{color:#8cc0e0}
.hero .big small{display:block;font-size:13px;font-weight:400;color:var(--ink3);margin-top:6px}
.stack{display:flex;height:22px;border-radius:8px;overflow:hidden;background:var(--chip)}
.stack span{display:block;height:100%;min-width:0}
.stack-leg{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:8px;font-size:12px;color:var(--ink2)}
.stack-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
.c-ok{background:var(--ok)}.c-par{background:var(--ok2)}.c-nok{background:var(--nok)}.c-ret{background:var(--ret)}.c-pre{background:#9aa5ad}.c-pend{background:var(--pend)}
.seg{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
.seg button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:999px;border:1px solid var(--linha);background:var(--card);color:var(--ink2);cursor:pointer}
.seg button.on{background:var(--azul);border-color:var(--azul);color:#fff}
.duas{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.barras{display:grid;grid-template-columns:max-content 1fr max-content;gap:6px 10px;align-items:center;font-size:13px}
.barras .b{height:12px;background:var(--azul);border-radius:0 4px 4px 0;min-width:2px}
.barras .bs{display:flex;height:14px;border-radius:0 4px 4px 0;overflow:hidden;background:transparent}
.barras .bs span{display:block;height:100%}
.barras .n{color:var(--ink2);text-align:right;font-variant-numeric:tabular-nums}
.barras .k{color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:280px;display:flex;align-items:center;gap:6px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;flex:none;border:1px solid rgba(0,0,0,.15)}
.legenda{font-size:11.5px;color:var(--ink3);margin-top:8px}
.filtros{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px;align-items:center}
.filtros select,.filtros input{font:inherit;font-size:13px;padding:7px 9px;border:1px solid var(--linha);border-radius:8px;background:var(--card);color:var(--ink)}
.filtros input[type=search]{min-width:260px;flex:1}
.filtros select{max-width:240px}
.filtros .n{color:var(--ink3);font-size:12.5px;margin-left:auto}
.btn{font:inherit;font-size:12.5px;padding:7px 12px;border-radius:8px;border:1px solid var(--azul);background:var(--card);color:var(--azul);cursor:pointer;text-decoration:none;display:inline-block}
.btn:hover{background:var(--azul);color:#fff}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--linha);border-radius:12px;overflow:hidden;font-size:12.5px}
th,td{padding:8px 9px;border-bottom:1px solid var(--linha);vertical-align:top;text-align:left}
th{background:var(--chip);color:var(--ink2);font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;white-space:nowrap;position:sticky;top:0;z-index:1}
tbody tr:nth-child(even) td{background:rgba(120,140,160,.05)}
tbody tr:hover td{background:rgba(39,86,115,.07)}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--chip);color:var(--ink2);font-size:11.5px;white-space:nowrap}
.chip.ok{background:#e3f1ea;color:#145a44}.chip.nok{background:#f9e3e1;color:#8a1711}.chip.pre{background:#eee;color:#555}.chip.ret{background:#fdf1d6;color:#7a5200}
.chip.gp .dot{margin-right:4px;vertical-align:0}
.vt{display:inline-block;font-size:10.5px;line-height:1.5;padding:0 5px;border-radius:4px;margin:1px 2px 1px 0;font-weight:500}
.vt.vf{background:#d5ecdf;color:#145a44}.vt.vc{background:#f6d5d2;color:#8a1711}.vt.va{background:#f8e8c2;color:#6b4a00}.vt.vx{background:#e6e9ec;color:#555}
:root[data-theme="dark"] .vt.vf{background:#1b3a30;color:#9fdcc2}:root[data-theme="dark"] .vt.vc{background:#4a1b18;color:#f5b3ad}:root[data-theme="dark"] .vt.va{background:#4a3a12;color:#f3d27a}:root[data-theme="dark"] .vt.vx{background:#2a3744;color:#b5c0cb}
.votos{min-width:240px;max-width:270px}
.prop{min-width:120px;max-width:190px}
.outros{min-width:230px;max-width:280px}
:root[data-theme="dark"] .chip.ok{background:#1b3a30;color:#9fdcc2}
:root[data-theme="dark"] .chip.nok{background:#4a1b18;color:#f5b3ad}
:root[data-theme="dark"] .chip.ret{background:#4a3a12;color:#f3d27a}
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
.obj{min-width:340px;max-width:460px}
#tab-pa{min-width:1760px}
.colunas svg{width:100%;height:auto;display:block}
#topo-btn{position:fixed;right:18px;bottom:18px;width:40px;height:40px;border-radius:50%;border:1px solid var(--linha);background:var(--card);color:var(--azul);cursor:pointer;box-shadow:0 2px 8px rgba(20,30,40,.15);display:none;align-items:center;justify-content:center;z-index:40}
#topo-btn svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
footer{max-width:1380px;margin:10px auto 24px;padding:0 16px;font-size:11.5px;color:var(--ink3)}
footer .filete{height:3px;background:linear-gradient(90deg,var(--azul),var(--teal),var(--verde));border-bottom:2px solid var(--vermelho);margin-bottom:10px;border-radius:2px}
@page{size:A4 landscape;margin:11mm 12mm}
@media print{
  *{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}
  html,body{background:#fff;color:#1c2630;font-size:11px}
  :root{--bg:#fff;--card:#fff;--ink:#1c2630;--ink2:#4b5a68;--ink3:#6b7884;--linha:#cfd6dc;--chip:#eef2f5;--sombra:none}
  header.topo{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  nav.tabs,.filtros,.acoes,.btn,#topo-btn,.faixa-amostra,#aviso-vazio{display:none!important}
  main{max-width:none;padding:0}
  section.tab{display:block!important;page-break-before:always;break-before:page}
  section.tab.oculta{display:none!important}
  section.tab:first-of-type{page-break-before:auto;break-before:auto}
  section.tab::before{content:attr(data-titulo);display:block;font-size:15px;font-weight:600;color:#275673;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid #275673}
  .card{break-inside:avoid;page-break-inside:avoid;box-shadow:none}
  .grid.duas{grid-template-columns:1fr 1fr}
  .kpis{grid-template-columns:repeat(7,1fr)}
  .kpi .v{font-size:22px}
  .kpi .info{display:none}
  .kpi .tip{display:none!important}
  .hero .big{font-size:34px}
  .tabela-wrap{max-height:none;overflow:visible}
  th{position:static}
  table{font-size:10px}th,td{padding:4px 6px}
  tbody tr:nth-child(n+61){display:none}
  .tabela-wrap::after{content:"Tabela limitada às primeiras 60 linhas na impressão. A lista completa está no painel e no ficheiro Excel.";display:block;font-size:9.5px;color:#6b7884;margin-top:4px}
  #tab-pa{min-width:0}.obj{min-width:0;max-width:none}
  .colunas svg{max-height:170px}
  a{text-decoration:none;color:inherit}
  footer{page-break-before:avoid}
}
@media (max-width:760px){.topo .dir{margin-left:0;align-items:flex-start}.topo .meta{text-align:left}.hero{grid-template-columns:1fr}.hero .big{font-size:34px}.barras .k{max-width:150px}nav.tabs .ed{display:none}}
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
      <div class="segm" id="edicoes" role="tablist" aria-label="Edição do Orçamento"></div>
      <button class="ic" id="b-tema" title="Modo escuro" aria-label="Mudar para modo escuro">
        <svg class="i-lua" viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>
        <svg class="i-sol" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      </button>
      <button class="ic" onclick="expandir()" title="Ecrã inteiro" aria-label="Ecrã inteiro"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg></button>
      <button class="ic" onclick="window.print()" title="Imprimir" aria-label="Imprimir"><svg viewBox="0 0 24 24"><path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/></svg></button>
    </div>
    <div class="meta" id="meta"></div>
  </div>
</div></header>
<div class="faixa-amostra" id="faixa" hidden></div>
<nav class="tabs"><div class="in">
  <button data-t="sintese" class="on"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>Síntese</button>
  <button data-t="pa"><svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>Propostas de alteração <span class="n" id="n-pa"></span></button>
  <button data-t="votacoes"><svg viewBox="0 0 24 24"><path d="M9 11l3 3 8-8"/><path d="M20 12v7a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h11"/></svg>Votações <span class="n" id="n-vot"></span></button>
  <button data-t="historico"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>Alterações entre capturas <span class="n" id="n-hist"></span></button>
  <button data-t="fontes"><svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/></svg>Fontes e método</button>
  <span class="ed" id="ed-nav"></span>
</div></nav>
<main>

<section class="tab on" id="t-sintese" data-titulo="Síntese">
  <div class="card" id="aviso-vazio" hidden style="margin-bottom:12px"></div>
  <div class="card hero" style="margin-bottom:12px">
    <div><div class="big" id="hero-n"></div></div>
    <div><div class="stack" id="hero-stack"></div><div class="stack-leg" id="hero-leg"></div><div class="legenda" id="hero-nota"></div></div>
  </div>
  <div class="grid kpis" id="kpis"></div>
  <div class="legenda">Contagens pela convenção da AR: cada registo numerado conta como uma proposta, incluindo as partes (120C-1, 120C-2) em que a AR divide uma proposta que altera vários artigos ou alíneas.</div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3 id="h-24h">Últimas 24 horas</h3><div class="barras" id="g-24h"></div></div>
    <div class="card"><h3>Estado das fontes da AR</h3><div id="fontes-estado" style="font-size:13px"></div></div>
  </div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>PA por proponente e resultado</h3><div class="barras" id="g-partido"></div><div class="stack-leg"><span><i class="c-ok"></i>aprovadas</span><span><i class="c-par"></i>aprovadas parcialmente</span><span><i class="c-nok"></i>rejeitadas</span><span><i class="c-ret"></i>retiradas ou não admitidas</span><span><i class="c-pre"></i>prejudicadas</span><span><i class="c-pend"></i>por votar</span></div></div>
    <div class="card"><h3>Entradas por dia</h3><div class="colunas" id="g-dias"></div><div class="legenda" id="g-dias-nota">Data e hora de entrada registadas pela AR, por registo.</div></div>
    <div class="card"><h3>PA por tema (atribuído pela AR)</h3><div class="barras" id="g-tema"></div><div class="legenda">Uma proposta com vários temas conta em cada um deles.</div></div>
    <div class="card"><h3>Entradas por hora no último dia</h3><div class="colunas" id="g-horas"></div><div class="legenda" id="g-horas-nota"></div></div>
    <div class="card"><h3>PA por tipo (natureza publicada pela AR)</h3><div class="barras" id="g-tipo"></div></div>
    <div class="card"><h3 id="h-cal">Calendário de apreciação na AR</h3><div class="cal" id="cal"></div><div class="legenda" id="cal-fonte"></div></div>
  </div>
</section>

<section class="tab" id="t-pa" data-titulo="Propostas de alteração">
  <div class="legenda" style="margin:0 0 12px">Tema atribuído pela AR a cada proposta (em 2026, a comissão parlamentar competente). Uma proposta com vários temas conta em cada um deles. Clique num tema para filtrar a lista.</div>
  <div class="grid">
    <div class="card"><h3>PA por tema e resultado</h3><div class="barras" id="g-tema-2"></div><div class="stack-leg"><span><i class="c-ok"></i>aprovadas</span><span><i class="c-par"></i>parcialmente</span><span><i class="c-nok"></i>rejeitadas</span><span><i class="c-ret"></i>retiradas ou não admitidas</span><span><i class="c-pre"></i>prejudicadas</span><span><i class="c-pend"></i>por votar</span></div></div>
    <div class="card"><h3>Resultado por tema</h3><div class="tabela-wrap"><table class="matriz" id="m-tema-res"></table></div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>PA por tema e proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-tema-prop"></table></div></div>
  <div class="card" id="lista-pa" style="margin-top:12px;scroll-margin-top:70px"><h3>Lista das propostas de alteração</h3>
    <div class="legenda" style="margin:-4px 0 10px">Sentido de voto de cada grupo parlamentar: <span class="vt vf">a favor</span><span class="vt vc">contra</span><span class="vt va">abstenção</span><span class="vt vx">ausente</span></div>
  <div class="filtros">
      <input type="search" id="f-q" placeholder="Pesquisar no objeto, artigo, epígrafe, diplomas, n.º da PA, deputados…">
      <select id="f-partido"><option value="">Proponente</option></select>
      <select id="f-tema"><option value="">Tema (AR)</option></select>
      <select id="f-tipo"><option value="">Tipo</option></select>
      <select id="f-incide"><option value="">Incide</option></select>
      <select id="f-estado"><option value="">Estado</option></select>
      <select id="f-extra"><option value="">Outros critérios</option><option value="avocacao">Avocadas a Plenário</option><option value="req">Com requerimento publicado</option><option value="ra">Com pedido de parecer às Regiões Autónomas</option><option value="diplomas">Alteram diplomas identificados pela AR</option><option value="partes">Com partes (-1, -2, …)</option><option value="semvoto">Decididas sem sentido de voto publicado</option></select>
      <span class="n" id="f-n"></span>
      <button class="btn" id="b-exp" onclick="exportarExcel()" title="Descarrega em Excel as propostas visíveis com os filtros escolhidos (sem filtros, todas as propostas)">Exportar para Excel</button>
    </div>
    <div class="tabela-wrap"><table id="tab-pa"><thead><tr>
      <th data-k="n_pa">N.º</th><th data-k="data_entrada">Entrada</th><th data-k="proponente">Proponente</th><th data-k="artigo">Artigo / mapa</th><th data-k="tipo_ar">Tipo</th><th>Objeto</th><th data-k="tema_ar">Tema (AR)</th><th data-k="estado">Estado</th><th>Votação</th><th>Outros dados da AR</th><th>Ligações</th>
    </tr></thead><tbody></tbody></table></div>
  </div>
</section>

<section class="tab" id="t-votacoes" data-titulo="Votações">
  <div class="grid kpis" id="kpis-vot"></div>
  <div class="grid duas" style="margin-top:12px">
    <div class="card"><h3>Resultado por proponente</h3><div class="tabela-wrap"><table class="matriz" id="m-resultado"></table></div><div class="legenda">Por registo publicado pela AR. Taxa de aprovação = aprovadas, incluindo as parciais, sobre os registos com votação publicada.</div></div>
    <div class="card"><h3>Sentido de voto por grupo parlamentar (PA votadas)</h3><div class="tabela-wrap"><table class="matriz" id="m-sentido"></table></div><div class="legenda">Tal como publicado pela AR. Inclui os deputados únicos representantes de partido e, quando a AR o regista, votos individuais de deputados e ausências.</div></div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Posição dos grupos parlamentares por tema</h3>
    <div class="filtros"><label class="mini" for="f-pos-prop">PA apresentadas por</label><select id="f-pos-prop"><option value="">todos os proponentes</option></select><span class="mini">Percentagem de votos a favor de cada grupo parlamentar nas PA votadas de cada tema; por baixo, favor · contra · abstenção.</span></div>
    <div class="tabela-wrap"><table class="matriz calor" id="m-posicao"></table></div>
    <div class="legenda">Indicador histórico calculado a partir dos temas e dos sentidos de voto publicados pela AR. Não é uma previsão. Inclui os deputados únicos representantes de partido.</div>
  </div>
  <div class="card" style="margin-top:12px"><h3>Como vota cada grupo parlamentar nas PA de cada proponente</h3><div class="tabela-wrap"><table class="matriz calor" id="m-cruzado"></table></div><div class="legenda">Linhas: proponente da PA. Colunas: grupo parlamentar que vota. Percentagem de votos a favor nas PA votadas; por baixo, favor · contra · abstenção.</div></div>
  <div class="card" style="margin-top:12px"><h3 id="h-docs">Documentos publicados pela COFAP</h3><div class="tabela-wrap"><table id="tab-docs"><thead><tr><th>Documento</th><th>Registado no painel</th></tr></thead><tbody></tbody></table></div><div class="legenda">Guiões e resultados de votações, textos finais, relatórios e pareceres (por exemplo, da UTAO e do Conselho das Finanças Públicas) publicados na página do OE da Comissão de Orçamento, Finanças e Administração Pública. Não inclui os contributos de entidades e cidadãos.</div></div>
  <div class="card" style="margin-top:12px"><h3>Detalhe das votações</h3>
    <div class="seg" id="seg-res"></div>
    <div class="tabela-wrap"><table id="tab-res"><thead><tr><th>N.º</th><th>Proponente</th><th>Artigo</th><th>Objeto</th><th>Tema</th><th>Resultado</th><th>Data</th><th>Sentido de voto por grupo parlamentar</th></tr></thead><tbody></tbody></table></div>
    <div class="legenda">Por registo publicado pela AR. «Em Plenário» assinala as votações feitas em Plenário por avocação. Sentido de voto: <span class="vt vf">a favor</span><span class="vt vc">contra</span><span class="vt va">abstenção</span><span class="vt vx">ausente</span></div>
  </div>
</section>

<section class="tab" id="t-historico" data-titulo="Alterações entre capturas">
  <div class="card"><h3>O que mudou na publicação da AR entre capturas (mais recente primeiro)</h3>
  <div class="legenda" style="margin:-4px 0 10px">Em cada captura automática, o painel compara a publicação da AR com a anterior e regista o que mudou. Serve para ver, desde a última consulta, que PA entraram, quais mudaram de estado e quais foram votadas.</div>
  <div class="tabela-wrap"><table id="tab-hist"><thead><tr><th>Momento</th><th>N.º PA</th><th>Evento</th><th>Detalhe</th><th>Fonte</th></tr></thead><tbody></tbody></table></div>
  <div class="legenda">«nova»: a PA apareceu pela primeira vez. «estado alterado»: o estado publicado mudou. «votada»: foi publicada uma votação. «ausente da fonte»: a PA deixou de constar da publicação da AR. O painel mostra os últimos 400 eventos; o histórico completo está em <code>historico.csv</code>.</div></div>
</section>

<section class="tab" id="t-fontes" data-titulo="Fontes e método">
  <div class="grid duas">
    <div class="card"><h3>Fontes (Assembleia da República)</h3><ul id="lista-fontes" style="margin:0;padding-left:18px;font-size:13px"></ul></div>
    <div class="card"><h3>Método</h3>
      <ol style="margin:0;padding-left:18px;font-size:13px">
        <li>Toda a informação do painel é publicada pela Assembleia da República: dados abertos (categoria «Orçamento do Estado», XVII Legislatura) e, em reserva, a página de detalhe de cada proposta no parlamento.pt.</li>
        <li>O painel não acrescenta classificações próprias. Tema, tipo, estado, requerimentos, pareceres e sentido de voto são os registados pela AR. O tema é o atribuído pelos serviços da AR a cada proposta (em 2026, corresponde à comissão parlamentar competente).</li>
        <li>Contagens pela convenção da AR: cada registo numerado conta como uma proposta, incluindo as partes em que a AR divide uma proposta que altera vários artigos ou alíneas. O número de propostas distintas (sem partes) é apresentado à parte.</li>
        <li>Cada captura guarda uma cópia dos dados recebidos. A base mantém a última versão de cada proposta e regista, entre capturas, entradas, alterações de estado e votações.</li>
        <li>Uma proposta que deixe de constar da fonte é assinalada como «ausente da fonte» e deve ser confirmada no parlamento.pt.</li>
        <li>O OE 2026 (processo concluído) serve de base de comparação: é a única edição completa da XVII Legislatura, com a mesma composição parlamentar.</li>
      </ol>
    </div>
  </div>
</section>
</main>
<button id="topo-btn" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="Voltar ao topo" aria-label="Voltar ao topo"><svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button>
<footer><div class="filete"></div><span id="rodape"></span> · Fonte: Assembleia da República (dados abertos e parlamento.pt). Tratamento: Área de Suporte à Decisão, Secretaria-Geral do Governo.</footer>

<script id="dados" type="application/json">__DADOS__</script>
<script>
const D = JSON.parse(document.getElementById('dados').textContent);
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtN = n => Number(n).toLocaleString('pt-PT');
const pct = (a,b) => b ? Math.round(a/b*1000)/10 : 0;
const fmtData = d => d ? d.slice(0,10).split('-').reverse().join('-') : '';
const MESES = ['jan.','fev.','mar.','abr.','mai.','jun.','jul.','ago.','set.','out.','nov.','dez.'];
const diaMes = d => { const [a,m,dd] = d.slice(0,10).split('-'); return `${+dd} ${MESES[+m-1]}`; };
const COR = D.cores || {};
const corGP = g => COR[g] || '#8a97a3';
function expandir(){const d=document;try{if(!d.fullscreenElement){d.documentElement.requestFullscreen&&d.documentElement.requestFullscreen()}else{d.exitFullscreen&&d.exitFullscreen()}}catch(e){}}
function modoAtual(){return document.documentElement.getAttribute('data-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}
function aplicarModo(m){document.documentElement.setAttribute('data-theme',m);try{localStorage.setItem('tema',m)}catch(e){}const b=$('#b-tema');const alvo=m==='dark'?'claro':'escuro';b.title=`Modo ${alvo}`;b.setAttribute('aria-label',`Mudar para modo ${alvo}`);}
try{const t=localStorage.getItem('tema');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}
aplicarModo(modoAtual());
$('#b-tema').addEventListener('click',()=>aplicarModo(modoAtual()==='dark'?'light':'dark'));
if (D.rotulo) { $('#faixa').hidden = false; $('#faixa').textContent = D.rotulo; }
window.addEventListener('scroll', () => { $('#topo-btn').style.display = window.scrollY > 600 ? 'flex' : 'none'; });

const cont = (arr, f) => { const m = new Map(); for (const r of arr) for (const k of f(r)) m.set(k, (m.get(k)||0)+1); return [...m.entries()].sort((a,b)=>b[1]-a[1]); };
const split = s => (s||'').split(';').map(x=>x.trim()).filter(Boolean);
const temaDe = r => (r.tema_ar||'').replace(/;\s*$/,'').trim();
const temasPA = r => split(r.tema_ar).length ? split(r.tema_ar) : ['—'];
const ESTADOS = ['aprovada','aprovada parcialmente','rejeitada','retirada','não admitida','prejudicada','em apreciação'];
const CLS = {aprovada:'c-ok','aprovada parcialmente':'c-par',rejeitada:'c-nok',retirada:'c-ret','não admitida':'c-ret',prejudicada:'c-pre','em apreciação':'c-pend'};
const estadoChip = e => { const c = {aprovada:'ok','aprovada parcialmente':'ok',rejeitada:'nok',prejudicada:'pre',retirada:'ret','não admitida':'ret'}[e]||''; return `<span class="chip ${c}">${esc(e||'—')}</span>`; };
const gpChip = p => `<span class="chip gp"><span class="dot" style="background:${corGP(p)}"></span>${esc(p)}</span>`;
const votosHTML = s => split(s).map(v => { const [g,x] = v.split(':').map(y=>y.trim()); const c = {Favor:'vf',Contra:'vc','Abstenção':'va'}[x]||'vx'; return `<span class="vt ${c}" title="${esc(g)}: ${esc(x)}">${esc(g)}</span>`; }).join('');
const numPA = s => { const m=/^(\d+)([A-Z]*)(?:-(\d+))?/.exec(s||''); return m ? [+m[1], m[2], +(m[3]||0)] : [1e9,'',0]; };
const ordemPA = (x,y) => { const a=numPA(x.n_pa),b=numPA(y.n_pa); return a[0]-b[0]||a[1].localeCompare(b[1])||a[2]-b[2]; };
const hm = m => m ? m.replace('T',' ').slice(0,16) : '—';
function barras(el, pares, onclick) {
  const max = Math.max(1, ...pares.map(p=>p[1]));
  el.innerHTML = pares.map(([k,v]) => `<div class="k" title="${esc(k)}" ${onclick?`style="cursor:pointer" data-k="${esc(k)}"`:''}>${esc(k)}</div><div><div class="b" style="width:${(v/max*100).toFixed(1)}%"></div></div><div class="n">${fmtN(v)}</div>`).join('') || '<div class="mini">Sem dados.</div>';
  if (onclick) el.querySelectorAll('.k').forEach(k => k.addEventListener('click', () => onclick(k.dataset.k)));
}
function barrasEmpilhadas(el, linhas, onclick, comCor) {
  // linhas: [chave, {estado: n}, total]
  const max = Math.max(1, ...linhas.map(l=>l[2]));
  el.innerHTML = linhas.map(([k,m,t]) => `<div class="k" title="${esc(k)}" ${onclick?`style="cursor:pointer" data-k="${esc(k)}"`:''}>${comCor?`<span class="dot" style="background:${corGP(k)}"></span>`:''}${esc(k)}</div><div><div class="bs" style="width:${(t/max*100).toFixed(1)}%">${ESTADOS.map(e=>m[e]?`<span class="${CLS[e]}" style="width:${(m[e]/t*100).toFixed(2)}%" title="${esc(k)} · ${e}: ${fmtN(m[e])}"></span>`:'').join('')}</div></div><div class="n">${fmtN(t)}</div>`).join('') || '<div class="mini">Sem dados.</div>';
  if (onclick) el.querySelectorAll('.k').forEach(k => k.addEventListener('click', () => onclick(k.dataset.k)));
}
function colunas(el, pares, fmtX) {
  // gráfico de colunas em SVG: pares [rótulo, valor]
  if (!pares.length) { el.innerHTML = '<div class="mini">Sem dados.</div>'; return; }
  const W = 640, H = 200, pad = {l: 40, r: 8, t: 10, b: 34}, n = pares.length, max = Math.max(1, ...pares.map(p=>p[1]));
  const cw = (W - pad.l - pad.r) / n, bw = Math.max(2, cw * 0.72);
  const y = v => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const passo = n > 16 ? Math.ceil(n / 12) : 1;
  const grelha = [0, .25, .5, .75, 1].map(f => `<line x1="${pad.l}" x2="${W-pad.r}" y1="${y(max*f)}" y2="${y(max*f)}" stroke="currentColor" stroke-opacity=".12"/><text x="${pad.l-6}" y="${y(max*f)+4}" text-anchor="end" font-size="10" fill="currentColor" fill-opacity=".6">${fmtN(Math.round(max*f))}</text>`).join('');
  const cols = pares.map(([k,v],i) => { const x = pad.l + i*cw + (cw-bw)/2; return `<rect x="${x}" y="${y(v)}" width="${bw}" height="${H-pad.b-y(v)}" rx="2" fill="var(--azul)"><title>${esc(k)}: ${fmtN(v)}</title></rect>${v&&n<=24?`<text x="${x+bw/2}" y="${y(v)-3}" text-anchor="middle" font-size="10" fill="currentColor" fill-opacity=".8">${fmtN(v)}</text>`:''}${i%passo===0?`<text x="${x+bw/2}" y="${H-pad.b+14}" text-anchor="middle" font-size="10" fill="currentColor" fill-opacity=".7">${esc(fmtX?fmtX(k):k)}</text>`:''}`; }).join('');
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Gráfico de colunas" style="color:var(--ink)">${grelha}${cols}</svg>`;
}
const opts = (id, vals, manter=1) => { const s=$(id); while (s.options.length>manter) s.remove(manter); for (const v of vals) { const o=document.createElement('option'); o.value=v; o.textContent=v; s.appendChild(o);} };
const INFO = {
  'Propostas de alteração (contagem da AR)': 'Registos numerados publicados pela AR. É a contagem que a AR usa: quando uma proposta altera vários artigos ou alíneas, a AR divide-a em partes (120C-1, 120C-2), cada uma com número, estado e votação próprios.',
  'Números de PA distintos': 'Números-base distintos (120C conta uma vez, com todas as suas partes). Diferença para a contagem da AR = número de partes adicionais.',
  'Em apreciação': 'Registos entregues que ainda não têm decisão: aguardam votação.',
  'Aprovadas (total ou parcialmente)': 'Registos aprovados em Comissão ou em Plenário, incluindo as aprovações por unanimidade e as parciais, em que só parte do texto proposto foi aprovada.',
  'Rejeitadas': 'Registos rejeitados em Comissão ou, depois de avocação, em Plenário.',
  'Retiradas, prejudicadas ou não admitidas': 'Retirada: o proponente desistiu da proposta. Prejudicada: deixou de poder ser votada porque uma votação anterior já decidiu a mesma matéria. Não admitida: não foi aceite para apreciação.',
  'Taxa de aprovação': 'Registos aprovados (incluindo parcialmente) sobre os registos com votação publicada pela AR.',
  'PA votadas': 'Registos com pelo menos uma votação publicada pela AR.',
  'Prejudicadas': 'Registos que deixaram de poder ser votados porque uma votação anterior já decidiu a mesma matéria.',
  'Votadas em Plenário (avocação)': 'Registos com votação em Plenário. Acontece quando um grupo parlamentar requer que a votação, normalmente feita na Comissão de Orçamento, Finanças e Administração Pública, seja feita (ou repetida) em Plenário.',
  'Requerimentos de avocação publicados': 'Requerimentos de avocação a Plenário publicados pela AR na ficha da proposta, com o grupo parlamentar requerente e a data.',
  'Por votar': 'Registos ainda sem votação.',
  'Temas atribuídos pela AR': 'Temas distintos que os serviços da AR atribuíram às propostas desta edição. Em 2026 correspondem às comissões parlamentares competentes.',
  'Registos com tema': 'Registos com pelo menos um tema atribuído pela AR.',
  'Registos com mais de um tema': 'Registos a que a AR atribuiu vários temas. Contam em cada um deles.',
  'Registos sem tema': 'Registos publicados sem tema. Aparecem como «—».',
  'Registos votados': 'Registos com sentido de voto publicado, base da matriz de posições por tema.',
  'Com pedido de parecer às Regiões Autónomas': 'Registos em que a AR assinala pedido de parecer à Região Autónoma dos Açores ou da Madeira.'
};
const kpi = ([l,v,c,sufixo]) => `<div class="card kpi ${c}">${INFO[l]?`<button class="info" aria-expanded="false" aria-label="O que significa «${esc(l)}»" title="O que significa?" onclick="const k=this.parentElement;k.classList.toggle('aberto');this.setAttribute('aria-expanded',k.classList.contains('aberto'))">i</button>`:''}<div class="v">${typeof v==='number'?fmtN(v):esc(v)}${sufixo||''}</div><div class="l">${l}</div>${INFO[l]?`<div class="tip">${esc(INFO[l])}</div>`:''}</div>`;
const matrizCalor = (el, linhas, colunas, celula, vazio, corLinha) => {
  if (!linhas.length) { el.innerHTML = `<tr><td class="mini">${vazio}</td></tr>`; return; }
  el.innerHTML = `<tr><th></th>${colunas.map(c=>`<th>${esc(c)}</th>`).join('')}</tr>` + linhas.map(l => `<tr><td style="text-align:left"><b>${corLinha?`<span class="dot" style="background:${corGP(l)}"></span> `:''}${esc(l)}</b></td>${colunas.map(c => { const s = celula(l,c); if (!s || !(s.F+s.C+s.A)) return '<td class="q mini">—</td>'; const n=s.F+s.C+s.A, p=s.F/n; const cor = `hsl(${Math.round(p*120)},55%,${82-Math.round(p*10)}%)`; return `<td class="q" style="background:${cor}" title="${esc(c)} nas PA de ${esc(l)}: ${s.F} a favor, ${s.C} contra, ${s.A} abstenções">${Math.round(p*100)}%<small>${s.F} · ${s.C} · ${s.A}</small></td>`; }).join('')}</tr>`).join('');
};
const sentidos = (regs, chaveLinha) => { const m = {}; for (const r of regs) { if (!r.votos_por_partido) continue; for (const l of chaveLinha(r)) { m[l] = m[l]||{}; for (const v of split(r.votos_por_partido)) { const [gp,s]=v.split(':').map(x=>x.trim()); const k={Favor:'F',Contra:'C','Abstenção':'A'}[s]; if(!gp||!k) continue; m[l][gp]=m[l][gp]||{F:0,C:0,A:0}; m[l][gp][k]++; } } } return m; };
const porEstadoDe = regs => { const m = {}; for (const r of regs) m[r.estado||'—'] = (m[r.estado||'—']||0)+1; return m; };

let ANO = D.edicao_ativa, E = D.edicoes[ANO], PA = [], ordem = {k:'n_pa', asc:true}, segAtivo = 0;
const hash = location.hash.replace('#','').split('/');
if (hash[0] && D.edicoes[hash[0].replace('oe','')]) ANO = hash[0].replace('oe','');
E = D.edicoes[ANO];
$('#edicoes').innerHTML = Object.keys(D.edicoes).sort().map(a => `<button role="tab" data-ano="${a}" class="${a===ANO?'on':''}">OE ${a}</button>`).join('');
$('#edicoes').querySelectorAll('button').forEach(b => b.addEventListener('click', () => { ANO = b.dataset.ano; E = D.edicoes[ANO]; $('#edicoes').querySelectorAll('button').forEach(x=>x.classList.toggle('on', x===b)); montar(); atualizarHash(); }));
function tabAtiva(){ return document.querySelector('nav.tabs button.on').dataset.t; }
function atualizarHash(){ history.replaceState(null, '', `#oe${ANO}/${tabAtiva()}`); }
function irPara(t){ document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.toggle('on', x.dataset.t===t)); document.querySelectorAll('section.tab').forEach(s=>s.classList.toggle('on', s.id==='t-'+t)); atualizarHash(); }
document.querySelectorAll('nav.tabs button').forEach(b => b.addEventListener('click', () => { irPara(b.dataset.t); window.scrollTo({top:0,behavior:'smooth'}); }));

function montar() {
  PA = E.pa;
  const concluido = E.estado === 'concluído';
  const ex = E.execucao || {};
  const fonteNome = {opendata:'dados abertos da AR', scrape:'parlamento.pt (página de cada PA)', normalize:'dados abertos da AR (cópia guardada)'}[ex.comando] || '—';
  $('#titulo').textContent = `Propostas de alteração ao Orçamento do Estado para ${ANO}`;
  $('#subtitulo').innerHTML = `${E.urls.url_iniciativa?`<a href="${esc(E.urls.url_iniciativa)}" target="_blank" rel="noopener">${esc(E.designacao)}</a>`:esc(E.designacao)} · informação publicada pela Assembleia da República` + (concluido ? ' · processo concluído' : '');
  $('#meta').innerHTML = `Última captura: <b>${esc(ex.momento ? ex.momento.replace('T',' ').slice(0,16) : '—')}</b><br>Fonte: <a href="${esc(D.fontes.dados_abertos_pagina_oe)}" target="_blank" rel="noopener">${esc(fonteNome)}</a> · painel gerado em ${esc(D.gerado_em)}`;
  $('#rodape').textContent = `PA ao OE ${ANO} · ${fmtN(PA.length)} registos · painel gerado em ${D.gerado_em}`;
  $('#ed-nav').textContent = `OE ${ANO}${concluido?' · concluído':''}`;
  $('#h-cal').textContent = `Calendário de apreciação do OE ${ANO} na AR`;
  $('#h-docs').textContent = `Documentos publicados pela COFAP sobre o OE ${ANO}`;

  // ----- síntese
  const porEstado = porEstadoDe(PA);
  const nBase = new Set(PA.map(r=>r.pa_base||r.n_pa)).size;
  const basesComPartes = new Set(PA.filter(r=>r.parte).map(r=>r.pa_base)).size;
  const votadas = PA.filter(r => r.votos_por_partido);
  const aprov = (porEstado['aprovada']||0)+(porEstado['aprovada parcialmente']||0);
  const taxa = votadas.length ? pct(aprov, votadas.length) : null;
  const av = $('#aviso-vazio'); av.hidden = true;
  if (!PA.length) {
    av.hidden = false;
    av.innerHTML = concluido ? `<b>Sem dados carregados para o OE ${ANO}.</b>` : `<b>Ainda não há propostas de alteração publicadas pela AR para a ${esc(E.designacao)}.</b><br><span class="mini">As propostas de alteração serão registadas a partir de ${E.inicio_registo ? fmtData(E.inicio_registo)+', às '+E.inicio_registo.slice(11,16).replace(':','h') : '29 de outubro, às 9h00'}, data de início do prazo para a sua inserção, segundo o calendário de apreciação da AR. O painel é atualizado automaticamente a partir dessa data. Use o seletor «OE 2026» no canto superior direito para ver o processo anterior, concluído.</span>`;
  }
  $('#hero-n').innerHTML = `${fmtN(PA.length)}<small>propostas de alteração, pela contagem da AR · ${fmtN(nBase)} números distintos${basesComPartes?` · ${fmtN(basesComPartes)} divididas em partes`:''}</small>`;
  $('#hero-stack').innerHTML = ESTADOS.filter(e=>porEstado[e]).map(e=>`<span class="${CLS[e]}" style="width:${(porEstado[e]/PA.length*100).toFixed(2)}%" title="${e}: ${fmtN(porEstado[e])}"></span>`).join('');
  $('#hero-leg').innerHTML = ESTADOS.filter(e=>porEstado[e]).map(e=>`<span><i class="${CLS[e]}"></i>${e} <b>${fmtN(porEstado[e])}</b> (${pct(porEstado[e],PA.length)}%)</span>`).join('');
  $('#hero-nota').textContent = taxa!==null ? `Taxa de aprovação: ${taxa}% dos ${fmtN(votadas.length)} registos com votação publicada.` : '';
  $('#kpis').innerHTML = [
    ['Propostas de alteração (contagem da AR)', PA.length, ''],
    ['Números de PA distintos', nBase, 'neu'],
    ['Em apreciação', porEstado['em apreciação']||0, 'neu'],
    ['Aprovadas (total ou parcialmente)', aprov, 'ok'],
    ['Rejeitadas', porEstado['rejeitada']||0, 'nok'],
    ['Retiradas, prejudicadas ou não admitidas', (porEstado['retirada']||0)+(porEstado['prejudicada']||0)+(porEstado['não admitida']||0), 'neu'],
    ['Taxa de aprovação', taxa===null?'—':taxa, 'ok', taxa===null?'':'%'],
  ].map(kpi).join('');
  $('#n-pa').textContent = fmtN(PA.length); $('#n-vot').textContent = fmtN(votadas.length); $('#n-hist').textContent = fmtN(E.historico.length);
  const bHist = document.querySelector('nav.tabs button[data-t="historico"]');
  bHist.hidden = concluido; $('#t-historico').classList.toggle('oculta', concluido);
  if (concluido && tabAtiva()==='historico') irPara('sintese');
  const proponentes = cont(PA, r=>split(r.proponente)).map(p=>p[0]);
  const porProp = proponentes.map(p => { const rs = PA.filter(r=>split(r.proponente).includes(p)); return [p, porEstadoDe(rs), rs.length]; });
  barrasEmpilhadas($('#g-partido'), porProp, p => { irPara('pa'); $('#f-partido').value = p; render(); }, true);
  const dias = cont(PA, r=>[(r.data_entrada||'').slice(0,10)||'—']).filter(d=>d[0]!=='—').sort((a,b)=>a[0].localeCompare(b[0]));
  colunas($('#g-dias'), dias, d=>diaMes(d));
  const ultimoDia = dias.length ? dias[dias.length-1][0] : '';
  const horas = ultimoDia ? cont(PA.filter(r=>(r.data_entrada||'').startsWith(ultimoDia)), r=>[(r.data_entrada||'').slice(11,13)+'h']).sort((a,b)=>a[0].localeCompare(b[0])) : [];
  colunas($('#g-horas'), horas);
  $('#g-horas-nota').textContent = ultimoDia ? `${fmtData(ultimoDia)}: ${fmtN(dias[dias.length-1][1])} registos (${pct(dias[dias.length-1][1], PA.length)}% do total), por hora de entrada.` : '';
  barras($('#g-tema'), cont(PA, temasPA).slice(0,16), tm => { irPara('pa'); filtrarTema(tm); });
  barras($('#g-tipo'), cont(PA, r=>[r.tipo_ar||'—']));
  const hoje = new Date().toISOString().slice(0,10);
  let cal = E.calendario || [];
  if (!cal.length && PA.length) {
    const entradas = PA.map(r=>r.data_entrada).filter(Boolean).sort(), vot = PA.map(r=>r.data_votacao).filter(Boolean).sort(), plen = PA.filter(r=>r.sede_votacao==='Plenário').map(r=>r.data_votacao).filter(Boolean).sort();
    cal = [{data:entradas[0], momento:`primeira PA registada pela AR (${entradas[0].slice(11,16).replace(':','h')})`}, {data:entradas[entradas.length-1], momento:`última PA registada pela AR (${entradas[entradas.length-1].slice(11,16).replace(':','h')})`}];
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
    `<div style="margin-bottom:10px"><b>De onde vêm os dados</b><br><span class="mini">${ligDA}. Um registo por PA (ou parte de PA): número, data e hora de entrada, título, artigo e epígrafe, diplomas alterados, tema, tipo, incidência, estado, proponentes, requerimentos, pedidos de parecer às Regiões Autónomas e todas as votações com o sentido de voto de cada grupo parlamentar.</span></div>` +
    linhaFonte('Estado dos dados abertos (fonte principal)', EF.dados_abertos, f => f.disponivel
      ? `${fmtN(f.pa||0)} PA (${fmtN(f.registos||0)} registos) · última entrada: ${esc(hm(f.ultima_entrada))} · ficheiro atualizado pela AR: ${esc(f.ultima_modificacao_ar||'—')} · verificado: ${esc(hm(f.momento))}`
      : `Ficheiro do OE ${ANO} ainda não publicado · verificado: ${esc(hm(f.momento))}`) +
    (concluido ? '' : (EF.portal && EF.portal.desativada) ? `<div style="margin-bottom:10px"><b>Portal da AR, página de cada proposta (reserva)</b><br><span class="mini">Desativada nesta edição: na nova aplicação de inserção de PA da AR, os identificadores recomeçam em 1 e a página de detalhe abre propostas de anos anteriores. Os dados abertos estão publicados e atualizados; cada PA liga ao respetivo PDF.</span></div><div style="margin-bottom:10px"><b>Artigo da proposta de lei</b><br><span class="mini">Só é mostrado o artigo associado pela AR cujo número e epígrafe coincidem com o texto da proposta de lei. Algumas PA chegam ligadas a artigos de Orçamentos anteriores (por exemplo, «Artigo 1.º – Aprovação» do OE 2006); nesses casos o artigo fica em branco e o artigo visado consta do título da PA.</span></div>` : linhaFonte('Portal da AR, página de cada proposta (reserva)', EF.portal, f =>
      `PA novas nesta verificação: ${fmtN(f.novos||0)} · atualizadas: ${fmtN(f.relidos||0)} · identificadores verificados: ${esc(f.primeiro_id_testado)}–${esc(f.ultimo_id_testado)}${f.erro?` · <b>erro: ${esc(f.erro)}</b>`:''} · verificado: ${esc(hm(f.momento))}`));

  // ----- tabela de PA
  opts('#f-partido', proponentes);
  opts('#f-tema', cont(PA, temasPA).map(p=>p[0]).filter(x=>x!=='—'));
  opts('#f-tipo', cont(PA, r=>[r.tipo_ar||'']).map(p=>p[0]).filter(Boolean));
  opts('#f-incide', cont(PA, r=>[r.incide||'']).map(p=>p[0]).filter(Boolean));
  opts('#f-estado', cont(PA, r=>[r.estado||'']).map(p=>p[0]).filter(Boolean));
  $('#f-q').value = ''; ['#f-partido','#f-tema','#f-tipo','#f-incide','#f-estado','#f-extra'].forEach(s=>$(s).value='');
  render();

  // ----- por tema
  const temasLista = cont(PA, temasPA).map(p=>p[0]);
  barrasEmpilhadas($('#g-tema-2'), temasLista.map(tm => { const rs = PA.filter(r=>temasPA(r).includes(tm)); return [tm, porEstadoDe(rs), rs.length]; }), filtrarTema);
  $('#m-tema-res').innerHTML = temasLista.length ? `<tr><th>Tema</th>${ESTADOS.map(e=>`<th>${e}</th>`).join('')}<th>total</th><th>taxa de aprovação</th></tr>` + temasLista.map(tm => { const rs = PA.filter(r=>temasPA(r).includes(tm)); const m = porEstadoDe(rs); const v = rs.filter(r=>r.votos_por_partido).length; return `<tr><td style="text-align:left"><b>${esc(tm)}</b></td>${ESTADOS.map(e=>`<td class="num">${fmtN(m[e]||0)}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td><td class="num">${v?pct((m['aprovada']||0)+(m['aprovada parcialmente']||0), v)+'%':'—'}</td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  $('#m-tema-prop').innerHTML = temasLista.length ? `<tr><th>Tema</th>${proponentes.map(p=>`<th><span class="dot" style="background:${corGP(p)}"></span> ${esc(p)}</th>`).join('')}<th>total</th></tr>` + temasLista.map(tm => { const rs = PA.filter(r=>temasPA(r).includes(tm)); return `<tr><td style="text-align:left"><b>${esc(tm)}</b></td>${proponentes.map(p=>`<td class="num">${fmtN(rs.filter(r=>split(r.proponente).includes(p)).length)||'<span class="mini">·</span>'}</td>`).join('')}<td class="num"><b>${fmtN(rs.length)}</b></td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  opts('#f-pos-prop', proponentes); $('#f-pos-prop').value = '';
  renderPosicao();

  // ----- votações
  const nReq = PA.filter(r=>/avocação/.test(r.requerimentos||'')).length;
  $('#kpis-vot').innerHTML = [['PA votadas', votadas.length,''],['Aprovadas (total ou parcialmente)', aprov,'ok'],['Rejeitadas', porEstado['rejeitada']||0,'nok'],['Prejudicadas', porEstado['prejudicada']||0,'neu'],['Votadas em Plenário (avocação)', PA.filter(r=>r.sede_votacao==='Plenário').length,'neu'],['Requerimentos de avocação publicados', nReq,'neu'],['Por votar', porEstado['em apreciação']||0,'neu']].map(kpi).join('');
  $('#m-resultado').innerHTML = proponentes.length ? `<tr><th>Proponente</th>${ESTADOS.map(e=>`<th>${e}</th>`).join('')}<th>total</th><th>taxa de aprovação</th></tr>` + porProp.map(([p,m,t]) => { const v = PA.filter(r=>split(r.proponente).includes(p) && r.votos_por_partido).length; return `<tr><td style="text-align:left"><b><span class="dot" style="background:${corGP(p)}"></span> ${esc(p)}</b></td>${ESTADOS.map(e=>`<td class="num">${fmtN(m[e]||0)}</td>`).join('')}<td class="num"><b>${fmtN(t)}</b></td><td class="num">${v?pct((m['aprovada']||0)+(m['aprovada parcialmente']||0), v)+'%':'—'}</td></tr>`; }).join('') : '<tr><td class="mini">Sem dados.</td></tr>';
  const sent = {}; for (const r of votadas) for (const v of split(r.votos_por_partido)) { const [gp, s] = v.split(':').map(x=>x.trim()); if(!gp||!s) continue; sent[gp] = sent[gp]||{Favor:0,Contra:0,'Abstenção':0,Ausente:0}; if (sent[gp][s]!==undefined) sent[gp][s]++; }
  const gpsVot = D.partidos.concat(Object.keys(sent).filter(g=>!D.partidos.includes(g))).filter(g=>sent[g]);
  $('#m-sentido').innerHTML = gpsVot.length ? `<tr><th>Grupo parlamentar</th><th>Favor</th><th>Contra</th><th>Abstenção</th><th>Ausente</th><th>votações</th></tr>` + gpsVot.map(g => { const s=sent[g], n=s.Favor+s.Contra+s['Abstenção']+s.Ausente; return `<tr><td style="text-align:left"><b><span class="dot" style="background:${corGP(g)}"></span> ${esc(g)}</b></td><td class="num f">${fmtN(s.Favor)}</td><td class="num c">${fmtN(s.Contra)}</td><td class="num a">${fmtN(s['Abstenção'])}</td><td class="num">${fmtN(s.Ausente)}</td><td class="num">${fmtN(n)}</td></tr>`; }).join('') : '<tr><td class="mini">Ainda sem votações registadas pela AR.</td></tr>';
  const cruz = sentidos(votadas, r=>split(r.proponente));
  matrizCalor($('#m-cruzado'), proponentes.filter(p=>cruz[p]), gpsVot.filter(g=>D.partidos.includes(g)), (l,c)=>cruz[l]&&cruz[l][c], 'Ainda sem votações registadas pela AR.', true);
  segAtivo = 0; renderRes();

  // ----- documentos, histórico, fontes
  $('#tab-docs tbody').innerHTML = (E.documentos||[]).map(d => `<tr><td><a href="${esc(d.url)}" target="_blank" rel="noopener">${esc(d.titulo)}</a></td><td class="num">${esc(hm(d.primeira_captura))}</td></tr>`).join('') || '<tr><td colspan="2" class="mini">Ainda sem documentos publicados.</td></tr>';
  $('#tab-hist tbody').innerHTML = E.historico.map(h => `<tr><td class="num">${esc((h.momento||'').replace('T',' ').slice(0,16))}</td><td class="num"><b>${esc(h.n_pa)}</b></td><td><span class="chip ${({nova:'ok','ausente da fonte':'ret'})[h.evento]||''}">${esc(h.evento)}</span></td><td>${esc(h.detalhe)}</td><td class="mini">${esc(h.fonte)}</td></tr>`).join('') || '<tr><td colspan="5" class="mini">Sem eventos.</td></tr>';
  const nomes = {pesquisa_pa:'Pesquisa de propostas de alteração', url_iniciativa:`${E.designacao} — detalhe da iniciativa`, url_texto_ppl:'Texto da proposta de lei com legislação citada', url_calendario:`Calendário de apreciação do OE ${ANO} (COFAP)`, url_cofap:`Página do OE ${ANO} na Comissão de Orçamento, Finanças e Administração Pública`, dados_abertos_pagina_oe:'Dados abertos — categoria Orçamento do Estado', dados_abertos_pasta_xvii:'Dados abertos — pasta XVII Legislatura'};
  $('#lista-fontes').innerHTML = `<li><b>Fonte principal:</b> ${ligDA}.</li>` + Object.entries({...D.fontes, ...E.urls}).filter(([k,v])=>nomes[k] && String(v).startsWith('http')).map(([k,v])=>`<li><a href="${esc(v)}" target="_blank" rel="noopener">${esc(nomes[k])}</a></li>`).join('') + (E.excel ? `<li><a href="${esc(E.excel)}" download>Base completa em Excel (dados da AR), gerada em cada captura</a></li>` : '');
}

function filtrar() {
  const q=$('#f-q').value.trim().toLowerCase(), p=$('#f-partido').value, t=$('#f-tema').value, tp=$('#f-tipo').value, inc=$('#f-incide').value, e=$('#f-estado').value, x=$('#f-extra').value;
  const extra = {avocacao: r=>r.avocacao==='S', req: r=>!!r.requerimentos, ra: r=>!!r.parecer_ra, diplomas: r=>!!r.diplomas, partes: r=>!!r.parte, semvoto: r=>['aprovada','aprovada parcialmente','rejeitada','prejudicada'].includes(r.estado) && !r.votos_por_partido}[x];
  return PA.filter(r =>
    (!q || [r.n_pa,r.objeto,r.artigo,r.artigo_epigrafe,r.diplomas,r.proponente_deputados].join(' ').toLowerCase().includes(q)) &&
    (!p || split(r.proponente).includes(p)) && (!t || temasPA(r).includes(t)) && (!tp || r.tipo_ar===tp) && (!inc || r.incide===inc) && (!e || r.estado===e) && (!extra || extra(r)));
}
const outrosAR = r => [r.artigo_epigrafe?`Epígrafe: ${esc(r.artigo_epigrafe)}`:'', r.diplomas?`Diplomas: ${esc(r.diplomas)}`:'', r.requerimentos?`Requerimentos: ${esc(r.requerimentos)}`:'', r.parecer_ra?`Parecer pedido: ${esc(r.parecer_ra)}`:'', r.ministerio_ar?`Ministério (AR): ${esc(r.ministerio_ar)}`:'', r.ausente_da_fonte?`<b>Ausente da fonte desde ${esc(fmtData(r.ausente_da_fonte))}</b>`:''].filter(Boolean).join('<br>') || '—';
function render() {
  const rows = filtrar().sort((x,y)=>{ if(ordem.k==='n_pa'){ const c=ordemPA(x,y); return ordem.asc?c:-c; } const c=String(x[ordem.k]||'').localeCompare(String(y[ordem.k]||''),'pt'); return ordem.asc?c:-c; });
  $('#f-n').textContent = `${fmtN(rows.length)} de ${fmtN(PA.length)} registos`;
  $('#tab-pa tbody').innerHTML = rows.slice(0,3000).map(r => `<tr>
    <td class="num"><b>${esc(r.n_pa)}</b></td>
    <td class="num">${esc(fmtData(r.data_entrada))}<br><span class="mini">${esc((r.data_entrada||'').slice(11,16))}</span></td>
    <td class="prop">${split(r.proponente).map(gpChip).join(' ')||'—'}${r.proponente_deputados?`<br><span class="mini">${esc(r.proponente_deputados)}</span>`:''}</td>
    <td>${esc(r.artigo)||'—'}<br><span class="mini">${esc(r.incide)}${r.apresentada?' · '+esc(r.apresentada):''}</span></td>
    <td class="mini">${esc(r.tipo_ar)}</td>
    <td class="obj">${esc(r.objeto)}</td>
    <td class="mini">${esc(temaDe(r))}</td>
    <td>${estadoChip(r.estado)}<br><span class="mini">${esc(r.estado_ar)}</span></td>
    <td class="mini votos">${r.resultado_votacao?`${esc(fmtData(r.data_votacao))}${r.sede_votacao?' · '+esc(r.sede_votacao):''}${r.n_votacoes>1?` · ${r.n_votacoes} votações`:''}<br>${votosHTML(r.votos_por_partido)}`:'—'}</td>
    <td class="mini outros">${outrosAR(r)}</td>
    <td class="mini">${r.url_detalhe?`<a href="${esc(r.url_detalhe)}" target="_blank" rel="noopener">AR</a>`:''}${r.url_pdf?` · <a href="${esc(r.url_pdf)}" target="_blank" rel="noopener">PDF</a>`:''}</td>
  </tr>`).join('') + (rows.length>3000?`<tr><td colspan="11" class="mini">Mostram-se 3 000 de ${fmtN(rows.length)} registos. Afine os filtros ou exporte.</td></tr>`:'') || '<tr><td colspan="11" class="mini">Sem registos.</td></tr>';
}
document.querySelectorAll('#t-pa .filtros select, #t-pa .filtros input').forEach(el => el.addEventListener('input', render));
document.querySelectorAll('#tab-pa th[data-k]').forEach(th => th.addEventListener('click', () => { const k=th.dataset.k; ordem = {k, asc: ordem.k===k ? !ordem.asc : true}; render(); }));
const COLS_EXP = [['n_pa','N.º PA'],['pa_base','N.º base'],['parte','Parte'],['id_ar','ID AR'],['data_entrada','Data e hora de entrada'],['proponente','Proponente'],['proponente_deputados','Deputados'],['apresentada','Apresentada'],['incide','Incide'],['artigo','Artigo / mapa'],['artigo_epigrafe','Epígrafe do artigo'],['diplomas','Diplomas alterados'],['tipo_ar','Tipo'],['objeto','Objeto'],['tema_ar','Tema (AR)'],['estado','Estado'],['estado_ar','Estado (AR)'],['data_votacao','Data da votação'],['sede_votacao','Sede da votação'],['resultado_votacao','Resultado da votação'],['votos_por_partido','Sentido de voto por grupo parlamentar'],['avocacao','Avocação'],['requerimentos','Requerimentos'],['parecer_ra','Parecer Regiões Autónomas'],['ministerio_ar','Ministério (AR)'],['n_votacoes','N.º de votações'],['url_detalhe','Ligação AR'],['url_pdf','PDF'],['primeira_captura','Primeira captura'],['ultima_captura','Última captura'],['fonte','Fonte'],['ausente_da_fonte','Ausente da fonte']];
function carregarXLSX() {
  return new Promise((ok, falha) => {
    if (window.XLSX) return ok();
    const s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js';
    s.onload = () => ok(); s.onerror = () => falha(new Error('biblioteca Excel indisponível'));
    document.head.appendChild(s);
  });
}
async function exportarExcel() {
  const b = $('#b-exp'), txt = b.textContent;
  b.disabled = true; b.textContent = 'A preparar o Excel…';
  try {
    await carregarXLSX();
    const linhas = filtrar().sort(ordemPA).map(r => Object.fromEntries(COLS_EXP.map(([k,l]) => {
      let v = r[k] ?? '';
      if (['data_entrada','primeira_captura','ultima_captura'].includes(k) && v) v = v.replace('T',' ').replace('Z','').slice(0,16);
      if (['parte','n_votacoes','id_ar'].includes(k) && v !== '' && !isNaN(+v)) v = +v;
      return [l, v];
    })));
    const ws = XLSX.utils.json_to_sheet(linhas, {header: COLS_EXP.map(c=>c[1])});
    ws['!cols'] = COLS_EXP.map(([k]) => ({wch: {objeto:60, votos_por_partido:50, proponente_deputados:30, tema_ar:30, artigo_epigrafe:35, diplomas:35, requerimentos:35, url_detalhe:30, url_pdf:30}[k] || 14}));
    ws['!autofilter'] = {ref: ws['!ref']};
    const filtros = [['Pesquisa', $('#f-q').value], ['Proponente', $('#f-partido').value], ['Tema (AR)', $('#f-tema').value], ['Tipo', $('#f-tipo').value], ['Incide', $('#f-incide').value], ['Estado', $('#f-estado').value], ['Outros critérios', $('#f-extra').selectedOptions[0]?.value ? $('#f-extra').selectedOptions[0].textContent : '']].filter(f => f[1]);
    const info = XLSX.utils.aoa_to_sheet([
      [`Propostas de alteração ao Orçamento do Estado para ${ANO} — ${E.designacao}`],
      ['Fonte', 'Assembleia da República, dados abertos (categoria «Orçamento do Estado», XVII Legislatura)'],
      ['Exportado em', new Date().toLocaleString('pt-PT')],
      ['Dados de', (E.execucao||{}).momento ? E.execucao.momento.replace('T',' ').slice(0,16)+' UTC' : '—'],
      ['Registos exportados', linhas.length],
      ['Filtros aplicados', filtros.length ? filtros.map(f => f.join(': ')).join(' · ') : 'nenhum (todas as propostas)'],
      ['Tratamento', 'Área de Suporte à Decisão, Secretaria-Geral do Governo']
    ]);
    info['!cols'] = [{wch: 22}, {wch: 110}];
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Propostas');
    XLSX.utils.book_append_sheet(wb, info, 'Sobre esta exportação');
    XLSX.writeFile(wb, `PA_OE${ANO}_${filtros.length ? 'selecao' : 'todas'}_${new Date().toISOString().slice(0,10)}.xlsx`);
  } catch (e) {
    if (E.excel) { const a = document.createElement('a'); a.href = E.excel; a.download = ''; a.click(); alert('Não foi possível gerar a seleção neste momento: foi descarregada a base completa em Excel.'); }
    else alert('Não foi possível gerar o Excel neste momento.');
  } finally { b.disabled = false; b.textContent = txt; }
}
function renderPosicao() {
  const p = $('#f-pos-prop').value;
  const vot = PA.filter(r => r.votos_por_partido && (!p || split(r.proponente).includes(p)));
  const m = sentidos(vot, temasPA);
  const gps = D.partidos.filter(g => Object.values(m).some(l=>l[g]));
  const temas = Object.keys(m).sort((a,b)=>Object.values(m[b]).reduce((s,x)=>s+x.F+x.C+x.A,0)-Object.values(m[a]).reduce((s,x)=>s+x.F+x.C+x.A,0));
  matrizCalor($('#m-posicao'), temas, gps, (l,c)=>m[l]&&m[l][c], 'Ainda sem votações registadas pela AR.');
}
$('#f-pos-prop').addEventListener('input', renderPosicao);
function filtrarTema(tm) {
  ['#f-q','#f-partido','#f-tipo','#f-incide','#f-estado','#f-extra'].forEach(s=>$(s).value='');
  $('#f-tema').value = tm; render();
  document.getElementById('lista-pa').scrollIntoView({behavior:'smooth', block:'start'});
}
const GRUPOS_RES = [
  ['Aprovadas', r=>r.estado==='aprovada'||r.estado==='aprovada parcialmente'],
  ['Rejeitadas', r=>r.estado==='rejeitada'],
  ['Prejudicadas', r=>r.estado==='prejudicada'],
  ['Retiradas ou não admitidas', r=>r.estado==='retirada'||r.estado==='não admitida'],
  ['Votadas em Plenário (avocação)', r=>r.sede_votacao==='Plenário'],
  ['Com mais de uma votação', r=>+r.n_votacoes>1],
  ['Por votar', r=>r.estado==='em apreciação'],
  ['Todas', r=>true]
];
function renderRes() {
  $('#seg-res').innerHTML = GRUPOS_RES.map(([l,f],i)=>`<button class="${i===segAtivo?'on':''}" onclick="segAtivo=${i};renderRes()">${esc(l)} (${fmtN(PA.filter(f).length)})</button>`).join('');
  const rows = PA.filter(GRUPOS_RES[segAtivo][1]).sort(ordemPA);
  $('#tab-res tbody').innerHTML = rows.slice(0,1500).map(r => `<tr><td class="num"><b>${esc(r.n_pa)}</b></td><td>${split(r.proponente).map(gpChip).join(' ')}</td><td>${esc(r.artigo)}</td><td class="obj">${esc(r.objeto)}</td><td class="mini">${esc(temaDe(r))}</td><td>${estadoChip(r.estado)}${r.sede_votacao==='Plenário'?'<br><span class="mini">em Plenário</span>':''}${+r.n_votacoes>1?`<br><span class="mini">${r.n_votacoes} votações</span>`:''}</td><td class="num">${esc(fmtData(r.data_votacao))}</td><td class="mini votos">${votosHTML(r.votos_por_partido)||'—'}</td></tr>`).join('')
    + (rows.length>1500?`<tr><td colspan="8" class="mini">Mostram-se 1 500 de ${fmtN(rows.length)} registos. Use a lista do separador «Propostas de alteração» para filtrar e exportar.</td></tr>`:'')
    || `<tr><td colspan="8" class="mini">Sem registos neste grupo.</td></tr>`;
}
montar();
const alvoHash = hash[1]==='temas' ? 'pa' : hash[1];
if (alvoHash && document.querySelector(`nav.tabs button[data-t="${alvoHash}"]:not([hidden])`)) irPara(alvoHash); else atualizarHash();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
