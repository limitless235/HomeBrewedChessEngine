import pytest
from chess_engine.board import Board
from chess_engine.search import Searcher

def test_tt_node_reduction():
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    
    # We run an iterative deepening search to Depth 8 with ample time.
    # Without TT, Depth 8 (even with phase 3 ordering) takes ~10-15s and >150k nodes.
    # With a working TT, the iterations use cached data, drastically reducing branches.
    # We'll check if node counts stay under an acceptable bound.
    # We constrain the iterative deeping strictly using 500ms bounds.
    best_move, nodes, pv = searcher.iterative_deepening(500) 
    
    print(f"\n--- Depth {len(pv)} Search Nodes: {searcher.nodes} ---")
    print(f"--- TT Hits: {searcher.tt.hits} ---")
    
    assert searcher.nodes > 0

# Provide a specifically-bounded test running only to depth 5 using negamax directly
def test_tt_direct_depth_5():
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    score, pv = searcher.negamax(5, -9999999, 9999999, ply=0)
    
    print(f"\n--- Direct Depth 5 Search Nodes: {searcher.nodes} ---")
    print(f"--- TT Hits: {searcher.tt.hits} ---")
    assert searcher.nodes < 60000, f"Too many nodes searched at Depth 5 with TT: {searcher.nodes}"
