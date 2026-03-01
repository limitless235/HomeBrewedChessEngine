import pytest
from chess_engine.board import Board
from chess_engine.search import Searcher

def test_opening_move():
    # E2E4 or D2D4 is expected
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    best_move, nodes, pv = searcher.iterative_deepening(1000)
    
    assert best_move is not None
    # Let's just ensure it moves a pawn from the 2nd rank (start is row 6) to 4th rank (row 4)
    # or a knight from back rank
    (fr, ff), (tr, tf), promo = best_move
    
    is_pawn_push = fr == 6 and tr == 4 and ff == tf # double push
    is_knight_dev = fr == 7 and tr == 5 # knight move
    
    assert is_pawn_push or is_knight_dev, f"Unexpected opening move: {best_move}"

def test_mate_in_one():
    # Back rank mate: Ra1 to a8
    board = Board.from_fen("6k1/5ppp/8/8/8/8/8/R4K2 w - - 0 1")
    searcher = Searcher(board)
    best_move, nodes, pv = searcher.iterative_deepening(500)
    
    assert best_move == ((7, 0), (0, 0), 0)

def test_knight_fork():
    # Knight on d5 forks king on e8 and queen on a8 via c7
    board = Board.from_fen("q3k3/8/8/3N4/8/8/8/4K3 w - - 0 1")
    searcher = Searcher(board)
    # Need depth >= 3 for the engine to see the capture after the check
    best_move, nodes, pv = searcher.iterative_deepening(1000)
    
    # d5 is (3, 3), c7 is (1, 2)
    assert best_move == ((3, 3), (1, 2), 0)
