#!/usr/bin/env python3
"""
Gera uma AMOSTRA SINTÉTICA de PA (data/amostra/) para testar o pipeline e o painel
antes de existirem PA à PPL 110/XVII/2.ª. Os registos são fictícios: números,
objetos, partidos e votações são gerados aleatoriamente e NÃO correspondem a
propostas reais. O painel assinala isto com uma faixa bem visível.

  python scripts/gerar_amostra.py            # cria amostra/t1_opendata.json e t2_opendata.json
  python scripts/fetch_pa.py normalize data/amostra/t1_opendata.json
  python scripts/fetch_pa.py normalize data/amostra/t2_opendata.json
"""
import json
import random
from pathlib import Path

random.seed(2027)
RAIZ = Path(__file__).resolve().parents[1]
OUT = RAIZ / "data" / "amostra"
OUT.mkdir(parents=True, exist_ok=True)

PARTIDOS = {"PSD": 12, "PS": 10, "CH": 30, "IL": 6, "L": 12, "PCP": 20, "CDS-PP": 4, "BE": 8, "PAN": 10, "JPP": 2}
TEMAS = ["Orçamento, Finanças e Administração Pública", "Trabalho, Segurança Social e Inclusão", "Saúde",
         "Educação e Ciência", "Agricultura e Pescas", "Infraestruturas, Mobilidade e Habitação",
         "Economia e Coesão Territorial", "Ambiente e Energia", "Cultura, Comunicação, Juventude e Desporto",
         "Reforma do Estado e Poder Local", "Assuntos Constitucionais, Direitos, Liberdades e Garantias",
         "Defesa Nacional", "Negócios Estrangeiros e Comunidades Portuguesas"]
OBJETOS = [
    "Artigo {n}.º-A (Atualização extraordinária das pensões) [FICTÍCIO]",
    "Artigo {n}.º (Redução da taxa de IVA aplicável à eletricidade) [FICTÍCIO]",
    "Artigo {n}.º-B (Reforço da dotação do programa de habitação acessível) [FICTÍCIO]",
    "Artigo {n}.º (Autorização legislativa em matéria de benefícios fiscais) [FICTÍCIO]",
    "Artigo {n}.º-C (Alteração ao Decreto-Lei n.º 000/2000 — regime de carreiras) [FICTÍCIO]",
    "Artigo {n}.º (Contratação de profissionais de saúde) [FICTÍCIO]",
    "Artigo {n}.º-A (Transferência de verbas para as autarquias locais) [FICTÍCIO]",
    "Artigo {n}.º (Isenção de IMI para primeira habitação) [FICTÍCIO]",
    "Mapa {m} (Reforço da dotação da missão de base orgânica) [FICTÍCIO]",
    "Artigo {n}.º-D (Passe de mobilidade nacional) [FICTÍCIO]",
    "Artigo {n}.º (Descida do imposto sobre produtos petrolíferos) [FICTÍCIO]",
    "Artigo {n}.º-A (Abono de família — majoração) [FICTÍCIO]",
]
TIPOS = ["Aditamento (Artigo PPL)"] * 7 + ["Substituição (Artigo PPL)"] * 2 + ["Eliminação (Artigo PPL)", "Aditamento (Mapa)"]
NOMES = ["A. Silva", "B. Costa", "C. Pereira", "D. Martins", "E. Sousa", "F. Rocha", "G. Nunes", "H. Lopes"]
SENTIDOS = ["Favor", "Contra", "Abstenção"]
GP_EXTENSO = {"PSD": "Partido Social Democrata", "PS": "Partido Socialista", "CH": "Chega", "IL": "Iniciativa Liberal",
              "L": "Livre", "PCP": "Partido Comunista Português", "CDS-PP": "Centro Democrático Social - Partido Popular",
              "BE": "Bloco de Esquerda", "PAN": "Pessoas-Animais-Natureza", "JPP": "Juntos pelo Povo"}


def registo(num: int, partido: str, data: str, votado: bool):
    tipo = random.choice(TIPOS)
    obj = random.choice(OBJETOS).format(n=random.randint(2, 180), m=random.randint(1, 12))
    tema = random.choice(TEMAS)
    r = {
        "Numero": f"{num}C",
        "BID": str(90000 + num),
        "Data": data,
        "Apresentada": "Comissão",
        "Incide": "Mapa" if "Mapa" in obj else "Articulado",
        "Objecto": obj,
        "Tema": tema,
        "Tipo": tipo,
        "NumeroArtigoNovo": obj.split(" (")[0] if "-" in obj.split(" (")[0] else "",
        "Estado": "Em apreciação",
        "Proponentes": [{"Deputado": n, "GP": GP_EXTENSO[partido]} for n in random.sample(NOMES, 3)] + [{"GP": GP_EXTENSO[partido]}],
        "Votacoes": [],
    }
    if votado:
        res = random.choices(["Aprovado(a)", "Rejeitado(a)", "Prejudicado(a)"], weights=[25, 65, 10])[0]
        r["Estado"] = f"{res} em Comissão"
        r["Votacoes"] = [{"Data": "2026-11-19", "Resultado": res,
                          "SentidoVoto": [{"GP": GP_EXTENSO[p], "Sentido": random.choice(SENTIDOS)} for p in PARTIDOS]}]
    return r


def main():
    regs, num = [], 1
    for partido, n in PARTIDOS.items():
        for _ in range(n):
            data = random.choice(["2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-06", "2026-11-06"])
            regs.append(registo(num, partido, data, votado=False))
            num += 1
    t1 = {"_AVISO": "AMOSTRA SINTÉTICA — dados fictícios para teste do pipeline", "PropostasAlteracao": regs}
    (OUT / "t1_opendata.json").write_text(json.dumps(t1, ensure_ascii=False, indent=1), encoding="utf-8")

    # t2: mais PA entradas no fim de semana, 3 substituições, 2 retiradas, 40 votadas
    regs2 = [json.loads(json.dumps(r)) for r in regs]
    idx = random.sample(range(len(regs2)), 43)
    for i in idx[:40]:
        v = registo(i + 1, "PSD", regs2[i]["Data"], votado=True)
        regs2[i]["Estado"], regs2[i]["Votacoes"] = v["Estado"], v["Votacoes"]
    for i in idx[40:]:
        sub = json.loads(json.dumps(regs2[i]))
        sub["Numero"] = regs2[i]["Numero"] + "-1"
        sub["BID"] = str(int(sub["BID"]) + 5000)
        sub["Data"] = "2026-11-08"
        regs2.append(sub)
    for i in sorted(random.sample(range(len(regs)), 2), reverse=True):
        regs2[i]["Estado"] = "Retirado(a)"
    for partido in ["CH", "PCP", "L", "PAN", "PS"]:
        for _ in range(4):
            regs2.append(registo(num, partido, "2026-11-08", votado=False))
            num += 1
    t2 = {"_AVISO": "AMOSTRA SINTÉTICA — dados fictícios para teste do pipeline", "PropostasAlteracao": regs2}
    (OUT / "t2_opendata.json").write_text(json.dumps(t2, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"t1: {len(regs)} PA · t2: {len(regs2)} PA → {OUT}")


if __name__ == "__main__":
    main()
