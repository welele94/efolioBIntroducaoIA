"""Single-file move decider for eFolio B adversarial search."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from math import inf
from pathlib import Path
from time import perf_counter
from typing import Optional, Tuple

BOARD_SIZE = 8
BOARD_CELLS = BOARD_SIZE * BOARD_SIZE
RAW_INITIAL_BOARD_STRING = "Pp p pD ppBp p pp pp pCpVpp PP ppApCp pp pp p pBpp Dp p pP"
INITIAL_BOARD_STRING = RAW_INITIAL_BOARD_STRING.ljust(BOARD_CELLS)

MAX_DEPTH = 2
DEFAULT_TIME_LIMIT = 1.0
MAX_ACTIONS = 60
MAX_GAMES = 10
RESULTS_PATH = Path("resultados.csv")
TIME_BUDGET_SECONDS = 19.0
TERMINAL_TOKENS = {"Brancas", "Pretas", "Empate", "Inválido", "Erro"}

ACTIVE_PIECES = ("T", "B", "C", "D")
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

WIN_BONUS = 10000
CAPTURE_WEIGHT = 120
MOBILITY_WEIGHT = 4
PAWN_DISTANCE_WEIGHT = 2

Coord = Tuple[int, int]


def make_board(rows: list[str]) -> str:
    if len(rows) != BOARD_SIZE:
        raise ValueError("An instance must have exactly 8 rows")
    if any(len(row) != BOARD_SIZE for row in rows):
        raise ValueError("Each instance row must have exactly 8 columns")
    return "".join(rows)


INSTANCES = {
    "official": INITIAL_BOARD_STRING,
    "open_race": make_board(
        [
            "p  T  p ",
            "   p    ",
            "  A     ",
            "        ",
            "     V  ",
            "    p   ",
            " p  D  p",
            "        ",
        ]
    ),
    "capture_race": make_board(
        [
            "p      p",
            "   T    ",
            "  A     ",
            "        ",
            "     V  ",
            "    B   ",
            "p      p",
            "   p    ",
        ]
    ),
    "knight_tactics": make_board(
        [
            "p      p",
            "   p    ",
            "  C     ",
            "  A     ",
            "        ",
            "     V  ",
            "     C  ",
            "p      p",
        ]
    ),
    "queen_pressure": make_board(
        [
            "p   p   ",
            "        ",
            "  A D   ",
            "        ",
            "        ",
            "   D V  ",
            "        ",
            "   p   p",
        ]
    ),
    "endgame_small": make_board(
        [
            "        ",
            "  A T p ",
            "        ",
            "        ",
            "        ",
            " p B V  ",
            "        ",
            "        ",
        ]
    ),
}


@dataclass
class Move:
    from_pos: Coord
    to_pos: Coord
    move_type: str
    captured_piece: Optional[str] = None
    notation: str = ""


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
            board=[row[:] for row in self.board],
            current_player=self.current_player,
            a_pos=self.a_pos,
            v_pos=self.v_pos,
            a_inside_piece=self.a_inside_piece,
            v_inside_piece=self.v_inside_piece,
            a_active_piece=self.a_active_piece,
            v_active_piece=self.v_active_piece,
            a_captures=self.a_captures,
            v_captures=self.v_captures,
            action_count=self.action_count,
            initial_black_pawns=self.initial_black_pawns,
        )

    def apply_move(self, move: Move) -> "GameState":
        new_state = self.clone()
        player = self.current_player
        pos = new_state.a_pos if player == "A" else new_state.v_pos

        if move.move_type == "pass":
            new_state.action_count += 1
            new_state.current_player = other_player(player)
            return new_state

        if move.move_type == "king":
            tr, tc = move.to_pos
            cell = new_state.board[tr][tc]
            if cell in ACTIVE_PIECES:
                if player == "A":
                    new_state.a_inside_piece = True
                    new_state.a_active_piece = cell
                else:
                    new_state.v_inside_piece = True
                    new_state.v_active_piece = cell
            if player == "A":
                new_state.a_pos = move.to_pos
            else:
                new_state.v_pos = move.to_pos

        elif move.move_type == "capture":
            tr, tc = move.to_pos
            new_state.board[tr][tc] = " "
            if player == "A":
                new_state.a_pos = move.to_pos
                new_state.a_captures += 1
            else:
                new_state.v_pos = move.to_pos
                new_state.v_captures += 1

        elif move.move_type == "exit":
            fr, fc = pos
            new_state.board[fr][fc] = "P"
            if player == "A":
                new_state.a_pos = move.to_pos
                new_state.a_inside_piece = False
                new_state.a_active_piece = None
            else:
                new_state.v_pos = move.to_pos
                new_state.v_inside_piece = False
                new_state.v_active_piece = None

        new_state.action_count += 1
        new_state.current_player = other_player(player)
        return new_state

    def is_terminal(self) -> bool:
        black_pawns_left = sum(cell == "p" for row in self.board for cell in row)
        if black_pawns_left == 0:
            return True
        if self.action_count >= MAX_ACTIONS:
            return True

        majority = self.initial_black_pawns // 2 + 1
        if self.a_captures >= majority or self.v_captures >= majority:
            return True

        usable_white_pieces_left = any(cell in ACTIVE_PIECES for row in self.board for cell in row)
        return not usable_white_pieces_left and not self.a_inside_piece and not self.v_inside_piece

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
    return [list(board_string[row * BOARD_SIZE : (row + 1) * BOARD_SIZE]) for row in range(BOARD_SIZE)]


def create_state_from_board_string(
    board_string: str,
    current_player: str = "A",
    a_captures: int = 0,
    v_captures: int = 0,
    action_count: int = 0,
    initial_black_pawns: Optional[int] = None,
    a_active_piece: Optional[str] = None,
    v_active_piece: Optional[str] = None,
) -> GameState:
    board = parse_board(board_string)
    a_pos = v_pos = (-1, -1)
    a_count = v_count = 0
    black_pawns = 0

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = board[r][c]
            if cell == "A":
                a_count += 1
                a_pos = (r, c)
                board[r][c] = " "
            elif cell == "V":
                v_count += 1
                v_pos = (r, c)
                board[r][c] = " "
            elif cell == "p":
                black_pawns += 1

    if a_count != 1 or v_count != 1:
        raise ValueError("Board state must contain exactly one A agent and exactly one V agent")
    if current_player not in {"A", "V"}:
        raise ValueError("Current player must be A or V")

    return GameState(
        board=board,
        current_player=current_player,
        a_pos=a_pos,
        v_pos=v_pos,
        a_inside_piece=a_active_piece is not None,
        v_inside_piece=v_active_piece is not None,
        a_active_piece=a_active_piece,
        v_active_piece=v_active_piece,
        a_captures=a_captures,
        v_captures=v_captures,
        action_count=action_count,
        initial_black_pawns=initial_black_pawns if initial_black_pawns is not None else black_pawns,
    )


def other_player(player: str) -> str:
    return "V" if player == "A" else "A"


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE


def coord_to_notation(pos: Coord) -> str:
    row, col = pos
    return f"{chr(ord('a') + col)}{BOARD_SIZE - row}"


def make_notation(_from_pos: Coord, to_pos: Coord, _move_type: str) -> str:
    return coord_to_notation(to_pos)


def is_adjacent_or_same(a: Coord, b: Coord) -> bool:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1


def agent_data(state: GameState, player: str):
    if player == "A":
        return state.a_pos, state.a_inside_piece, state.a_active_piece, state.v_pos
    return state.v_pos, state.v_inside_piece, state.v_active_piece, state.a_pos


def generate_legal_moves(state: GameState) -> list[Move]:
    player = state.current_player
    pos, inside_piece, active_piece, opp_pos = agent_data(state, player)
    legal_moves: list[Move] = []

    if inside_piece and active_piece:
        legal_moves.extend(generate_piece_capture_moves(state, pos, active_piece, opp_pos))
        legal_moves.extend(generate_exit_moves(state, pos, opp_pos))
    else:
        legal_moves.extend(generate_king_moves(state, pos, opp_pos))

    if not legal_moves:
        return [Move(pos, pos, "pass", notation=make_notation(pos, pos, "pass"))]
    return legal_moves


def generate_king_moves(state: GameState, pos: Coord, opp_pos: Coord) -> list[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if is_adjacent_or_same((nr, nc), opp_pos):
            continue

        cell = state.board[nr][nc]
        if cell in {" ", "T", "B", "C", "D"}:
            moves.append(Move(pos, (nr, nc), "king", notation=make_notation(pos, (nr, nc), "king")))
    return moves


def generate_exit_moves(state: GameState, pos: Coord, opp_pos: Coord) -> list[Move]:
    moves = []
    for dr, dc in KING_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if is_adjacent_or_same((nr, nc), opp_pos):
            continue
        if state.board[nr][nc] != " ":
            continue
        moves.append(Move(pos, (nr, nc), "exit", notation=make_notation(pos, (nr, nc), "exit")))
    return moves


def generate_piece_capture_moves(state: GameState, pos: Coord, piece: str, opp_pos: Coord) -> list[Move]:
    if piece in {"T", "B", "D"}:
        return sliding_captures(state, pos, piece, opp_pos)
    if piece == "C":
        return knight_captures(state, pos, opp_pos)
    return []


def sliding_captures(state: GameState, pos: Coord, piece: str, opp_pos: Coord) -> list[Move]:
    moves = []
    for dr, dc in SLIDING_DIRECTIONS[piece]:
        nr, nc = pos[0] + dr, pos[1] + dc
        while in_bounds(nr, nc):
            cell = state.board[nr][nc]
            if cell == " ":
                nr += dr
                nc += dc
                continue

            if cell == "p" and not is_adjacent_or_same((nr, nc), opp_pos):
                moves.append(
                    Move(pos, (nr, nc), "capture", captured_piece="p", notation=make_notation(pos, (nr, nc), "capture"))
                )
            break
    return moves


def knight_captures(state: GameState, pos: Coord, opp_pos: Coord) -> list[Move]:
    moves = []
    for dr, dc in KNIGHT_DELTAS:
        nr, nc = pos[0] + dr, pos[1] + dc
        if not in_bounds(nr, nc):
            continue
        if is_adjacent_or_same((nr, nc), opp_pos):
            continue
        if state.board[nr][nc] == "p":
            moves.append(
                Move(pos, (nr, nc), "capture", captured_piece="p", notation=make_notation(pos, (nr, nc), "capture"))
            )
    return moves


def nearest_black_pawn_distance(state: GameState, pos: Coord) -> Optional[int]:
    best = None
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if state.board[r][c] == "p":
                distance = abs(pos[0] - r) + abs(pos[1] - c)
                best = distance if best is None else min(best, distance)
    return best


def evaluate(state: GameState, perspective_player: str = "A") -> float:
    if state.is_terminal():
        winner = state.get_winner()
        if winner == "draw":
            return 0
        score = WIN_BONUS if winner == "A" else -WIN_BONUS
        return score if perspective_player == "A" else -score

    capture_score = (state.a_captures - state.v_captures) * CAPTURE_WEIGHT

    original_player = state.current_player
    state.current_player = "A"
    a_mobility = len(generate_legal_moves(state))
    state.current_player = "V"
    v_mobility = len(generate_legal_moves(state))
    state.current_player = original_player

    mobility_score = (a_mobility - v_mobility) * MOBILITY_WEIGHT

    a_distance = nearest_black_pawn_distance(state, state.a_pos)
    v_distance = nearest_black_pawn_distance(state, state.v_pos)
    distance_score = 0
    if a_distance is not None and v_distance is not None:
        distance_score = (v_distance - a_distance) * PAWN_DISTANCE_WEIGHT

    total = capture_score + mobility_score + distance_score
    return total if perspective_player == "A" else -total


def order_moves(moves: list[Move]) -> list[Move]:
    return sorted(moves, key=lambda move: (move.move_type != "capture", move.move_type == "pass"))


def minimax_decision(state: GameState, depth: int, time_limit: Optional[float] = None) -> Optional[Move]:
    maximizing = state.current_player == "A"
    best_score = -inf if maximizing else inf
    best_move = None
    deadline = perf_counter() + time_limit if time_limit is not None else None

    for move in order_moves(generate_legal_moves(state)):
        try:
            score = minimax(state.apply_move(move), depth - 1, -inf, inf, deadline)
        except SearchTimeout:
            break

        if maximizing and score > best_score:
            best_score, best_move = score, move
        if not maximizing and score < best_score:
            best_score, best_move = score, move

    return best_move


def minimax(state: GameState, depth: int, alpha: float, beta: float, deadline: Optional[float]) -> float:
    if deadline is not None and perf_counter() >= deadline:
        raise SearchTimeout

    if depth == 0 or state.is_terminal():
        return evaluate(state, perspective_player="A")

    if state.current_player == "A":
        value = -inf
        for move in order_moves(generate_legal_moves(state)):
            value = max(value, minimax(state.apply_move(move), depth - 1, alpha, beta, deadline))
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    value = inf
    for move in order_moves(generate_legal_moves(state)):
        value = min(value, minimax(state.apply_move(move), depth - 1, alpha, beta, deadline))
        beta = min(beta, value)
        if alpha >= beta:
            break
    return value


def render_with_agents(state: GameState) -> list[list[str]]:
    board = [row[:] for row in state.board]
    ar, ac = state.a_pos
    vr, vc = state.v_pos
    board[ar][ac] = "A"
    board[vr][vc] = "V"
    return board


def print_board(board: list[list[str]]) -> None:
    print("    a b c d e f g h")
    print("   " + "-" * 17)
    for row in range(BOARD_SIZE):
        rank = BOARD_SIZE - row
        print(f"{rank} | {' '.join(board[row])} |")
    print("   " + "-" * 17)


def choose_move_destination(state: GameState, depth: int, time_limit: float) -> str:
    current_pos = state.a_pos if state.current_player == "A" else state.v_pos
    if state.is_terminal():
        return coord_to_notation(current_pos)

    move = minimax_decision(state, depth=depth, time_limit=time_limit)
    if move is None:
        return coord_to_notation(current_pos)
    return coord_to_notation(move.to_pos)


def parse_result_tokens(line: str) -> list[str]:
    stripped = line.strip()
    return stripped.split() if stripped else []


def terminal_token_for_state(state: GameState) -> str:
    winner = state.get_winner()
    if winner == "A":
        return "Brancas"
    if winner == "V":
        return "Pretas"
    return "Empate"


def rebuild_state_from_tokens(tokens: list[str]) -> Optional[GameState]:
    state = create_state_from_board_string(INITIAL_BOARD_STRING)
    for token in tokens:
        if token in TERMINAL_TOKENS:
            break

        legal_moves = generate_legal_moves(state)
        move = next((candidate for candidate in legal_moves if candidate.notation == token), None)
        if move is None:
            return None
        state = state.apply_move(move)
    return state


def controlled_player_for_line(line_index: int) -> str:
    return "V" if line_index % 2 == 0 else "A"


def append_move_or_result(tokens: list[str], line_index: int, depth: int, deadline: float) -> list[str]:
    if tokens and tokens[-1] in TERMINAL_TOKENS:
        return tokens

    state = rebuild_state_from_tokens(tokens)
    if state is None:
        return tokens + ["Inválido"]

    if state.is_terminal():
        return tokens + [terminal_token_for_state(state)]

    if state.current_player != controlled_player_for_line(line_index):
        return tokens

    remaining = deadline - perf_counter()
    if remaining <= 0:
        return tokens + ["Erro"]

    move = minimax_decision(state, depth=depth, time_limit=min(DEFAULT_TIME_LIMIT, remaining))
    if move is None:
        return tokens + ["Erro"]

    return tokens + [move.notation]


def read_results_lines(path: Path) -> list[str]:
    if not path.exists():
        return [""] * MAX_GAMES

    lines = path.read_text(encoding="utf-8").splitlines()

    if len(lines) < MAX_GAMES:
        lines.extend([""] * (MAX_GAMES - len(lines)))
    return lines[:MAX_GAMES]


def run_results_csv(path: Path, depth: int) -> None:
    lines = read_results_lines(path)
    deadline = perf_counter() + TIME_BUDGET_SECONDS
    updated_lines = []

    for line_index, line in enumerate(lines):
        tokens = parse_result_tokens(line)
        updated_tokens = append_move_or_result(tokens, line_index, depth, deadline)
        updated_lines.append(" ".join(updated_tokens))

    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def build_state(args) -> GameState:
    board_string = sys.stdin.read().rstrip("\n") if args.board == "-" else args.board
    if board_string is None:
        board_string = INSTANCES[args.instance]

    return create_state_from_board_string(
        board_string,
        current_player=args.player,
        a_captures=args.a_captures,
        v_captures=args.v_captures,
        action_count=args.actions,
        initial_black_pawns=args.initial_black_pawns,
        a_active_piece=args.a_active_piece,
        v_active_piece=args.v_active_piece,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Escolhe uma jogada para o estado atual do eFolio B.")
    parser.add_argument(
        "--instance",
        default="official",
        choices=sorted(INSTANCES),
        help="Instancia de fallback/teste local a usar quando --board nao e fornecido.",
    )
    parser.add_argument("--depth", type=int, default=MAX_DEPTH, help="Profundidade do Minimax.")
    parser.add_argument("--time-limit", type=float, default=DEFAULT_TIME_LIMIT, help="Limite de tempo em segundos.")
    parser.add_argument("--player", choices=["A", "V"], default="A", help="Jogador a mover.")
    parser.add_argument("--board", help="String externa de 64 caracteres. Use '-' para ler de stdin.")
    parser.add_argument("--a-captures", type=int, default=0, help="Capturas ja feitas pelo agente A.")
    parser.add_argument("--v-captures", type=int, default=0, help="Capturas ja feitas pelo agente V.")
    parser.add_argument("--actions", type=int, default=0, help="Numero de acoes ja realizadas.")
    parser.add_argument("--initial-black-pawns", type=int, default=None, help="Numero inicial de peoes pretos.")
    parser.add_argument("--a-active-piece", choices=ACTIVE_PIECES, help="Peca controlada por A, se existir.")
    parser.add_argument("--v-active-piece", choices=ACTIVE_PIECES, help="Peca controlada por V, se existir.")
    parser.add_argument("--results", default=str(RESULTS_PATH), help="Caminho do ficheiro resultados.csv.")
    parser.add_argument("--csv", action="store_true", help="Atualiza resultados.csv e nao imprime jogada.")
    parser.add_argument("--move", action="store_true", help="Imprime uma unica jogada no terminal.")
    parser.add_argument("--list-instances", action="store_true", help="Lista as instancias disponiveis.")
    parser.add_argument("--simulate", action="store_true", help="Modo local: simula a partida completa.")
    parser.add_argument("--quiet", action="store_true", help="Nao imprime o tabuleiro durante simulacao.")
    return parser.parse_args()


def run_simulation(state: GameState, args) -> None:
    history = []
    if not args.quiet:
        print(f"Estado inicial: {args.instance}")
        print_board(render_with_agents(state))

    while not state.is_terminal():
        move = minimax_decision(state, depth=args.depth, time_limit=args.time_limit)
        if move is None:
            break
        history.append(f"{state.current_player}: {move.notation}")
        state = state.apply_move(move)

        if not args.quiet:
            print(f"\nAcao {state.action_count}: {history[-1]}")
            print_board(render_with_agents(state))

    print("\n=== Resultado final ===")
    print("Sequencia de jogadas:")
    for idx, item in enumerate(history, start=1):
        print(f"{idx:02d}. {item}")
    print(f"\nCapturas A (verde): {state.a_captures}")
    print(f"Capturas V (vermelho): {state.v_captures}")
    print(f"Total de acoes: {state.action_count}")
    print(f"Vencedor: {state.get_winner()}")


def main() -> None:
    args = parse_args()

    if args.list_instances:
        print("Instancias disponiveis:")
        for name in sorted(INSTANCES):
            print(f"- {name}")
        return

    one_move_mode = args.move or args.simulate or args.board is not None or "--instance" in sys.argv
    if args.csv or not one_move_mode:
        run_results_csv(Path(args.results), args.depth)
        return

    state = build_state(args)

    if args.simulate:
        run_simulation(state, args)
        return

    print(choose_move_destination(state, args.depth, args.time_limit))


if __name__ == "__main__":
    main()
