#!/usr/bin/env python3
"""
Descoberta e calibração (corre no GitHub Actions, que chega ao parlamento.pt).

1. Lista os ficheiros da pasta «XVII Legislatura» da categoria «Orçamento do
   Estado» dos dados abertos da AR (data/calibracao/descoberta.json).
2. Descarrega o ficheiro de PA do OE 2026 (referência para testes) e, se já
   existir, o do OE 2027.
3. Descarrega o calendário oficial de apreciação do OE 2027.

Nada do que fica em data/calibracao/ entra na base de dados nem no painel do OE 2027.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pa as fp  # noqa: E402

OUT = fp.RAIZ / "data" / "calibracao"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    s = fp.sessao()
    res = {"momento": fp.agora(), "ficheiros_xvii": []}
    itens = fp.listar_pasta(fp.CONFIG["fontes"]["dados_abertos_pasta_xvii"], s)
    res["ficheiros_xvii"] = [i["fich"] for i in itens]
    print("Pasta XVII:", *res["ficheiros_xvii"], sep="\n  ")
    for i in itens:
        m = re.match(r"OEPropostasAlteracao(\d{4})\w*_json", i["fich"], re.I)
        if not m:
            continue
        txt = fp.http_get(i["url"], s).content.decode("utf-8-sig")
        with gzip.open(OUT / f"OEPropostasAlteracao{m.group(1)}.json.gz", "wt", encoding="utf-8") as fh:
            fh.write(txt)
        regs = fp.normalizar_opendata(json.loads(txt), res["momento"])
        res[f"pa_{m.group(1)}"] = {"registos": len(regs), "pa": len({r["pa_base"] for r in regs})}
        print(f"OE {m.group(1)}: {len(regs)} registos")
    r = s.get(fp.CONFIG["ppl"]["url_calendario"], timeout=120)
    if r.ok:
        (OUT / "calendario_OE2027.pdf").write_bytes(r.content)
    (OUT / "descoberta.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
