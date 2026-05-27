from __future__ import annotations

from main import (
    DEFAULT_TIME_LIMIT,
    MAX_DEPTH,
    create_initial_state,
    generate_legal_moves,
    minimax_decision,
)


def board_with_agents(state):
    board = [row[:] for row in state.board]
    ar, ac = state.a_pos
    vr, vc = state.v_pos
    board[ar][ac] = "A"
    board[vr][vc] = "V"
    return board


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


def self_play(max_turns: int = 60, time_limit: float = 0.30, show_board: bool = True) -> None:
    state = create_initial_state()
    moves: list[str] = []

    print("=== SELF-PLAY: nosso agente vs cópia do nosso agente ===")
    print(f"MAX_DEPTH={MAX_DEPTH} | time_limit por jogada={time_limit}s")
    print_state_summary(state)
    if show_board:
        print_board(state)

    while not state.is_terminal() and state.action_count < max_turns:
        player = state.current_player
        legal_moves = generate_legal_moves(state)
        move = minimax_decision(state, depth=MAX_DEPTH, time_limit=time_limit)

        if move is None:
            move = legal_moves[0]

        moves.append(move.notation)

        print()
        print(
            f"{state.action_count + 1:02d}. {player} joga {move.notation} "
            f"({move.move_type}) | legais={len(legal_moves)}"
        )

        state = state.apply_move(move)
        print_state_summary(state)

        if show_board:
            print_board(state)

    print()
    print("=== FIM ===")
    print("Sequência:")
    print(" ".join(moves))
    print(f"Total de ações: {state.action_count}")
    print(f"Capturas A: {state.a_captures}")
    print(f"Capturas V: {state.v_captures}")
    print(f"Vencedor: {state.get_winner()}")


if __name__ == "__main__":
    self_play(time_limit=min(0.30, DEFAULT_TIME_LIMIT), show_board=True)
