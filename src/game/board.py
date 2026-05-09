from __future__ import annotations

from typing import Iterable

EMPTY = ""
AI = "X"
HUMAN = "O"

WIN_LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)

MOVE_PRIORITY: tuple[int, ...] = (4, 0, 2, 6, 8, 1, 3, 5, 7)


def available_moves(board: Iterable[str]) -> list[int]:
    return [index for index, value in enumerate(board) if value == EMPTY]


def ordered_moves(board: Iterable[str]) -> list[int]:
    free = set(available_moves(board))
    return [move for move in MOVE_PRIORITY if move in free]


def winner(board: Iterable[str]) -> str | None:
    cells = tuple(board)
    for a, b, c in WIN_LINES:
        if cells[a] != EMPTY and cells[a] == cells[b] == cells[c]:
            return cells[a]
    if EMPTY not in cells:
        return "draw"
    return None


def winning_line(board: Iterable[str]) -> tuple[int, int, int] | None:
    cells = tuple(board)
    for line in WIN_LINES:
        a, b, c = line
        if cells[a] != EMPTY and cells[a] == cells[b] == cells[c]:
            return line
    return None
