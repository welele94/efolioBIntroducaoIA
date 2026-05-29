from __future__ import annotations

# Experimental wrapper around the stable main.py.
# Use this for local_arena tests only. Do not copy this file over main.py.
from math import inf
from pathlib import Path
from time import perf_counter
from typing import Optional

from main import *  # noqa: F401,F403

THREAT_TOP_N = 3
THREAT_MARGIN = 250


def winning_move_now(s: GameState, moves: list[Move]) -> Optional[Move]:
    player = s.current_player
    for move in moves:
        next_state = s.apply_move(move)
        if next_state.is_terminal() and next_state.get_winner() == player:
            return move
    return None


def opponent_can_win_next(s: GameState) -> bool:
    opponent = s.current_player
    for reply in generate_legal_moves(s):
        next_state = s.apply_move(reply)
        if next_state.is_terminal() and next_state.get_winner() == opponent:
            return True
    return False


def filter_suicidal_moves(s: GameState, moves: list[Move]) -> list[Move]:
    safe = []
    for move in moves:
        next_state = s.apply_move(move)
        if not opponent_can_win_next(next_state):
            safe.append(move)
    return safe if safe else moves


def player_captures(s: GameState, player: str) -> int:
    return s.a_captures if player == "A" else s.v_captures


def player_active_data(s: GameState, player: str):
    if player == "A":
        return s.a_pos, s.a_inside_piece, s.a_active_piece, s.v_pos
    return s.v_pos, s.v_inside_piece, s.v_active_piece, s.a_pos


def reply_danger(after_our_move: GameState, reply: Move) -> int:
    opponent = after_our_move.current_player
    ns = after_our_move.apply_move(reply)

    if ns.is_terminal() and ns.get_winner() == opponent:
        return 10000

    danger = 0
    if reply.move_type == "capture":
        danger += 300

    majority = ns.initial_black_pawns // 2 + 1
    remaining = majority - player_captures(ns, opponent)
    if remaining <= 1:
        danger += 2000
    elif remaining == 2:
        danger += 800
    elif remaining == 3:
        danger += 300

    pos, inside, piece, opp = player_active_data(ns, opponent)
    if inside and piece:
        vision = len(piece_captures(ns, pos, piece, opp))
        danger += vision * 120
        if piece == "D":
            danger += 120
        elif piece in {"T", "B"}:
            danger += 70

    return danger


def candidate_move_danger(s: GameState, move: Move, top_n: int = THREAT_TOP_N) -> int:
    after = s.apply_move(move)
    replies = order_moves(after, generate_legal_moves(after))[:top_n]
    if not replies:
        return 0
    return max(reply_danger(after, reply) for reply in replies)


def filter_high_threat_moves(s: GameState, moves: list[Move]) -> list[Move]:
    if len(moves) <= 1:
        return moves
    danger_pairs = [(candidate_move_danger(s, move), move) for move in moves]
    min_danger = min(d for d, _ in danger_pairs)
    safer = [move for d, move in danger_pairs if d <= min_danger + THREAT_MARGIN]
    return safer if safer else moves


def minimax_decision(s: GameState, depth: int, time_limit: float) -> Optional[Move]:
    deadline = perf_counter() + (time_limit * 0.80)
    legal_moves = order_moves(s, generate_legal_moves(s))
    if not legal_moves:
        return None

    win_now = winning_move_now(s, legal_moves)
    if win_now is not None:
        return win_now

    legal_moves = order_moves(s, filter_suicidal_moves(s, legal_moves))
    legal_moves = order_moves(s, filter_high_threat_moves(s, legal_moves))

    best_completed_move = legal_moves[0]
    maximizing = s.current_player == "A"
    table: dict[tuple, tuple[int, float]] = {}

    for current_depth in range(1, depth + 1):
        if perf_counter() >= deadline:
            break
        try:
            best_score = -inf if maximizing else inf
            best_move = None
            for move in legal_moves:
                score = minimax(s.apply_move(move), current_depth - 1, -inf, inf, deadline, table)
                if maximizing and score > best_score:
                    best_score, best_move = score, move
                elif not maximizing and score < best_score:
                    best_score, best_move = score, move
            if best_move is not None:
                best_completed_move = best_move
        except SearchTimeout:
            break
    return best_completed_move


def update_tokens(tokens: list[str], line_index: int, depth: int, deadline: float) -> list[str]:
    if tokens and tokens[-1] in TERMINAL_TOKENS:
        return tokens

    s = rebuild_state(tokens)
    if s is None:
        return tokens + ["Inválido"]
    if s.is_terminal():
        return tokens + [terminal_token(s)]
    if s.current_player != controlled_player_for_line(line_index):
        return tokens

    book_move = opening_book_move(s, tokens)
    if book_move is not None:
        return append_move_and_result(tokens, s, book_move)

    remaining = min(DEFAULT_TIME_LIMIT, deadline - perf_counter())
    if remaining <= 0:
        move = safe_fallback_move(s)
        return append_move_and_result(tokens, s, move) if move else tokens + ["Erro"]

    move = minimax_decision(s, depth, remaining) or safe_fallback_move(s)
    return append_move_and_result(tokens, s, move) if move else tokens + ["Erro"]


def process_line_raw(line: str, line_index: int, depth: int, deadline: float) -> str:
    stripped = line.strip()
    tokens = stripped.split() if stripped else []
    if tokens and tokens[-1] in TERMINAL_TOKENS:
        return line
    return " ".join(update_tokens(tokens, line_index, depth, deadline))


def run_results_csv(path: Path, depth: int = MAX_DEPTH) -> None:
    deadline = perf_counter() + TIME_BUDGET_SECONDS
    output = [process_line_raw(line, i, depth, deadline) for i, line in enumerate(read_results(path))]
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    run_results_csv(RESULTS_PATH, MAX_DEPTH)


if __name__ == "__main__":
    main()
