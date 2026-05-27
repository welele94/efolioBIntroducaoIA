from __future__ import annotations

import csv
from pathlib import Path

from main import (
    DEFAULT_TIME_LIMIT,
    MAX_DEPTH,
    RECENT_OWN_LIMIT,
    create_initial_state,
    generate_legal_moves,
    minimax_decision,
)

OUTPUT_PATH = Path("resultados_selfplay.csv")


def board_with_agents(state):
    board = [row[:] for row in state.board]
    ar, ac = state.a_pos
    vr, vc = state.v_pos
    board[ar][ac] = "A"
    board[vr][vc] = "V"
    return board


def board_to_string(state) -> str:
    return "/".join("".join(row) for row in board_with_agents(state))


def print_board(state) -> None:
    board = board_with_agents(state)
    print("   a b c d e f g h")
    print("  -----------------")
    for r in range(8):
        rank = 8 - r
        print(f"{rank}|" + " ".join(board[r]) + f"|{rank}")
    print("  -----------------")
    print("   a b c d e f g h")


def print_state_summary(state) -> None:
    print(f"Capturas A: {state.a_captures} | Capturas V: {state.v_captures}")
    print(
        "A:"
        f" pos={state.a_pos} dentro={state.a_inside_piece} peça={state.a_active_piece}"
        " | "
        "V:"
        f" pos={state.v_pos} dentro={state.v_inside_piece} peça={state.v_active_piece}"
    )


def write_selfplay_csv(rows: list[dict[str, object]], final_sequence: str, final_state) -> None:
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")

        writer.writerow(["Resumo"])
        writer.writerow(["Sequencia", final_sequence])
        writer.writerow(["Total de acoes", final_state.action_count])
        writer.writerow(["Capturas A", final_state.a_captures])
        writer.writerow(["Capturas V", final_state.v_captures])
        writer.writerow(["Vencedor", final_state.get_winner()])
        writer.writerow([])

        writer.writerow([
            "acao",
            "jogador",
            "jogada",
            "tipo",
            "legais",
            "recentes_proprias",
            "capturas_A",
            "capturas_V",
            "A_pos",
            "V_pos",
            "A_dentro",
            "V_dentro",
            "A_peca",
            "V_peca",
            "tabuleiro",
        ])

        for row in rows:
            writer.writerow([
                row["acao"],
                row["jogador"],
                row["jogada"],
                row["tipo"],
                row["legais"],
                row["recentes_proprias"],
                row["capturas_A"],
                row["capturas_V"],
                row["A_pos"],
                row["V_pos"],
                row["A_dentro"],
                row["V_dentro"],
                row["A_peca"],
                row["V_peca"],
                row["tabuleiro"],
            ])


def self_play(max_turns: int = 60, time_limit: float = 0.30, show_board: bool = True) -> None:
    state = create_initial_state()
    moves: list[str] = []
    rows: list[dict[str, object]] = []
    recent_by_player: dict[str, list[str]] = {"A": [], "V": []}

    print("=== SELF-PLAY: nosso agente vs cópia do nosso agente ===")
    print(f"MAX_DEPTH={MAX_DEPTH} | time_limit por jogada={time_limit}s")
    print(f"Anti-loop raiz: últimas {RECENT_OWN_LIMIT} casas próprias")
    print_state_summary(state)
    if show_board:
        print_board(state)

    while not state.is_terminal() and state.action_count < max_turns:
        player = state.current_player
        recent_own = set(recent_by_player[player][-RECENT_OWN_LIMIT:])
        legal_moves = generate_legal_moves(state)
        move = minimax_decision(state, depth=MAX_DEPTH, time_limit=time_limit, recent_own=recent_own)

        if move is None:
            move = legal_moves[0]

        moves.append(move.notation)

        print()
        print(
            f"{state.action_count + 1:02d}. {player} joga {move.notation} "
            f"({move.move_type}) | legais={len(legal_moves)} | recentes={sorted(recent_own)}"
        )

        state = state.apply_move(move)
        recent_by_player[player].append(move.notation)

        rows.append({
            "acao": state.action_count,
            "jogador": player,
            "jogada": move.notation,
            "tipo": move.move_type,
            "legais": len(legal_moves),
            "recentes_proprias": " ".join(sorted(recent_own)),
            "capturas_A": state.a_captures,
            "capturas_V": state.v_captures,
            "A_pos": state.a_pos,
            "V_pos": state.v_pos,
            "A_dentro": state.a_inside_piece,
            "V_dentro": state.v_inside_piece,
            "A_peca": state.a_active_piece or "",
            "V_peca": state.v_active_piece or "",
            "tabuleiro": board_to_string(state),
        })

        print_state_summary(state)

        if show_board:
            print_board(state)

    final_sequence = " ".join(moves)
    write_selfplay_csv(rows, final_sequence, state)

    print()
    print("=== FIM ===")
    print("Sequência:")
    print(final_sequence)
    print(f"Total de ações: {state.action_count}")
    print(f"Capturas A: {state.a_captures}")
    print(f"Capturas V: {state.v_captures}")
    print(f"Vencedor: {state.get_winner()}")
    print(f"CSV gravado em: {OUTPUT_PATH}")


if __name__ == "__main__":
    self_play(time_limit=min(0.30, DEFAULT_TIME_LIMIT), show_board=True)
