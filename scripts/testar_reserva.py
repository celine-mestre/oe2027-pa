#!/usr/bin/env python3
"""Teste temporário da reserva com páginas reais da AR (só resumo de validação; nada entra na base).
1) concordância campo a campo entre a página de detalhe e os dados abertos, numa amostra;
2) resposta da AR a identificadores que ainda não existem (fim da sequência)."""
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pa as fp
import requests

s = fp.sessao(); res = {}
f = fp.localizar_ficheiro_pa(2026, s)
regs = fp.normalizar_opendata(json.loads(fp.http_get(f["url"], s).content.decode("utf-8-sig")), "teste")
ref = {r["id_ar"]: r for r in regs}
random.seed(7)
amostra = random.sample(list(ref), 30)
campos = ["n_pa", "data_entrada", "proponente", "apresentada", "incide", "tipo_ar", "objeto", "tema_ar", "estado_ar", "votos_por_partido", "url_pdf"]
conc = {c: 0 for c in campos}; difs = {c: [] for c in campos}
for bid in amostra:
    d = fp.ler_detalhe(bid, "teste", s); r = ref[bid]
    for c in campos:
        a, b = (d.get(c) or "").strip(), (r.get(c) or "").strip()
        if c == "data_entrada": a, b = a[:10], b[:10]
        if c == "url_pdf": a, b = bool(a), bool(b)
        if c == "votos_por_partido": a, b = sorted(str(a).split("; ")), sorted(str(b).split("; "))
        if a == b: conc[c] += 1
        elif len(difs[c]) < 2: difs[c].append({"portal": str(a)[:70], "dados_abertos": str(b)[:70]})
res["concordancia_em_30"] = conc; res["diferencas"] = {k: v for k, v in difs.items() if v}
fim = []
ultimo = max(int(i) for i in ref)
for bid in range(ultimo - 2, ultimo + 6):
    url = fp.CONFIG["fontes"]["detalhe_pa"].format(bid=bid)
    try:
        r = s.get(url, timeout=180); estado = r.status_code
        lido = fp.ler_detalhe(str(bid), "teste", s)["n_pa"] if r.ok else ""
    except Exception as e:
        estado, lido = f"erro: {str(e)[:80]}", ""
    fim.append({"id": bid, "http": estado, "n_pa_lido": bool(lido)})
res["fim_da_sequencia"] = fim
Path("teste_reserva.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
