"""Minimax with alpha-beta pruning."""

from __future__ import annotations

from math import inf

from evaluation import evaluate
from moves import generate_legal_moves



def _order_moves(moves):
    return sorted(moves, key=lambda m: (m.move_type != "capture", m.move_type == "pass"))



def minimax_decision(state, depth: int):
    maximizing = state.current_player == "A"
    best_score = -inf if maximizing else inf
    best_move = None

    for move in _order_moves(generate_legal_moves(state)):
        nxt = state.apply_move(move)
        score = _minimax(nxt, depth - 1, -inf, inf)
        if maximizing and score > best_score:
            best_score, best_move = score, move
        if not maximizing and score < best_score:
            best_score, best_move = score, move

    return best_move



def _minimax(state, depth: int, alpha: float, beta: float):
    if depth == 0 or state.is_terminal():
        return evaluate(state, perspective_player="A")

    if state.current_player == "A":
        value = -inf
        for move in _order_moves(generate_legal_moves(state)):
            value = max(value, _minimax(state.apply_move(move), depth - 1, alpha, beta))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = inf
    for move in _order_moves(generate_legal_moves(state)):
        value = min(value, _minimax(state.apply_move(move), depth - 1, alpha, beta))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value
