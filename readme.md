# eFólio B — Introdução à Inteligência Artificial

Implementação base de **procura adversa** (Minimax + poda alfa-beta) para o eFólio B.

## Execução

```bash
python main.py
```

## Formato de `resultados.csv`

O programa está preparado para o modo de avaliação incremental do enunciado:

- o ficheiro contém **10 linhas** (1 por jogo);
- cada linha contém uma sequência de jogadas separadas por espaço;
- uma linha pode terminar num resultado final: `Brancas`, `Pretas`, `Empate`, `Inválido`, `Erro`.

## Comportamento por chamada

Em **cada execução** de `python main.py`, o programa:

1. Lê `resultados.csv`;
2. Reescreve o ficheiro completo;
3. Acrescenta **exatamente 1 jogada válida** em cada linha/jogo ainda em curso;
4. Não altera linhas já terminadas;
5. Se um histórico for inconsistente, termina esse jogo com `Inválido`.

Isto permite que o avaliador invoque o programa repetidamente até os 10 jogos terminarem.

## Estrutura

- `board.py`: parsing do tabuleiro, coordenadas e utilitários;
- `game_state.py`: estado de jogo, `apply_move`, terminal, vencedor;
- `moves.py`: geração de movimentos válidos;
- `evaluation.py`: função de avaliação heurística;
- `minimax.py`: Minimax com alfa-beta;
- `main.py`: loop incremental de atualização de `resultados.csv`.
