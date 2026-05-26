"""Static evaluation function for adversarial search."""

from moves import generate_legal_moves

WIN_BONUS = 10000
CAPTURE_WEIGHT = 120
MOBILITY_WEIGHT = 4
PAWN_DISTANCE_WEIGHT = 2



def _nearest_black_pawn_distance(state, pos):
    best = None
    for r in range(8):
        for c in range(8):
            if state.board[r][c] == "p":
                d = abs(pos[0] - r) + abs(pos[1] - c)
                best = d if best is None else min(best, d)
    return best



def evaluate(state, perspective_player: str = "A") -> float:
    if state.is_terminal():
        winner = state.get_winner()
        if winner == "draw":
            return 0
        score = WIN_BONUS if winner == "A" else -WIN_BONUS
        return score if perspective_player == "A" else -score

    capture_score = (state.a_captures - state.v_captures) * CAPTURE_WEIGHT

    player_backup = state.current_player
    state.current_player = "A"
    a_mob = len(generate_legal_moves(state))
    state.current_player = "V"
    v_mob = len(generate_legal_moves(state))
    state.current_player = player_backup

    mobility_score = (a_mob - v_mob) * MOBILITY_WEIGHT

    a_dist = _nearest_black_pawn_distance(state, state.a_pos)
    v_dist = _nearest_black_pawn_distance(state, state.v_pos)
    distance_score = 0
    if a_dist is not None and v_dist is not None:
        distance_score = (v_dist - a_dist) * PAWN_DISTANCE_WEIGHT

    total = capture_score + mobility_score + distance_score
    return total if perspective_player == "A" else -total
