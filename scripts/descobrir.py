#!/usr/bin/env python3
"""
Descoberta e calibração (corre no GitHub Actions, que chega ao parlamento.pt).

1. Percorre a pasta «XVII Legislatura» da categoria «Orçamento do Estado» dos
   dados abertos da AR e lista todos os ficheiros publicados.
2. Descarrega os ficheiros JSON encontrados (OE 2026 e, se já existir, OE 2027),
   guarda a estrutura (chaves) e uma extração tabular das PA em data/calibracao/.
3. Descarrega o calendário oficial de apreciação do OE 2027 e páginas de
   referência (pesquisa e detalhe de PA do OE 2026, página da PPL 110/XVII).

Nada do que fica em data/calibracao/ entra na base de dados nem no painel do OE 2027.
"""
from __future__ import annotations

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import csv
import gzip
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pa as fp  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
OUT = RAIZ / "data" / "calibracao"
OUT.mkdir(parents=True, exist_ok=True)
CFG = fp.CONFIG
UA = {"User-Agent": CFG["http"]["user_agent"]}
LOG: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.append(msg)


def get(url: str, **kw) -> requests.Response:
    for espera in (0, 20, 60):
        if espera:
            time.sleep(espera)
        try:
            r = requests.get(url, headers=UA, timeout=180, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            log(f"  falhou ({e}); nova tentativa")
    raise RuntimeError(f"não foi possível obter {url}")


def listar_pasta(url: str, nivel: int = 0, vistos: set | None = None) -> list[dict]:
    vistos = vistos if vistos is not None else set()
    if url in vistos or nivel > 3:
        return []
    vistos.add(url)
    html = get(url).text
    soup = BeautifulSoup(html, "html.parser")
    corpo = soup.find(id="contentBox") or soup
    itens = []
    for a in corpo.find_all("a", href=True):
        href = urljoin(url, a["href"])
        nome = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        if "webutils" in href and "fich=" in href.lower():
            m = re.search(r"fich=([^&]+)", href, flags=re.I)
            itens.append({"tipo": "ficheiro", "nome": nome, "fich": m.group(1) if m else "", "url": href, "nivel": nivel})
        elif "DAOE.aspx" in href and "Path=" in href and href not in vistos:
            itens.append({"tipo": "pasta", "nome": nome, "url": href, "nivel": nivel})
            time.sleep(1)
            itens.extend(listar_pasta(href, nivel + 1, vistos))
    return itens


def main() -> int:
    resultado: dict = {"momento": fp.agora()}

    # 1. Pasta XVII dos dados abertos (OE)
    log("1. Dados abertos — pasta XVII Legislatura (Orçamento do Estado)")
    itens = listar_pasta(CFG["fontes"]["dados_abertos_pasta_xvii"])
    resultado["dados_abertos_xvii"] = itens
    for i in itens:
        log(f"  [{i['tipo']}] nível {i['nivel']}: {i['nome']} {i.get('fich', '')}")

    # 2. Ficheiros JSON
    for i in itens:
        if i["tipo"] != "ficheiro" or "json" not in (i["fich"] + i["nome"]).lower():
            continue
        etiqueta = re.sub(r"[^A-Za-z0-9]+", "_", i["fich"] or i["nome"]).strip("_")[:60]
        log(f"2. A descarregar {etiqueta}")
        try:
            r = get(i["url"])
        except RuntimeError as e:
            log(f"  ERRO: {e}")
            continue
        bruto_txt = r.content.decode("utf-8-sig", errors="replace")
        log(f"  {len(r.content) / 1e6:.1f} MB")
        gz = OUT / f"{etiqueta}.json.gz"
        if len(r.content) < 90e6:
            with gzip.open(gz, "wb") as fh:
                fh.write(bruto_txt.encode("utf-8"))
        try:
            obj = json.loads(bruto_txt)
        except json.JSONDecodeError as e:
            log(f"  JSON inválido: {e}")
            continue
        cont = fp.inspecionar(obj)
        (OUT / f"{etiqueta}_estrutura.txt").write_text(
            "\n".join(f"{n:7d}  {k}" for k, n in sorted(cont.items())), encoding="utf-8")
        lista = fp.encontrar_lista_pa(obj)
        log(f"  lista de PA detetada: {len(lista)} elementos")
        (OUT / f"{etiqueta}_exemplos.json").write_text(
            json.dumps(lista[:5], ensure_ascii=False, indent=1), encoding="utf-8")
        regs = fp.normalizar_opendata(obj, resultado["momento"])
        with (OUT / f"{etiqueta}_pa.csv").open("w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=fp.CAMPOS, extrasaction="ignore", delimiter=";")
            w.writeheader()
            w.writerows(regs)
        resultado.setdefault("ficheiros", {})[etiqueta] = {
            "mb": round(len(r.content) / 1e6, 2), "pa": len(regs),
            "por_data": dict(sorted(Counter(x["data_entrada"] for x in regs).items())),
            "campos_vazios": {c: sum(1 for x in regs if not x.get(c)) for c in fp.CAMPOS},
        }

    # 3. Calendário e páginas de referência
    refs = {
        "calendario_OE2027.pdf": CFG["ppl"]["url_calendario"],
        "ppl_110_XVII_detalhe.html": CFG["ppl"]["url_iniciativa"],
        "cofap_OE2027.html": CFG["ppl"]["url_cofap"],
        "pesquisa_pa_OE2026.html": CFG["fontes"]["pesquisa_pa_oe2026"],
        "pesquisa_pa_OE2027.html": CFG["fontes"]["pesquisa_pa_oe2027"],
        "oe_pagina_principal.html": "https://www.parlamento.pt/OrcamentoEstado/Paginas/oe.aspx",
    }
    for nome, url in refs.items():
        log(f"3. {nome}")
        try:
            r = requests.get(url, headers=UA, timeout=120)
            log(f"  HTTP {r.status_code}, {len(r.content)} bytes")
            if r.ok:
                (OUT / nome).write_bytes(r.content)
            resultado.setdefault("referencias", {})[nome] = {"url": url, "http": r.status_code}
        except requests.RequestException as e:
            log(f"  ERRO: {e}")
        time.sleep(1)

    # um detalhe de PA do OE 2026, a partir da página de pesquisa
    p = OUT / "pesquisa_pa_OE2026.html"
    if p.exists():
        bids = re.findall(r"DetalhePropostaAlteracao\.aspx\?BID=(\d+)", p.read_text(encoding="utf-8", errors="replace"))
        resultado["pesquisa_OE2026_bids_na_1a_pagina"] = len(set(bids))
        if bids:
            url = CFG["fontes"]["detalhe_pa"].format(bid=bids[0])
            r = requests.get(url, headers=UA, timeout=120)
            if r.ok:
                (OUT / f"detalhe_pa_OE2026_BID{bids[0]}.html").write_bytes(r.content)
                try:
                    resultado["detalhe_OE2026_lido"] = fp.ler_detalhe(bids[0], resultado["momento"])
                except Exception as e:  # noqa: BLE001
                    resultado["detalhe_OE2026_lido"] = f"erro: {e}"

    resultado["log"] = LOG
    (OUT / "descoberta.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
