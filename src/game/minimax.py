from __future__ import annotations

from dataclasses import dataclass
from math import inf
import random
from time import perf_counter

from src.game.board import AI, EMPTY, HUMAN, available_moves, ordered_moves, winner


@dataclass(frozen=True)
class SearchResult:
    position: int | None
    score: int
    nodes: int
    elapsed_ms: float


class _Search:
    def __init__(self, use_pruning: bool) -> None:
        self.use_pruning = use_pruning
        self.nodes = 0
        self.cache: dict[tuple[tuple[str, ...], str], tuple[int, int | None]] = {}

    def run(self, board: list[str], current_player: str) -> tuple[int, int | None]:
        return self._minimax(board, current_player, depth=0, alpha=-inf, beta=inf)

    def _minimax(
        self,
        board: list[str],
        current_player: str,
        depth: int,
        alpha: float,
        beta: float,
    ) -> tuple[int, int | None]:
        self.nodes += 1
        state = winner(board)

        if state == AI:
            return 10 - depth, None
        if state == HUMAN:
            return depth - 10, None
        if state == "draw":
            return 0, None

        key = (tuple(board), current_player)
        if self.use_pruning and key in self.cache:
            return self.cache[key]

        if current_player == AI:
            best_score = -inf
            best_position: int | None = None

            for move in ordered_moves(board):
                board[move] = AI
                score, _ = self._minimax(board, HUMAN, depth + 1, alpha, beta)
                board[move] = EMPTY

                if score > best_score:
                    best_score = score
                    best_position = move

                if self.use_pruning:
                    alpha = max(alpha, best_score)
                    if alpha >= beta:
                        break
        else:
            best_score = inf
            best_position = None

            for move in ordered_moves(board):
                board[move] = HUMAN
                score, _ = self._minimax(board, AI, depth + 1, alpha, beta)
                board[move] = EMPTY

                if score < best_score:
                    best_score = score
                    best_position = move

                if self.use_pruning:
                    beta = min(beta, best_score)
                    if alpha >= beta:
                        break

        result = int(best_score), best_position
        if self.use_pruning:
            self.cache[key] = result
        return result


def best_move(
    board: list[str],
    current_player: str = AI,
    use_pruning: bool = True,
) -> SearchResult:
    start = perf_counter()
    search = _Search(use_pruning=use_pruning)
    score, position = search.run(board.copy(), current_player)
    elapsed_ms = (perf_counter() - start) * 1000
    return SearchResult(
        position=position,
        score=score,
        nodes=search.nodes,
        elapsed_ms=elapsed_ms,
    )


def _winning_move(board: list[str], player: str) -> int | None:
    for move in ordered_moves(board):
        board[move] = player
        won = winner(board) == player
        board[move] = EMPTY
        if won:
            return move
    return None


def easy_move(board: list[str]) -> SearchResult:
    start = perf_counter()
    moves = available_moves(board)
    position = random.choice(moves) if moves else None
    return SearchResult(position=position, score=0, nodes=1, elapsed_ms=(perf_counter() - start) * 1000)


def normal_move(board: list[str]) -> SearchResult:
    start = perf_counter()
    win = _winning_move(board, AI)
    if win is not None:
        return SearchResult(win, 6, 3, (perf_counter() - start) * 1000)

    block = _winning_move(board, HUMAN)
    if block is not None:
        return SearchResult(block, 4, 6, (perf_counter() - start) * 1000)

    if random.random() < 0.65:
        return best_move(board, AI, use_pruning=True)

    moves = ordered_moves(board)
    position = random.choice(moves[: min(4, len(moves))]) if moves else None
    return SearchResult(position, 1, len(moves), (perf_counter() - start) * 1000)


def impossible_draw_move(board: list[str]) -> SearchResult:
    """Optimal move that prefers a draw when a non-losing draw exists."""
    start = perf_counter()
    search = _Search(use_pruning=True)
    candidates: list[tuple[int, int, int]] = []

    for move in ordered_moves(board):
        board[move] = AI
        score, _ = search._minimax(board, HUMAN, depth=1, alpha=-inf, beta=inf)
        board[move] = EMPTY
        candidates.append((score, move, search.nodes))

    if not candidates:
        return SearchResult(None, 0, search.nodes, (perf_counter() - start) * 1000)

    draw_moves = [item for item in candidates if item[0] == 0]
    winning_moves = [item for item in candidates if item[0] > 0]
    losing_moves = [item for item in candidates if item[0] < 0]

    if draw_moves:
        score, position, _ = draw_moves[0]
    elif winning_moves:
        score, position, _ = max(winning_moves, key=lambda item: item[0])
    else:
        score, position, _ = max(losing_moves, key=lambda item: item[0])

    return SearchResult(position, score, search.nodes, (perf_counter() - start) * 1000)


def move_for_difficulty(board: list[str], difficulty: str) -> SearchResult:
    normalized = difficulty.strip().lower()
    if normalized == "facil":
        return easy_move(board)
    if normalized == "normal":
        return normal_move(board)
    if normalized == "imposible":
        return impossible_draw_move(board)
    return impossible_draw_move(board)
