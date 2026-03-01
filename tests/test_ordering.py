import pytest
from chess_engine.board import Board
from chess_engine.search import Searcher

def test_node_reduction():
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    
    # Run a finite depth search instead of iterative deepening time limit
    # We'll just run negamax directly to depth 5 to see node count
    score, pv = searcher.negamax(5, -9999999, 9999999)
    print(f"\n--- Depth 5 Search Nodes: {searcher.nodes} ---")
    
    # With perfect ordering (or close to it) depth 5 should be well under 40k nodes.
    # Without ordering it would be > 100k nodes (even with AB).
    assert searcher.nodes < 50000, f"Too many nodes searched: {searcher.nodes}"
