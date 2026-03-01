import numpy as np
from typing import Tuple, List, Optional
from .tt import ZOBRIST_PIECES, ZOBRIST_SIDE, ZOBRIST_CASTLE, ZOBRIST_EP

# Piece encoding (positive = white, negative = black)
EMPTY = 0
PAWN = 1
KNIGHT = 2
BISHOP = 3
ROOK = 4
QUEEN = 5
KING = 6

# Castling rights bits
CASTLE_WHITE_KING = 1 << 0  # K
CASTLE_WHITE_QUEEN = 1 << 1  # Q
CASTLE_BLACK_KING = 1 << 2  # k
CASTLE_BLACK_QUEEN = 1 << 3  # q

# Helper to convert square (rank, file) to 0‑63 index (a8 = 0, h1 = 63)
def sq_to_index(rank: int, file: int) -> int:
    return rank * 8 + file

def index_to_sq(index: int) -> Tuple[int, int]:
    return divmod(index, 8)

class Board:
    """Board representation using an 8×8 NumPy array.

    The board stores signed integers for pieces (positive = white, negative = black).
    Additional state includes side to move, castling rights, en‑passant target square,
    half‑move clock and full‑move number.
    """

    def __init__(self, board: Optional[np.ndarray] = None,
                 side_to_move: str = 'w',
                 castling_rights: int = CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN | CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN,
                 en_passant: Optional[Tuple[int, int]] = None,
                 halfmove_clock: int = 0,
                 fullmove_number: int = 1):
        if board is None:
            self.board = np.zeros((8, 8), dtype=np.int8)
        else:
            self.board = board.astype(np.int8)
        self.side_to_move = side_to_move  # 'w' or 'b'
        self.castling_rights = castling_rights
        self.en_passant = en_passant  # (rank, file) or None
        self.halfmove_clock = halfmove_clock
        self.fullmove_number = fullmove_number
        # Stack for undo information
        self._history: List[dict] = []
        
        self.zobrist_key = self._compute_zobrist()

    def _piece_index(self, piece: int) -> int:
        return piece + 6

    def _compute_zobrist(self) -> int:
        h = 0
        for r in range(8):
            for f in range(8):
                piece = self.board[r, f]
                if a := abs(piece):
                    h ^= ZOBRIST_PIECES[self._piece_index(piece)][r * 8 + f]
        
        if self.side_to_move == 'b':
            h ^= ZOBRIST_SIDE
            
        h ^= ZOBRIST_CASTLE[self.castling_rights]
        
        if self.en_passant:
            # En passant is given by rank, file
            h ^= ZOBRIST_EP[self.en_passant[1]]
            
        return h

    @property
    def turn(self) -> str:
        return self.side_to_move

    @turn.setter
    def turn(self, value: str):
        self.side_to_move = value

    # ---------------------------------------------------------------------
    # Construction helpers
    # ---------------------------------------------------------------------
    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        """Create a Board from a FEN string (full 6‑field FEN)."""
        parts = fen.split()
        if len(parts) < 4:
            raise ValueError("Invalid FEN – not enough fields")
        placement, active, castling, ep = parts[:4]
        halfmove = int(parts[4]) if len(parts) > 4 else 0
        fullmove = int(parts[5]) if len(parts) > 5 else 1
        board_arr = np.zeros((8, 8), dtype=np.int8)
        rows = placement.split('/')
        if len(rows) != 8:
            raise ValueError("Invalid FEN – board rows count != 8")
        for r, row in enumerate(rows):
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                else:
                    piece = {
                        'P': PAWN, 'N': KNIGHT, 'B': BISHOP, 'R': ROOK, 'Q': QUEEN, 'K': KING,
                        'p': -PAWN, 'n': -KNIGHT, 'b': -BISHOP, 'r': -ROOK, 'q': -QUEEN, 'k': -KING,
                    }[ch]
                    board_arr[r, file] = piece
                    file += 1
        # Castling rights bits
        rights = 0
        if 'K' in castling:
            rights |= CASTLE_WHITE_KING
        if 'Q' in castling:
            rights |= CASTLE_WHITE_QUEEN
        if 'k' in castling:
            rights |= CASTLE_BLACK_KING
        if 'q' in castling:
            rights |= CASTLE_BLACK_QUEEN
        # En‑passant square
        en_pass = None
        if ep != '-':
            file = ord(ep[0]) - ord('a')
            rank = 8 - int(ep[1])
            en_pass = (rank, file)
        return cls(board_arr, side_to_move=active, castling_rights=rights,
                   en_passant=en_pass, halfmove_clock=halfmove, fullmove_number=fullmove)

    # ---------------------------------------------------------------------
    # Utility methods
    # ---------------------------------------------------------------------
    def piece_at(self, sq: Tuple[int, int]) -> int:
        r, f = sq
        return int(self.board[r, f])

    def set_piece(self, sq: Tuple[int, int], piece: int) -> None:
        r, f = sq
        self.board[r, f] = piece

    def king_position(self, colour: str) -> Tuple[int, int]:
        target = KING if colour == 'w' else -KING
        pos = np.argwhere(self.board == target)
        if pos.size == 0:
            hist = []
            for s in self._history:
                if s.get('move') == 'null':
                    hist.append("NULL")
                else:
                    (fr, ff), (tr, tf), promo = s['move']
                    hist.append(f"({fr},{ff})->({tr},{tf})")
            print("HISTORY:", " ".join(hist))
            print("BOARD:\n", self)
            raise ValueError(f"King not found for {colour}")
        return tuple(pos[0])  # (rank, file)

    # ---------------------------------------------------------------------
    # Move handling (make/unmake)
    # ---------------------------------------------------------------------
    def make_move(self, move: Tuple[Tuple[int, int], Tuple[int, int], int]) -> None:
        """Apply a move and push the previous state onto the history stack.

        ``move`` is ``((from_r, from_f), (to_r, to_f), promotion_piece)`` where
        ``promotion_piece`` is one of ``PAWN, KNIGHT, BISHOP, ROOK, QUEEN`` for a
        promotion (positive for white, negative for black) or ``0`` for no promotion.
        """
        (fr, ff), (tr, tf), promo = move
        moving_piece = self.board[fr, ff]
        captured_piece = self.board[tr, tf]
        # Save state needed for unmake
        state = {
            'move': move,
            'captured': captured_piece,
            'castling_rights': self.castling_rights,
            'en_passant': self.en_passant,
            'halfmove_clock': self.halfmove_clock,
            'fullmove_number': self.fullmove_number,
            'side_to_move': self.side_to_move,
            'zobrist_key': self.zobrist_key,
        }
        self._history.append(state)
        
        # Remove old castling and EP from hash
        self.zobrist_key ^= ZOBRIST_CASTLE[self.castling_rights]
        if self.en_passant:
            self.zobrist_key ^= ZOBRIST_EP[self.en_passant[1]]
            
        # Side to move flips hash unconditionally
        self.zobrist_key ^= ZOBRIST_SIDE
        # Update half‑move clock
        if moving_piece == 0 or captured_piece != 0:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        # Update full‑move number after Black's move
        if self.side_to_move == 'b':
            self.fullmove_number += 1
        # Handle en‑passant capture
        if abs(moving_piece) == PAWN and self.en_passant and (tr, tf) == self.en_passant:
            cap_rank = tr + (1 if self.side_to_move == 'w' else -1)
            captured_piece = self.board[cap_rank, tf]
            self.board[cap_rank, tf] = EMPTY
            self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(captured_piece)][cap_rank * 8 + tf]
            
        # Move the piece
        self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(moving_piece)][fr * 8 + ff]
        self.board[fr, ff] = EMPTY
        
        # If normal capture, remove it
        if captured_piece != 0 and not (abs(moving_piece) == PAWN and self.en_passant and (tr, tf) == self.en_passant):
             self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(captured_piece)][tr * 8 + tf]
        
        if promo != 0:
            promo_p = promo if moving_piece > 0 else -promo
            self.board[tr, tf] = promo_p
            self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(promo_p)][tr * 8 + tf]
        else:
            self.board[tr, tf] = moving_piece
            self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(moving_piece)][tr * 8 + tf]
            
            # Also move the Rook if this was a castling move
            if abs(moving_piece) == KING and abs(ff - tf) == 2:
                if tf == 6:  # Kingside
                    rook_piece = ROOK if moving_piece == KING else -ROOK
                    self.board[fr, 7] = EMPTY
                    self.board[fr, 5] = rook_piece
                    self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(rook_piece)][fr * 8 + 7]
                    self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(rook_piece)][fr * 8 + 5]
                elif tf == 2:  # Queenside
                    rook_piece = ROOK if moving_piece == KING else -ROOK
                    self.board[fr, 0] = EMPTY
                    self.board[fr, 3] = rook_piece
                    self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(rook_piece)][fr * 8 + 0]
                    self.zobrist_key ^= ZOBRIST_PIECES[self._piece_index(rook_piece)][fr * 8 + 3]
        # Update castling rights (remove if king or rook moves)
        if moving_piece == KING:
            self.castling_rights &= ~(CASTLE_WHITE_KING | CASTLE_WHITE_QUEEN)
        elif moving_piece == -KING:
            self.castling_rights &= ~(CASTLE_BLACK_KING | CASTLE_BLACK_QUEEN)
        elif moving_piece == ROOK:
            if (fr, ff) == (7, 0):  # a1
                self.castling_rights &= ~CASTLE_WHITE_QUEEN
            elif (fr, ff) == (7, 7):  # h1
                self.castling_rights &= ~CASTLE_WHITE_KING
        elif moving_piece == -ROOK:
            if (fr, ff) == (0, 0):  # a8
                self.castling_rights &= ~CASTLE_BLACK_QUEEN
            elif (fr, ff) == (0, 7):  # h8
                self.castling_rights &= ~CASTLE_BLACK_KING
        # If a rook is captured, update opponent's castling rights
        if captured_piece == ROOK:
            if (tr, tf) == (7, 0):
                self.castling_rights &= ~CASTLE_WHITE_QUEEN
            elif (tr, tf) == (7, 7):
                self.castling_rights &= ~CASTLE_WHITE_KING
        elif captured_piece == -ROOK:
            if (tr, tf) == (0, 0):
                self.castling_rights &= ~CASTLE_BLACK_QUEEN
            elif (tr, tf) == (0, 7):
                self.castling_rights &= ~CASTLE_BLACK_KING
        # Set en‑passant target square for double pawn push
        if abs(moving_piece) == PAWN and abs(fr - tr) == 2:
            ep_rank = (fr + tr) // 2
            self.en_passant = (ep_rank, ff)
            self.zobrist_key ^= ZOBRIST_EP[ff]
        else:
            self.en_passant = None
            
        self.zobrist_key ^= ZOBRIST_CASTLE[self.castling_rights]
        
        # Switch side to move
        self.side_to_move = 'b' if self.side_to_move == 'w' else 'w'

    def unmake_move(self) -> None:
        """Revert the last move using the stored history entry."""
        if not self._history:
            raise RuntimeError("No move to unmake")
        state = self._history.pop()
        (fr, ff), (tr, tf), promo = state['move']
        moving_piece = self.board[tr, tf]
        # Restore pieces
        self.board[fr, ff] = moving_piece if promo == 0 else (PAWN if moving_piece > 0 else -PAWN)
        self.board[tr, tf] = state['captured']
        
        # Restore castling Rook if this was a castling move
        if abs(moving_piece) == KING and abs(ff - tf) == 2:
            if tf == 6:  # Kingside
                rook_piece = ROOK if moving_piece > 0 else -ROOK
                self.board[fr, 5] = EMPTY
                self.board[fr, 7] = rook_piece
            elif tf == 2:  # Queenside
                rook_piece = ROOK if moving_piece > 0 else -ROOK
                self.board[fr, 3] = EMPTY
                self.board[fr, 0] = rook_piece
        # Restore en‑passant capture pawn if it happened
        if abs(moving_piece) == PAWN and state['en_passant'] and (tr, tf) == state['en_passant']:
            cap_rank = tr + (1 if state['side_to_move'] == 'w' else -1)
            self.board[cap_rank, tf] = -PAWN if moving_piece > 0 else PAWN
        # Restore saved state
        self.castling_rights = state['castling_rights']
        self.en_passant = state['en_passant']
        self.halfmove_clock = state['halfmove_clock']
        self.fullmove_number = state['fullmove_number']
        self.side_to_move = state['side_to_move']
        self.zobrist_key = state['zobrist_key']

    # ---------------------------------------------------------------------
    # Attack detection
    # ---------------------------------------------------------------------
    def is_square_attacked(self, sq: Tuple[int, int], by_colour: str) -> bool:
        """Return True if ``sq`` is attacked by any piece of ``by_colour``.

        This is a lightweight implementation used for legality checks and
        castling validation.
        """
        opponent = 1 if by_colour == 'w' else -1
        rank, file = sq
        # Pawn attacks
        pawn_dir = -1 if by_colour == 'w' else 1
        for df in (-1, 1):
            r, f = rank - pawn_dir, file + df
            if 0 <= r < 8 and 0 <= f < 8 and self.board[r, f] == opponent * PAWN:
                return True
        # Knight attacks
        knight_moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, df in knight_moves:
            r, f = rank + dr, file + df
            if 0 <= r < 8 and 0 <= f < 8 and self.board[r, f] == opponent * KNIGHT:
                return True
        # Sliding pieces
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, df in directions:
            r, f = rank + dr, file + df
            while 0 <= r < 8 and 0 <= f < 8:
                piece = self.board[r, f]
                if piece != 0:
                    p_type = abs(piece)
                    if dr == 0 or df == 0:  # rook/queen line
                        if p_type == ROOK or p_type == QUEEN:
                            if (piece > 0) == (opponent > 0):
                                return True
                    else:  # bishop/queen diagonal
                        if p_type == BISHOP or p_type == QUEEN:
                            if (piece > 0) == (opponent > 0):
                                return True
                    break
                r += dr
                f += df
        # King attacks (adjacent squares)
        for dr in (-1, 0, 1):
            for df in (-1, 0, 1):
                if dr == 0 and df == 0:
                    continue
                r, f = rank + dr, file + df
                if 0 <= r < 8 and 0 <= f < 8 and self.board[r, f] == opponent * KING:
                    return True
        return False

    def is_in_check(self, colour: str) -> bool:
        """Return True if ``colour``'s king is under attack."""
        king_sq = self.king_position(colour)
        opponent = 'b' if colour == 'w' else 'w'
        return self.is_square_attacked(king_sq, opponent)

    # ---------------------------------------------------------------------
    # Debug helpers
    # ---------------------------------------------------------------------
    def __repr__(self) -> str:
        rows = []
        for r in range(8):
            row = []
            for f in range(8):
                piece = self.board[r, f]
                if piece == 0:
                    row.append('.')
                else:
                    sym = {
                        PAWN: 'P', KNIGHT: 'N', BISHOP: 'B', ROOK: 'R', QUEEN: 'Q', KING: 'K'
                    }[abs(piece)]
                    row.append(sym if piece > 0 else sym.lower())
            rows.append(' '.join(row))
        return '\n'.join(rows) + f"\nSide: {self.side_to_move} Castling:{self.castling_rights} EP:{self.en_passant}"
