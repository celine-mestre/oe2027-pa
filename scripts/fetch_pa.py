#!/usr/bin/env python3
"""
Extração automática das propostas de alteração (PA) à PPL 110/XVII/2.ª (OE 2027)
a partir do parlamento.pt, com histórico de versões.

Fontes, por ordem de preferência:
  1. Dados abertos da AR — categoria "Orçamento do Estado", pasta "XVII Legislatura"
     (ficheiro JSON do OE 2027; URL em config.json → fontes.dados_abertos_json_oe2027).
  2. Reserva: página de pesquisa de PA (PesquisaPropAlteracao110XVII.aspx) e
     páginas de detalhe (DetalhePropostaAlteracao.aspx?BID=...).

Comandos:
  python scripts/fetch_pa.py opendata            # descarrega o JSON dos dados abertos e normaliza
  python scripts/fetch_pa.py opendata --url URL  # idem, com URL explícito (ex.: OE 2026 para calibrar)
  python scripts/fetch_pa.py scrape              # reserva: lê a página de pesquisa + detalhes
  python scripts/fetch_pa.py inspect FICHEIRO    # mostra a estrutura (chaves) de um JSON descarregado
  python scripts/fetch_pa.py normalize FICHEIRO  # normaliza um JSON já descarregado (sem rede)

Saídas (pasta data/):
  raw/AAAA-MM-DD_HHMM_<fonte>.json   snapshot bruto de cada execução (nunca apagado)
  pa.json / pa.csv                   base de dados normalizada (um registo por PA, última versão)
  historico.csv                      eventos: nova, substituída, retirada, estado alterado, votada
  ultima_execucao.json               metadados da última execução (fonte, contagens, erros)
"""
from __future__ import annotations

# O servidor app.parlamento.pt envia uma cadeia de certificados incompleta
# (falta o intermédio). Com 'truststore' o Python usa o repositório de
# certificados do sistema operativo, que resolve a cadeia; sem ele, o
# descarregamento pode falhar com erro de SSL. Tem de ser feito antes de
# importar 'requests'.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import argparse
import csv
import datetime as dt
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
RAW = DATA / "raw"
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
TAX = json.loads((DATA / "taxonomia.json").read_text(encoding="utf-8"))

# Campos da base de dados (ponto 6 do plano de ação). Os campos marcados como
# "manual" são preenchidos pela DACDP em data/classificacao_manual.csv e juntos
# pelo build_painel.py; aqui ficam vazios.
CAMPOS = [
    "n_pa",                 # N.º da PA (AR), ex. 1581C
    "bid",                  # identificador interno da AR (liga ao detalhe)
    "data_entrada",         # data de entrada
    "versao",               # original / substituição (derivado do histórico)
    "versao_anterior",      # n.º da PA substituída, se conhecido
    "proponente",           # partido(s) — sigla(s)
    "proponente_deputados", # deputados signatários
    "apresentada",          # Comissão / Plenário
    "incide",               # Articulado / Mapa
    "artigo",               # artigo ou mapa da PPL alterado/aditado/eliminado
    "tipo_ar",              # Aditamento/Substituição/Eliminação (Artigo PPL | Mapa)
    "objeto",               # texto do objeto (AR)
    "tema_ar",              # tema (comissão) atribuído pela AR
    "area_governativa_sug", # sugestão automática a partir do tema (taxonomia)
    "natureza_sug",         # sugestão automática: receita/despesa/norma/leg. avulsa/autorização
    "estado_ar",            # estado tal como publicado pela AR
    "estado",               # estado normalizado (em apreciação/aprovada/rejeitada/prejudicada/retirada/substituída)
    "data_votacao",
    "resultado_votacao",
    "votos_por_partido",    # "PSD:Contra; PS:Abstenção; ..."
    "avocacao",             # S/N/vazio — avocação a Plenário
    "url_detalhe",
    "url_pdf",
    "primeira_captura",     # data/hora em que a PA foi vista pela primeira vez
    "ultima_captura",
    "fonte",                # opendata | scrape
]

# ----------------------------------------------------------------------------
# utilitários
# ----------------------------------------------------------------------------

def agora() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def carimbo() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d_%H%M")


def http_get(url: str, *, binario: bool = False):
    """GET com requests; devolve texto (ou bytes)."""
    import requests  # importado aqui para que 'inspect' e 'normalize' funcionem sem rede

    h = CONFIG["http"]
    esperas = (0, 30, 60, 120)  # 3 novas tentativas com espera crescente (indisponibilidade transitória da AR)
    for i, espera in enumerate(esperas):
        if espera:
            print(f"... tentativa {i + 1}/{len(esperas)} dentro de {espera}s", file=sys.stderr)
            time.sleep(espera)
        try:
            r = requests.get(url, headers={"User-Agent": h["user_agent"]}, timeout=h["timeout"])
            r.raise_for_status()
            break
        except requests.RequestException as e:  # noqa: PERF203
            if i == len(esperas) - 1:
                raise
            print(f"... falhou: {e}", file=sys.stderr)
    time.sleep(h.get("pausa_entre_pedidos_seg", 1.0))
    if binario:
        return r.content
    # os ficheiros .txt dos dados abertos vêm em UTF-8 (por vezes com BOM)
    r.encoding = r.encoding or "utf-8"
    return r.text.lstrip("﻿")


def sigla_partido(nome: str) -> str:
    nome = (nome or "").strip()
    for sigla, variantes in TAX["partidos"].items():
        if nome in variantes or nome.lower() in [v.lower() for v in variantes]:
            return sigla
    return nome


def estado_normalizado(estado_ar: str) -> str:
    e = (estado_ar or "").strip().lower()
    if not e:
        return ""
    for norm, variantes in TAX["estados_ar"].items():
        for v in variantes:
            if e == v.lower():
                return norm
    for norm, chave in [("aprovada", "aprovad"), ("rejeitada", "rejeitad"), ("prejudicada", "prejudicad"),
                        ("retirada", "retirad"), ("substituída", "substitu")]:
        if chave in e:
            return norm
    return "em apreciação"


def natureza_sugerida(objeto: str, tipo_ar: str, incide: str) -> str:
    texto = f"{objeto or ''} {tipo_ar or ''}".lower()
    if (incide or "").lower().startswith("mapa"):
        return "despesa"
    for regra in TAX["natureza"]["regras_sugestao"]:
        if re.search(regra["padrao"], texto, flags=re.IGNORECASE):
            return regra["natureza"]
    return TAX["natureza"]["por_defeito"]


def area_sugerida(tema_ar: str) -> str:
    t = (tema_ar or "").strip().rstrip(";").strip()
    # a AR pode listar vários temas separados por ';'
    temas = [x.strip() for x in re.split(r";|\|", t) if x.strip()]
    areas: list[str] = []
    for tema in temas:
        for k, v in TAX["tema_para_area_governativa"].items():
            if tema.lower() == k.lower():
                areas.extend(v)
    areas = list(dict.fromkeys(areas))
    return "; ".join(areas) if areas else ""


def artigo_de(objeto: str, numero_artigo_novo: str = "") -> str:
    if numero_artigo_novo:
        return numero_artigo_novo.strip()
    m = re.match(r"\s*((?:Artigo|Art\.º|Mapa)\s+[0-9]+\.?º?(?:-[A-Z]+)?)", objeto or "", flags=re.IGNORECASE)
    return m.group(1) if m else ""


# ----------------------------------------------------------------------------
# 1. Dados abertos (JSON) — parser tolerante
# ----------------------------------------------------------------------------

def _get(d: dict, *chaves, default=""):
    """Devolve o primeiro valor não vazio entre várias chaves candidatas (insensível a maiúsculas)."""
    if not isinstance(d, dict):
        return default
    baixo = {k.lower(): v for k, v in d.items()}
    for c in chaves:
        v = baixo.get(c.lower())
        if v not in (None, "", [], {}):
            return v
    return default


def _lista(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        # alguns exports embrulham listas em {"pt_gov_ar_objectos_...": [...]}
        for x in v.values():
            if isinstance(x, list):
                return x
        return [v]
    return [v]


def encontrar_lista_pa(obj) -> list[dict]:
    """Procura recursivamente a lista de PA (lista de dicts com número + tipo/estado)."""
    melhores: list[dict] = []

    def parece_pa(d: dict) -> bool:
        ks = {k.lower() for k in d}
        tem_num = any(k in ks for k in ("numero", "número", "panumero", "nrpa", "numeropa", "num"))
        tem_tipo = any(k in ks for k in ("tipo", "estado", "objecto", "objeto", "tema"))
        return tem_num and tem_tipo

    def rec(o):
        nonlocal melhores
        if isinstance(o, list):
            if o and all(isinstance(x, dict) for x in o) and sum(parece_pa(x) for x in o) >= max(1, len(o) // 2):
                if len(o) > len(melhores):
                    melhores = o
                return
            for x in o:
                rec(x)
        elif isinstance(o, dict):
            for v in o.values():
                rec(v)

    rec(obj)
    return melhores


def normalizar_opendata(bruto, momento: str) -> list[dict]:
    lista = encontrar_lista_pa(bruto)
    registos = []
    for d in lista:
        proponentes = _lista(_get(d, "Proponentes", "GruposParlamentares", "GP", "Autores", "Partidos"))
        partidos, deputados = [], []
        for p in proponentes:
            if isinstance(p, dict):
                gp = _get(p, "GP", "GrupoParlamentar", "Partido", "sigla", "nome")
                dep = _get(p, "Deputado", "NomeDeputado", "nome")
                if gp:
                    partidos.append(sigla_partido(str(gp)))
                if dep and dep != gp:
                    deputados.append(str(dep))
            else:
                partidos.append(sigla_partido(str(p)))
        votacoes = _lista(_get(d, "Votacoes", "Votacao", "votacoes"))
        data_vot, res_vot, votos, avoc = "", "", [], ""
        for v in votacoes:
            if not isinstance(v, dict):
                continue
            data_vot = str(_get(v, "Data", "data", "DataVotacao")) or data_vot
            res_vot = str(_get(v, "Resultado", "resultado")) or res_vot
            for s in _lista(_get(v, "SentidoVoto", "Votos", "GruposParlamentares", "detalhe")):
                if isinstance(s, dict):
                    gp = sigla_partido(str(_get(s, "GP", "GrupoParlamentar", "Partido", "nome")))
                    sv = str(_get(s, "Sentido", "Voto", "sentido", "voto"))
                    if gp and sv:
                        votos.append(f"{gp}:{sv}")
                elif isinstance(s, str) and ":" in s:
                    votos.append(s)
            if "avoc" in json.dumps(v, ensure_ascii=False).lower():
                avoc = "S"
        objeto = str(_get(d, "Objecto", "Objeto", "Assunto", "Titulo", "Descricao"))
        tipo_ar = str(_get(d, "Tipo", "TipoPA", "tipo"))
        incide = str(_get(d, "Incide", "incide", "IncideSobre"))
        tema = str(_get(d, "Tema", "Temas", "tema"))
        estado_ar = str(_get(d, "Estado", "estado", "Situacao"))
        bid = str(_get(d, "BID", "Id", "ID", "id", "PAId", "paId"))
        n_pa = str(_get(d, "Numero", "Número", "PANumero", "NumeroPA", "num")).strip()
        registos.append({
            "n_pa": n_pa,
            "bid": bid,
            "data_entrada": str(_get(d, "Data", "DataEntrada", "data"))[:10],
            "versao": "",
            "versao_anterior": "",
            "proponente": "; ".join(dict.fromkeys(partidos)),
            "proponente_deputados": "; ".join(dict.fromkeys(deputados)),
            "apresentada": str(_get(d, "Apresentada", "ApresentadaEm", "Orgao")),
            "incide": incide,
            "artigo": artigo_de(objeto, str(_get(d, "NumeroArtigoNovo", "ArtigoNovo", "Artigo"))),
            "tipo_ar": tipo_ar,
            "objeto": objeto,
            "tema_ar": tema,
            "area_governativa_sug": area_sugerida(tema),
            "natureza_sug": natureza_sugerida(objeto, tipo_ar, incide),
            "estado_ar": estado_ar,
            "estado": estado_normalizado(estado_ar),
            "data_votacao": data_vot[:10],
            "resultado_votacao": res_vot,
            "votos_por_partido": "; ".join(votos),
            "avocacao": avoc,
            "url_detalhe": CONFIG["fontes"]["detalhe_pa"].format(bid=bid) if bid else "",
            "url_pdf": str(_get(d, "LinkPDF", "Ficheiro", "Documento", "url_pdf", "Link")),
            "primeira_captura": momento,
            "ultima_captura": momento,
            "fonte": "opendata",
        })
    return registos


def inspecionar(obj, prefixo: str = "", contador: Counter | None = None, nivel: int = 0) -> Counter:
    """Conta as chaves (caminhos) presentes num JSON — para calibrar o parser."""
    contador = contador if contador is not None else Counter()
    if nivel > 8:
        return contador
    if isinstance(obj, dict):
        for k, v in obj.items():
            contador[f"{prefixo}.{k}" if prefixo else k] += 1
            inspecionar(v, f"{prefixo}.{k}" if prefixo else k, contador, nivel + 1)
    elif isinstance(obj, list):
        for x in obj[:200]:
            inspecionar(x, prefixo + "[]", contador, nivel + 1)
    return contador


# ----------------------------------------------------------------------------
# 2. Reserva — scraping da página de pesquisa e dos detalhes
# ----------------------------------------------------------------------------

def _texto(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el is not None else ""


def listar_bids_pesquisa(url: str) -> list[dict]:
    """Lê a página de pesquisa (SharePoint/ASP.NET) e devolve [{bid, n_pa, data, ...}] de todas as páginas."""
    import requests
    from bs4 import BeautifulSoup

    h = CONFIG["http"]
    s = requests.Session()
    s.headers["User-Agent"] = h["user_agent"]
    vistos: dict[str, dict] = {}
    r = s.get(url, timeout=h["timeout"])
    r.raise_for_status()
    pagina = 1
    while True:
        soup = BeautifulSoup(r.text, "html.parser")
        novos = 0
        for a in soup.select("a[href*='DetalhePropostaAlteracao.aspx?BID=']"):
            m = re.search(r"BID=(\d+)", a["href"])
            if not m:
                continue
            bid = m.group(1)
            if bid not in vistos:
                vistos[bid] = {"bid": bid, "n_pa": _texto(a)}
                novos += 1
        # paginação ASP.NET: procurar um controlo "seguinte" com __doPostBack
        prox = None
        for a in soup.find_all("a", href=True):
            if "__doPostBack" in a["href"] and re.search(r"seguinte|next|›|»|>$", _texto(a), flags=re.IGNORECASE):
                prox = a
                break
        if not prox or novos == 0:
            break
        m = re.search(r"__doPostBack\('([^']+)'\s*,\s*'([^']*)'\)", prox["href"])
        if not m:
            break
        form = {i.get("name"): i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}
        form["__EVENTTARGET"], form["__EVENTARGUMENT"] = m.group(1), m.group(2)
        time.sleep(h.get("pausa_entre_pedidos_seg", 1.0))
        r = s.post(url, data=form, timeout=h["timeout"])
        r.raise_for_status()
        pagina += 1
        if pagina > 400:
            break
    return list(vistos.values())


def ler_detalhe(bid: str, momento: str) -> dict:
    """Lê uma página DetalhePropostaAlteracao.aspx?BID=... (estrutura verificada no OE 2025, BID 22660)."""
    from bs4 import BeautifulSoup

    url = CONFIG["fontes"]["detalhe_pa"].format(bid=bid)
    html = http_get(url)
    soup = BeautifulSoup(html, "html.parser")
    corpo = soup.find(id="contentBox") or soup
    texto = _texto(corpo)

    def campo(rotulo: str) -> str:
        m = re.search(rf"{rotulo}:\s*(.*?)(?=\s(?:Número|Data|Apresentada|Incide|Objecto|Objeto|Tema|Tipo|Número Artigo Novo|Estado|Deputado|Grupo Parlamentar|Votação|Votações|Iniciativas)\b:|$)", texto)
        return m.group(1).strip() if m else ""

    n_pa = campo("Número")
    objeto = campo("Objecto") or campo("Objeto")
    tipo_ar = campo("Tipo")
    incide = campo("Incide")
    tema = campo("Tema")
    estado_ar = campo("Estado")
    deputados, partidos = [], []
    for m in re.finditer(r"Deputado\s+(.+?)\s+Grupo Parlamentar/Partido\s+([A-Z\-/]+)", texto):
        deputados.append(m.group(1).strip())
        partidos.append(sigla_partido(m.group(2)))
    # partidos listados por extenso como proponentes
    for sigla, variantes in TAX["partidos"].items():
        for v in variantes:
            if len(v) > 4 and re.search(rf"Proponentes.*?\b{re.escape(v)}\b", texto):
                partidos.append(sigla)
    votos = []
    for sigla, variantes in TAX["partidos"].items():
        for v in variantes:
            if len(v) > 4:
                m = re.search(rf"{re.escape(v)}\s*\((Favor|Contra|Abstenção)\)", texto)
                if m:
                    votos.append(f"{sigla}:{m.group(1)}")
                    break
    mdata = re.search(r"Votaç(?:ão|ões).*?Data:?\s*(\d{4}-\d{2}-\d{2})", texto)
    mres = re.search(r"Resultado:?\s*([A-Za-zçãõ()\s]+?)(?=\s(?:Iniciativa|Proposta|Grupos|$))", texto)
    pdf = ""
    a = corpo.find("a", href=re.compile(r"doc\.pdf", re.IGNORECASE))
    if a:
        pdf = a["href"]
    return {
        "n_pa": n_pa, "bid": bid, "data_entrada": campo("Data")[:10], "versao": "", "versao_anterior": "",
        "proponente": "; ".join(dict.fromkeys(partidos)), "proponente_deputados": "; ".join(dict.fromkeys(deputados)),
        "apresentada": campo("Apresentada"), "incide": incide,
        "artigo": artigo_de(objeto, campo("Número Artigo Novo")), "tipo_ar": tipo_ar, "objeto": objeto,
        "tema_ar": tema, "area_governativa_sug": area_sugerida(tema),
        "natureza_sug": natureza_sugerida(objeto, tipo_ar, incide),
        "estado_ar": estado_ar, "estado": estado_normalizado(estado_ar),
        "data_votacao": mdata.group(1) if mdata else "", "resultado_votacao": mres.group(1).strip() if mres else "",
        "votos_por_partido": "; ".join(votos), "avocacao": "S" if re.search(r"avoca", texto, re.I) else "",
        "url_detalhe": url, "url_pdf": pdf, "primeira_captura": momento, "ultima_captura": momento, "fonte": "scrape",
    }


# ----------------------------------------------------------------------------
# 3. Base de dados e histórico de versões
# ----------------------------------------------------------------------------

def ler_bd() -> dict[str, dict]:
    f = DATA / "pa.json"
    if not f.exists():
        return {}
    return {r["n_pa"]: r for r in json.loads(f.read_text(encoding="utf-8"))}


def chave(r: dict) -> str:
    return r.get("n_pa") or f"BID{r.get('bid')}"


def raiz_numero(n_pa: str) -> str:
    """'1162P-2' → '1162P' (substituições mantêm o número base com sufixo)."""
    return re.sub(r"-\d+$", "", n_pa or "")


def fundir(bd: dict[str, dict], novos: list[dict], momento: str, fonte: str) -> list[dict]:
    """Atualiza a BD com os registos capturados e devolve os eventos do histórico."""
    eventos: list[dict] = []
    vistos = set()
    por_raiz: dict[str, list[str]] = {}
    for n in bd:
        por_raiz.setdefault(raiz_numero(n), []).append(n)

    for r in novos:
        k = chave(r)
        if not k:
            continue
        vistos.add(k)
        if k not in bd:
            r["primeira_captura"] = momento
            r["versao"] = "substituição" if re.search(r"-\d+$", k) else "original"
            if r["versao"] == "substituição":
                anteriores = por_raiz.get(raiz_numero(k), [])
                r["versao_anterior"] = "; ".join(anteriores)
                for ant in anteriores:
                    if bd[ant]["estado"] == "em apreciação":
                        bd[ant]["estado"] = "substituída"
                        eventos.append({"momento": momento, "n_pa": ant, "evento": "substituída", "detalhe": f"por {k}", "fonte": fonte})
            bd[k] = r
            eventos.append({"momento": momento, "n_pa": k, "evento": "nova", "detalhe": f"{r['proponente']} · {r['tipo_ar']} · {r['artigo']}", "fonte": fonte})
            por_raiz.setdefault(raiz_numero(k), []).append(k)
            continue
        antigo = bd[k]
        if antigo["estado_ar"] != r["estado_ar"] and r["estado_ar"]:
            eventos.append({"momento": momento, "n_pa": k, "evento": "estado alterado", "detalhe": f"{antigo['estado_ar'] or '—'} → {r['estado_ar']}", "fonte": fonte})
        if r["resultado_votacao"] and r["resultado_votacao"] != antigo["resultado_votacao"]:
            eventos.append({"momento": momento, "n_pa": k, "evento": "votada", "detalhe": f"{r['resultado_votacao']} ({r['votos_por_partido']})", "fonte": fonte})
        for c in CAMPOS:
            if c in ("primeira_captura", "versao", "versao_anterior"):
                continue
            if r.get(c) not in (None, ""):
                antigo[c] = r[c]
        antigo["ultima_captura"] = momento

    # PA que desapareceram da fonte: assinalar (não apagar)
    for k, r in bd.items():
        if k not in vistos and r.get("fonte") == fonte and r["estado"] == "em apreciação" and r["ultima_captura"] != momento:
            r["estado"] = "retirada"
            r["estado_ar"] = r["estado_ar"] or "ausente da fonte (retirada?)"
            eventos.append({"momento": momento, "n_pa": k, "evento": "retirada", "detalhe": "deixou de constar na fonte — confirmar na AR", "fonte": fonte})
    return eventos


def gravar_bd(bd: dict[str, dict], eventos: list[dict], meta: dict) -> None:
    DATA.mkdir(exist_ok=True)
    def ordem(r):
        m = re.match(r"(\d+)([A-Z]*)(?:-(\d+))?", r.get("n_pa") or "")
        return (int(m.group(1)) if m else 10**9, m.group(2) if m else "", int(m.group(3) or 0) if m else 0)
    regs = sorted(bd.values(), key=ordem)
    (DATA / "pa.json").write_text(json.dumps(regs, ensure_ascii=False, indent=1), encoding="utf-8")
    with (DATA / "pa.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore", delimiter=";")
        w.writeheader()
        w.writerows(regs)
    hist = DATA / "historico.csv"
    novo = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["momento", "n_pa", "evento", "detalhe", "fonte"], delimiter=";")
        if novo:
            w.writeheader()
        w.writerows(eventos)
    (DATA / "ultima_execucao.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def resumo(bd: dict[str, dict]) -> dict:
    por_partido = Counter()
    for r in bd.values():
        for p in (r["proponente"] or "—").split("; "):
            por_partido[p] += 1
    return {"total": len(bd), "por_partido": dict(por_partido.most_common()),
            "por_estado": dict(Counter(r["estado"] for r in bd.values()).most_common()),
            "por_tema": dict(Counter(r["tema_ar"] or "—" for r in bd.values()).most_common())}


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["opendata", "scrape", "inspect", "normalize"])
    ap.add_argument("ficheiro", nargs="?", help="JSON local (para inspect/normalize)")
    ap.add_argument("--url", help="URL do JSON dos dados abertos (substitui config.json)")
    ap.add_argument("--max", type=int, default=0, help="scrape: limitar n.º de detalhes (teste)")
    args = ap.parse_args(argv)

    momento = agora()
    RAW.mkdir(parents=True, exist_ok=True)
    meta = {"momento": momento, "comando": args.comando, "erros": []}

    if args.comando == "inspect":
        obj = json.loads(Path(args.ficheiro).read_text(encoding="utf-8-sig"))
        cont = inspecionar(obj)
        for k, n in sorted(cont.items()):
            print(f"{n:6d}  {k}")
        lista = encontrar_lista_pa(obj)
        print(f"\nLista de PA detetada: {len(lista)} elementos")
        if lista:
            print(json.dumps(lista[0], ensure_ascii=False, indent=1)[:4000])
        return 0

    if args.comando in ("opendata", "normalize"):
        if args.comando == "opendata":
            url = args.url or CONFIG["fontes"]["dados_abertos_json_oe2027"]
            if url.startswith("A_PREENCHER"):
                print("ERRO: falta o URL do JSON dos dados abertos em config.json (fontes.dados_abertos_json_oe2027).\n"
                      "Abrir a pasta 'XVII Legislatura' em https://www.parlamento.pt/Cidadania/Paginas/DAOE.aspx, "
                      "copiar o URL do ficheiro JSON do OE 2027 e colar no config.json.", file=sys.stderr)
                return 2
            txt = http_get(url)
            bruto = json.loads(txt)
            f_raw = RAW / f"{carimbo()}_opendata.json"
            f_raw.write_text(json.dumps(bruto, ensure_ascii=False), encoding="utf-8")
            meta["url"], meta["raw"] = url, str(f_raw)
        else:
            bruto = json.loads(Path(args.ficheiro).read_text(encoding="utf-8-sig"))
        novos = normalizar_opendata(bruto, momento)
        if not novos:
            meta["erros"].append("nenhuma PA reconhecida no JSON — correr 'inspect' e ajustar normalizar_opendata()")
            print(meta["erros"][-1], file=sys.stderr)
        bd = ler_bd()
        eventos = fundir(bd, novos, momento, "opendata")
        meta.update({"capturadas": len(novos), "eventos": len(eventos), "resumo": resumo(bd)})
        gravar_bd(bd, eventos, meta)
        print(json.dumps(meta, ensure_ascii=False, indent=1))
        return 0 if not meta["erros"] else 1

    if args.comando == "scrape":
        url = args.url or CONFIG["fontes"]["pesquisa_pa_oe2027"]
        try:
            lista = listar_bids_pesquisa(url)
        except Exception as e:  # noqa: BLE001
            meta["erros"].append(f"pesquisa: {e}")
            lista = []
        if args.max:
            lista = lista[: args.max]
        novos, falhas = [], []
        for i, item in enumerate(lista, 1):
            try:
                novos.append(ler_detalhe(item["bid"], momento))
            except Exception as e:  # noqa: BLE001
                falhas.append({"bid": item["bid"], "erro": str(e)})
            if i % 50 == 0:
                print(f"... {i}/{len(lista)} detalhes lidos", file=sys.stderr)
        (RAW / f"{carimbo()}_scrape.json").write_text(json.dumps(novos, ensure_ascii=False), encoding="utf-8")
        bd = ler_bd()
        eventos = fundir(bd, novos, momento, "scrape")
        meta.update({"url": url, "listadas": len(lista), "capturadas": len(novos), "falhas": falhas,
                     "eventos": len(eventos), "resumo": resumo(bd)})
        gravar_bd(bd, eventos, meta)
        print(json.dumps(meta, ensure_ascii=False, indent=1))
        return 0 if not meta["erros"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
