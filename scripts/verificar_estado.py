#!/usr/bin/env python3
"""
Alerta: termina com erro (execução a vermelho no GitHub, que envia e-mail de aviso)
quando a captura não está a funcionar durante o processo de apreciação.

Condições de alerta:
  1. Prazo de inserção aberto há mais de 3 horas e nenhuma PA na base.
  2. A página de pesquisa da AR lista mais de 50 PA que não foi possível recuperar para a base.
  3. Página de pesquisa com erro que não seja «página ainda não criada».
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
ABERTURA = dt.datetime(2026, 10, 29, 9, 0, tzinfo=dt.timezone.utc)  # 9h00 em Lisboa (UTC+0)
FIM = dt.datetime(2026, 12, 10, tzinfo=dt.timezone.utc)


def main() -> int:
    agora = dt.datetime.now(dt.timezone.utc)
    if agora < ABERTURA + dt.timedelta(hours=3) or agora > FIM:
        print("fora da janela de alerta")
        return 0
    pa = json.loads((DATA / "pa.json").read_text(encoding="utf-8")) if (DATA / "pa.json").exists() else []
    estado = json.loads((DATA / "estado_fontes.json").read_text(encoding="utf-8")) if (DATA / "estado_fontes.json").exists() else {}
    alertas = []
    if not pa:
        alertas.append("o prazo de inserção abriu há mais de 3 horas e a base continua sem propostas: "
                       "verificar se a AR mudou a publicação (nova aplicação)")
    pesq = estado.get("pesquisa", {})
    if pesq.get("disponivel") and pesq.get("por_recuperar", 0) > 50:
        alertas.append(f"a página de pesquisa da AR lista {pesq['por_recuperar']} propostas que não estão na base")
    if pesq.get("erro"):
        alertas.append(f"erro na página de pesquisa da AR: {pesq['erro']}")
    for a in alertas:
        print(f"::error::{a}")
    return 1 if alertas else 0


if __name__ == "__main__":
    sys.exit(main())
