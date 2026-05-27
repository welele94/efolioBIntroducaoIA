from __future__ import annotations

from dataclasses import dataclass
from math import inf
from pathlib import Path
from time import perf_counter
from typing import Optional, Tuple

BOARD_SIZE = 8
BOARD_CELLS = 64
INITIAL_BOARD_STRING = "Pp p pD ppBp p   pp pp  pCpVpp PP ppApCp  pp pp   p pBpp Dp p pP"

MAX_DEPTH = 10
DEFAULT_TIME_LIMIT = 0.95
MAX_ACTIONS = 60
MAX_GAMES = 10
RESULTS_PATH = Path("resultados.csv")
TIME_BUDGET_SECONDS = 19.0
TERMINAL_TOKENS = {"Brancas", "Pretas", "Empate", "Inválido", "Erro"}
ACTIVE_PIECES = {"T", "B", "C", "D"}

SLIDING_DIRECTIONS = {
    "T": [(-1, 0), (1, 0), (0, -1), (0, 1)],
    "B": [(-1, -1), (-1, 1), (1, -1), (1, 1)],
    "D": [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)],
}
KNIGHT_DELTAS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
KING_DELTAS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

WIN_BONUS = 10000
CAPTURE_WEIGHT = 120
MOBILITY_WEIGHT = 4
DISTANCE_WEIGHT = 2
BLOCKED_WEIGHT = 150
PIECE_PRIORITY = {None: 0, "C": 25, "B": 40, "T": 40, "D": 70}
PIECE_VALUE = {None: 0, "C": 25, "B": 40, "T": 40, "D": 70}
PIECE_VALUE_WEIGHT = 2

Coord = Tuple[int, int]


@dataclass
class Move:
    from_pos: Coord
    to_pos: Coord
    move_type: str
    notation: str


@dataclass
class GameState:
    board: list[list[str]]
    current_player: str
    a_pos: Coord
    v_pos: Coord
    a_inside_piece: bool = False
    v_inside_piece: bool = False
    a_active_piece: Optional[str] = None
    v_active_piece: Optional[str] = None
    a_captures: int = 0
    v_captures: int = 0
    action_count: int = 0
    initial_black_pawns: int = 0

    def clone(self) -> "GameState":
        return GameState(
            [row[:] for row in self.board], self.current_player, self.a_pos, self.v_pos,
            self.a_inside_piece, self.v_inside_piece, self.a_active_piece, self.v_active_piece,
            self.a_captures, self.v_captures, self.action_count, self.initial_black_pawns,
        )

    def apply_move(self, move: Move) -> "GameState":
        s = self.clone()
        player = s.current_player
        pos = s.a_pos if player == "A" else s.v_pos

        if move.move_type == "pass":
            s.action_count += 1
            s.current_player = other_player(player)
            return s

        tr, tc = move.to_pos
        if move.move_type == "king":
            cell = s.board[tr][tc]
            if cell in ACTIVE_PIECES:
                s.board[tr][tc] = " "
                if player == "A":
                    s.a_inside_piece = True
                    s.a_active_piece = cell
                else:
                    s.v_inside_piece = True
                    s.v_active_piece = cell
            if player == "A":
                s.a_pos = move.to_pos
            else:
                s.v_pos = move.to_pos

        elif move.move_type == "capture":
            s.board[tr][tc] = " "
            if player == "A":
                s.a_pos = move.to_pos
                s.a_captures += 1
            else:
                s.v_pos = move.to_pos
                s.v_captures += 1

        elif move.move_type == "exit":
            fr, fc = pos
            s.board[fr][fc] = "P"
            if player == "A":
                s.a_pos = move.to_pos
                s.a_inside_piece = False
                s.a_active_piece = None
            else:
                s.v_pos = move.to_pos
                s.v_inside_piece = False
                s.v_active_piece = None

        s.action_count += 1
        s.current_player = other_player(player)
        return s

    def is_terminal(self) -> bool:
        if sum(cell == "p" for row in self.board for cell in row) == 0:
            return True
        if self.action_count >= MAX_ACTIONS:
            return True
        majority = self.initial_black_pawns // 2 + 1
        if self.a_captures >= majority or self.v_captures >= majority:
            return True
        pieces_left = any(cell in ACTIVE_PIECES for row in self.board for cell in row)
        return not pieces_left and not self.a_inside_piece and not self.v_inside_piece

    def get_winner(self) -> str:
        if self.a_captures > self.v_captures:
            return "A"
        if self.v_captures > self.a_captures:
            return "V"
        return "draw"


class SearchTimeout(Exception):
    pass


def parse_board(board_string: str) -> list[list[str]]:
    if len(board_string) != BOARD_CELLS:
        raise ValueError("Board string must have exactly 64 characters")
    return [list(board_string[(7 - row) * 8:(8 - row) * 8]) for row in range(8)]


def create_initial_state() -> GameState:
    board = parse_board(INITIAL_BOARD_STRING)
    a_pos = v_pos = (-1, -1)
    pawns = 0
    for r in range(8):
        for c in range(8):
            if board[r][c] == "A":
                a_pos = (r, c)
                board[r][c] = " "
            elif board[r][c] == "V":
                v_pos = (r, c)
                board[r][c] = " "
            elif board[r][c] == "p":
                pawns += 1
    return GameState(board, "A", a_pos, v_pos, initial_black_pawns=pawns)


def other_player(player: str) -> str:
    return "V" if player == "A" else "A"


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < 8 and 0 <= c < 8


def coord_to_notation(pos: Coord) -> str:
    r, c = pos
    return f"{chr(ord('a') + c)}{8 - r}"


def adjacent_or_same(a: Coord, b: Coord) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1


def agent_data(s: GameState, player: str):
    if player == "A":
        return s.a_pos, s.a_inside_piece, s.a_active_piece, s.v_pos
    return s.v_pos, s.v_inside_piece, s.v_active_piece, s.a_pos


def generate_legal_moves(s: GameState) -> list[Move]:
    player = s.current_player
    pos, inside, piece, opp = agent_data(s, player)
    moves: list[Move] = []
    if inside and piece:
        moves.extend(piece_captures(s, pos, piece, opp))
        moves.extend(exit_moves(s, pos, opp))
    else:
        moves.extend(king_moves(s, pos, opp))
    if not moves:
        return [Move(pos, pos, "pass", coord_to_notation(pos))]
    return moves


def king_moves(s: GameState, pos: Coord, opp: Coord) -> list[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc) or adjacent_or_same((nr, nc), opp):
            continue
        if s.board[nr][nc] in {" ", "T", "B", "C", "D"}:
            moves.append(Move(pos, (nr, nc), "king", coord_to_notation((nr, nc))))
    return moves


def exit_moves(s: GameState, pos: Coord, opp: Coord) -> list[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc) or adjacent_or_same((nr, nc), opp):
            continue
        if s.board[nr][nc] == " ":
            moves.append(Move(pos, (nr, nc), "exit", coord_to_notation((nr, nc))))
    return moves


def piece_captures(s: GameState, pos: Coord, piece: str, opp: Coord) -> list[Move]:
    if piece == "C":
        return knight_captures(s, pos, opp)
    moves = []
    for dr, dc in SLIDING_DIRECTIONS[piece]:
        nr, nc = pos[0] + dr, pos[1] + dc
        while in_bounds(nr, nc):
            cell = s.board[nr][nc]
            if cell == " ":
                nr += dr
                nc += dc
                continue
            if cell == "p" and not adjacent_or_same((nr, nc), opp):
                moves.append(Move(pos, (nr, nc), "capture", coord_to_notation((nr, nc))))
            break
    return moves


def knight_captures(s: GameState, pos: Coord, opp: Coord) -> list[Move]:
    moves = []
    for dr, dc in KNIGHT_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if in_bounds(nr, nc) and s.board[nr][nc] == "p" and not adjacent_or_same((nr, nc), opp):
            moves.append(Move(pos, (nr, nc), "capture", coord_to_notation((nr, nc))))
    return moves


def nearest_pawn_distance(s: GameState, pos: Coord) -> int:
    distances = [abs(pos[0] - r) + abs(pos[1] - c) for r in range(8) for c in range(8) if s.board[r][c] == "p"]
    return min(distances) if distances else 0


def mobility_counts(s: GameState) -> tuple[int, int]:
    original = s.current_player
    s.current_player = "A"
    a_mob = len(generate_legal_moves(s))
    s.current_player = "V"
    v_mob = len(generate_legal_moves(s))
    s.current_player = original
    return a_mob, v_mob


def evaluate(s: GameState) -> float:
    if s.is_terminal():
        winner = s.get_winner()
        if winner == "draw":
            return 0
        return WIN_BONUS if winner == "A" else -WIN_BONUS

    score = (s.a_captures - s.v_captures) * CAPTURE_WEIGHT

    a_mob, v_mob = mobility_counts(s)
    score += (a_mob - v_mob) * MOBILITY_WEIGHT
    score += (nearest_pawn_distance(s, s.v_pos) - nearest_pawn_distance(s, s.a_pos)) * DISTANCE_WEIGHT

    piece_score = PIECE_VALUE[s.a_active_piece] - PIECE_VALUE[s.v_active_piece]
    score += piece_score * PIECE_VALUE_WEIGHT

    if a_mob <= 1:
        score -= BLOCKED_WEIGHT
    if v_mob <= 1:
        score += BLOCKED_WEIGHT

    return score


def move_priority(state: GameState, move: Move) -> int:
    if move.move_type == "capture":
        return 0

    tr, tc = move.to_pos
    cell = state.board[tr][tc]

    if move.move_type == "king" and cell in ACTIVE_PIECES:
        return 100 - PIECE_PRIORITY[cell]
    if move.move_type == "king":
        return 200
    if move.move_type == "exit":
        return 300
    return 400


def order_moves(state: GameState, moves: list[Move]) -> list[Move]:
    return sorted(moves, key=lambda m: (move_priority(state, m), m.notation))


def minimax_decision(s: GameState, depth: int, time_limit: float) -> Optional[Move]:
    start_time = perf_counter()
    deadline = start_time + (time_limit * 0.80)

    legal_moves = order_moves(s, generate_legal_moves(s))
    if not legal_moves:
        return None

    best_move = legal_moves[0]
    maximizing = s.current_player == "A"
    current_depth = 1

    while current_depth <= depth:
        if perf_counter() >= deadline:
            break

        try:
            current_best_score = -inf if maximizing else inf
            current_best_move = None

            for move in legal_moves:
                score = minimax(s.apply_move(move), current_depth - 1, -inf, inf, deadline)
                if maximizing and score > current_best_score:
                    current_best_score = score
                    current_best_move = move
                elif not maximizing and score < current_best_score:
                    current_best_score = score
                    current_best_move = move

            if current_best_move is not None:
                best_move = current_best_move
            current_depth += 1

        except SearchTimeout:
            break

    return best_move


def minimax(s: GameState, depth: int, alpha: float, beta: float, deadline: float) -> float:
    if perf_counter() >= deadline:
        raise SearchTimeout
    if depth == 0 or s.is_terminal():
        return evaluate(s)
    if s.current_player == "A":
        value = -inf
        for move in order_moves(s, generate_legal_moves(s)):
            value = max(value, minimax(s.apply_move(move), depth - 1, alpha, beta, deadline))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value
    value = inf
    for move in order_moves(s, generate_legal_moves(s)):
        value = min(value, minimax(s.apply_move(move), depth - 1, alpha, beta, deadline))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def rebuild_state(tokens: list[str]) -> Optional[GameState]:
    s = create_initial_state()
    for token in tokens:
        if token in TERMINAL_TOKENS:
            break
        move = next((m for m in generate_legal_moves(s) if m.notation == token), None)
        if move is None:
            return None
        s = s.apply_move(move)
    return s


def terminal_token(s: GameState) -> str:
    winner = s.get_winner()
    if winner == "A":
        return "Brancas"
    if winner == "V":
        return "Pretas"
    return "Empate"


def controlled_player_for_line(line_index: int) -> str:
    return "V" if line_index % 2 == 0 else "A"


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
    remaining = min(DEFAULT_TIME_LIMIT, deadline - perf_counter())
    if remaining <= 0:
        return tokens + ["Erro"]
    move = minimax_decision(s, depth, remaining)
    return tokens + ([move.notation] if move else ["Erro"])


def read_results(path: Path) -> list[str]:
    if not path.exists():
        return [""] * MAX_GAMES
    lines = path.read_text(encoding="utf-8").splitlines()
    return (lines + [""] * MAX_GAMES)[:MAX_GAMES]


def run_results_csv(path: Path, depth: int = MAX_DEPTH) -> None:
    deadline = perf_counter() + TIME_BUDGET_SECONDS
    output = []
    for i, line in enumerate(read_results(path)):
        tokens = line.strip().split() if line.strip() else []
        output.append(" ".join(update_tokens(tokens, i, depth, deadline)))
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    run_results_csv(RESULTS_PATH, MAX_DEPTH)


if __name__ == "__main__":
    main()
