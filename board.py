"""Utilities for board representation and coordinate conversions."""

from __future__ import annotations

from typing import List, Tuple

BOARD_SIZE = 8
INITIAL_BOARD_STRING = "Pp p pD ppBp p pp pp pCpVpp PP ppApCp pp pp p pBpp Dp p pP"

Coord = Tuple[int, int]
Board = List[List[str]]



def parse_board(board_string: str = INITIAL_BOARD_STRING) -> Board:
    """Convert a flat 64-char string into an 8x8 matrix."""
    if len(board_string) > BOARD_SIZE * BOARD_SIZE:
        raise ValueError("Board string cannot exceed 64 characters")

    normalized = board_string.ljust(BOARD_SIZE * BOARD_SIZE)

    board = []
    for row in range(BOARD_SIZE):
        start = row * BOARD_SIZE
        board.append(list(normalized[start : start + BOARD_SIZE]))
    return board



def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE



def coord_to_notation(pos: Coord) -> str:
    row, col = pos
    file_char = chr(ord("a") + col)
    rank_char = str(BOARD_SIZE - row)
    return f"{file_char}{rank_char}"



def notation_to_coord(notation: str) -> Coord:
    notation = notation.strip().lower()
    if len(notation) != 2:
        raise ValueError("Notation must have length 2, e.g. c7")

    file_char, rank_char = notation[0], notation[1]
    if file_char < "a" or file_char > "h" or rank_char < "1" or rank_char > "8":
        raise ValueError("Notation outside 8x8 board")

    col = ord(file_char) - ord("a")
    row = BOARD_SIZE - int(rank_char)
    return (row, col)



def board_to_string(board: Board) -> str:
    return "".join("".join(row) for row in board)



def print_board(board: Board) -> None:
    header = "    a b c d e f g h"
    line = "   " + "-" * 17
    print(header)
    print(line)
    for row in range(BOARD_SIZE):
        rank = BOARD_SIZE - row
        symbols = " ".join(board[row])
        print(f"{rank} | {symbols} |")
    print(line)
