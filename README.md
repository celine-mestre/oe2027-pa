# PA ao OE 2027 — extração automática, base de dados e painel

Ferramenta da Unidade de Pesquisa e Estatísticas (UPE) para o levantamento das propostas de alteração (PA) à Proposta de Lei n.º 110/XVII/2.ª (Orçamento do Estado para 2027), em apoio ao plano de ação da DACDP (e-mail da Diretora da DSSD de 23 de outubro de 2026).

## 1. O que cabe à UPE (ponto 5 do plano: «Apoio técnico e dados — UPE + Daniel Pardal»)

| Responsabilidade no plano | O que esta ferramenta faz |
|---|---|
| Extração automática do parlamento.pt | `scripts/fetch_pa.py` lê os dados abertos da AR (fonte principal) ou, em reserva, a página de pesquisa de PA e as páginas de detalhe. Guarda um snapshot bruto por execução. |
| Base de dados (ponto 6) | `data/pa.csv` / `data/pa.json` — um registo por PA com os campos do ponto 6; `data/historico.csv` — versões (substituições, retiradas, alterações de estado, votações). |
| Taxonomia (Fase 0) | `data/taxonomia.json` — tipo (AR), natureza, área governativa, estados, relevância. Sugestões automáticas assinaladas como tal. |
| Eventual painel | `scripts/build_painel.py` → `docs/index.html` (autónomo, estilo SGGov): síntese, lista filtrável, votações, medidas anunciadas, histórico, fontes. |
| Captura diária e várias vezes no último dia (Fase 2) | `.github/workflows/atualizar.yml` — 2×/dia na rotina, de hora a hora de 6 a 9 de novembro, de 2 em 2 horas de 18 a 24 de novembro. |

O que **não** faz, por desenho: classificar relevância, estimar impactos, fazer análise jurídica ou qualquer leitura política. Esses campos são preenchidos pela DACDP e pelo Flávio Lopes na folha `data/classificacao_manual.csv`, com fonte, e o painel passa a mostrá-los no lugar das sugestões automáticas.

## 2. Onde estão as PA nos dados abertos da AR

Sim, as PA ao OE constam dos dados abertos da Assembleia da República, numa categoria própria:

- Página de dados abertos: https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx
- Categoria **«Orçamento do Estado»** — «Informação relativa ao processo legislativo de apreciação do Orçamento de Estado e respetivas propostas de alteração», dados da X Legislatura à atual, em XML e JSON: https://www.parlamento.pt/Cidadania/Paginas/DAOE.aspx
- Dentro desta, a pasta **«XVII Legislatura»** contém os ficheiros por orçamento (OE 2026 já existe; o OE 2027 aparecerá quando houver PA, previsivelmente a partir do fim do prazo de 6 de novembro, podendo surgir antes).

Complementarmente, no portal:

- Pesquisa de PA ao OE 2027 (página por PPL, ainda não publicada): `https://www.parlamento.pt/OrcamentoEstado/Paginas/PesquisaPropAlteracao110XVII.aspx` — o padrão foi confirmado com a página do OE 2026 (`PesquisaPropAlteracao37XVII.aspx`).
- Detalhe de cada PA: `https://www.parlamento.pt/OrcamentoEstado/Paginas/DetalhePropostaAlteracao.aspx?BID=...` — com Número, Data, Apresentada, Incide, Objeto, Tema, Tipo, Estado, proponentes, PDF e sentido de voto por grupo parlamentar.
- Página da PPL 110/XVII/2.ª: https://www.parlamento.pt/ActividadeParlamentar/Paginas/DetalheIniciativa.aspx?BID=377352
- Página do OE 2027 na COFAP (calendário, contributos, pareceres UTAO/CFP; terá os resultados de votação em PDF): https://www.parlamento.pt/sites/COM/XVIILeg/5COFAP/Paginas/OE2027.aspx

**Passo único a fazer a partir de um computador da SGGov (o parlamento.pt não é acessível a partir do ambiente onde a ferramenta foi construída):**
abrir a pasta «XVII Legislatura» em https://www.parlamento.pt/Cidadania/Paginas/DAOE.aspx, copiar o URL do ficheiro JSON do OE 2026 e, quando existir, do OE 2027 (formato `https://app.parlamento.pt/webutils/docs/doc.txt?path=...&fich=..._json.txt&Inline=true`) e colar em `config.json` → `fontes.dados_abertos_json_oe2026` / `dados_abertos_json_oe2027`. Depois:

```bash
pip install -r requirements.txt
python scripts/fetch_pa.py opendata --url "<URL do JSON do OE 2026>"   # calibrar o parser com dados reais
python scripts/fetch_pa.py inspect data/raw/<ficheiro>.json            # ver a estrutura, ajustar normalizar_opendata() se faltar algum campo
```

Nota sobre a periodicidade: a AR indica atualização mensal para legislaturas anteriores; para a legislatura atual não declara a cadência. Se o JSON do OE 2027 não acompanhar o ritmo diário, o workflow recorre automaticamente à reserva (`scrape`), que lê o portal diretamente.

## 3. Como correr

```bash
python scripts/fetch_pa.py opendata          # fonte principal
python scripts/fetch_pa.py scrape            # reserva (portal); --max 20 para testar
python scripts/build_painel.py               # gera docs/index.html
```

Para testar sem rede, com uma amostra sintética (dados fictícios, assinalados no painel):

```bash
python scripts/gerar_amostra.py
python scripts/fetch_pa.py normalize data/amostra/t1_opendata.json
python scripts/fetch_pa.py normalize data/amostra/t2_opendata.json
python scripts/build_painel.py --amostra
```

O pacote é entregue sem os ficheiros gerados pela amostra; a primeira captura real cria `data/pa.json`, `data/pa.csv` e `data/historico.csv` de raiz.

## 4. Estrutura da base de dados (`data/pa.csv`, separador «;»)

| Campo | Origem | Correspondência no ponto 6 |
|---|---|---|
| `n_pa`, `bid`, `data_entrada` | AR | N.º da PA · data de entrada |
| `versao`, `versao_anterior` | derivado do histórico (sufixo «-n» e desaparecimentos) | versão (original / substituição) |
| `proponente`, `proponente_deputados` | AR | proponente (partido ou deputados) |
| `artigo`, `incide`, `tipo_ar`, `objeto` | AR | artigo ou mapa alterado / aditado / eliminado |
| `tema_ar` | AR | tema |
| `area_governativa_sug` | taxonomia (tema → área) | área governativa — **sugestão** |
| `natureza_sug` | palavras-chave no objeto | tipo (receita · despesa · norma · leg. avulsa · autorização) — **sugestão** |
| `estado_ar`, `estado` | AR, normalizado | estado |
| `data_votacao`, `resultado_votacao`, `votos_por_partido`, `avocacao` | AR | resultado · sentido de voto por partido · avocação |
| `url_detalhe`, `url_pdf` | AR | — |
| `primeira_captura`, `ultima_captura`, `fonte` | pipeline | rastreabilidade |

Campos manuais, em `data/classificacao_manual.csv` (chave `n_pa`): `natureza`, `area_governativa`, `descricao_sumaria`, `impacto_orcamental_eur`, `fonte_impacto`, `anunciada_previamente`, `data_anuncio`, `fonte_anuncio`, `id_medida`, `relevancia`, `justificacao_relevancia`, `cavaleiro_orcamental`, `analise_juridica`, `observacoes`, `classificado_por`, `data_classificacao`.

Folha ex ante, em `data/medidas_anunciadas.csv`: `id_medida`, `partido`, `data`, `fonte`, `url_fonte`, `descricao`, `custo_anunciado_eur`, `tema`, `area_governativa`, `entregue_como_pa`, `n_pa`, `observacoes`. Liga-se à de PA pelo `n_pa` quando a medida chega a ser entregue (e, no sentido inverso, pelo `id_medida` na classificação manual).

As duas folhas podem ser editadas em Excel (abrir como CSV com «;») ou, se a equipa preferir, convertidas para um livro partilhado; o `build_painel.py` só precisa de as reencontrar como CSV.

## 5. Produtos do ponto 7 e o que o painel dá a cada um

| Produto | Data | Onde sai |
|---|---|---|
| Ponto de situação de medidas anunciadas | 2.ª e 5.ª até 6 nov. | separador «Medidas anunciadas» (fonte por linha) |
| Nota de fecho do prazo das PA | 10 nov. | separador «Síntese»: contagens por proponente, tema e área; «Exportar CSV» para o anexo |
| Dossiê de PA relevantes por área governativa | 17 nov. | filtro «Relevância» + «Área governativa» na lista de PA |
| Ponto de situação das votações | diário, 18–24 nov. | separador «Votações» (resultado por proponente, sentido de voto, aprovadas, avocações) |
| Relatório final | 11 dez. | lista de aprovadas com impacto e área; histórico completo em `data/historico.csv` |

## 6. Publicação

O workflow publica `docs/` no GitHub Pages do repositório (organização `upe-sggov`). Os dados são públicos na origem; a classificação manual é trabalho da DSSD — se não dever ficar visível fora da SGGov, manter o repositório privado e distribuir o `index.html` por e-mail ou pela pasta partilhada (o ficheiro é autónomo).

## 7. Pendências para a reunião de arranque (até 27 out.)

1. URL dos ficheiros JSON do OE 2026 e OE 2027 nos dados abertos (ver secção 2) — Daniel Pardal.
2. Calibrar o parser com o ficheiro do OE 2026 e validar o mapa tema → área governativa contra a orgânica do Governo — UPE.
3. Decidir o repositório (upe-sggov, privado ou público) e quem edita as folhas manuais — DACDP/UPE.
4. Alertas de monitorização de media e feed para a folha de medidas anunciadas — Ana Luísa Dias.
