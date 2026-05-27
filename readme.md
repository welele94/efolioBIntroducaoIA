# eFólio B — Introdução à Inteligência Artificial

Este projeto é uma **evolução do eFólio A**.

- No **eFólio A**, o problema era de procura clássica com um único agente.
- No **eFólio B**, o problema passa a **procura adversa**, com dois agentes (A e V) a competir por capturas de peões pretos.

## Estrutura

- `main.py`: versão autónoma com todo o código necessário; é o ficheiro a entregar/correr.
- Os restantes ficheiros mantêm a versão modular usada durante desenvolvimento e testes:
- `board.py`: parsing do tabuleiro, coordenadas e utilitários de impressão.
- `game_state.py`: classe `GameState`, aplicação de jogadas e condições de terminal.
- `moves.py`: geração de movimentos legais (rei, capturas em peça, saída da peça e pass).
- `evaluation.py`: função de avaliação com pesos ajustáveis.
- `minimax.py`: Minimax com poda alfa-beta e ordenação simples de jogadas.
- `instances.py`: conjunto de instâncias alternativas para testar o agente.

## Como correr

```bash
python main.py
```

Por defeito, o programa usa o protocolo do avaliador: cria/lê `resultados.csv`, reconstrói cada jogo pelas jogadas já escritas, acrescenta uma jogada válida apenas quando for a vez do nosso agente nessa linha, e grava o ficheiro sem imprimir nada.

O ficheiro `resultados.csv` fica com 10 linhas, uma por jogo. Cada linha é uma sequência simples de casas, por exemplo:

```text
a3 b6 b4
```

Isto significa que foram registadas três jogadas válidas sucessivas: `a3`, depois `b6`, depois `b4`.

As 10 linhas alternam o lado do nosso agente:

- linhas 1, 3, 5, 7 e 9: a referência joga primeiro; o nosso agente joga como Pretas/V.
- linhas 2, 4, 6, 8 e 10: o nosso agente joga primeiro como Brancas/A.

Para testes manuais, o programa também pode escolher apenas uma jogada e imprimir só a casa destino:

```bash
python main.py --list-instances
python main.py --instance open_race --depth 2
python main.py --move --instance official
python main.py --instance knight_tactics --depth 2 --time-limit 1.0
```

Para correr todas as instâncias e comparar resultados:

```bash
python test_instances.py --depth 2
```

## Modo Manual

O modo principal do avaliador é `resultados.csv`. Para testes manuais, o programa também aceita um tabuleiro externo completo com exatamente 64 caracteres.
Nesse modo, o estado é construído diretamente a partir do tabuleiro recebido, são identificadas as posições de `A` e `V`, e a saída é apenas a casa de destino da jogada escolhida, por exemplo `d6`.

```bash
python main.py --board "<string de 64 caracteres>" --player A
```

Também pode ler a string por `stdin`:

```bash
python -c "from instances import get_instance; print(get_instance('open_race'), end='')" | python main.py --board - --player A
```

Se o protocolo fornecer informação adicional, ela pode ser passada assim:

```bash
python main.py --board "<string de 64 caracteres>" --player A --a-captures 2 --v-captures 1 --actions 12 --initial-black-pawns 20
python main.py --board "<string de 64 caracteres>" --player A --a-active-piece D
```

Por defeito, a procura usa profundidade `2` e limite de tempo de `1.0` segundo, para evitar avaliações demasiado demoradas.

## resultados.csv

O modo principal é:

```bash
python main.py
```

Também podes indicar outro ficheiro para testes:

```bash
python main.py --csv --results /tmp/resultados.csv
```

Se o ficheiro não existir, é criado. Se já existir, o programa lê as jogadas anteriores, incluindo as jogadas escritas pelo algoritmo do professor, reconstrói o estado atual e acrescenta no máximo uma jogada por linha ativa. Linhas terminadas com `Brancas`, `Pretas`, `Empate`, `Inválido` ou `Erro` não são alteradas.

## Simulação local

A simulação completa existe apenas para depuração local. Não é o modo principal do avaliador.

```bash
python main.py --simulate --instance official --depth 2
```

## Instâncias de teste

O ficheiro `instances.py` contém cenários pequenos e controlados para testar partes diferentes do algoritmo:

- `official`: instância oficial do enunciado.
- `open_race`: tabuleiro mais aberto para comparar mobilidade e corrida aos peões.
- `capture_race`: peças fáceis de alcançar para testar entrada em peça e capturas.
- `knight_tactics`: cenário focado em movimentos de cavalo.
- `queen_pressure`: cenário com damas para testar linhas, colunas e diagonais.
- `endgame_small`: cenário curto para testar finais rápidos.

## Minimax, alfa-beta e avaliação

O agente escolhe jogadas com Minimax de profundidade limitada.

- **Minimax**: modela o jogo como alternância entre jogador maximizador (A) e minimizador (V).
- **Poda alfa-beta**: corta ramos que não podem melhorar o resultado, reduzindo custo de pesquisa.
- **Função de avaliação**: combina diferença de capturas, mobilidade e proximidade a peões pretos.

A base foi feita para ser simples de evoluir, sobretudo na heurística (`evaluation.py`) e no ajuste de profundidade (`main.py`).
