#!/usr/bin/env python3
"""
Exporta a base de dados das PA para o modelo Excel da DACDP (Registo_PA_OE<ano>.xlsx).

Estrutura igual ao modelo «Registo_PA_OE2027_v1» da DACDP (7 folhas), mais uma folha «Resposta UPE».
  - Colunas A–W de «Propostas de Alteração»: o modelo da DACDP. A UPE preenche, a partir da AR, as colunas
    B, C, E, F, G, L, S, T, U, V e as ligações em W; as restantes ficam para a DACDP.
  - Colunas X em diante: informação adicional publicada pela AR (tema, incidência, natureza e estado da PA,
    avocação, identificadores e ligações).
  - «Registo de Consultas» e «Calendário e Documentos» são preenchidas automaticamente.

  python scripts/exportar_excel.py                 # edição ativa → docs/Registo_PA_OE2027.xlsx
  python scripts/exportar_excel.py --ano 2026
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
TAX = json.loads((RAIZ / "data" / "taxonomia.json").read_text(encoding="utf-8"))
AREAS = json.loads((RAIZ / "data" / "areas_governativas.json").read_text(encoding="utf-8"))

AZUL = "1F3864"
FONTE = "Arial"
LINHAS_MAX = 5000  # o OE 2026 teve 2 176 PA (≈2 300 registos com as partes)

# ---- modelo da DACDP (Registo_PA_OE2027_v1) ---------------------------------------------------------------
COLUNAS_DACDP = ["ID", "N.º PA", "Data Entrada", "Versão", "Partido", "Deputado/Proponente", "Artigo Alterado", "Tipo de PA",
                 "Tema", "Área Governativa", "Ministério", "Descrição Sumária", "Impacto Receita (€)", "Impacto Despesa (€)",
                 "Fonte da Estimativa", "Medida Anunciada (S/N)", "Relevância", "Necessita Análise Jurídica (S/N)", "Estado",
                 "Resultado Votação", "Sentido de Voto", "Data Votação", "Observações"]
COLUNAS_UPE = ["Tema AR", "Incide", "Tipo (AR)", "Estado (AR)", "Avocação a Plenário", "Parte", "N.º de votações", "ID AR",
               "Ligação AR", "PDF", "Primeira captura", "Última captura", "Ausente da fonte"]
LARGURAS = [7, 10, 12, 13, 11, 24, 18, 22, 18, 22, 22, 50, 14, 14, 16, 12, 11, 14, 22, 18, 40, 12, 40] + \
           [22, 11, 22, 24, 10, 7, 9, 9, 40, 40, 17, 17, 17]
COLUNAS_MEDIDAS = ["ID", "Data do Anúncio", "Partido", "Quem Anunciou", "Natureza", "Medida Anunciada", "Tema", "Valor Anunciado",
                   "Canal Oficial", "Ligação", "Entregue como PA (S/N)", "N.º PA Associada", "Observações"]
LISTAS = {
    "Versão": ["Original", "Substituição", "Retirada"],
    "Partido": ["PSD", "CH", "PS", "IL", "L", "PCP", "CDS-PP", "BE", "PAN", "JPP", "Deputado único/não inscrito", "Vários"],
    "Tipo de PA": ["Receita", "Despesa", "Norma orçamental", "Alteração a legislação avulsa", "Autorização legislativa"],
    "SN": ["S", "N"],
    "Relevância": ["Alta", "Média", "Baixa"],
    "Estado": ["Entregue", "Admitida", "Substituída", "Retirada", "Em votação", "Votada", "Avocada a Plenário"],
    "Resultado": ["Aprovada", "Rejeitada", "Prejudicada", "Retirada", "Aprovada parcialmente"],
    "Área Governativa": AREAS["areas"],
}
INSTRUCOES = [
    ("ID", "Número sequencial interno do registo.", "Inteiro (1, 2, 3…)"),
    ("N.º PA", "Número atribuído à PA pela Assembleia da República.", "Conforme publicado pela AR"),
    ("Data Entrada", "Data de entrada da PA na AR.", "DD/MM/AAAA"),
    ("Versão", "Versão da PA. Cada PA mantém o número original; as substituições registam-se em nova linha.", "Original · Substituição · Retirada"),
    ("Partido", "Grupo parlamentar ou partido proponente.", "PSD · CH · PS · IL · L · PCP · CDS-PP · BE · PAN · JPP · Deputado único/não inscrito · Vários"),
    ("Deputado/Proponente", "Deputado(s) subscritor(es), conforme a PA.", "Texto"),
    ("Artigo Alterado", "Artigo ou mapa da Proposta de Lei alterado, aditado ou eliminado.", "Ex.: formato «Art. n.º (alteração)», «Artigo novo», «Mapa n.º»"),
    ("Tipo de PA", "Natureza da PA.", "Receita · Despesa · Norma orçamental · Alteração a legislação avulsa · Autorização legislativa"),
    ("Tema", "Tema da PA.", "Texto (taxonomia a fixar pela DACDP)"),
    ("Área Governativa", "Área governativa abrangida.", "Texto, conforme a orgânica do Governo"),
    ("Ministério", "Ministério responsável pela execução.", "Texto, conforme a orgânica do Governo"),
    ("Descrição Sumária", "Descrição numa linha do conteúdo da PA.", "Texto"),
    ("Impacto Receita (€)", "Impacto estimado na receita, em euros.", "Número; em branco se não quantificado"),
    ("Impacto Despesa (€)", "Impacto estimado na despesa, em euros.", "Número; em branco se não quantificado"),
    ("Fonte da Estimativa", "Origem da quantificação do impacto.", "Proponente · UTAO · Governo · Sem quantificação"),
    ("Medida Anunciada (S/N)", "A medida foi anunciada publicamente antes da entrega da PA?", "S · N (data e fonte em Observações)"),
    ("Relevância", "Classificação de relevância para apoio à decisão.", "Alta · Média · Baixa (justificação em Observações)"),
    ("Necessita Análise Jurídica (S/N)", "A PA requer análise jurídica (PA normativas, cavaleiros orçamentais, legislação avulsa).", "S · N"),
    ("Estado", "Fase da tramitação da PA.", "Entregue · Admitida · Substituída · Retirada · Em votação · Votada · Avocada a Plenário"),
    ("Resultado Votação", "Resultado da votação, conforme guião/súmula de votação.", "Aprovada · Rejeitada · Prejudicada · Retirada · Aprovada parcialmente"),
    ("Sentido de Voto", "Sentido de voto por partido.", "«Favor: …; Contra: …; Abstenção: …»"),
    ("Data Votação", "Data da votação.", "DD/MM/AAAA"),
    ("Observações", "Fonte (com ligação), ausência de dados, avocação, histórico de versões e outras notas.", "Texto"),
]

# Resposta da UPE ao pedido da DACDP: o que se assegura de imediato, o que exige desenvolvimento, o que não tem fonte na AR
RESPOSTA = [
    ("ID", "Imediato", "Número sequencial atribuído na exportação.", ""),
    ("N.º PA", "Imediato", "AR (dados abertos; reserva: página de cada PA).", "Uma PA com várias partes (120C-1, 120C-2) ocupa uma linha por parte, porque a AR as vota separadamente."),
    ("Data Entrada", "Imediato", "AR: data e hora de entrada.", ""),
    ("Versão", "Limitação", "A AR não publica a ligação entre uma PA e a que ela substitui. A coluna recebe «Retirada» quando a AR publica esse estado e «Original» nos restantes casos.", "Confirmação pela DACDP."),
    ("Partido", "Imediato", "AR: grupo(s) parlamentar(es) proponente(s). «Vários» quando há mais de um.", "Sigla normalizada (CDS-P → CDS-PP)."),
    ("Deputado/Proponente", "Imediato", "AR: deputados signatários.", ""),
    ("Artigo Alterado", "Imediato", "AR: artigo ou mapa e natureza (alteração, aditamento, eliminação).", ""),
    ("Tipo de PA", "Limitação", "Sem fonte na AR (a AR publica a natureza da PA: aditamento, substituição, eliminação, na coluna «Tipo (AR)»).", "Classificação da DACDP. Fase posterior: sugestão automática a validar."),
    ("Tema", "Limitação", "A AR atribui um tema próprio (coluna «Tema AR»). A taxonomia da DACDP é preenchida pela DACDP.", ""),
    ("Área Governativa", "Desenvolvimento (fase posterior)", "Sem fonte na AR. O tema atribuído pela AR (coluna «Tema AR», a comissão parlamentar competente) é a aproximação disponível. A classificação por área governativa será feita numa fase posterior, com validação humana.", "Nesta fase, o painel e o Excel só usam variáveis dos dados abertos da AR."),
    ("Ministério", "Desenvolvimento (fase posterior)", "Decorre da área governativa.", ""),
    ("Descrição Sumária", "Imediato (parcial)", "AR: título da PA tal como publicado. A DACDP pode reescrever; a UPE não substitui texto já escrito.", ""),
    ("Impacto Receita (€)", "Limitação", "Sem fonte na AR. Só existe quando a UTAO ou o proponente publicam uma estimativa.", "A UPE pode extrair o texto da nota justificativa do PDF de cada PA para facilitar a leitura."),
    ("Impacto Despesa (€)", "Limitação", "Idem.", ""),
    ("Fonte da Estimativa", "Limitação", "Idem.", ""),
    ("Medida Anunciada (S/N)", "Limitação", "Sem fonte na AR. Ligação à folha «Medidas Anunciadas» pelo n.º da PA, a cargo da DACDP.", ""),
    ("Relevância", "Limitação", "Juízo da DACDP.", ""),
    ("Necessita Análise Jurídica (S/N)", "Limitação", "Juízo da DACDP.", ""),
    ("Estado", "Imediato", "AR: estado publicado (coluna «Estado (AR)»); a coluna «Estado» recebe o estado da AR, que é o único verificável.", "A lista do modelo (Entregue, Admitida, …) não coincide com os estados que a AR publica."),
    ("Resultado Votação", "Imediato", "AR: resultado da última votação, nos valores do modelo (Aprovada, Rejeitada, Prejudicada, Retirada, Aprovada parcialmente).", ""),
    ("Sentido de Voto", "Imediato", "AR: sentido de voto de cada grupo parlamentar, no formato do modelo.", "Inclui os deputados únicos representantes de partido."),
    ("Data Votação", "Imediato", "AR: data da última votação.", ""),
    ("Observações", "Imediato (parcial)", "A UPE acrescenta a ligação à ficha da PA e ao PDF, a avocação a Plenário e a nota «ausente da fonte» quando a PA deixa de constar da publicação. O resto é da DACDP.", ""),
    ("Medidas Anunciadas (folha)", "Limitação", "Fora das fontes da AR: fica a cargo da DACDP. A UPE preserva o conteúdo nas sincronizações.", ""),
    ("Ponto de Situação (folha)", "Imediato", "Fórmulas do modelo, alargadas a 5 000 linhas; situação na fonte oficial preenchida pela captura.", ""),
    ("Registo de Consultas (folha)", "Imediato", "Cada captura automática regista fonte, momento, resultado e PA novas.", ""),
    ("Calendário e Documentos (folha)", "Imediato", "Calendário oficial da AR e documentos publicados na página da COFAP.", ""),
]


def ler_csv(f: Path) -> list[dict]:
    if not f.exists():
        return []
    with f.open(encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh, delimiter=";")]


def ler_json(f: Path, default):
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def data(iso: str):
    try:
        return dt.datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M") if "T" in iso else dt.datetime.strptime(iso[:10], "%Y-%m-%d")
    except ValueError:
        return iso or None


def partido(prop: str) -> str:
    gps = [p.strip() for p in (prop or "").split(";") if p.strip()]
    if not gps:
        return ""
    return "Vários" if len(gps) > 1 else gps[0]


def artigo_alterado(r: dict) -> str:
    art, tipo, incide = r.get("artigo") or "", r.get("tipo_ar") or "", r.get("incide") or ""
    nat = ""
    t = tipo.lower()
    if "elimina" in t:
        nat = "eliminação"
    elif "adita" in t:
        nat = "aditamento, artigo novo" if "novo" in t else "aditamento"
    elif "substitu" in t:
        nat = "substituição"
    elif "altera" in t:
        nat = "alteração"
    if not art:
        return (f"{incide} ({nat})" if nat else incide).strip()
    art = re.sub(r"^Artigo\s+", "Art. ", art)
    return f"{art} ({nat})" if nat else art




def resultado_modelo(estado: str) -> str:
    return {"aprovada": "Aprovada", "aprovada parcialmente": "Aprovada parcialmente", "rejeitada": "Rejeitada",
            "prejudicada": "Prejudicada", "retirada": "Retirada"}.get(estado or "", "")


def sentido_modelo(votos: str) -> str:
    grupos = {"Favor": [], "Contra": [], "Abstenção": []}
    for v in (votos or "").split(";"):
        if ":" in v:
            gp, s = (x.strip() for x in v.split(":", 1))
            if s in grupos:
                grupos[s].append(gp)
    partes = [f"{k}: {', '.join(v)}" for k, v in grupos.items() if v]
    return "; ".join(partes)


def observacoes(r: dict) -> str:
    notas = []
    if r.get("avocacao") == "S":
        notas.append("Avocada a Plenário.")
    if r.get("ausente_da_fonte"):
        notas.append(f"Deixou de constar da publicação da AR em {r['ausente_da_fonte'][:10]}: confirmar no parlamento.pt.")
    if r.get("url_detalhe"):
        notas.append(f"AR: {r['url_detalhe']}")
    if r.get("url_pdf"):
        notas.append(f"PDF: {r['url_pdf']}")
    return " ".join(notas)


def linha_pa(i: int, r: dict) -> list:
    return [
        i, r.get("n_pa"), data(r.get("data_entrada") or ""), "Retirada" if r.get("estado") == "retirada" else "Original",
        partido(r.get("proponente")), r.get("proponente_deputados") or (r.get("proponente") or ""), artigo_alterado(r), None,
        None, None, None, r.get("objeto"), None, None, None, None, None, None, r.get("estado_ar") or "Em apreciação",
        resultado_modelo(r.get("estado")), sentido_modelo(r.get("votos_por_partido")), data(r.get("data_votacao") or ""), observacoes(r),
        # colunas UPE
        r.get("tema_ar"), r.get("incide"), r.get("tipo_ar"), r.get("estado_ar"), r.get("avocacao"), r.get("parte"), r.get("n_votacoes"), r.get("id_ar"),
        r.get("url_detalhe"), r.get("url_pdf"), data(r.get("primeira_captura") or ""), data(r.get("ultima_captura") or ""),
        (r.get("ausente_da_fonte") or "")[:10],
    ]


def cabecalho(ws, colunas: list[str], larguras: list[int] | None = None, congelar: str = "A2", filtro: bool = True) -> None:
    ws.append(colunas)
    for c in ws[1]:
        c.font = Font(name=FONTE, size=10, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 30
    for i, w in enumerate(larguras or [13] * len(colunas), 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = congelar
    if filtro:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(colunas))}{LINHAS_MAX + 1}"


def titulo(ws, texto: str, linha: int = 1) -> None:
    ws.cell(row=linha, column=1, value=texto).font = Font(name=FONTE, size=13, bold=True, color=AZUL)


def validacoes(ws) -> None:
    """Listas pendentes nas colunas do modelo (ligadas à folha «Listas»)."""
    n = LINHAS_MAX + 1
    for col, lista in (("D", "A"), ("E", "B"), ("H", "C"), ("P", "D"), ("Q", "E"), ("R", "D"), ("T", "G"), ("J", "H")):
        tam = len(list(LISTAS.values())["ABCDEFGH".index(lista)])
        dv = DataValidation(type="list", formula1=f"=Listas!${lista}$2:${lista}${tam + 1}", allow_blank=True)
        dv.add(f"{col}2:{col}{n}")
        ws.add_data_validation(dv)


def construir(ano: str, saida: Path, pasta: Path | None = None) -> dict:
    ed = CONFIG["edicoes"][ano]
    pasta = pasta or RAIZ / ed["pasta"]
    pa = sorted(ler_json(pasta / "pa.json", []), key=lambda r: (int(re.match(r"\d*", r["n_pa"]).group(0) or 0), r["n_pa"]))
    estado_fontes = ler_json(pasta / "estado_fontes.json", {})
    documentos = ler_json(pasta / "documentos.json", [])
    historico = ler_csv(pasta / "historico.csv")
    execucao = ler_json(pasta / "ultima_execucao.json", {})
    agora = dt.datetime.now(dt.timezone.utc)

    wb = Workbook()
    ws = wb.active
    ws.title = "Propostas de Alteração"
    cabecalho(ws, COLUNAS_DACDP + COLUNAS_UPE, LARGURAS, "C2")
    for i, r in enumerate(pa, 1):
        ws.append(linha_pa(i, r))
    for row in ws.iter_rows(min_row=2, max_row=max(2, len(pa) + 1)):
        for c in row:
            c.font = Font(name=FONTE, size=10)
        for idx in (3, 22, 34, 35):
            row[idx - 1].number_format = "DD/MM/YYYY"
        for idx in (13, 14):
            row[idx - 1].number_format = "#,##0"
    validacoes(ws)

    ws2 = wb.create_sheet("Medidas Anunciadas")
    cabecalho(ws2, COLUNAS_MEDIDAS, [6, 12, 9, 24, 13, 50, 18, 22, 24, 40, 12, 12, 40], "D2")
    ws2["A2"].value = None

    ws3 = wb.create_sheet("Ponto de Situação")
    ws3.column_dimensions["A"].width, ws3.column_dimensions["B"].width, ws3.column_dimensions["C"].width, ws3.column_dimensions["D"].width = 34, 14, 20, 13
    titulo(ws3, f"Propostas de alteração à {ed['designacao']} (Orçamento do Estado para {ed['ano_oe']})")
    ws3["A2"], ws3["B2"] = "Última atualização:", agora.strftime("%d/%m/%Y, %Hh%M UTC")
    da = estado_fontes.get("dados_abertos", {})
    if pa:
        situacao = (f"{len({r['pa_base'] for r in pa})} PA ({len(pa)} registos, com as partes) publicadas pela AR; "
                    f"última entrada registada: {max((r.get('data_entrada') or '' for r in pa), default='—')[:16].replace('T', ' ')}.")
    else:
        situacao = ("Sem propostas de alteração publicadas pela AR. "
                    + (f"Registo a partir de {data(ed['inicio_registo']).strftime('%d/%m/%Y, %Hh%M')} (início do prazo de inserção, segundo o calendário da AR)." if ed.get("inicio_registo") else ""))
    ws3["A3"], ws3["B3"] = "Situação na fonte oficial:", situacao
    ws3["A5"], ws3["B5"] = "Total de PA registadas", f"=COUNTA('Propostas de Alteração'!B2:B{LINHAS_MAX + 1})"
    ws3["A7"] = "Por partido"
    ws3.append([])
    ws3["A8"], ws3["B8"], ws3["C8"], ws3["D8"] = "Partido", "N.º PA", "Aprovadas", "Rejeitadas"
    rng_e, rng_t = f"'Propostas de Alteração'!$E$2:$E${LINHAS_MAX + 1}", f"'Propostas de Alteração'!$T$2:$T${LINHAS_MAX + 1}"
    linha = 9
    for p in LISTAS["Partido"]:
        ws3[f"A{linha}"], ws3[f"B{linha}"] = p, f"=COUNTIF({rng_e},A{linha})"
        ws3[f"C{linha}"], ws3[f"D{linha}"] = f'=COUNTIFS({rng_e},A{linha},{rng_t},"Aprovada")', f'=COUNTIFS({rng_e},A{linha},{rng_t},"Rejeitada")'
        linha += 1
    ws3[f"A{linha}"], ws3[f"B{linha}"], ws3[f"C{linha}"], ws3[f"D{linha}"] = "Total", f"=SUM(B9:B{linha - 1})", f"=SUM(C9:C{linha - 1})", f"=SUM(D9:D{linha - 1})"
    linha += 2
    ws3[f"A{linha}"] = "Por resultado da votação"
    linha += 1
    ws3[f"A{linha}"], ws3[f"B{linha}"] = "Resultado", "N.º PA"
    primeiro = linha + 1
    for res in LISTAS["Resultado"]:
        linha += 1
        ws3[f"A{linha}"], ws3[f"B{linha}"] = res, f"=COUNTIF({rng_t},A{linha})"
    linha += 1
    ws3[f"A{linha}"], ws3[f"B{linha}"] = "Sem resultado registado", f"=B5-SUM(B{primeiro}:B{linha - 1})"
    linha += 2
    ws3[f"A{linha}"] = "Por tipo de PA"
    linha += 1
    ws3[f"A{linha}"], ws3[f"B{linha}"], ws3[f"C{linha}"], ws3[f"D{linha}"] = "Tipo de PA", "N.º PA", "Impacto Receita (€)", "Impacto Despesa (€)"
    rng_h = f"'Propostas de Alteração'!$H$2:$H${LINHAS_MAX + 1}"
    for t in LISTAS["Tipo de PA"]:
        linha += 1
        ws3[f"A{linha}"], ws3[f"B{linha}"] = t, f"=COUNTIF({rng_h},A{linha})"
        ws3[f"C{linha}"] = f"=SUMIF({rng_h},A{linha},'Propostas de Alteração'!$M$2:$M${LINHAS_MAX + 1})"
        ws3[f"D{linha}"] = f"=SUMIF({rng_h},A{linha},'Propostas de Alteração'!$N$2:$N${LINHAS_MAX + 1})"
    linha += 2
    ws3[f"A{linha}"] = "Nota: os impactos somam apenas os valores registados; PA sem quantificação na fonte não são contabilizadas."
    for row in ws3.iter_rows():
        for c in row:
            if not c.font.bold:
                c.font = Font(name=FONTE, size=10)
    for ref in ("A7", "A8", "B8", "C8", "D8"):
        ws3[ref].font = Font(name=FONTE, size=10, bold=True)

    ws4 = wb.create_sheet("Listas")
    ws4.append(list(LISTAS.keys()))
    for i, (k, vals) in enumerate(LISTAS.items(), 1):
        ws4.column_dimensions[get_column_letter(i)].width = max(13, min(44, max(len(v) for v in vals) + 2))
        for j, v in enumerate(vals, 2):
            ws4.cell(row=j, column=i, value=v).font = Font(name=FONTE, size=10)
    for c in ws4[1]:
        c.font = Font(name=FONTE, size=10, bold=True)

    ws5 = wb.create_sheet("Instruções")
    ws5.column_dimensions["A"].width, ws5.column_dimensions["B"].width, ws5.column_dimensions["C"].width = 30, 70, 60
    titulo(ws5, "Instruções de preenchimento")
    ws5["A2"] = ("Um registo por proposta de alteração (PA). Preencher apenas com informação constante de fontes oficiais. "
                 "Quando a fonte não indicar o valor, deixar a célula em branco e referir a ausência em Observações.")
    ws5["A4"], ws5["B4"], ws5["C4"] = "Campo", "Conteúdo", "Valores admissíveis / formato"
    for ref in ("A4", "B4", "C4"):
        ws5[ref].font = Font(name=FONTE, size=10, bold=True)
    for i, (a, b, c) in enumerate(INSTRUCOES, 5):
        ws5[f"A{i}"], ws5[f"B{i}"], ws5[f"C{i}"] = a, b, c
    i = 5 + len(INSTRUCOES) + 1
    ws5[f"A{i}"] = "Preenchimento automático pela UPE"
    ws5[f"A{i}"].font = Font(name=FONTE, size=10, bold=True)
    ws5[f"A{i + 1}"] = ("As colunas B, C, E, F, G, L, S, T, U e V e as ligações em W são preenchidas a partir dos dados abertos da Assembleia da "
                        "República em cada captura automática. As colunas X em diante são informação adicional publicada pela AR: tema, incidência, "
                        "natureza e estado da PA, avocação, identificadores e ligações. As restantes colunas do modelo (D, H a K, M a R e o texto de W) "
                        "são da DACDP e nunca são alteradas pela sincronização.")
    ws5[f"A{i + 3}"] = "Fontes oficiais"
    ws5[f"A{i + 3}"].font = Font(name=FONTE, size=10, bold=True)
    fontes = [("Ficha da proposta de lei", ed.get("url_iniciativa", "")), ("Página do OE na COFAP", ed.get("url_cofap", "")),
              ("Calendário de apreciação", ed.get("url_calendario", "")), ("Dados abertos — Orçamento do Estado", CONFIG["fontes"]["dados_abertos_pagina_oe"]),
              ("Painel UPE", f"https://upe-sggov.github.io/oe2027-pa/"), ("Repositório", "https://github.com/upe-sggov/oe2027-pa")]
    for j, (a, b) in enumerate([f for f in fontes if f[1]], i + 4):
        ws5[f"A{j}"], ws5[f"B{j}"] = a, b
    for row in ws5.iter_rows():
        for c in row:
            if not c.font.bold:
                c.font = Font(name=FONTE, size=10)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    ws6 = wb.create_sheet("Registo de Consultas")
    cabecalho(ws6, ["Data/hora", "Fonte", "Ligação", "Resultado da consulta", "N.º PA novas"], [18, 34, 60, 70, 12], "A2", filtro=False)
    for c in consultas(pasta, estado_fontes, historico, ed):
        ws6.append(c)
    for row in ws6.iter_rows(min_row=2):
        for c in row:
            c.font = Font(name=FONTE, size=10)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    ws7 = wb.create_sheet("Calendário e Documentos")
    ws7.column_dimensions["A"].width, ws7.column_dimensions["B"].width, ws7.column_dimensions["C"].width, ws7.column_dimensions["D"].width = 22, 60, 50, 40
    titulo(ws7, f"Calendário oficial e documentos publicados (situação a {agora.strftime('%d/%m/%Y')})")
    ws7["A3"], ws7["B3"], ws7["C3"], ws7["D3"] = "Data", "Momento / Documento", "Fonte oficial", "Observações"
    for ref in ("A3", "B3", "C3", "D3"):
        ws7[ref].font = Font(name=FONTE, size=10, bold=True)
    linha = 4
    for c in ed.get("calendario", []):
        ws7[f"A{linha}"], ws7[f"B{linha}"], ws7[f"C{linha}"] = data(c["data"]).strftime("%d/%m/%Y"), c["momento"], ed.get("url_calendario", "")
        linha += 1
    if ed.get("calendario_nota"):
        ws7[f"D{linha - 1}"] = ed["calendario_nota"]
    for d in documentos:
        ws7[f"A{linha}"], ws7[f"B{linha}"], ws7[f"C{linha}"], ws7[f"D{linha}"] = "—", d["titulo"], d["url"], f"Registado no painel em {d.get('primeira_captura', '')[:16].replace('T', ' ')}"
        linha += 1
    for row in ws7.iter_rows(min_row=4):
        for c in row:
            c.font = Font(name=FONTE, size=10)
            c.alignment = Alignment(wrap_text=True, vertical="top")

    folha_resposta(wb, agora)

    saida.parent.mkdir(parents=True, exist_ok=True)
    wb.save(saida)
    return {"ficheiro": str(saida), "registos": len(pa), "pa": len({r["pa_base"] for r in pa}), "consultas": ws6.max_row - 1}


def folha_resposta(wb, agora: dt.datetime) -> None:
    """Folha «Resposta UPE»: o que a captura assegura, o que exige desenvolvimento e as limitações (refeita a cada exportação)."""
    if "Resposta UPE" in wb.sheetnames:
        del wb["Resposta UPE"]
    ws8 = wb.create_sheet("Resposta UPE")
    ws8.column_dimensions["A"].width, ws8.column_dimensions["B"].width, ws8.column_dimensions["C"].width, ws8.column_dimensions["D"].width = 30, 18, 80, 60
    titulo(ws8, "Resposta da UPE ao modelo da DACDP: o que a captura automática assegura, o que exige desenvolvimento e as limitações")
    ws8["A2"] = (f"Gerado automaticamente em {agora.strftime('%d/%m/%Y, %Hh%M')} UTC a partir da informação publicada pela Assembleia da República. "
                 "«Imediato»: preenchido em cada captura. «Desenvolvimento»: sugestão automática a validar pela DACDP. «Limitação»: sem fonte na AR.")
    ws8["A4"], ws8["B4"], ws8["C4"], ws8["D4"] = "Campo", "Classificação", "Como se preenche", "Observações"
    for ref in ("A4", "B4", "C4", "D4"):
        ws8[ref].font = Font(name=FONTE, size=10, bold=True)
    for i, linha_r in enumerate(RESPOSTA, 5):
        for j, v in enumerate(linha_r, 1):
            ws8.cell(row=i, column=j, value=v)
    for row in ws8.iter_rows(min_row=2):
        for c in row:
            if not c.font.bold:
                c.font = Font(name=FONTE, size=10)
            c.alignment = Alignment(wrap_text=True, vertical="top")



def consultas(pasta: Path, estado_fontes: dict, historico: list[dict], ed: dict) -> list[list]:
    """Linhas da folha «Registo de Consultas»: uma por verificação de fonte, acumuladas em consultas.csv."""
    f = pasta / "consultas.csv"
    antigas = ler_csv(f)
    chaves = {(c["momento"], c["fonte"]) for c in antigas}
    novas = []
    novas_por_momento: dict[str, int] = {}
    for h in historico:
        if h.get("evento") == "nova":
            novas_por_momento[h["momento"][:16]] = novas_por_momento.get(h["momento"][:16], 0) + 1
    nomes = {"dados_abertos": ("Dados abertos da AR — ficheiro de PA da edição", CONFIG["fontes"]["dados_abertos_pagina_oe"]),
             "portal": ("Portal da AR — página de cada PA (reserva)", CONFIG["fontes"]["detalhe_pa"].replace("{bid}", "…")),
             "pesquisa": ("Portal da AR — pesquisa de PA", CONFIG["fontes"]["pesquisa_pa"]),
             "documentos": ("Página do OE na COFAP", ed.get("url_cofap", ""))}
    for fonte, e in estado_fontes.items():
        m = (e.get("momento") or "")[:16]
        if not m or (m, fonte) in chaves:
            continue
        if fonte == "dados_abertos":
            res = (f"Ficheiro {e.get('ficheiro', '')}: {e.get('pa', 0)} PA ({e.get('registos', 0)} registos); última entrada {str(e.get('ultima_entrada', ''))[:16].replace('T', ' ')}; "
                   f"atualizado pela AR: {e.get('ultima_modificacao_ar') or '—'}" if e.get("disponivel") else "Ficheiro da edição ainda não publicado na pasta dos dados abertos.")
        elif fonte == "portal":
            res = f"Identificadores {e.get('primeiro_id_testado')}–{e.get('ultimo_id_testado')}: {e.get('novos', 0)} PA novas, {e.get('relidos', 0)} atualizadas" + (f"; erro: {e['erro']}" if e.get("erro") else "")
        else:
            res = json.dumps({k: v for k, v in e.items() if k != "momento"}, ensure_ascii=False)
        novas.append({"momento": m, "fonte": fonte, "resultado": res, "novas": str(novas_por_momento.get(m, 0)) if fonte == "dados_abertos" else ""})
    todas = antigas + novas
    with f.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["momento", "fonte", "resultado", "novas"], delimiter=";")
        w.writeheader()
        w.writerows(todas)
    linhas = []
    for c in sorted(todas, key=lambda c: c["momento"], reverse=True)[:400]:
        nome, url = nomes.get(c["fonte"], (c["fonte"], ""))
        linhas.append([c["momento"].replace("T", " ") + " UTC", nome, url, c["resultado"], int(c["novas"]) if c.get("novas") else None])
    return linhas


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ano", default=CONFIG["edicao_ativa"])
    ap.add_argument("--saida", default="")
    ap.add_argument("--pasta", default="", help="outra pasta de dados (testes)")
    a = ap.parse_args(argv)
    saida = Path(a.saida) if a.saida else RAIZ / "docs" / f"Registo_PA_OE{a.ano}.xlsx"
    print(json.dumps(construir(str(a.ano), saida, Path(a.pasta) if a.pasta else None), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
