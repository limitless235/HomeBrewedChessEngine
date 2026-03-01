import pytest
from chess_engine.board import Board
from chess_engine.evaluate import evaluate

def test_passed_pawn_evaluation():
    # White passed pawn on b6
    board_pawn_b6 = Board.from_fen("8/8/1P6/8/8/8/k7/4K3 w - - 0 1")
    # White passed pawn advanced to b7
    board_pawn_b7 = Board.from_fen("8/1P6/8/8/8/8/k7/4K3 w - - 0 1")
    
    eval_b6 = evaluate(board_pawn_b6)
    eval_b7 = evaluate(board_pawn_b7)
    
    # An advanced passed pawn should be heavily rewarded in the endgame
    assert eval_b7 > eval_b6 + 20, "Engine fails to realize advanced passed pawns are highly valuable"

def test_doubled_pawn_penalty():
    # White has two pawns on e-file
    board_doubled = Board.from_fen("8/8/8/8/4P3/4P3/8/4K2k w - - 0 1")
    # White has pawns side by side on d-file and e-file
    board_parallel = Board.from_fen("8/8/8/8/3P4/4P3/8/4K2k w - - 0 1")
    
    eval_doubled = evaluate(board_doubled)
    eval_parallel = evaluate(board_parallel)
    
    # Parallel pawns are structurally better than doubled pawns
    assert eval_parallel > eval_doubled + 10, "Engine fails to penalize doubled pawns"

def test_castling_safety_preference():
    # Uncastled king in center with open e-file
    board_uncastled = Board.from_fen("r3k2r/pppp1ppp/8/8/8/8/PPPP1PPP/R3K2R w KQkq - 0 1")
    # Castled king behind pawn shield
    board_castled = Board.from_fen("r3k2r/pppp1ppp/8/8/8/8/PPPP1PPP/R4RK1 b kq - 1 1") 
    
    # Needs to be white's perspective to compare, so let's just use manual states
    board_castled_w = Board.from_fen("r3k2r/pppp1ppp/8/8/8/8/PPPP1PPP/R4RK1 w kq - 1 1")
    
    eval_uncastled = evaluate(board_uncastled)
    eval_castled = evaluate(board_castled_w)
    
    # King safety should heavily favor the castled position
    assert eval_castled > eval_uncastled + 15, "Engine fails to reward King Safety (Pawn Shields and Castling)"

def test_isolated_pawn_penalty():
    # Isolated pawn on d4 (no c or e pawns)
    board_isolated = Board.from_fen("8/8/8/8/3P4/8/8/4K2k w - - 0 1")
    # Supported pawn on d4 (with c3 pawn)
    board_supported = Board.from_fen("8/8/8/8/3P4/2P5/8/4K2k w - - 0 1")
    
    # For a fair comparison, let's just evaluate an isolated configuration vs connected.
    # Actually, adding a pawn changes material. 
    # Let's compare isolated (a4, c4) vs connected (a4, b4). Same material!
    board_iso = Board.from_fen("8/8/8/8/P1P5/8/8/4K2k w - - 0 1")
    board_conn = Board.from_fen("8/8/8/8/PP6/8/8/4K2k w - - 0 1")
    
    eval_iso = evaluate(board_iso)
    eval_conn = evaluate(board_conn)
    
    assert eval_conn > eval_iso + 10, "Engine fails to penalize isolated pawns"
