import numpy as np
from typing import List, Tuple
from .board import Board, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING, CASTLE_WHITE_KING, CASTLE_WHITE_QUEEN, CASTLE_BLACK_KING, CASTLE_BLACK_QUEEN

# Move type: ((from_r, from_f), (to_r, to_f), promotion_piece)
# promotion_piece is 0 for no promotion, otherwise one of PAWN, KNIGHT, BISHOP, ROOK, QUEEN (positive for white, negative for black)
Move = Tuple[Tuple[int, int], Tuple[int, int], int]

class MoveGenerator:
    """Generate pseudo‑legal moves for a given board position.

    The generator does **not** check for king safety. Use ``generate_legal`` to obtain
    only moves that leave the moving side's king out of check.
    """

    def __init__(self, board: Board):
        self.board = board
        self.turn = board.side_to_move
        self.turn_sign = 1 if self.turn == 'w' else -1
        self.opponent_sign = -self.turn_sign

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate(self) -> List[Move]:
        """Return a list of **pseudo‑legal** moves for the side to move."""
        moves: List[Move] = []
        for r in range(8):
            for f in range(8):
                piece = self.board.board[r, f]
                if piece == 0:
                    continue
                if piece * self.turn_sign <= 0:
                    continue  # not our piece
                p_type = abs(piece)
                if p_type == PAWN:
                    moves.extend(self._pawn_moves((r, f), piece))
                elif p_type == KNIGHT:
                    moves.extend(self._knight_moves((r, f), piece))
                elif p_type == BISHOP:
                    moves.extend(self._sliding_moves((r, f), piece, _BISHOP_OFFSETS))
                elif p_type == ROOK:
                    moves.extend(self._sliding_moves((r, f), piece, _ROOK_OFFSETS))
                elif p_type == QUEEN:
                    moves.extend(self._sliding_moves((r, f), piece, _QUEEN_OFFSETS))
                elif p_type == KING:
                    moves.extend(self._king_moves((r, f), piece))
        return moves

    def generate_legal(self) -> List[Move]:
        """Filter pseudo‑legal moves to only those that leave the king safe."""
        legal: List[Move] = []
        for move in self.generate():
            self.board.make_move(move)
            if not self.board.is_in_check(self.turn):
                legal.append(move)
            self.board.unmake_move()
        return legal

    # ---------------------------------------------------------------------
    # Piece‑specific generators
    # ---------------------------------------------------------------------
    def _pawn_moves(self, sq: Tuple[int, int], piece: int) -> List[Move]:
        r, f = sq
        direction = -1 if self.turn == 'w' else 1
        start_rank = 6 if self.turn == 'w' else 1
        moves: List[Move] = []
        # Single forward
        forward = (r + direction, f)
        if 0 <= forward[0] < 8 and self.board.board[forward] == 0:
            # Promotion?
            if forward[0] in (0, 7):
                for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                    moves.append(((r, f), forward, promo))
            else:
                moves.append(((r, f), forward, 0))
            # Double forward from start rank
            if r == start_rank:
                double = (r + 2 * direction, f)
                if self.board.board[double] == 0:
                    moves.append(((r, f), double, 0))
        # Captures
        for df in (-1, 1):
            cap = (r + direction, f + df)
            if 0 <= cap[0] < 8 and 0 <= cap[1] < 8:
                target = self.board.board[cap]
                if target != 0 and (target * self.opponent_sign) > 0:
                    if cap[0] in (0, 7):
                        for promo in (QUEEN, ROOK, BISHOP, KNIGHT):
                            moves.append(((r, f), cap, promo))
                    else:
                        moves.append(((r, f), cap, 0))
        # En‑passant capture
        if self.board.en_passant:
            ep_r, ep_f = self.board.en_passant
            if ep_r == r + direction and abs(ep_f - f) == 1:
                moves.append(((r, f), (ep_r, ep_f), 0))
        return moves

    def _knight_moves(self, sq: Tuple[int, int], piece: int) -> List[Move]:
        moves: List[Move] = []
        for dr, df in _KNIGHT_OFFSETS:
            to = (sq[0] + dr, sq[1] + df)
            if 0 <= to[0] < 8 and 0 <= to[1] < 8:
                target = self.board.board[to]
                if target == 0 or (target * self.opponent_sign) > 0:
                    moves.append((sq, to, 0))
        return moves

    def _king_moves(self, sq: Tuple[int, int], piece: int) -> List[Move]:
        moves: List[Move] = []
        for dr, df in _KING_OFFSETS:
            to = (sq[0] + dr, sq[1] + df)
            if 0 <= to[0] < 8 and 0 <= to[1] < 8:
                target = self.board.board[to]
                if target == 0 or (target * self.opponent_sign) > 0:
                    moves.append((sq, to, 0))
        # Castling – only if king and rook have not moved and squares are empty and not attacked
        if piece == KING:
            # White king side
            if self.turn == 'w' and (self.board.castling_rights & CASTLE_WHITE_KING):
                if self.board.board[7, 5] == 0 and self.board.board[7, 6] == 0:
                    if not self.board.is_square_attacked((7, 4), 'b') and not self.board.is_square_attacked((7, 5), 'b') and not self.board.is_square_attacked((7, 6), 'b'):
                        moves.append(((7, 4), (7, 6), 0))
            # White queen side
            if self.turn == 'w' and (self.board.castling_rights & CASTLE_WHITE_QUEEN):
                if self.board.board[7, 1] == 0 and self.board.board[7, 2] == 0 and self.board.board[7, 3] == 0:
                    if not self.board.is_square_attacked((7, 4), 'b') and not self.board.is_square_attacked((7, 3), 'b') and not self.board.is_square_attacked((7, 2), 'b'):
                        moves.append(((7, 4), (7, 2), 0))
            # Black king side
            if self.turn == 'b' and (self.board.castling_rights & CASTLE_BLACK_KING):
                if self.board.board[0, 5] == 0 and self.board.board[0, 6] == 0:
                    if not self.board.is_square_attacked((0, 4), 'w') and not self.board.is_square_attacked((0, 5), 'w') and not self.board.is_square_attacked((0, 6), 'w'):
                        moves.append(((0, 4), (0, 6), 0))
            # Black queen side
            if self.turn == 'b' and (self.board.castling_rights & CASTLE_BLACK_QUEEN):
                if self.board.board[0, 1] == 0 and self.board.board[0, 2] == 0 and self.board.board[0, 3] == 0:
                    if not self.board.is_square_attacked((0, 4), 'w') and not self.board.is_square_attacked((0, 3), 'w') and not self.board.is_square_attacked((0, 2), 'w'):
                        moves.append(((0, 4), (0, 2), 0))
        return moves

    def _sliding_moves(self, sq: Tuple[int, int], piece: int, directions: List[Tuple[int, int]]) -> List[Move]:
        moves: List[Move] = []
        for dr, df in directions:
            r, f = sq[0] + dr, sq[1] + df
            while 0 <= r < 8 and 0 <= f < 8:
                target = self.board.board[r, f]
                if target == 0:
                    moves.append((sq, (r, f), 0))
                else:
                    if (target * self.opponent_sign) > 0:
                        moves.append((sq, (r, f), 0))
                    break
                r += dr
                f += df
        return moves

# Direction vectors
_KNIGHT_OFFSETS = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)
]
_BISHOP_OFFSETS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_ROOK_OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_QUEEN_OFFSETS = _BISHOP_OFFSETS + _ROOK_OFFSETS
_KING_OFFSETS = _QUEEN_OFFSETS

# ---------------------------------------------------------------------
# Perft utility
# ---------------------------------------------------------------------
def perft(board: Board, depth: int) -> int:
    """Return the number of leaf nodes reachable from ``board`` at ``depth``.

    Depth ``0`` counts the current position as a single node.
    """
    if depth == 0:
        return 1
    nodes = 0
    gen = MoveGenerator(board)
    for move in gen.generate_legal():
        board.make_move(move)
        nodes += perft(board, depth - 1)
        board.unmake_move()
    return nodes
