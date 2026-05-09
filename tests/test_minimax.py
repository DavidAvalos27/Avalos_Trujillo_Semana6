import unittest

from src.game.board import AI, EMPTY, HUMAN, winner
from src.game.minimax import best_move, impossible_draw_move, move_for_difficulty


class MinimaxTests(unittest.TestCase):
    def test_ai_takes_winning_move(self):
        board = [
            AI,
            AI,
            EMPTY,
            HUMAN,
            HUMAN,
            EMPTY,
            EMPTY,
            EMPTY,
            EMPTY,
        ]
        result = best_move(board, AI, use_pruning=True)
        self.assertEqual(result.position, 2)

    def test_ai_blocks_immediate_loss(self):
        board = [
            HUMAN,
            HUMAN,
            EMPTY,
            AI,
            EMPTY,
            EMPTY,
            EMPTY,
            AI,
            EMPTY,
        ]
        result = best_move(board, AI, use_pruning=True)
        self.assertEqual(result.position, 2)

    def test_ai_never_loses_from_empty_board_when_it_starts(self):
        outcome = self._worst_case_for_ai([EMPTY] * 9, AI)
        self.assertGreaterEqual(outcome, 0)

    def test_modes_return_valid_moves(self):
        board = [EMPTY] * 9
        for mode in ("facil", "normal", "imposible"):
            result = move_for_difficulty(board, mode)
            self.assertIn(result.position, range(9))

    def test_impossible_prefers_draw_when_available(self):
        board = [
            AI,
            EMPTY,
            EMPTY,
            EMPTY,
            HUMAN,
            EMPTY,
            EMPTY,
            EMPTY,
            EMPTY,
        ]
        result = impossible_draw_move(board)
        self.assertGreaterEqual(result.score, 0)

    def _worst_case_for_ai(self, board, turn):
        state = winner(board)
        if state == AI:
            return 1
        if state == HUMAN:
            return -1
        if state == "draw":
            return 0

        if turn == AI:
            move = best_move(board, AI, use_pruning=True).position
            self.assertIsNotNone(move)
            board[move] = AI
            score = self._worst_case_for_ai(board, HUMAN)
            board[move] = EMPTY
            return score

        scores = []
        for index, value in enumerate(board):
            if value == EMPTY:
                board[index] = HUMAN
                scores.append(self._worst_case_for_ai(board, AI))
                board[index] = EMPTY
        return min(scores)


if __name__ == "__main__":
    unittest.main()
