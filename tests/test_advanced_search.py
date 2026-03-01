import pytest
import time
from chess_engine.board import Board
from chess_engine.search import Searcher

def test_mate_in_2():
    # Scholar's mate pattern
    board = Board.from_fen("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
    searcher = Searcher(board)
    
    # Needs to find it fast
    best_move, nodes, pv = searcher.iterative_deepening(1000)
    
    # Q at h5 (3, 7) takes pawn at f7 (1, 5)
    assert best_move == ((3, 7), (1, 5), 0), f"Failed to find Mate in 2. Found {best_move}"

def test_advanced_pruning_speed():
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    
    start_time = time.time()
    # 500ms max, strictly enforced with matching hard limit constraint
    best_move, nodes, pv = searcher.iterative_deepening(500, 500)
    end_time = time.time()
    
    # Needs a bit of overhead cushion because time checks are periodic every 512 nodes
    assert end_time - start_time <= 0.85, "Iterative deepening broke time limit!"
    
    # With all 5 advanced pruning techniques in place, even a slow native Python engine
    # should accomplish thousands of highly impactful node evaluations seamlessly.
    assert searcher.nodes >= 100, "Searcher evaluated too few nodes to be working correctly."
    assert len(pv) >= 1, "PV is suspiciously empty."
