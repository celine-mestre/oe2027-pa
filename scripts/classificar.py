#!/usr/bin/env python3
"""
Classificação SGGov das PA por área governativa (orgânica do XXV Governo).

Não é informação publicada pela AR. Cada registo fica com o método e a confiança
da classificação, e o painel e o Excel assinalam-na como «classificação SGGov».

Ordem de aplicação, por PA:
  1. dacdp     classificação da DACDP no ficheiro mestre (data/oe<ano>/analise.csv, coluna «Área Governativa»)
  2. artigo    tabela artigo → área da edição (data/oe<ano>/classificacao_artigos.csv), quando a PA altera,
               substitui ou elimina um artigo da PPL
  3. mapa      PA aos mapas: o programa orçamental identifica o ministério (areas_governativas.json → mapas)
  4. palavras  expressões no tema da AR e na epígrafe do artigo (confiança alta) ou só no objeto (média)
  5. —         «por classificar»

  python scripts/classificar.py              # edição ativa → data/oe2027/classificacao.csv
  python scripts/classificar.py --ano 2026
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
AREAS = json.loads((RAIZ / "data" / "areas_governativas.json").read_text(encoding="utf-8"))
CAMPOS = ["n_pa", "area", "metodo", "confianca", "justificacao"]


def ler_csv(f: Path) -> list[dict]:
    if not f.exists():
        return []
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=";")]


def chave_artigo(txt: str) -> str:
    """'Artigo 12.º-A' → '12-A'; 'Mapa 5' → 'Mapa 5'; outro → ''."""
    t = txt or ""
    m = re.search(r"\b(\d{1,3})\.?\s*º(?:\s*-\s*([A-Z]{1,3}))?", t)
    if m:
        return m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
    m = re.search(r"\bmapa\s+(\d{1,2})\b", t, re.I)
    return f"Mapa {m.group(1)}" if m else ""


def procurar(dicionario: dict[str, list[str]], texto: str) -> tuple[str, str]:
    for area, padroes in dicionario.items():
        for p in padroes:
            if re.search(p, texto, re.I):
                return area, p
    return "", ""


def classificar(regs: list[dict], tabela: dict[str, dict], dacdp: dict[str, str]) -> list[dict]:
    saida = []
    for r in regs:
        n = r["n_pa"]
        if dacdp.get(n):
            saida.append({"n_pa": n, "area": dacdp[n], "metodo": "dacdp", "confianca": "validada", "justificacao": "ficheiro mestre da DACDP"})
            continue
        ch = chave_artigo(r.get("artigo", ""))
        novo = bool(re.search(r"novo", r.get("tipo_ar", ""), re.I))
        if ch and not novo and ch in tabela and tabela[ch].get("area"):
            t = tabela[ch]
            saida.append({"n_pa": n, "area": t["area"], "metodo": "artigo", "confianca": t.get("confianca") or "alta",
                          "justificacao": f"artigo {ch} · {t.get('epigrafe', '')}".strip(" ·")})
            continue
        if re.search(r"mapa", (r.get("incide") or "") + " " + (r.get("artigo") or ""), re.I):
            area, p = procurar(AREAS["mapas"], f"{r.get('artigo', '')} {r.get('objeto', '')}")
            if area:
                saida.append({"n_pa": n, "area": area, "metodo": "mapa", "confianca": "alta", "justificacao": f"mapa · «{p}»"})
                continue
        forte = f"{r.get('tema_ar', '')} {tabela.get(ch, {}).get('epigrafe', '') if ch else ''}"
        area, p = procurar(AREAS["palavras_chave"], forte)
        if area:
            saida.append({"n_pa": n, "area": area, "metodo": "palavras", "confianca": "alta", "justificacao": f"tema/epígrafe · «{p}»"})
            continue
        area, p = procurar(AREAS["palavras_chave"], f"{r.get('objeto', '')} {r.get('artigo', '')}")
        if area:
            saida.append({"n_pa": n, "area": area, "metodo": "palavras", "confianca": "média", "justificacao": f"objeto · «{p}»"})
            continue
        saida.append({"n_pa": n, "area": "por classificar", "metodo": "", "confianca": "", "justificacao": ""})
    return saida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ano", default=CONFIG["edicao_ativa"])
    ap.add_argument("--pasta", default="", help="outra pasta de dados (testes)")
    a = ap.parse_args(argv)
    ed = CONFIG["edicoes"][str(a.ano)]
    pasta = Path(a.pasta) if a.pasta else RAIZ / ed["pasta"]
    f = pasta / "pa.json"
    regs = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    tabela = {t["artigo"]: t for t in ler_csv(pasta / "classificacao_artigos.csv") if t.get("artigo")}
    dacdp = {r["n_pa"]: r["area_governativa"].strip() for r in ler_csv(pasta / "analise.csv")
             if r.get("n_pa") and (r.get("area_governativa") or "").strip()}
    saida = classificar(regs, tabela, dacdp)
    with (pasta / "classificacao.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS, delimiter=";")
        w.writeheader()
        w.writerows(saida)
    met = Counter(s["metodo"] or "por classificar" for s in saida)
    print(json.dumps({"edicao": a.ano, "registos": len(saida), "por_metodo": dict(met),
                      "artigos_na_tabela": len(tabela), "dacdp": len(dacdp)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
