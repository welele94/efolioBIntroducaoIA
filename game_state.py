"""Game state model and transition functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from board import parse_board

Coord = Tuple[int, int]


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

    def apply_move(self, move) -> "GameState":
        new_state = self.clone()
        player = self.current_player
        pos = new_state.a_pos if player == "A" else new_state.v_pos

        if move.move_type == "pass":
            new_state.action_count += 1
            new_state.current_player = "V" if player == "A" else "A"
            return new_state

        if move.move_type == "king":
            tr, tc = move.to_pos
            cell = new_state.board[tr][tc]
            if cell in {"T", "B", "C", "D"}:
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
        new_state.current_player = "V" if player == "A" else "A"
        return new_state

    def is_terminal(self) -> bool:
        black_pawns_left = sum(cell == "p" for row in self.board for cell in row)
        if black_pawns_left == 0:
            return True

        if self.action_count >= 60:
            return True

        majority = self.initial_black_pawns // 2 + 1
        if self.a_captures >= majority or self.v_captures >= majority:
            return True

        usable_white_pieces_left = any(cell in {"T", "B", "C", "D"} for row in self.board for cell in row)
        if not usable_white_pieces_left and not self.a_inside_piece and not self.v_inside_piece:
            return True

        return False

    def get_winner(self) -> str:
        if self.a_captures > self.v_captures:
            return "A"
        if self.v_captures > self.a_captures:
            return "V"
        return "draw"



def create_initial_state() -> GameState:
    board = parse_board()
    a_pos = v_pos = (-1, -1)
    initial_black_pawns = 0

    for r in range(8):
        for c in range(8):
            if board[r][c] == "A":
                a_pos = (r, c)
                board[r][c] = " "
            elif board[r][c] == "V":
                v_pos = (r, c)
                board[r][c] = " "
            elif board[r][c] == "p":
                initial_black_pawns += 1

    return GameState(
        board=board,
        current_player="A",
        a_pos=a_pos,
        v_pos=v_pos,
        initial_black_pawns=initial_black_pawns,
    )
