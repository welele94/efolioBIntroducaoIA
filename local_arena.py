from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

import main as game


MoveChooser = Callable[[game.GameState, list[str], random.Random], game.Move | None]


@dataclass
class GameResult:
    opponent: str
    our_player: str
    winner: str
    our_captures: int
    opp_captures: int
    actions: int
    terminal_reason: str
    moves: list[str]
    loop_suspected: bool


def sorted_legal_moves(state: game.GameState) -> list[game.Move]:
    return game.order_moves(state, game.generate_legal_moves(state))


def terminal_reason(state: game.GameState) -> str:
    majority = state.initial_black_pawns // 2 + 1
    pawns_left = sum(cell == "p" for row in state.board for cell in row)
    pieces_left = any(cell in game.ACTIVE_PIECES for row in state.board for cell in row)

    if state.a_captures >= majority or state.v_captures >= majority:
        return "majority"
    if pawns_left == 0:
        return "no_pawns"
    if state.action_count >= game.MAX_ACTIONS:
        return "max_actions"
    if not pieces_left and not state.a_inside_piece and not state.v_inside_piece:
        return "no_active_pieces"
    return "unknown"


def has_repeated_cycle(moves: list[str], cycle_len: int = 4, repeats: int = 3) -> bool:
    needed = cycle_len * repeats
    if len(moves) < needed:
        return False
    tail = moves[-needed:]
    pattern = tail[:cycle_len]
    return all(tail[i:i + cycle_len] == pattern for i in range(0, needed, cycle_len))


def our_agent_move(state: game.GameState, tokens: list[str], rng: random.Random) -> game.Move | None:
    book = game.opening_book_move(state, tokens)
    if book is not None:
        return book
    return game.minimax_decision(state, game.MAX_DEPTH, game.DEFAULT_TIME_LIMIT) or safe_first_move(state, rng)


def safe_first_move(state: game.GameState, rng: random.Random) -> game.Move | None:
    moves = sorted_legal_moves(state)
    return moves[0] if moves else None


def random_shuffle_agent(state: game.GameState, tokens: list[str], rng: random.Random) -> game.Move | None:
    moves = sorted_legal_moves(state)
    if not moves:
        return None
    rng.shuffle(moves)
    return moves[0]


def greedy_capture_agent(state: game.GameState, tokens: list[str], rng: random.Random) -> game.Move | None:
    moves = sorted_legal_moves(state)
    if not moves:
        return None

    captures = [m for m in moves if m.move_type == "capture"]
    if captures:
        return captures[0]

    # Prefer entering active pieces, especially the queen, then rook/bishop, then knight.
    entries = []
    for m in moves:
        tr, tc = m.to_pos
        cell = state.board[tr][tc]
        if cell in game.ACTIVE_PIECES:
            entries.append((piece_rank(cell), m))
    if entries:
        return min(entries, key=lambda x: (x[0], x[1].notation))[1]

    return moves[0]


def queen_lover_agent(state: game.GameState, tokens: list[str], rng: random.Random) -> game.Move | None:
    moves = sorted_legal_moves(state)
    if not moves:
        return None

    # If already inside a piece, capture first. Queen chains are usually decisive.
    captures = [m for m in moves if m.move_type == "capture"]
    if captures:
        return captures[0]

    # Enter queen if immediately possible.
    queen_entries = []
    active_entries = []
    for m in moves:
        tr, tc = m.to_pos
        cell = state.board[tr][tc]
        if cell == "D":
            queen_entries.append(m)
        elif cell in game.ACTIVE_PIECES:
            active_entries.append((piece_rank(cell), m))
    if queen_entries:
        return sorted(queen_entries, key=lambda m: m.notation)[0]
    if active_entries:
        return min(active_entries, key=lambda x: (x[0], x[1].notation))[1]

    # If queen exists, move closer to it.
    queen_positions = [(r, c) for r in range(game.BOARD_SIZE) for c in range(game.BOARD_SIZE) if state.board[r][c] == "D"]
    if queen_positions:
        def dist_to_queen(move: game.Move) -> int:
            r, c = move.to_pos
            return min(abs(r - qr) + abs(c - qc) for qr, qc in queen_positions)
        return min(moves, key=lambda m: (dist_to_queen(m), m.notation))

    return moves[0]


def small_minimax_agent(state: game.GameState, tokens: list[str], rng: random.Random) -> game.Move | None:
    # Approximation of a simple reference bot: lower depth and shorter time.
    return game.minimax_decision(state, depth=3, time_limit=0.12) or safe_first_move(state, rng)


def piece_rank(piece: str) -> int:
    # Lower is better.
    return {"D": 0, "T": 1, "B": 1, "C": 2}.get(piece, 9)


OPPONENTS: dict[str, MoveChooser] = {
    "random": random_shuffle_agent,
    "greedy": greedy_capture_agent,
    "queen": queen_lover_agent,
    "minimax": small_minimax_agent,
}


def simulate_game(opponent_name: str, our_player: str, seed: int, verbose: bool = False) -> GameResult:
    rng = random.Random(seed)
    opponent = OPPONENTS[opponent_name]
    state = game.create_initial_state()
    tokens: list[str] = []

    while not state.is_terminal():
        chooser = our_agent_move if state.current_player == our_player else opponent
        move = chooser(state, tokens, rng)
        if move is None:
            break

        legal = {m.notation for m in game.generate_legal_moves(state)}
        if move.notation not in legal:
            raise RuntimeError(
                f"Illegal local move {move.notation} by {state.current_player}. Legal: {sorted(legal)}"
            )

        if verbose:
            side = "OUR" if state.current_player == our_player else opponent_name.upper()
            print(
                f"{len(tokens) + 1:02d}. {state.current_player} {side:7s} {move.notation:>2s} "
                f"type={move.move_type:7s} captures A/V={state.a_captures}/{state.v_captures}"
            )

        tokens.append(move.notation)
        state = state.apply_move(move)

        if len(tokens) > game.MAX_ACTIONS + 5:
            # Safety guard in case a future code change breaks terminal detection.
            break

    winner = state.get_winner()
    our_captures = state.a_captures if our_player == "A" else state.v_captures
    opp_captures = state.v_captures if our_player == "A" else state.a_captures

    return GameResult(
        opponent=opponent_name,
        our_player=our_player,
        winner=winner,
        our_captures=our_captures,
        opp_captures=opp_captures,
        actions=state.action_count,
        terminal_reason=terminal_reason(state),
        moves=tokens,
        loop_suspected=has_repeated_cycle(tokens),
    )


def run_batch(opponents: list[str], games_per_side: int, seed: int, verbose_losses: int) -> None:
    for opponent in opponents:
        results: list[GameResult] = []
        for our_player in ("A", "V"):
            for i in range(games_per_side):
                results.append(simulate_game(opponent, our_player, seed + i + (10000 if our_player == "V" else 0)))

        wins = sum(1 for r in results if r.winner == r.our_player)
        losses = sum(1 for r in results if r.winner not in {r.our_player, "draw"})
        draws = sum(1 for r in results if r.winner == "draw")
        reasons = Counter(r.terminal_reason for r in results)
        avg_actions = sum(r.actions for r in results) / len(results)
        avg_margin = sum(r.our_captures - r.opp_captures for r in results) / len(results)
        loops = sum(1 for r in results if r.loop_suspected)

        print(f"\n=== Opponent: {opponent} ===")
        print(f"Games: {len(results)} | Wins: {wins} | Losses: {losses} | Draws: {draws}")
        print(f"Win rate: {wins / len(results):.1%} | Avg actions: {avg_actions:.1f} | Avg capture margin: {avg_margin:+.2f}")
        print(f"Terminal reasons: {dict(reasons)} | Suspected loops: {loops}")

        if losses:
            print("Worst losses:")
            worst = sorted(
                [r for r in results if r.winner != r.our_player and r.winner != "draw"],
                key=lambda r: (r.our_captures - r.opp_captures, -r.actions),
            )[:verbose_losses]
            for r in worst:
                print(
                    f"  our={r.our_player} winner={r.winner} captures={r.our_captures}-{r.opp_captures} "
                    f"actions={r.actions} reason={r.terminal_reason} loop={r.loop_suspected}"
                )
                print("  moves:", " ".join(r.moves))


def main() -> None:
    parser = argparse.ArgumentParser(description="Local arena for testing main.py against simple reference-style agents.")
    parser.add_argument("--opponents", nargs="+", default=list(OPPONENTS), choices=list(OPPONENTS))
    parser.add_argument("--games", type=int, default=10, help="Games per side against each opponent.")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--verbose-losses", type=int, default=3)
    parser.add_argument("--trace", choices=list(OPPONENTS), help="Trace one game against one opponent.")
    parser.add_argument("--side", choices=["A", "V"], default="A", help="Our side for --trace.")
    args = parser.parse_args()

    if args.trace:
        result = simulate_game(args.trace, args.side, args.seed, verbose=True)
        print("\nResult:", result)
        print("Moves:", " ".join(result.moves))
        return

    run_batch(args.opponents, args.games, args.seed, args.verbose_losses)


if __name__ == "__main__":
    main()
