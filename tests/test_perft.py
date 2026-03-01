import pytest
from chess_engine.board import Board
from chess_engine.movegen import perft

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

@pytest.mark.parametrize("depth,expected", [
    (1, 20),
    (2, 400),
    (3, 8902),
    (4, 197281),
])
def test_perft(depth, expected):
    board = Board.from_fen(START_FEN)
    assert perft(board, depth) == expected
