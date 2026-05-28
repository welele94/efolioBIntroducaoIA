"""Experimental variant: active target vision bonus.

This is a lightweight test runner. It imports the current stable `main.py`,
replaces only the evaluation function, and then runs the same CSV protocol.

Do not copy this file over `main.py` directly, because it imports `main`.
To test it locally, run:
    python test_main.py

If this variant is better, we will merge the same evaluate() logic into main.py.
"""

from __future__ import annotations

import main as agent

# Keep majority pressure identical to the current stable main.py.
# The experiment here is only the active capture vision bonus.
VISION_WEIGHT = 15


def active_capture_vision(s: agent.GameState) -> int:
    """Return a small score for immediate capture options from active pieces."""
    a_vision = 0
    v_vision = 0

    if s.a_inside_piece and s.a_active_piece:
        a_vision = len(agent.piece_captures(s, s.a_pos, s.a_active_piece, s.v_pos))

    if s.v_inside_piece and s.v_active_piece:
        v_vision = len(agent.piece_captures(s, s.v_pos, s.v_active_piece, s.a_pos))

    return (a_vision - v_vision) * VISION_WEIGHT


def evaluate_with_vision(s: agent.GameState) -> float:
    if s.is_terminal():
        winner = s.get_winner()
        if winner == "draw":
            return 0
        return agent.WIN_BONUS if winner == "A" else -agent.WIN_BONUS

    score = (s.a_captures - s.v_captures) * agent.CAPTURE_WEIGHT
    a_mob, v_mob = agent.mobility_counts(s)
    score += (a_mob - v_mob) * agent.MOBILITY_WEIGHT
    score += agent.target_distance_score(s) * agent.DISTANCE_WEIGHT
    score += agent.majority_pressure_score(s)
    score += (agent.PIECE_VALUE[s.a_active_piece] - agent.PIECE_VALUE[s.v_active_piece]) * agent.PIECE_VALUE_WEIGHT

    # Experimental feature: prefer being inside a piece that still has
    # immediate legal captures, and penalize the opponent having the same.
    score += active_capture_vision(s)

    if a_mob <= 1:
        score -= agent.BLOCKED_WEIGHT
    if v_mob <= 1:
        score += agent.BLOCKED_WEIGHT
    return score


agent.evaluate = evaluate_with_vision


def main() -> None:
    agent.run_results_csv(agent.RESULTS_PATH, agent.MAX_DEPTH)


if __name__ == "__main__":
    main()
