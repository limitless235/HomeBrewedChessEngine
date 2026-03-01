import numpy as np
from typing import List, Tuple
from .board import Board, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING

# Simple move representation as a tuple: ((from_rank, from_file), (to_rank, to_file), promotion_piece)
# promotion_piece is None for non-pawn promotions.
Move = Tuple[Tuple[int, int], Tuple[int, int], int]

# Direction vectors for each piece type (row, col)
_KNIGHT_OFFSETS = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1)
]

_BISHOP_OFFSETS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
_ROOK_OFFSETS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
_QUEEN_OFFSETS = _BISHOP_OFFSETS + _ROOK_OFFSETS
_KING_OFFSETS = _QUEEN_OFFSETS

class MoveGenerator:
    """Generate pseudo‑legal moves for a given board position.

    The generator does **not** check for king safety, castling rights, or
    en‑passant. It simply produces all moves that a piece could make based on
    its movement rules and the current occupancy of the board.
    """

    def __init__(self, board: Board):
        self.board = board
        self.turn_offset = WHITE if board.turn == 'w' else BLACK
        self.opponent_offset = BLACK if board.turn == 'w' else WHITE

    def generate(self) -> List[Move]:
        moves: List[Move] = []
        for r in range(8):
            for f in range(8):
                piece = self.board.board[r, f]
                if piece == 0:
                    continue
                if (piece & 8) != self.turn_offset:
                    continue  # not our piece
                piece_type = piece & 7
                if piece_type == PAWN:
                    moves.extend(self._pawn_moves((r, f)))
                elif piece_type == KNIGHT:
                    moves.extend(self._knight_moves((r, f)))
                elif piece_type == BISHOP:
                    moves.extend(self._sliding_moves((r, f), _BISHOP_OFFSETS))
                elif piece_type == ROOK:
                    moves.extend(self._sliding_moves((r, f), _ROOK_OFFSETS))
                elif piece_type == QUEEN:
                    moves.extend(self._sliding_moves((r, f), _QUEEN_OFFSETS))
                elif piece_type == KING:
                    moves.extend(self._king_moves((r, f)))
        return moves

    # ---------------------------------------------------------------------
    # Piece‑specific move generators
    # ---------------------------------------------------------------------
    def _pawn_moves(self, sq: Tuple[int, int]) -> List[Move]:
        r, f = sq
        direction = -1 if self.board.turn == 'w' else 1
        start_rank = 6 if self.board.turn == 'w' else 1
        moves: List[Move] = []
        # Single step forward
        forward_sq = (r + direction, f)
        if self._on_board(forward_sq) and self.board.board[forward_sq] == 0:
            # Promotion check
            if forward_sq[0] in (0, 7):
                for promo_piece in (QUEEN, ROOK, BISHOP, KNIGHT):
                    moves.append(((r, f), forward_sq, promo_piece))
            else:
                moves.append(((r, f), forward_sq, 0))
            # Double step from starting rank
            if r == start_rank:
                double_sq = (r + 2 * direction, f)
                if self.board.board[double_sq] == 0:
                    moves.append(((r, f), double_sq, 0))
        # Captures
        for df in (-1, 1):
            cap_sq = (r + direction, f + df)
            if not self._on_board(cap_sq):
                continue
            target = self.board.board[cap_sq]
            if target != 0 and (target & 8) == self.opponent_offset:
                if cap_sq[0] in (0, 7):
                    for promo_piece in (QUEEN, ROOK, BISHOP, KNIGHT):
                        moves.append(((r, f), cap_sq, promo_piece))
                else:
                    moves.append(((r, f), cap_sq, 0))
        return moves

    def _knight_moves(self, sq: Tuple[int, int]) -> List[Move]:
        moves: List[Move] = []
        for dr, df in _KNIGHT_OFFSETS:
            to_sq = (sq[0] + dr, sq[1] + df)
            if not self._on_board(to_sq):
                continue
            target = self.board.board[to_sq]
            if target == 0 or (target & 8) == self.opponent_offset:
                moves.append((sq, to_sq, 0))
        return moves

    def _king_moves(self, sq: Tuple[int, int]) -> List[Move]:
        moves: List[Move] = []
        for dr, df in _KING_OFFSETS:
            to_sq = (sq[0] + dr, sq[1] + df)
            if not self._on_board(to_sq):
                continue
            target = self.board.board[to_sq]
            if target == 0 or (target & 8) == self.opponent_offset:
                moves.append((sq, to_sq, 0))
        return moves

    def _sliding_moves(self, sq: Tuple[int, int], directions: List[Tuple[int, int]]) -> List[Move]:
        moves: List[Move] = []
        for dr, df in directions:
            r, f = sq[0] + dr, sq[1] + df
            while self._on_board((r, f)):
                target = self.board.board[r, f]
                if target == 0:
                    moves.append((sq, (r, f), 0))
                else:
                    if (target & 8) == self.opponent_offset:
                        moves.append((sq, (r, f), 0))
                    break
                r += dr
                f += df
        return moves

    # ---------------------------------------------------------------------
    def _on_board(self, sq: Tuple[int, int]) -> bool:
        return 0 <= sq[0] < 8 and 0 <= sq[1] < 8
