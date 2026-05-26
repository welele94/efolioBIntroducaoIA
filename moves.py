"""Move generation and move representation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from board import BOARD_SIZE, coord_to_notation, in_bounds

Coord = Tuple[int, int]

WHITE_PIECES = {"P", "T", "B", "C", "D"}
SLIDING_DIRECTIONS = {
    "T": [(-1, 0), (1, 0), (0, -1), (0, 1)],
    "B": [(-1, -1), (-1, 1), (1, -1), (1, 1)],
    "D": [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)],
}
KNIGHT_DELTAS = [
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
]
KING_DELTAS = [
    (-1, -1),
    (-1, 0),
    (-1, 1),
    (0, -1),
    (0, 1),
    (1, -1),
    (1, 0),
    (1, 1),
]


@dataclass(frozen=True)
class Move:
    from_pos: Coord
    to_pos: Coord
    move_type: str  # king, capture, exit, pass
    captured_piece: Optional[str] = None
    notation: str = ""



def make_notation(from_pos: Coord, to_pos: Coord, move_type: str) -> str:
    if move_type == "pass":
        return f"{coord_to_notation(from_pos)}-pass"
    return f"{coord_to_notation(from_pos)}->{coord_to_notation(to_pos)}[{move_type}]"



def is_adjacent(a: Coord, b: Coord) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1



def _is_adjacent_or_same(a: Coord, b: Coord) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1



def _agent_data(state, player: str):
    if player == "A":
        return state.a_pos, state.a_inside_piece, state.a_active_piece, state.v_pos
    return state.v_pos, state.v_inside_piece, state.v_active_piece, state.a_pos



def generate_legal_moves(state) -> List[Move]:
    player = state.current_player
    pos, inside_piece, active_piece, opp_pos = _agent_data(state, player)
    legal_moves: List[Move] = []

    if inside_piece and active_piece:
        legal_moves.extend(_generate_piece_capture_moves(state, pos, active_piece, opp_pos))
        legal_moves.extend(_generate_exit_moves(state, pos, opp_pos))
    else:
        legal_moves.extend(_generate_king_moves(state, pos, opp_pos))

    if not legal_moves:
        return [Move(pos, pos, "pass", notation=make_notation(pos, pos, "pass"))]

    return legal_moves



def _generate_king_moves(state, pos: Coord, opp_pos: Coord) -> List[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if _is_adjacent_or_same((nr, nc), opp_pos):
            continue

        cell = state.board[nr][nc]
        if cell in {" ", "T", "B", "C", "D"}:
            move = Move(pos, (nr, nc), "king", notation=make_notation(pos, (nr, nc), "king"))
            moves.append(move)
    return moves



def _generate_exit_moves(state, pos: Coord, opp_pos: Coord) -> List[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if _is_adjacent_or_same((nr, nc), opp_pos):
            continue
        if state.board[nr][nc] != " ":
            continue
        move = Move(pos, (nr, nc), "exit", notation=make_notation(pos, (nr, nc), "exit"))
        moves.append(move)
    return moves



def _generate_piece_capture_moves(state, pos: Coord, piece: str, opp_pos: Coord) -> List[Move]:
    if piece in {"T", "B", "D"}:
        return _sliding_captures(state, pos, piece, opp_pos)
    if piece == "C":
        return _knight_captures(state, pos, opp_pos)
    return []



def _sliding_captures(state, pos: Coord, piece: str, opp_pos: Coord) -> List[Move]:
    moves = []
    for dr, dc in SLIDING_DIRECTIONS[piece]:
        nr, nc = pos[0] + dr, pos[1] + dc
        while in_bounds(nr, nc):
            cell = state.board[nr][nc]
            if cell == " ":
                nr += dr
                nc += dc
                continue

            if cell == "p" and not _is_adjacent_or_same((nr, nc), opp_pos):
                mv = Move(pos, (nr, nc), "capture", captured_piece="p", notation=make_notation(pos, (nr, nc), "capture"))
                moves.append(mv)
            break
    return moves



def _knight_captures(state, pos: Coord, opp_pos: Coord) -> List[Move]:
    moves = []
    for dr, dc in KNIGHT_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if _is_adjacent_or_same((nr, nc), opp_pos):
            continue
        if state.board[nr][nc] == "p":
            mv = Move(pos, (nr, nc), "capture", captured_piece="p", notation=make_notation(pos, (nr, nc), "capture"))
            moves.append(mv)
    return moves
