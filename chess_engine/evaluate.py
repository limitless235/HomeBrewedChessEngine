import numpy as np
from .board import Board, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from .movegen import MoveGenerator

PIECE_VALUES = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

MG_VALUE = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

EG_VALUE = {
    PAWN: 120,
    KNIGHT: 300,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

BISHOP_PAIR_MG = 30
BISHOP_PAIR_EG = 50

# White PSTs (Middlegame)
PST_MG_PAWN = np.array([
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [ 50, 50, 50, 50, 50, 50, 50, 50],
    [ 10, 10, 20, 30, 30, 20, 10, 10],
    [  5,  5, 10, 25, 25, 10,  5,  5],
    [  0,  0,  0, 20, 20,  0,  0,  0],
    [  5, -5,-10,  0,  0,-10, -5,  5],
    [  5, 10, 10,-20,-20, 10, 10,  5],
    [  0,  0,  0,  0,  0,  0,  0,  0]
], dtype=np.int32)
PST_EG_PAWN = np.array([
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [ 80, 80, 80, 80, 80, 80, 80, 80],
    [ 50, 50, 50, 50, 50, 50, 50, 50],
    [ 30, 30, 30, 30, 30, 30, 30, 30],
    [ 20, 20, 20, 20, 20, 20, 20, 20],
    [ 10, 10, 10, 10, 10, 10, 10, 10],
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [  0,  0,  0,  0,  0,  0,  0,  0]
], dtype=np.int32)

PST_MG_KNIGHT = np.array([
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50]
], dtype=np.int32)
PST_EG_KNIGHT = PST_MG_KNIGHT.copy()

PST_MG_BISHOP = np.array([
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20]
], dtype=np.int32)
PST_EG_BISHOP = PST_MG_BISHOP.copy()

PST_MG_ROOK = np.array([
    [  0,  0,  0,  0,  0,  0,  0,  0],
    [  5, 10, 10, 10, 10, 10, 10,  5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [ -5,  0,  0,  0,  0,  0,  0, -5],
    [  0,  0,  0,  5,  5,  0,  0,  0]
], dtype=np.int32)
PST_EG_ROOK = PST_MG_ROOK.copy()

PST_MG_QUEEN = np.array([
    [-20,-10,-10, -5, -5,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5,  5,  5,  5,  0,-10],
    [ -5,  0,  5,  5,  5,  5,  0, -5],
    [  0,  0,  5,  5,  5,  5,  0, -5],
    [-10,  5,  5,  5,  5,  5,  0,-10],
    [-10,  0,  5,  0,  0,  0,  0,-10],
    [-20,-10,-10, -5, -5,-10,-10,-20]
], dtype=np.int32)
PST_EG_QUEEN = PST_MG_QUEEN.copy()

PST_MG_KING = np.array([
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [ 20, 20,  0,  0,  0,  0, 20, 20],
    [ 20, 30, 10,  0,  0, 10, 30, 20]
], dtype=np.int32)

PST_EG_KING = np.array([
    [-50,-40,-30,-20,-20,-30,-40,-50],
    [-30,-20,-10,  0,  0,-10,-20,-30],
    [-30,-10, 20, 30, 30, 20,-10,-30],
    [-30,-10, 30, 40, 40, 30,-10,-30],
    [-30,-10, 30, 40, 40, 30,-10,-30],
    [-30,-10, 20, 30, 30, 20,-10,-30],
    [-30,-30,  0,  0,  0,  0,-30,-30],
    [-50,-30,-30,-30,-30,-30,-30,-50]
], dtype=np.int32)

PST_WHITE_MG = { PAWN: PST_MG_PAWN, KNIGHT: PST_MG_KNIGHT, BISHOP: PST_MG_BISHOP, ROOK: PST_MG_ROOK, QUEEN: PST_MG_QUEEN, KING: PST_MG_KING }
PST_BLACK_MG = { p: np.flipud(pst) for p, pst in PST_WHITE_MG.items() }

PST_WHITE_EG = { PAWN: PST_EG_PAWN, KNIGHT: PST_EG_KNIGHT, BISHOP: PST_EG_BISHOP, ROOK: PST_EG_ROOK, QUEEN: PST_EG_QUEEN, KING: PST_EG_KING }
PST_BLACK_EG = { p: np.flipud(pst) for p, pst in PST_WHITE_EG.items() }

# Passed Pawn bonuses based on rank index (0-7).
# Note: For white, 0 is the 8th rank. A passed pawn on the 7th rank is at rank index 1.
PASS_BONUS = {
    1: 120, # 7th rank
    2:  90, # 6th rank
    3:  60, # 5th rank
    4:  40, # 4th rank
    5:  20, # 3rd rank
    6:  10  # 2nd rank
}

def evaluate(board: Board) -> int:
    score_mg = 0
    score_eg = 0
    
    b = board.board
    
    # Material Phase calculation
    w_q = np.sum(b == QUEEN)
    b_q = np.sum(b == -QUEEN)
    w_r = np.sum(b == ROOK)
    b_r = np.sum(b == -ROOK)
    w_b = np.sum(b == BISHOP)
    b_b = np.sum(b == -BISHOP)
    w_n = np.sum(b == KNIGHT)
    b_n = np.sum(b == -KNIGHT)
    
    phase = ((w_q + b_q)*4 + (w_r + b_r)*2 + (w_b + b_b)*1 + (w_n + b_n)*1)
    phase = min(phase, 24.0)
    phase_weight = phase / 24.0
    
    # Primary features (Material and PSTs)
    for p_type in MG_VALUE.keys():
        w_mask = (b == p_type)
        b_mask = (b == -p_type)
        w_count = np.count_nonzero(w_mask)
        b_count = np.count_nonzero(b_mask)
        
        score_mg += (w_count - b_count) * MG_VALUE[p_type]
        score_eg += (w_count - b_count) * EG_VALUE[p_type]
        
        score_mg += int(np.sum(w_mask * PST_WHITE_MG[p_type]))
        score_eg += int(np.sum(w_mask * PST_WHITE_EG[p_type]))
        score_mg -= int(np.sum(b_mask * PST_BLACK_MG[p_type]))
        score_eg -= int(np.sum(b_mask * PST_BLACK_EG[p_type]))
        
    # Bishop Pair Bonus
    if w_b >= 2:
        score_mg += BISHOP_PAIR_MG
        score_eg += BISHOP_PAIR_EG
    if b_b >= 2:
        score_mg -= BISHOP_PAIR_MG
        score_eg -= BISHOP_PAIR_EG

    # Pawn Structure Cache Setup
    w_pawns = (b == PAWN)
    b_pawns = (b == -PAWN)
    w_p_counts = np.sum(w_pawns, axis=0)
    b_p_counts = np.sum(b_pawns, axis=0)

    # Doubled Pawns (-20)
    score_mg -= np.sum(w_p_counts > 1) * 20
    score_eg -= np.sum(w_p_counts > 1) * 20
    score_mg += np.sum(b_p_counts > 1) * 20
    score_eg += np.sum(b_p_counts > 1) * 20
    
    # Isolated Pawns (-15)
    for f in range(8):
        if w_p_counts[f] > 0:
            left_f = max(0, f-1)
            right_f = min(7, f+1)
            if (f == 0 or w_p_counts[left_f] == 0) and (f == 7 or w_p_counts[right_f] == 0):
                score_mg -= 15 * w_p_counts[f]
                score_eg -= 15 * w_p_counts[f]
        if b_p_counts[f] > 0:
            left_f = max(0, f-1)
            right_f = min(7, f+1)
            if (f == 0 or b_p_counts[left_f] == 0) and (f == 7 or b_p_counts[right_f] == 0):
                score_mg += 15 * b_p_counts[f]
                score_eg += 15 * b_p_counts[f]
                
    # Passed Pawns (huge bonus based on rank)
    w_pawn_r, w_pawn_f = np.where(w_pawns)
    for r, f in zip(w_pawn_r, w_pawn_f):
        left_f = max(0, f-1)
        right_f = min(7, f+1)
        # White pawns go from 6 down to 0, "in front" is 0:r
        if not np.any(b_pawns[0:r, left_f:right_f+1]):
            bonus = PASS_BONUS.get(r, 0)
            score_mg += bonus
            score_eg += bonus * 2 # Endgames prioritize pass pawns
            
    b_pawn_r, b_pawn_f = np.where(b_pawns)
    for r, f in zip(b_pawn_r, b_pawn_f):
        left_f = max(0, f-1)
        right_f = min(7, f+1)
        # Black pawns go from 1 down to 7, "in front" is r+1:8
        if not np.any(w_pawns[r+1:8, left_f:right_f+1]):
            mapped_rank = 7 - r # from rank 6 (7th rank proxy) to index
            bonus = PASS_BONUS.get(mapped_rank, 0)
            score_mg -= bonus
            score_eg -= bonus * 2
            
    # King Safety (only applied in middlegame practically)
    w_k_pos = np.argwhere(b == KING)
    if w_k_pos.size > 0:
        kr, kf = w_k_pos[0]
        # Only heavily reward castled/cornered kings
        if kf < 3 or kf > 4:
            shield = 0
            if kr > 0:
                for df in (-1, 0, 1):
                    sf = kf + df
                    if 0 <= sf < 8:
                        if b[kr-1, sf] == PAWN:
                            shield += 1
                        elif kr > 1 and b[kr-2, sf] == PAWN:
                            shield += 1
            score_mg += shield * 15
            for df in (-1, 0, 1):
                sf = kf + df
                if 0 <= sf < 8:
                    if w_p_counts[sf] == 0 and b_p_counts[sf] == 0:
                        score_mg -= 30
                    elif w_p_counts[sf] == 0:
                        score_mg -= 15

    b_k_pos = np.argwhere(b == -KING)
    if b_k_pos.size > 0:
        kr, kf = b_k_pos[0]
        if kf < 3 or kf > 4:
            shield = 0
            if kr < 7:
                for df in (-1, 0, 1):
                    sf = kf + df
                    if 0 <= sf < 8:
                        if b[kr+1, sf] == -PAWN:
                            shield += 1
                        elif kr < 6 and b[kr+2, sf] == -PAWN:
                            shield += 1
            score_mg -= shield * 15
            for df in (-1, 0, 1):
                sf = kf + df
                if 0 <= sf < 8:
                    if w_p_counts[sf] == 0 and b_p_counts[sf] == 0:
                        score_mg += 30
                    elif b_p_counts[sf] == 0:
                        score_mg += 15
                        
    # Rook Bonuses
    w_rooks = (b == ROOK)
    b_rooks = (b == -ROOK)
    score_mg += np.sum(np.sum(w_rooks, axis=0) > 1) * 15
    score_eg += np.sum(np.sum(w_rooks, axis=0) > 1) * 15
    score_mg -= np.sum(np.sum(b_rooks, axis=0) > 1) * 15
    score_eg -= np.sum(np.sum(b_rooks, axis=0) > 1) * 15
    
    _, w_rook_f = np.where(w_rooks)
    for f in w_rook_f:
        if w_p_counts[f] == 0:
            if b_p_counts[f] == 0:
                score_mg += 20; score_eg += 20
            else:
                score_mg += 10; score_eg += 10
                
    _, b_rook_f = np.where(b_rooks)
    for f in b_rook_f:
        if b_p_counts[f] == 0:
            if w_p_counts[f] == 0:
                score_mg -= 20; score_eg -= 20
            else:
                score_mg -= 10; score_eg -= 10

    # Mobility (+5cp per extra pseudo-legal move vs opponent)
    original_side = board.side_to_move
    gen = MoveGenerator(board)
    my_moves = len(gen.generate())
    
    board.side_to_move = 'b' if original_side == 'w' else 'w'
    gen_opp = MoveGenerator(board)
    opp_moves = len(gen_opp.generate())
    board.side_to_move = original_side # Restore
    
    mob_diff = my_moves - opp_moves
    mob_score = mob_diff * 5
    if original_side == 'w':
        score_mg += mob_score
        score_eg += mob_score
    else:
        score_mg -= mob_score
        score_eg -= mob_score

    # Tapered combine
    final_score = int(score_mg * phase_weight + score_eg * (1.0 - phase_weight))

    # Return perspective score
    if board.turn == 'b':
        final_score = -final_score
        
    return final_score
