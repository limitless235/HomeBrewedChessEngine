import numpy as np
from .board import Board, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

# Simple piece-square tables (values from 0-100). These are illustrative and can be refined.
# Index order: a8, b8, ..., h1 (row-major from top-left).
PAWN_TABLE = np.array([
    0,   0,   0,   0,   0,   0,   0,   0,
    5,  10,  10, -20, -20,  10,  10,   5,
    5,  -5, -10,   0,   0, -10,  -5,   5,
    0,   0,   0,  20,  20,   0,   0,   0,
    5,   5,  10,  25,  25,  10,   5,   5,
    10, 10,  20,  30,  30,  20,  10,  10,
    50, 50,  50,  50,  50,  50,  50,  50,
    0,   0,   0,   0,   0,   0,   0,   0
])

KNIGHT_TABLE = np.array([
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20,   0,   5,   5,   0, -20, -40,
    -30,   5,  10,  15,  15,  10,   5, -30,
    -30,   0,  15,  20,  20,  15,   0, -30,
    -30,   5,  15,  20,  20,  15,   5, -30,
    -30,   0,  10,  15,  15,  10,   0, -30,
    -40, -20,   0,   0,   0,   0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50
])

BISHOP_TABLE = np.array([
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10,   5,   0,   0,   0,   0,   5, -10,
    -10,  10,  10,  10,  10,  10,  10, -10,
    -10,   0,  10,  10,  10,  10,   0, -10,
    -10,   5,   5,  10,  10,   5,   5, -10,
    -10,   0,   5,  10,  10,   5,   0, -10,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20
])

ROOK_TABLE = np.array([
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0
])

QUEEN_TABLE = np.array([
    -20, -10, -10,  -5,  -5, -10, -10, -20,
    -10,   0,   0,   0,   0,   0,   0, -10,
    -10,   0,   5,   5,   5,   5,   0, -10,
     -5,   0,   5,   5,   5,   5,   0,  -5,
      0,   0,   5,   5,   5,   5,   0,  -5,
    -10,   5,   5,   5,   5,   5,   0, -10,
    -10,   0,   5,   0,   0,   0,   0, -10,
    -20, -10, -10,  -5,  -5, -10, -10, -20
])

KING_TABLE_MID = np.array([
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
     20,  20,   0,   0,   0,   0,  20,  20,
     20,  30,  10,   0,   0,  10,  30,  20
])

# Material values (centipawns)
MATERIAL = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

# Helper to get piece-square value (mirrored for black)
def _piece_square_value(piece: int, square_index: int) -> int:
    # piece encoding includes colour offset (0 for white, 8 for black)
    piece_type = piece & 7
    colour = (piece & 8) == WHITE
    if piece_type == PAWN:
        table = PAWN_TABLE
    elif piece_type == KNIGHT:
        table = KNIGHT_TABLE
    elif piece_type == BISHOP:
        table = BISHOP_TABLE
    elif piece_type == ROOK:
        table = ROOK_TABLE
    elif piece_type == QUEEN:
        table = QUEEN_TABLE
    elif piece_type == KING:
        table = KING_TABLE_MID
    else:
        return 0
    # For black pieces, mirror vertically (flip board)
    if not colour:
        # black: flip index vertically (rotate 180)
        square_index = 63 - square_index
    return int(table[square_index])


def evaluate(board: Board) -> int:
    """Static evaluation function.

    Returns a score in centipawns from White's perspective.
    Positive => White advantage, Negative => Black advantage.
    """
    total = 0
    # Iterate over board squares
    for r in range(8):
        for f in range(8):
            piece = board.board[r, f]
            if piece == 0:
                continue
            idx = r * 8 + f  # 0‑63 index, a8=0, h1=63
            piece_type = piece & 7
            value = MATERIAL.get(piece_type, 0)
            # Add material (white positive, black negative)
            if (piece & 8) == WHITE:
                total += value
            else:
                total -= value
            # Add piece‑square table value
            ps_val = _piece_square_value(piece, idx)
            if (piece & 8) == WHITE:
                total += ps_val
            else:
                total -= ps_val
    return total
