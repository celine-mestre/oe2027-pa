# PA ao Orçamento do Estado

Extração automática, base de dados, painel e Excel das propostas de alteração (PA) às propostas de lei do Orçamento do Estado, exclusivamente a partir da informação publicada pela Assembleia da República (AR).

| Edição | Proposta de lei | Situação |
|---|---|---|
| OE 2027 | Proposta de Lei n.º 110/XVII/2.ª | Em curso. PA registadas a partir de 29 de outubro de 2026, às 9h00 (início do prazo de inserção, segundo o calendário da AR). |
| OE 2026 | Proposta de Lei n.º 37/XVII/1.ª | Concluída e congelada: dados fixados a 27 out. 2026 (ficheiro final dos dados abertos, 2 193 registos). Nenhum script ou workflow volta a escrever nesta edição (`"congelada": true` em `config.json`). |

- Painel: https://upe-sggov.github.io/oe2027-pa/ (seletor de edição no canto superior direito)
- Base completa em Excel: https://upe-sggov.github.io/oe2027-pa/PA_OE2027_dados_AR.xlsx (e `PA_OE2026_dados_AR.xlsx`)
- Repositório: https://github.com/upe-sggov/oe2027-pa

## Fontes

Só informação publicada pela AR, tal como publicada (títulos, temas e estados sem reescrita). Não há classificações próprias. Em cada edição só entram registos dessa edição: no OE 2027 todas as PA entraram a partir de 29 out. 2026, e os artigos que a AR associa a Orçamentos anteriores não são usados (ver ponto 4 abaixo).

| Fonte | O que dá | Uso |
|---|---|---|
| [Dados abertos da AR](https://www.parlamento.pt/Cidadania/Paginas/DAOE.aspx), categoria «Orçamento do Estado», pasta «XVII Legislatura»: ficheiro `OEPropostasAlteracao<ano>Or_json.txt` (também em XML) | Por registo: número, data e hora de entrada, título, artigo e epígrafe, diplomas alterados, tema, tipo, incidência, estado, proponentes (grupo parlamentar e deputados), requerimentos, pedidos de parecer às Regiões Autónomas, PDF e todas as votações com o sentido de voto de cada grupo parlamentar | Fonte principal. O ficheiro é localizado automaticamente em cada captura (os endereços da AR mudam). |
| Página de cada PA no portal da AR (`DetalhePropostaAlteracao.aspx?BID=…`) | Os mesmos campos, proposta a proposta | Reserva e verificação cruzada: procura PA novas a seguir ao maior identificador conhecido (a AR atribui-os por ordem de entrada) e relê as que ainda não foram votadas. |
| Página do OE na Comissão de Orçamento, Finanças e Administração Pública (COFAP) | Guiões e resultados de votações, textos finais, relatórios e pareceres | Lista de documentos no separador «Votações» (sem os contributos de entidades e cidadãos). |
| Calendário de apreciação do OE 2027 (PDF da AR, cópia em `data/calibracao/`) | Datas e horas oficiais | Transcrito em `config.json` e mostrado na Síntese. |

A página de pesquisa de PA do portal não é usada nas capturas automáticas. O endereço `PesquisaPropAlteracao110XVII.aspx` não existe na nova aplicação da AR (29 out. 2026); o painel só mostra a ligação quando `url_pesquisa_pa` estiver confirmado na edição, em `config.json`. A agenda parlamentar tem as reuniões (audições, votações, debates), mas não as PA.

## Contagens

- Convenção da AR: cada registo numerado conta como uma proposta. Quando uma PA altera vários artigos ou alíneas, a AR divide-a em partes (`120C-1`, `120C-2`), com a mesma hora de entrada e votações separadas. Cada parte conta como um registo.
- O número de propostas distintas (número-base, sem partes) é apresentado à parte.
- `estado` agrupa o estado publicado pela AR (por exemplo, «Rejeitado(a) em Comissão» → rejeitada; «Aprovado(a) por Unanimidade em Comissão» → aprovada).
- O tema é o atribuído pela AR a cada PA (em 2026, corresponde à comissão parlamentar competente). Uma PA com vários temas conta em cada um deles.
- Referência para 2026: o ficheiro final dos dados abertos tem 2 193 registos e 2 076 propostas distintas.

## Painel

| Separador | Conteúdo |
|---|---|
| Síntese | Total e distribuição por estado, indicadores (com explicação no botão «i»), últimas 24 horas, estado das fontes, PA por proponente e resultado, entradas por dia e por hora, PA por tema e por tipo, calendário de apreciação. |
| Propostas de alteração | PA por tema e resultado, resultado por tema, tema × proponente e a lista completa, com pesquisa, filtros e exportação para Excel da seleção. |
| Votações | Resultado por proponente, sentido de voto por grupo parlamentar, posição dos grupos por tema, voto de cada grupo nas PA de cada proponente, documentos da COFAP e detalhe das votações. |
| Alterações entre capturas | Só na edição em curso: o que mudou na publicação da AR desde a captura anterior (PA novas, alterações de estado, votações, PA que deixam de constar). |
| Fontes e método | Ligações às fontes da AR e descrição do método. |

O painel é um único ficheiro HTML (`docs/index.html`), com modo claro e escuro, ecrã inteiro e impressão em A4 horizontal com cores. O endereço guarda a edição e o separador (por exemplo, `#oe2026/votacoes`), para partilhar ligações diretas.

## Excel

`scripts/exportar_dados.py` gera, em cada captura, `docs/PA_OE<ano>_dados_AR.xlsx`:

- folha «Propostas»: uma linha por registo publicado pela AR, com as mesmas colunas da exportação feita no painel;
- folha «Sobre este ficheiro»: fonte, data dos dados, número de registos e de propostas distintas.

No painel, o botão «Exportar para Excel» descarrega as propostas visíveis com os filtros escolhidos (sem filtros, todas). Se a biblioteca de Excel não carregar, descarrega a base completa.

## Capturas automáticas (GitHub Actions)

`.github/workflows/atualizar.yml` captura o OE 2027, gera o Excel, publica o painel e guarda uma cópia de cada captura em `data/oe2027/raw/`. Horas de Lisboa (= UTC até março):

| Período | Capturas |
|---|---|
| 29 out. (abertura do prazo) | 7h15, de hora a hora das 10h15 às 18h15, 19h15 |
| 30 out. – 4 nov. | 7h15 e 19h15 |
| 5 nov. | de 2 em 2 horas, das 8h às 22h |
| 6 nov. (fim do prazo) | de hora a hora, das 7h às 23h |
| 7 – 8 nov. | 9 por dia (entradas tardias) |
| 9 nov. (plano de contingência) | de hora a hora, das 7h às 23h |
| 10 – 17 nov. (guiões) | 7h15 e 19h15 |
| 18 – 20 e 23 – 24 nov. (votações) | 7h10, 13h10 e de hora a hora das 16h10 às 23h10 |
| 25 – 30 nov. | 7h15 e 19h15 |
| 1 – 11 dez. | 7h15 |

O workflow corre também quando o código é alterado. Se, durante o processo, a captura não estiver a funcionar (nenhuma PA três horas depois de abrir o prazo, ou erros repetidos no portal), o último passo termina a vermelho e o GitHub envia um aviso por e-mail.

`.github/workflows/calibracao.yml` (manual, ou quando o próprio ficheiro é alterado): lista a pasta dos dados abertos, descarrega o calendário e o texto da proposta de lei do OE 2027, gera o Excel e publica o painel. Não mexe no OE 2026.

## Comandos

```
python scripts/fetch_pa.py opendata              # dados abertos, edição ativa (2027)
python scripts/fetch_pa.py verificar             # reserva incremental pelo portal
python scripts/fetch_pa.py documentos            # documentos da página da COFAP
python scripts/fetch_pa.py listar                # ficheiros publicados na pasta XVII dos dados abertos
python scripts/exportar_dados.py --ano 2027      # docs/PA_OE2027_dados_AR.xlsx
python scripts/build_painel.py                   # docs/index.html (todas as edições)
python scripts/verificar_estado.py               # alerta usado no workflow
```

Dependências em `requirements.txt` (requests, beautifulsoup4, truststore, openpyxl).

## Base de dados (`data/oe<ano>/`)

| Ficheiro | Conteúdo |
|---|---|
| `pa.json`, `pa.csv` (separador «;») | Um registo por PA ou parte de PA, última versão publicada. |
| `historico.csv` | Eventos entre capturas: nova, estado alterado, votada, ausente da fonte. |
| `consultas.csv` | Registo das verificações das fontes. |
| `estado_fontes.json`, `ultima_execucao.json` | Estado da última captura. |
| `documentos.json` | Documentos da página da COFAP. |
| `raw/` | Cópia comprimida de cada captura, tal como a AR a publicou. |

Campos de `pa.csv`: `n_pa`, `pa_base`, `parte`, `id_ar`, `data_entrada`, `proponente`, `proponente_deputados`, `apresentada`, `incide`, `artigo`, `artigo_epigrafe`, `diplomas`, `tipo_ar`, `objeto`, `tema_ar`, `estado_ar`, `estado`, `data_votacao`, `sede_votacao`, `resultado_votacao`, `votos_por_partido`, `avocacao`, `requerimentos`, `parecer_ra`, `ministerio_ar`, `n_votacoes`, `url_detalhe`, `url_pdf`, `primeira_captura`, `ultima_captura`, `fonte`, `ausente_da_fonte`. Todos vêm da AR, exceto os de captura (`primeira_captura`, `ultima_captura`, `fonte`, `ausente_da_fonte`) e o agrupamento `estado`.

Configuração em `config.json` (edições, ligações, calendário) e `data/taxonomia.json` (siglas dos partidos, agrupamento dos estados, cores).

Os scripts `classificar.py`, `indice_ppl.py`, `exportar_excel.py` e `sincronizar_mestre.py` e o ficheiro `data/areas_governativas.json` não correm nos workflows nem alimentam o painel.

## Pontos a confirmar a partir de 29 de outubro

1. O calendário indica que as PA ao OE 2027 serão inseridas numa «nova aplicação». Se a publicação mudar de formato, a primeira captura assinala-o.
2. Não se sabe com que frequência a AR atualiza o ficheiro dos dados abertos durante o prazo. Se não acompanhar o portal, a reserva passa a fonte principal.
3. A lista de temas da AR pode diferir da de 2026.
4. Artigo: na nova aplicação, algumas PA chegam ligadas a artigos de Orçamentos anteriores (ex.: «Artigo 1.º – Aprovação» do OE 2006, «Artigo 6.º – Transferências orçamentais»). `fetch_pa.py` só aceita o artigo associado quando o número e a epígrafe coincidem com o índice do texto da proposta de lei (`data/oe2027/ppl.html`); caso contrário, fica em branco.
5. O campo «Ministerio» dos dados abertos veio vazio em 2026; fica registado caso a AR o preencha em 2027.
