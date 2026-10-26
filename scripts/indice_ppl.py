#!/usr/bin/env python3
"""
Índice dos artigos da Proposta de Lei do OE (texto publicado pela AR em app.parlamento.pt) e
sugestão de área governativa por artigo, a validar pela DACDP.

Lê data/oe<ano>/ppl.html (descarregado pelo workflow «Calibração») e escreve
data/oe<ano>/classificacao_artigos.csv com: artigo; epigrafe; capitulo; seccao; area; metodo; confianca; nota.

Linhas já existentes com metodo «dacdp» (validadas no ficheiro mestre) não são alteradas:
o script só preenche artigos novos ou com metodo «sugestão».

  python scripts/indice_ppl.py --ano 2027
  python scripts/indice_ppl.py --ano 2026 --ficheiro outro.html
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
AREAS = json.loads((RAIZ / "data" / "areas_governativas.json").read_text(encoding="utf-8"))
CAMPOS = ["artigo", "epigrafe", "capitulo", "seccao", "area", "metodo", "confianca", "nota"]

# Capítulos do articulado do OE que, pela sua natureza, cabem numa área (reserva quando a epígrafe não decide)
CAPITULOS = [
    (r"seguran[çc]a social", "Trabalho, Solidariedade e Segurança Social"),
    (r"finan[çc]as (locais|regionais)|autarquias|regi[õo]es aut[óo]nomas|transfer[êe]ncias para", "Economia e Coesão Territorial"),
    (r"trabalhadores|fun[çc][õo]es p[úu]blicas|administra[çc][ãa]o p[úu]blica", "Estado e Finanças"),
    (r"impostos?|fiscal|benef[íi]cios fiscais|tribut", "Estado e Finanças"),
    (r"disposi[çc][õo]es gerais|preliminares|disciplina or[çc]amental|execu[çc][ãa]o or[çc]amental|opera[çc][õo]es|d[íi]vida|tesouraria|financiamento|endividamento|empresas p[úu]blicas|entidades p[úu]blicas reclassificadas|aquisi[çc][ãa]o de servi[çc]os|consigna|car[áa]ter fiscal", "Estado e Finanças"),
    (r"sa[úu]de", "Saúde"),
    (r"educa[çc][ãa]o|ensino|ci[êe]ncia", "Educação, Ciência e Inovação"),
    (r"habita[çc][ãa]o|infraestruturas", "Infraestruturas e Habitação"),
    (r"ambiente|energia|clim", "Ambiente e Energia"),
    (r"cultura|juventude|desporto", "Cultura, Juventude e Desporto"),
    (r"justi[çc]a", "Justiça"),
    (r"defesa", "Defesa Nacional"),
    (r"seguran[çc]a interna|administra[çc][ãa]o interna", "Administração Interna"),
    (r"agricultura|\bmar\b", "Agricultura e Mar"),
    (r"economia|empresas|turismo", "Economia e Coesão Territorial"),
]


def texto_de_html(html: str) -> list[str]:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style"]):
            t.decompose()
        txt = soup.get_text("\n")
    except ImportError:
        txt = re.sub(r"<[^>]+>", "\n", html)
    linhas = [re.sub(r"\s+", " ", l).strip() for l in txt.splitlines()]
    return [l for l in linhas if l]


def indexar(linhas: list[str]) -> list[dict]:
    titulo = capitulo = seccao = ""
    artigos: list[dict] = []
    i = 0
    while i < len(linhas):
        l = linhas[i]
        if re.match(r"^T[ÍI]TULO\s+[IVXLC]+\b", l, re.I):
            titulo = l + ((" " + linhas[i + 1]) if i + 1 < len(linhas) and not re.match(r"^(CAP[ÍI]TULO|SEC[ÇC][ÃA]O|Artigo)\b", linhas[i + 1], re.I) else "")
            capitulo = seccao = ""
        elif re.match(r"^CAP[ÍI]TULO\s+[IVXLC]+\b", l, re.I):
            capitulo = l + ((" " + linhas[i + 1]) if i + 1 < len(linhas) and not re.match(r"^(SEC[ÇC][ÃA]O|Artigo)\b", linhas[i + 1], re.I) else "")
            seccao = ""
        elif re.match(r"^(SEC[ÇC][ÃA]O|SUBSEC[ÇC][ÃA]O)\s+[IVXLC]+\b", l, re.I):
            seccao = l + ((" " + linhas[i + 1]) if i + 1 < len(linhas) and not re.match(r"^Artigo\b", linhas[i + 1], re.I) else "")
        m = re.match(r"^Artigo\s+(\d{1,3})\.?\s*º(?:\s*-\s*([A-Z]{1,3}))?\s*$", l)
        if m:
            chave = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
            epigrafe = re.sub(r"^[\s\-–—]+", "", linhas[i + 1]) if i + 1 < len(linhas) else ""
            cap = (titulo + " · " + capitulo).strip(" ·")
            if not any(a["artigo"] == chave for a in artigos):  # o índice e o texto repetem os artigos
                artigos.append({"artigo": chave, "epigrafe": epigrafe[:160], "capitulo": cap[:160], "seccao": seccao[:120]})
        i += 1
    return artigos


def sugerir(a: dict) -> tuple[str, str, str]:
    """Área pela epígrafe (confiança alta), pela secção (média) ou pelo capítulo (baixa)."""
    if not a.get("epigrafe") or a["epigrafe"].startswith("["):
        return "", "", ""
    for campo, conf in (("epigrafe", "alta"), ("seccao", "média")):
        for area, padroes in AREAS["palavras_chave"].items():
            for p in padroes:
                if re.search(p, a.get(campo, ""), re.I):
                    return area, conf, f"{campo} · «{p}»"
    for p, area in CAPITULOS:
        if re.search(p, a.get("capitulo", "") + " " + a.get("seccao", ""), re.I):
            return area, "baixa", f"capítulo · «{p}»"
    return "", "", ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ano", default=CONFIG["edicao_ativa"])
    ap.add_argument("--ficheiro", default="")
    a = ap.parse_args(argv)
    pasta = RAIZ / CONFIG["edicoes"][str(a.ano)]["pasta"]
    f = Path(a.ficheiro) if a.ficheiro else pasta / "ppl.html"
    if not f.exists():
        print(f"sem texto da PPL em {f}: corra o workflow «Calibração» para o descarregar", file=sys.stderr)
        return 3
    html = f.read_text(encoding="utf-8", errors="replace")
    artigos = indexar(texto_de_html(html))
    saida = pasta / "classificacao_artigos.csv"
    existentes: dict[str, dict] = {}
    if saida.exists():
        with saida.open(encoding="utf-8-sig", newline="") as fh:
            existentes = {r["artigo"]: dict(r) for r in csv.DictReader(fh, delimiter=";")}
    linhas = []
    for art in artigos:
        ex = existentes.get(art["artigo"])
        if ex and ex.get("metodo") == "dacdp":
            linhas.append(ex)
            continue
        area, conf, nota = sugerir(art)
        linhas.append({**art, "area": area, "metodo": "sugestão" if area else "", "confianca": conf, "nota": nota})
    for k, ex in existentes.items():  # artigos só existentes na tabela (p. ex. mapas) mantêm-se
        if not any(l["artigo"] == k for l in linhas):
            linhas.append(ex)
    with saida.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
    n_sug = sum(1 for l in linhas if l.get("area"))
    print(json.dumps({"edicao": a.ano, "artigos": len(artigos), "com_sugestao": n_sug,
                      "validados_dacdp": sum(1 for l in linhas if l.get("metodo") == "dacdp")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
