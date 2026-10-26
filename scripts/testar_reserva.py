#!/usr/bin/env python3
"""Teste temporário da reserva (página de pesquisa e detalhe) com páginas reais da AR.
Compara uma amostra lida no portal com o ficheiro de dados abertos do mesmo orçamento.
Escreve só um resumo de validação (taxas de concordância por campo); nada entra na base."""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pa as fp

URL = "https://www.parlamento.pt/OrcamentoEstado/Paginas/PesquisaPropAlteracao37XVII.aspx"
s = fp.sessao(); res = {}
t0 = time.time()
try:
    ids = fp.listar_ids_pesquisa(URL, s)
    res["pesquisa"] = {"ids": len(ids), "segundos": round(time.time() - t0)}
except Exception as e:
    res["pesquisa"] = {"erro": str(e)}; ids = []
f = fp.localizar_ficheiro_pa(2026, s)
ref = {}
if f:
    regs = fp.normalizar_opendata(json.loads(fp.http_get(f["url"], s).content.decode("utf-8-sig")), "teste")
    ref = {r["id_ar"]: r for r in regs}
    res["referencia_registos"] = len(regs)
    res["ids_pesquisa_na_referencia"] = sum(1 for i in ids if i in ref)
random.seed(1)
amostra = random.sample(ids, min(25, len(ids))) if ids else random.sample(list(ref), 25)
campos = ["n_pa", "data_entrada", "proponente", "apresentada", "incide", "artigo", "tipo_ar", "objeto", "tema_ar", "estado_ar", "votos_por_partido", "url_pdf"]
conc = {c: 0 for c in campos}; difs = {c: [] for c in campos}; falhas = []
for bid in amostra:
    try:
        d = fp.ler_detalhe(bid, "teste", s)
    except Exception as e:
        falhas.append(str(e)[:120]); continue
    r = ref.get(bid, {})
    for c in campos:
        a, b = (d.get(c) or "").strip(), (r.get(c) or "").strip()
        if c == "data_entrada": a, b = a[:10], b[:10]
        if c == "url_pdf": a, b = bool(a), bool(b)
        if c == "votos_por_partido": a, b = sorted(str(a).split("; ")), sorted(str(b).split("; "))
        if a == b: conc[c] += 1
        elif len(difs[c]) < 2: difs[c].append({"portal": str(a)[:90], "dados_abertos": str(b)[:90]})
res["amostra"] = len(amostra); res["falhas"] = falhas[:5]
res["concordancia"] = conc; res["exemplos_diferencas"] = difs
Path("teste_reserva.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
# rerun 0430
