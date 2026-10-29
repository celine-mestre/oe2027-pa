#!/usr/bin/env python3
"""
Descoberta e calibração (corre no GitHub Actions, que chega ao parlamento.pt).

1. Lista os ficheiros da pasta «XVII Legislatura» da categoria «Orçamento do Estado»
   dos dados abertos da AR (data/calibracao/descoberta.json).
2. Descarrega o calendário oficial de apreciação da edição ativa (data/calibracao/).
3. Descarrega o texto de cada proposta de lei configurada (url_texto_ppl) para
   data/oe<ano>/ppl.html, de onde scripts/indice_ppl.py tira o índice dos artigos.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pa as fp  # noqa: E402

OUT = fp.RAIZ / "data" / "calibracao"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    s = fp.sessao()
    res = {"momento": fp.agora(), "ficheiros_xvii": [], "ppl": {}}
    try:
        res["ficheiros_xvii"] = [i["fich"] for i in fp.listar_pasta(fp.CONFIG["fontes"]["dados_abertos_pasta_xvii"], s)]
        print("Pasta XVII:", *res["ficheiros_xvii"], sep="\n  ")
    except Exception as e:  # noqa: BLE001
        res["erro_pasta"] = str(e)[:200]
        print(f"pasta XVII indisponível: {e}", file=sys.stderr)
    ativa = fp.CONFIG["edicoes"][fp.CONFIG["edicao_ativa"]]
    if ativa.get("url_calendario"):
        try:
            r = s.get(ativa["url_calendario"], timeout=120)
            if r.ok:
                (OUT / f"calendario_OE{ativa['ano_oe']}.pdf").write_bytes(r.content)
        except Exception as e:  # noqa: BLE001
            print(f"calendário indisponível: {e}", file=sys.stderr)
    for ano, ed in fp.CONFIG["edicoes"].items():
        url = ed.get("url_texto_ppl")
        if not url or ed.get("congelada"):
            continue
        try:
            r = s.get(url, timeout=180)
            r.raise_for_status()
            pasta = fp.RAIZ / ed["pasta"]
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / "ppl.html").write_text(r.text, encoding="utf-8")
            res["ppl"][ano] = {"url": url, "bytes": len(r.content)}
            print(f"OE {ano}: texto da PPL guardado ({len(r.content)} bytes)")
        except Exception as e:  # noqa: BLE001
            res["ppl"][ano] = {"url": url, "erro": str(e)[:200]}
            print(f"OE {ano}: texto da PPL indisponível: {e}", file=sys.stderr)
    (OUT / "descoberta.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
