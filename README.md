# PA ao OE 2027

Extração automática e painel das propostas de alteração (PA) à Proposta de Lei n.º 110/XVII/2.ª (Orçamento do Estado para 2027), exclusivamente a partir da informação publicada pela Assembleia da República (AR).

- Painel: https://upe-sggov.github.io/oe2027-pa/
- Repositório: https://github.com/upe-sggov/oe2027-pa

## Fontes

| Fonte | O que dá | Uso |
|---|---|---|
| Dados abertos da AR, categoria «Orçamento do Estado», pasta «XVII Legislatura» — ficheiro `OEPropostasAlteracao<ano>Or` (JSON e XML) | Por PA: número, data e hora de entrada, título, artigo, tema, tipo, incidência, estado, proponentes (grupo parlamentar e deputados), PDF e todas as votações com o sentido de voto de cada grupo | Fonte principal. O ficheiro é localizado automaticamente em cada captura. |
| Pesquisa de PA (`PesquisaPropAlteracao110XVII.aspx`) e detalhe de cada PA (`DetalhePropostaAlteracao.aspx?BID=…`) | O mesmo, página a página | Reserva, se o ficheiro dos dados abertos não estiver disponível ou atualizado. |
| Calendário de apreciação do OE 2027 (PDF da AR, cópia em `data/calibracao/`) | Datas e horas oficiais | Transcrito em `config.json` e mostrado no painel. |

A agenda parlamentar (e os respetivos dados abertos) tem as reuniões — audições, votações na Comissão de Orçamento, Finanças e Administração Pública (COFAP), debates em Plenário —, mas não as PA.

Uma PA que incide sobre vários artigos ou alíneas é publicada pela AR em partes (por exemplo, `120C-1`, `120C-2`), com a mesma hora de entrada e votações separadas. O painel conta propostas pelo número-base e estados e votações por registo.

As propostas de alteração começam a ser registadas a 29 de outubro, às 9h00 (início do prazo de inserção, segundo o calendário da AR). Até lá, o painel está vazio.

## Como funciona

```
python scripts/fetch_pa.py opendata    # fonte principal
python scripts/fetch_pa.py scrape      # reserva
python scripts/build_painel.py         # gera docs/index.html
python scripts/fetch_pa.py listar      # lista os ficheiros publicados na pasta XVII
```

O workflow `.github/workflows/atualizar.yml` corre segundo o calendário (de hora a hora no último dia do prazo e nos dias de votação), guarda em `data/raw/` uma cópia de cada captura, atualiza `data/pa.csv` e `data/historico.csv` e publica o painel. O workflow `calibracao.yml` (manual) lista os ficheiros publicados na pasta dos dados abertos e descarrega o calendário oficial.

## Base de dados (`data/pa.csv`, separador «;»)

`n_pa`, `pa_base`, `parte`, `id_ar`, `data_entrada`, `proponente`, `proponente_deputados`, `apresentada`, `incide`, `artigo`, `tipo_ar`, `objeto`, `tema_ar`, `estado_ar`, `estado`, `data_votacao`, `sede_votacao`, `resultado_votacao`, `votos_por_partido`, `avocacao`, `n_votacoes`, `url_detalhe`, `url_pdf`, `primeira_captura`, `ultima_captura`, `fonte`, `ausente_da_fonte`.

Todos os campos vêm da AR, exceto os de captura. `estado` agrupa o `estado_ar` publicado (por exemplo, «Rejeitado(a) em Comissão» → rejeitada). `historico.csv` regista, entre capturas, as PA novas, as alterações de estado, as votações e as PA que deixam de constar da publicação.

## Pontos a confirmar a partir de 29 de outubro

1. O calendário indica que as PA ao OE 2027 serão inseridas numa «nova aplicação». Se a publicação mudar de formato, a primeira captura assinala-o.
2. Não se sabe com que frequência a AR atualiza o ficheiro dos dados abertos durante o prazo. Se não acompanhar a página de pesquisa, a reserva passa a fonte principal.
