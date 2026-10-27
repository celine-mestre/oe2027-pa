# PA ao Orçamento do Estado

Extração automática, base de dados, registo no modelo da DACDP e painel das propostas de alteração (PA) às propostas de lei do Orçamento do Estado, a partir da informação publicada pela Assembleia da República (AR):

- **OE 2027** — Proposta de Lei n.º 110/XVII/2.ª, em curso (PA a partir de 29 de outubro de 2026, 9h00).
- **OE 2026** — Proposta de Lei n.º 37/XVII/1.ª, processo concluído. Base de comparação: é a única edição completa da XVII Legislatura, com a mesma composição parlamentar.

- Painel: https://upe-sggov.github.io/oe2027-pa/ (seletor de edição no canto superior direito)
- Registo no modelo da DACDP (Excel, gerado em cada captura): https://upe-sggov.github.io/oe2027-pa/Registo_PA_OE2027.xlsx
- Repositório: https://github.com/upe-sggov/oe2027-pa

## Fontes

| Fonte | O que dá | Uso |
|---|---|---|
| Dados abertos da AR, categoria «Orçamento do Estado», pasta «XVII Legislatura» — ficheiro `OEPropostasAlteracao<ano>Or` (JSON e XML) | Por PA: número, data e hora de entrada, título, artigo, tema, tipo, incidência, estado, proponentes (grupo parlamentar e deputados), PDF e todas as votações com o sentido de voto de cada grupo | Fonte principal. O ficheiro é localizado automaticamente em cada captura. |
| Página de cada PA no portal da AR (`DetalhePropostaAlteracao.aspx?BID=…`) | Os mesmos campos, proposta a proposta | Reserva e verificação cruzada, em cada captura: procura PA novas a seguir ao maior identificador conhecido (a AR atribui-os por ordem de entrada) e relê as que ainda não foram votadas. Deteta um ficheiro de dados abertos desatualizado. |
| Página do OE na COFAP | Resultados de votações, textos finais, relatórios e pareceres | Lista de documentos no painel (sem os contributos). |
| Calendário de apreciação do OE 2027 (PDF da AR, cópia em `data/calibracao/`) | Datas e horas oficiais | Transcrito em `config.json` e mostrado no painel. |

A agenda parlamentar (e os respetivos dados abertos) tem as reuniões — audições, votações na Comissão de Orçamento, Finanças e Administração Pública (COFAP), debates em Plenário —, mas não as PA.

Uma PA que incide sobre vários artigos ou alíneas é publicada pela AR em partes (por exemplo, `120C-1`, `120C-2`), com a mesma hora de entrada e votações separadas. O painel conta propostas pelo número-base e estados e votações por registo.

## Só dados abertos da AR

Contagens pela convenção da AR: cada registo numerado conta como uma proposta, incluindo as partes (120C-1, 120C-2). O número de propostas distintas (sem partes) é apresentado à parte. A base inclui também, por registo, a epígrafe do artigo, os diplomas alterados, os requerimentos (avocação), os pedidos de parecer às Regiões Autónomas e o campo «Ministerio» dos dados abertos (vazio em 2026).

O painel e o Excel usam exclusivamente variáveis publicadas pela AR. Não há classificações próprias. O separador «Propostas de alteração» agrupa as PA pelo tema que a AR lhes atribui (em 2026, a comissão parlamentar competente) e tem a lista completa, filtrável. Em «Votações», a matriz de posições dos grupos parlamentares cruza esse tema com os sentidos de voto publicados. O separador «Alterações entre capturas» só aparece na edição em curso: mostra o que mudou na publicação da AR desde a captura anterior.

Os scripts `classificar.py` e `indice_ppl.py` e o ficheiro `data/areas_governativas.json` são material preparatório que não corre nos workflows nem entra no painel.

## Registo no modelo da DACDP e sincronização do ficheiro mestre

`scripts/exportar_excel.py` gera, em cada captura, `docs/Registo_PA_OE<ano>.xlsx` com a estrutura do modelo da DACDP (folhas «Propostas de Alteração», «Medidas Anunciadas», «Ponto de Situação», «Listas», «Instruções», «Registo de Consultas», «Calendário e Documentos») e uma folha «Resposta UPE» que diz, coluna a coluna, o que a captura assegura, o que exige desenvolvimento e o que não tem fonte na AR. Nas colunas A–W do modelo, a UPE preenche as que vêm da AR (B, C, E, F, G, L, S, T, U, V e as ligações em W); as colunas X em diante são informação adicional publicada pela AR (tema, incidência, natureza e estado, avocação, identificadores e ligações).


```
python scripts/sincronizar_mestre.py "C:/…/Registo_PA_OE2027.xlsx" --ensaio   # mostra o que faria
python scripts/sincronizar_mestre.py "C:/…/Registo_PA_OE2027.xlsx"            # sincroniza e exporta analise.csv
```

## Como funciona

```
python scripts/fetch_pa.py opendata              # fonte principal (edição ativa: 2027)
python scripts/fetch_pa.py opendata --ano 2026   # OE 2026, processo concluído
python scripts/fetch_pa.py verificar             # reserva incremental pelo portal
python scripts/fetch_pa.py documentos            # documentos da página da COFAP
python scripts/exportar_excel.py --ano 2027      # docs/Registo_PA_OE2027.xlsx
python scripts/build_painel.py                   # docs/index.html (todas as edições)
python scripts/fetch_pa.py listar                # lista os ficheiros publicados na pasta XVII
```

A página de pesquisa de PA (`PesquisaPropAlteracao110XVII.aspx`) não é usada nas capturas automáticas: demora cerca de um minuto por página de 20 resultados.

Se, durante o processo, a captura não estiver a funcionar (nenhuma PA três horas depois de abrir o prazo, ou erros repetidos no portal), o último passo do workflow termina a vermelho e o GitHub envia um aviso por e-mail.

Workflows:
- `atualizar.yml` — corre segundo o calendário (de hora a hora no último dia do prazo e nos dias de votação): captura o OE 2027, exporta os Excel, publica o painel. Guarda em `data/oe2027/raw/` uma cópia de cada captura.
- `calibracao.yml` — manual (ou ao alterar o próprio ficheiro): lista a pasta dos dados abertos, descarrega o calendário e o texto das PPL, carrega o OE 2026 e publica.

## Base de dados (`data/oe<ano>/`)

`pa.csv` (separador «;»): `n_pa`, `pa_base`, `parte`, `id_ar`, `data_entrada`, `proponente`, `proponente_deputados`, `apresentada`, `incide`, `artigo`, `artigo_epigrafe`, `diplomas`, `tipo_ar`, `objeto`, `tema_ar`, `estado_ar`, `estado`, `data_votacao`, `sede_votacao`, `resultado_votacao`, `votos_por_partido`, `avocacao`, `requerimentos`, `parecer_ra`, `ministerio_ar`, `n_votacoes`, `url_detalhe`, `url_pdf`, `primeira_captura`, `ultima_captura`, `fonte`, `ausente_da_fonte`. Todos os campos vêm da AR, exceto os de captura. `estado` agrupa o `estado_ar` publicado (por exemplo, «Rejeitado(a) em Comissão» → rejeitada).

`analise.csv` (quando existir): classificações da DACDP vindas do mestre. `historico.csv`: eventos entre capturas (PA novas, alterações de estado, votações, PA que deixam de constar da publicação). `consultas.csv`: registo das verificações de fontes. `estado_fontes.json`, `documentos.json`, `ultima_execucao.json`: estado da última captura.

## Pontos a confirmar a partir de 29 de outubro

1. O calendário indica que as PA ao OE 2027 serão inseridas numa «nova aplicação». Se a publicação mudar de formato, a primeira captura assinala-o.
2. Não se sabe com que frequência a AR atualiza o ficheiro dos dados abertos durante o prazo. Se não acompanhar a página de pesquisa, a reserva passa a fonte principal.
3. A lista de temas da AR pode diferir da de 2026 (em 2026 correspondia às comissões parlamentares).
