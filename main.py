"""Incremental runner for eFólio B (one move per active game per call)."""

from __future__ import annotations

import time
from pathlib import Path

from game_state import create_initial_state
from minimax import minimax_decision
from moves import generate_legal_moves

RESULTS_PATH = Path("resultados.csv")
MAX_DEPTH = 3
MAX_GAMES = 10
TERMINAL_TOKENS = {"Brancas", "Pretas", "Empate", "Inválido", "Erro"}
TIME_BUDGET_SECONDS = 19.0


def _parse_tokens(line: str) -> list[str]:
    stripped = line.strip()
    return stripped.split() if stripped else []


def _rebuild_state_from_tokens(tokens: list[str]):
    state = create_initial_state()
    for token in tokens:
        if token in TERMINAL_TOKENS:
            break
        legal = generate_legal_moves(state)
        found = next((m for m in legal if m.notation == token), None)
        if found is None:
            return None
        state = state.apply_move(found)
    return state


def _append_single_move_or_result(tokens: list[str], global_deadline: float) -> list[str]:
    if tokens and tokens[-1] in TERMINAL_TOKENS:
        return tokens

    state = _rebuild_state_from_tokens(tokens)
    if state is None:
        return tokens + ["Inválido"]

    if state.is_terminal():
        winner = state.get_winner()
        if winner == "A":
            return tokens + ["Brancas"]
        if winner == "V":
            return tokens + ["Pretas"]
        return tokens + ["Empate"]

    # keep per-game move computation bounded to ~1 second and global cap under 19 seconds
    search_start = time.perf_counter()
    move = minimax_decision(state, depth=MAX_DEPTH)
    elapsed = time.perf_counter() - search_start
    if elapsed > 1.0 or time.perf_counter() > global_deadline:
        return tokens + ["Erro"]

    if move is None:
        return tokens + ["Erro"]

    return tokens + [move.notation]


def main() -> None:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError("resultados.csv não existe. O ficheiro deve ser fornecido pelo avaliador.")

    lines = RESULTS_PATH.read_text(encoding="utf-8").splitlines()
    if len(lines) < MAX_GAMES:
        lines.extend([""] * (MAX_GAMES - len(lines)))
    lines = lines[:MAX_GAMES]

    deadline = time.perf_counter() + TIME_BUDGET_SECONDS
    updated_lines: list[str] = []

    for line in lines:
        tokens = _parse_tokens(line)
        updated_tokens = _append_single_move_or_result(tokens, deadline)
        updated_lines.append(" ".join(updated_tokens))

    RESULTS_PATH.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
