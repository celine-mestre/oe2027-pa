#!/usr/bin/env python3
"""
Extração das propostas de alteração (PA) à PPL 110/XVII/2.ª (OE 2027) a partir
da informação publicada pela Assembleia da República.

Fonte principal — dados abertos da AR, categoria «Orçamento do Estado», pasta
«XVII Legislatura»: ficheiro OEPropostasAlteracao<ano>Or_json.txt.
O ficheiro é localizado automaticamente em cada execução (os URL da AR têm
tokens no parâmetro «path»).

Reserva — página de pesquisa de PA da PPL e páginas de detalhe de cada PA.

Comandos:
  python scripts/fetch_pa.py opendata              # localiza o ficheiro do ano em config.json e extrai
  python scripts/fetch_pa.py scrape                # reserva (portal): lê todas as PA da página de pesquisa
  python scripts/fetch_pa.py verificar             # compara com a página de pesquisa e recupera as PA em falta
  python scripts/fetch_pa.py documentos            # documentos de votação na página da COFAP (guiões, resultados, textos)
  python scripts/fetch_pa.py normalize FICHEIRO    # extrai a partir de um JSON local (.json ou .json.gz)
  python scripts/fetch_pa.py listar                # lista os ficheiros da pasta XVII dos dados abertos

Saídas (por defeito em data/):
  raw/AAAA-MM-DD_HHMM_<fonte>.json.gz   cópia do que a AR publicou em cada captura
  pa.json / pa.csv                      um registo por PA (ou parte de PA), última versão publicada
  historico.csv                         eventos entre capturas: nova, estado alterado, votada, ausente da fonte
  ultima_execucao.json                  metadados da última captura
  estado_fontes.json                    estado de cada fonte (disponível, registos, atualização, PA em falta)
  documentos.json                       documentos de votação publicados pela COFAP
"""
from __future__ import annotations

# app.parlamento.pt envia uma cadeia de certificados incompleta; o truststore usa o
# repositório de certificados do sistema operativo, que a completa.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import argparse
import csv
import datetime as dt
import gzip
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
TAX = json.loads((RAIZ / "data" / "taxonomia.json").read_text(encoding="utf-8"))

# Campos: apenas informação publicada pela AR, mais metadados de captura.
CAMPOS = [
    "n_pa",                 # número publicado pela AR (ex.: 2076C, 2046C-1)
    "pa_base",              # número sem o sufixo de parte (2046C-1 → 2046C)
    "parte",                # n.º da parte quando a PA incide sobre vários artigos/alíneas (vazio se única)
    "id_ar",                # identificador interno da AR (BID)
    "data_entrada",         # data e hora de entrada (ISO)
    "proponente",           # grupo(s) parlamentar(es) / partido(s)
    "proponente_deputados", # deputados signatários
    "apresentada",          # Comissão / Plenário
    "incide",               # Articulado / Mapas
    "artigo",               # artigo da PPL ou de outro diploma
    "tipo_ar",              # Aditamento (Artigo PPL), Substituição, Eliminação, ...
    "objeto",               # título publicado
    "tema_ar",              # tema(s) atribuído(s) pela AR
    "estado_ar",            # estado tal como publicado
    "estado",               # estado agrupado
    "data_votacao",         # data da última votação
    "sede_votacao",         # Comissão / Plenário (última votação)
    "resultado_votacao",    # resultado completo da última votação
    "votos_por_partido",    # sentido de voto na última votação ("PSD:Contra; PS:Abstenção; ...")
    "avocacao",             # S quando houve votação em Plenário (avocação)
    "n_votacoes",           # número de votações registadas
    "url_detalhe",
    "url_pdf",
    "primeira_captura",
    "ultima_captura",
    "fonte",
]

# ----------------------------------------------------------------------------
# utilitários
# ----------------------------------------------------------------------------

def agora() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def carimbo() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%M")


def sessao():
    import requests

    s = requests.Session()
    s.headers["User-Agent"] = CONFIG["http"]["user_agent"]
    return s


def http_get(url: str, s=None):
    import requests

    s = s or sessao()
    esperas = (0, 30, 60, 120)
    for i, espera in enumerate(esperas):
        if espera:
            print(f"... nova tentativa dentro de {espera}s", file=sys.stderr)
            time.sleep(espera)
        try:
            r = s.get(url, timeout=CONFIG["http"]["timeout"])
            r.raise_for_status()
            time.sleep(CONFIG["http"].get("pausa_entre_pedidos_seg", 1.0))
            return r
        except requests.HTTPError as e:
            # 4xx (ex.: 404, página ainda não criada pela AR) não se resolve a repetir
            if e.response is not None and 400 <= e.response.status_code < 500:
                raise
            if i == len(esperas) - 1:
                raise
            print(f"... falhou: {e}", file=sys.stderr)
        except requests.RequestException as e:
            # falhas de rede, tempo esgotado: nova tentativa
            if i == len(esperas) - 1:
                raise
            print(f"... falhou: {e}", file=sys.stderr)


def sigla(nome: str) -> str:
    n = (nome or "").strip()
    for s, variantes in TAX["partidos"].items():
        if n.lower() in (v.lower() for v in variantes):
            return s
    return n


def estado_agrupado(estado_ar: str) -> str:
    e = (estado_ar or "").lower()
    if not e:
        return "em apreciação"
    for chave, grupo in TAX["estados"]:
        if chave in e:
            return grupo
    return "em apreciação"


def iso(data_ar: str) -> str:
    """'07/11/2025 20:00:00' → '2025-11-07T20:00'."""
    try:
        return dt.datetime.strptime(data_ar.strip(), "%d/%m/%Y %H:%M:%S").strftime("%Y-%m-%dT%H:%M")
    except (ValueError, AttributeError):
        return (data_ar or "").strip()


def limpo(txt: str) -> str:
    """Espaços, quebras de linha e tabulações reduzidos a um espaço."""
    return re.sub(r"\s+", " ", txt or "").strip()


def artigo_de_texto(txt: str) -> str:
    m = re.search(r"Artigo\s+\d+\.?º(?:-[A-Z]+)?", txt or "")
    return m.group(0) if m else ""


def como_lista(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


# ----------------------------------------------------------------------------
# 1. Dados abertos
# ----------------------------------------------------------------------------

def listar_pasta(url: str, s=None, nivel: int = 0, vistos: set | None = None) -> list[dict]:
    """Lista os ficheiros (e subpastas) de uma pasta dos dados abertos da AR."""
    from bs4 import BeautifulSoup

    s = s or sessao()
    vistos = vistos if vistos is not None else set()
    if url in vistos or nivel > 3:
        return []
    vistos.add(url)
    soup = BeautifulSoup(http_get(url, s).text, "html.parser")
    corpo = soup.find(id="contentBox") or soup
    itens = []
    for a in corpo.find_all("a", href=True):
        href = urljoin(url, a["href"])
        if "webutils" in href and "fich=" in href.lower():
            m = re.search(r"fich=([^&]+)", href, flags=re.I)
            itens.append({"fich": m.group(1) if m else "", "nome": a.get_text(" ", strip=True), "url": href})
        elif "DAOE.aspx" in href and "Path=" in href and href not in vistos:
            itens.extend(listar_pasta(href, s, nivel + 1, vistos))
    return itens


def localizar_ficheiro_pa(ano: int, s=None) -> dict | None:
    alvo = re.compile(rf"OEPropostasAlteracao{ano}\w*_json", re.I)
    for f in listar_pasta(CONFIG["fontes"]["dados_abertos_pasta_xvii"], s):
        if alvo.search(f["fich"]):
            return f
    return None


def normalizar_opendata(bruto: dict, momento: str) -> list[dict]:
    lista = bruto.get("PropostaDeAlteracao") if isinstance(bruto, dict) else None
    if lista is None:
        raise ValueError("estrutura inesperada: falta a chave 'PropostaDeAlteracao' — ver o tutorial da AR na pasta dos dados abertos")
    regs = []
    for p in como_lista(lista):
        n = (p.get("Numero") or "").strip()
        m = re.match(r"^(.*?)(?:-(\d+))?$", n)
        props = como_lista((p.get("Proponentes") or {}).get("Proponente"))
        gps = [sigla(x.get("GP_Partido", "")) for x in props if x.get("GP_Partido")]
        if not gps:
            gps = [sigla(x) for x in re.split(r",\s*", p.get("GrupoParlamentar_Partido") or "") if x]
        deps = [x.get("Deputado", "") for x in props if x.get("Deputado")]
        artigos = [a.get("Artigo", "") for a in como_lista((p.get("Iniciativas_Artigos") or {}).get("Iniciativa_Artigo")) if a]
        votacoes = sorted(como_lista((p.get("Votacoes") or {}).get("Votacao")), key=lambda v: iso(v.get("Data", "")))
        ult = votacoes[-1] if votacoes else {}
        g = ult.get("GruposParlamentares") or {}
        votos = [f"{sigla(gp)}:{vt}" for gp, vt in zip(como_lista(g.get("GrupoParlamentar")), como_lista(g.get("Voto")))]
        rc = ult.get("ResultadoCompleto") or ""
        bid = (p.get("ID") or "").strip()
        regs.append({
            "n_pa": n,
            "pa_base": m.group(1) if m else n,
            "parte": (m.group(2) or "") if m else "",
            "id_ar": bid,
            "data_entrada": iso(p.get("Data", "")),
            "proponente": "; ".join(dict.fromkeys(gps)),
            "proponente_deputados": "; ".join(dict.fromkeys(deps)),
            "apresentada": p.get("Apresentada") or "",
            "incide": p.get("Incide") or "",
            "artigo": p.get("NumeroArtigoNovo") or "; ".join(a for a in artigos if a),
            "tipo_ar": p.get("Tipo") or "",
            "objeto": limpo(p.get("Titulo")),
            "tema_ar": "; ".join(limpo(t) for t in (p.get("Tema") or "").split(";") if t.strip()),
            "estado_ar": p.get("Estado") or "",
            "estado": estado_agrupado(p.get("Estado") or ""),
            "data_votacao": iso(ult.get("Data", ""))[:10] if ult else "",
            "sede_votacao": "Plenário" if "plenário" in rc.lower() else ("Comissão" if "comissão" in rc.lower() else ""),
            "resultado_votacao": rc,
            "votos_por_partido": "; ".join(votos),
            "avocacao": "S" if any("plenário" in (v.get("ResultadoCompleto") or "").lower() for v in votacoes) else "",
            "n_votacoes": str(len(votacoes)),
            "url_detalhe": CONFIG["fontes"]["detalhe_pa"].format(bid=bid) if bid else "",
            "url_pdf": (p.get("Ficheiro") or "").replace("http://", "https://"),
            "primeira_captura": momento,
            "ultima_captura": momento,
            "fonte": "opendata",
        })
    return regs


# ----------------------------------------------------------------------------
# 2. Reserva — pesquisa e detalhe no portal
# ----------------------------------------------------------------------------

def _texto(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el is not None else ""


def listar_ids_pesquisa(url: str, s=None) -> list[str]:
    from bs4 import BeautifulSoup

    s = s or sessao()
    vistos: list[str] = []
    r = http_get(url, s)
    for _ in range(400):
        soup = BeautifulSoup(r.text, "html.parser")
        novos = [b for b in dict.fromkeys(re.findall(r"DetalhePropostaAlteracao\.aspx\?BID=(\d+)", r.text)) if b not in vistos]
        vistos.extend(novos)
        prox = next((a for a in soup.find_all("a", href=True)
                     if "__doPostBack" in a["href"] and re.search(r"seguinte|próxima|next|>|»", _texto(a), re.I)), None)
        if not prox or not novos:
            break
        m = re.search(r"__doPostBack\('([^']+)'\s*,\s*'([^']*)'\)", prox["href"])
        if not m:
            break
        form = {i.get("name"): i.get("value", "") for i in soup.select("input[type=hidden]") if i.get("name")}
        form["__EVENTTARGET"], form["__EVENTARGUMENT"] = m.group(1), m.group(2)
        time.sleep(CONFIG["http"].get("pausa_entre_pedidos_seg", 1.0))
        r = s.post(url, data=form, timeout=CONFIG["http"]["timeout"])
        r.raise_for_status()
    return vistos


def ler_detalhe(bid: str, momento: str, s=None) -> dict:
    """Lê DetalhePropostaAlteracao.aspx?BID=… e devolve um registo no mesmo formato."""
    from bs4 import BeautifulSoup

    url = CONFIG["fontes"]["detalhe_pa"].format(bid=bid)
    soup = BeautifulSoup(http_get(url, s).text, "html.parser")
    corpo = soup.find(id="contentBox") or soup
    t = _texto(corpo)
    rotulos = ["Número", "Data", "Apresentada", "Incide", "Objecto", "Objeto", "Tema", "Tipo", "Número Artigo Novo", "Estado"]

    def campo(r):
        m = re.search(rf"\b{r}:\s*(.*?)(?=\s(?:{'|'.join(rotulos)}|Proponentes|Deputado|Grupo Parlamentar|Iniciativas|Votaç)\b:?|$)", t)
        return m.group(1).strip().rstrip(";") if m else ""

    n = campo("Número")
    m = re.match(r"^(.*?)(?:-(\d+))?$", n)
    deps = re.findall(r"Deputado\s+(.+?)\s+Grupo Parlamentar/Partido\s+([A-Z]{1,6}(?:-[A-Z]{1,3})?)\b", t)
    votos = []
    for s_, variantes in TAX["partidos"].items():
        for v in variantes:
            mm = re.search(rf"{re.escape(v)}\s*\((Favor|Contra|Abstenção|Ausência)\)", t)
            if mm and len(v) > 4:
                votos.append(f"{s_}:{mm.group(1)}")
                break
    estado_ar = campo("Estado")
    a = corpo.find("a", href=re.compile(r"doc\.pdf", re.I))
    mdata = re.search(r"Votaç(?:ão|ões).*?(\d{4}-\d{2}-\d{2})", t)
    return {
        "n_pa": n, "pa_base": m.group(1) if m else n, "parte": (m.group(2) or "") if m else "", "id_ar": bid,
        "data_entrada": campo("Data"), "proponente": "; ".join(dict.fromkeys(sigla(g.strip()) for _, g in deps)),
        "proponente_deputados": "; ".join(dict.fromkeys(d for d, _ in deps)), "apresentada": campo("Apresentada"),
        "incide": campo("Incide"), "artigo": campo("Número Artigo Novo") or artigo_de_texto(campo("Objecto") or campo("Objeto")),
        "tipo_ar": campo("Tipo"), "objeto": limpo(campo("Objecto") or campo("Objeto")),
        "tema_ar": "; ".join(x.strip() for x in campo("Tema").split(";") if x.strip()), "estado_ar": estado_ar,
        "estado": estado_agrupado(estado_ar), "data_votacao": mdata.group(1) if mdata else "",
        "sede_votacao": "Plenário" if "plenário" in estado_ar.lower() else ("Comissão" if "comissão" in estado_ar.lower() else ""),
        "resultado_votacao": estado_ar if votos else "", "votos_por_partido": "; ".join(votos),
        "avocacao": "S" if "plenário" in estado_ar.lower() else "", "n_votacoes": "",
        "url_detalhe": url, "url_pdf": a["href"] if a else "", "primeira_captura": momento,
        "ultima_captura": momento, "fonte": "scrape",
    }


# ----------------------------------------------------------------------------
# 3. Base de dados e histórico
# ----------------------------------------------------------------------------

def ordem(r: dict):
    m = re.match(r"(\d+)([A-Z]*)(?:-(\d+))?", r.get("n_pa") or "")
    return (int(m.group(1)) if m else 10**9, m.group(2) if m else "", int(m.group(3) or 0) if m else 0)


def ler_bd(pasta: Path) -> dict[str, dict]:
    f = pasta / "pa.json"
    return {r["n_pa"]: r for r in json.loads(f.read_text(encoding="utf-8"))} if f.exists() else {}


def fundir(bd: dict[str, dict], novos: list[dict], momento: str, fonte: str, marcar_ausentes: bool = True) -> list[dict]:
    eventos, vistos = [], set()
    for r in novos:
        k = r["n_pa"]
        if not k:
            continue
        vistos.add(k)
        if k not in bd:
            bd[k] = r
            eventos.append({"momento": momento, "n_pa": k, "evento": "nova",
                            "detalhe": f"{r['proponente']} · {r['tipo_ar']} · {r['objeto'][:80]}", "fonte": fonte})
            continue
        antigo = bd[k]
        if r["estado_ar"] and r["estado_ar"] != antigo["estado_ar"]:
            eventos.append({"momento": momento, "n_pa": k, "evento": "estado alterado",
                            "detalhe": f"{antigo['estado_ar'] or '—'} → {r['estado_ar']}", "fonte": fonte})
        if r["n_votacoes"] and r["n_votacoes"] != antigo.get("n_votacoes"):
            eventos.append({"momento": momento, "n_pa": k, "evento": "votada",
                            "detalhe": f"{r['resultado_votacao']} · {r['votos_por_partido']}", "fonte": fonte})
        for c in CAMPOS:
            if c != "primeira_captura" and r.get(c) not in (None, ""):
                antigo[c] = r[c]
        antigo["ultima_captura"] = momento
        antigo.pop("ausente_da_fonte", None)
    for k, r in bd.items():
        if marcar_ausentes and k not in vistos and r.get("fonte") == fonte and not r.get("ausente_da_fonte"):
            r["ausente_da_fonte"] = momento
            eventos.append({"momento": momento, "n_pa": k, "evento": "ausente da fonte",
                            "detalhe": "deixou de constar na publicação da AR — confirmar no parlamento.pt", "fonte": fonte})
    return eventos


def gravar(pasta: Path, bd: dict[str, dict], eventos: list[dict], meta: dict | None) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    regs = sorted(bd.values(), key=ordem)
    (pasta / "pa.json").write_text(json.dumps(regs, ensure_ascii=False, indent=0), encoding="utf-8")
    with (pasta / "pa.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS + ["ausente_da_fonte"], extrasaction="ignore", delimiter=";")
        w.writeheader()
        w.writerows(regs)
    h = pasta / "historico.csv"
    novo = not h.exists()
    with h.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["momento", "n_pa", "evento", "detalhe", "fonte"], delimiter=";")
        if novo:
            w.writeheader()
        w.writerows(eventos)
    if meta is not None:
        (pasta / "ultima_execucao.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


def atualizar_estado(pasta: Path, fonte: str, dados: dict) -> None:
    """Regista em estado_fontes.json o resultado mais recente de cada fonte."""
    f = pasta / "estado_fontes.json"
    estado = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    estado[fonte] = dados
    f.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")


def chave_documento(d: dict) -> str:
    """O URL da AR muda a cada visita (token no parâmetro path); identifica-se o documento pelo título e pelo nome do ficheiro."""
    m = re.search(r"fich=([^&]+)", d.get("url", ""), re.I)
    return f"{d.get('titulo', '').strip().lower()}|{(m.group(1) if m else '').lower()}"


def ler_documentos(url: str, s=None) -> list[dict]:
    """Ligações a documentos de votação na página do OE na COFAP (guiões, resultados, textos finais, relatórios)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(http_get(url, s).text, "html.parser")
    corpo = soup.find(id="contentBox") or soup
    padrao = re.compile(r"gui[ãa]o|vota[çc]|s[úu]mula|texto final|relat[óo]rio|parecer|reda[çc][ãa]o final|avoca", re.I)
    docs = []
    for a in corpo.find_all("a", href=True):
        titulo = _texto(a)
        if titulo and padrao.search(titulo) and not re.search(r"contributo", titulo, re.I) and re.search(r"doc\.pdf|\.pdf|webutils", a["href"], re.I):
            docs.append({"titulo": titulo, "url": urljoin(url, a["href"])})
    return list({chave_documento(d): d for d in docs}.values())


def resumo(bd: dict[str, dict]) -> dict:
    regs = list(bd.values())
    return {
        "registos": len(regs),
        "pa": len({r["pa_base"] for r in regs}),
        "por_proponente": dict(Counter(p for r in regs for p in (r["proponente"] or "—").split("; ")).most_common()),
        "por_estado": dict(Counter(r["estado"] for r in regs).most_common()),
    }


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["opendata", "scrape", "verificar", "documentos", "normalize", "listar"])
    ap.add_argument("--url", help="scrape/verificar: outra página de pesquisa (testes)")
    ap.add_argument("ficheiro", nargs="?")
    ap.add_argument("--ano", type=int, default=CONFIG["ppl"]["ano_oe"])
    ap.add_argument("--saida", default=str(RAIZ / "data"))
    ap.add_argument("--max", type=int, default=0, help="scrape: limitar o n.º de detalhes (teste)")
    a = ap.parse_args(argv)
    pasta = Path(a.saida)
    raw = pasta / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    momento = agora()
    meta = {"momento": momento, "comando": a.comando, "ano": a.ano, "erros": []}

    if a.comando == "listar":
        for f in listar_pasta(CONFIG["fontes"]["dados_abertos_pasta_xvii"]):
            print(f"{f['fich']:50s} {f['url'][:90]}…")
        return 0

    if a.comando in ("opendata", "normalize"):
        if a.comando == "opendata":
            s = sessao()
            f = localizar_ficheiro_pa(a.ano, s)
            if not f:
                meta["erros"].append(f"o ficheiro OEPropostasAlteracao{a.ano} ainda não consta da pasta XVII dos dados abertos da AR")
                print(meta["erros"][-1], file=sys.stderr)
                atualizar_estado(pasta, "dados_abertos", {"momento": momento, "disponivel": False})
                bd = ler_bd(pasta)
                meta["resumo"] = resumo(bd)
                gravar(pasta, bd, [], meta)
                return 3
            meta["ficheiro_ar"], meta["url"] = f["fich"], f["url"]
            resp = http_get(f["url"], s)
            meta["ultima_modificacao_ar"] = resp.headers.get("Last-Modified", "")
            txt = resp.content.decode("utf-8-sig")
            with gzip.open(raw / f"{carimbo()}_opendata.json.gz", "wt", encoding="utf-8") as fh:
                fh.write(txt)
            bruto = json.loads(txt)
        else:
            p = Path(a.ficheiro)
            abrir = gzip.open if p.suffix == ".gz" else open
            with abrir(p, "rt", encoding="utf-8-sig") as fh:
                bruto = json.load(fh)
            meta["ficheiro_local"] = str(p)
        novos = normalizar_opendata(bruto, momento)
        bd = ler_bd(pasta)
        eventos = fundir(bd, novos, momento, "opendata")
        meta.update({"capturados": len(novos), "eventos": len(eventos), "resumo": resumo(bd)})
        gravar(pasta, bd, eventos, meta)
        if a.comando == "opendata":
            atualizar_estado(pasta, "dados_abertos", {
                "momento": momento, "disponivel": True, "ficheiro": meta["ficheiro_ar"],
                "registos": len(novos), "pa": len({r["pa_base"] for r in novos}),
                "ultima_entrada": max((r["data_entrada"] for r in novos), default=""),
                "ultima_modificacao_ar": meta.get("ultima_modificacao_ar", ""),
            })
        print(json.dumps({k: v for k, v in meta.items() if k != "resumo"} | {"pa": meta["resumo"]["pa"]}, ensure_ascii=False))
        return 0

    if a.comando == "verificar":
        import requests

        s = sessao()
        url = a.url or CONFIG["fontes"]["pesquisa_pa"]
        try:
            ids = listar_ids_pesquisa(url, s)
        except requests.HTTPError as e:
            disponivel = not (e.response is not None and e.response.status_code == 404)
            atualizar_estado(pasta, "pesquisa", {"momento": momento, "disponivel": False,
                                                 "erro": "" if not disponivel else str(e)})
            print(f"página de pesquisa indisponível: {e}", file=sys.stderr)
            return 0 if not disponivel else 3
        bd = ler_bd(pasta)
        conhecidos = {r.get("id_ar") for r in bd.values()}
        em_falta = [i for i in ids if i not in conhecidos]
        limite = a.max or 600
        novos, falhas = [], []
        for bid in em_falta[:limite]:
            try:
                novos.append(ler_detalhe(bid, momento, s))
            except Exception as e:  # noqa: BLE001
                falhas.append({"id": bid, "erro": str(e)})
        eventos = fundir(bd, novos, momento, "scrape", marcar_ausentes=False) if novos else []
        gravar(pasta, bd, eventos, None)
        if novos:
            with gzip.open(raw / f"{carimbo()}_verificar.json.gz", "wt", encoding="utf-8") as fh:
                json.dump(novos, fh, ensure_ascii=False)
        conhecidos = {r.get("id_ar") for r in bd.values()}
        restantes = sum(1 for i in ids if i not in conhecidos)
        atualizar_estado(pasta, "pesquisa", {"momento": momento, "disponivel": True, "registos": len(ids),
                                             "em_falta_na_base": len(em_falta), "recuperados": len(novos),
                                             "por_recuperar": restantes, "falhas": len(falhas)})
        print(json.dumps({"pesquisa": len(ids), "em_falta": len(em_falta), "recuperados": len(novos),
                          "por_recuperar": restantes, "falhas": falhas[:5]}, ensure_ascii=False))
        return 0

    if a.comando == "documentos":
        s = sessao()
        f = pasta / "documentos.json"
        antigos: dict[str, dict] = {}
        for d in (json.loads(f.read_text(encoding="utf-8")) if f.exists() else []):
            k = chave_documento(d)
            if k not in antigos or d["primeira_captura"] < antigos[k]["primeira_captura"]:
                antigos[k] = d
        try:
            docs = ler_documentos(CONFIG["ppl"]["url_cofap"], s)
        except Exception as e:  # noqa: BLE001
            print(f"página da COFAP indisponível: {e}", file=sys.stderr)
            return 0
        for d in docs:
            k = chave_documento(d)
            if k not in antigos:
                antigos[k] = d | {"primeira_captura": momento}
            else:
                antigos[k]["url"] = d["url"]  # guarda a ligação mais recente
        f.write_text(json.dumps(sorted(antigos.values(), key=lambda d: d["primeira_captura"], reverse=True),
                                ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(docs)} documentos de votação na página da COFAP ({len(antigos)} registados)")
        return 0

    if a.comando == "scrape":
        s = sessao()
        url = a.url or CONFIG["fontes"]["pesquisa_pa"]
        try:
            ids = listar_ids_pesquisa(url, s)
        except Exception as e:  # noqa: BLE001
            meta["erros"].append(f"pesquisa: {e}")
            ids = []
        if a.max:
            ids = ids[: a.max]
        novos, falhas = [], []
        for bid in ids:
            try:
                novos.append(ler_detalhe(bid, momento, s))
            except Exception as e:  # noqa: BLE001
                falhas.append({"id": bid, "erro": str(e)})
        if novos:
            with gzip.open(raw / f"{carimbo()}_scrape.json.gz", "wt", encoding="utf-8") as fh:
                json.dump(novos, fh, ensure_ascii=False)
        bd = ler_bd(pasta)
        eventos = fundir(bd, novos, momento, "scrape") if novos else []
        meta.update({"url": url, "listados": len(ids), "capturados": len(novos), "falhas": falhas,
                     "eventos": len(eventos), "resumo": resumo(bd)})
        gravar(pasta, bd, eventos, meta)
        print(json.dumps({k: v for k, v in meta.items() if k != "resumo"}, ensure_ascii=False)[:800])
        return 0 if novos else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
