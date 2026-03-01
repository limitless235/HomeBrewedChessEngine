import pytest
from chess_engine.board import Board

def test_starting_position():
    board = Board.from_fen('rn1qkbnr/ppp1pppp/8/3p4/2PP4/5N2/PP2PPPP/RNBQKB1R b KQkq - 2 3')
    # Verify turn is black as per FEN
    assert board.turn == 'b'
    # Verify a few piece placements
    # a8 rook (black)
    assert board.piece_at((0, 0)) == -4  # -ROOK
    # e1 king (white)
    assert board.piece_at((7, 4)) == 6  # KING

def test_invalid_fen_raises():
    with pytest.raises(ValueError):
        Board.from_fen('invalid_fen_string')
