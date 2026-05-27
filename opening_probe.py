from __future__ import annotations

from main import (
    MAX_DEPTH,
    DEFAULT_TIME_LIMIT,
    create_initial_state,
    generate_legal_moves,
    minimax_decision,
)


def probe_opening(turns: int = 8, time_limit: float = 0.30) -> None:
    state = create_initial_state()
    played: list[str] = []

    print("=== OPENING PROBE ===")
    print(f"MAX_DEPTH={MAX_DEPTH} | time_limit={time_limit}s")
    print()

    for turn in range(1, turns + 1):
        player = state.current_player
        legal_moves = generate_legal_moves(state)
        ordered = sorted(legal_moves, key=lambda move: move.notation)

        print(f"Turno {turn} | jogador {player}")
        print(f"Jogadas já feitas: {' '.join(played) if played else '(nenhuma)'}")
        print(f"N.º de jogadas legais: {len(legal_moves)}")
        print("Jogadas legais:", ", ".join(move.notation for move in ordered))

        chosen = minimax_decision(state, depth=MAX_DEPTH, time_limit=time_limit)
        if chosen is None:
            chosen = legal_moves[0]

        print(f"Jogada escolhida pelo agente: {chosen.notation} ({chosen.move_type})")
        print("---")

        played.append(chosen.notation)
        state = state.apply_move(chosen)

        if state.is_terminal():
            print("Estado terminal atingido.")
            break

    print()
    print("Sequência gerada:")
    print(" ".join(played))


if __name__ == "__main__":
    probe_opening()
