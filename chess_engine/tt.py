import random
from typing import Optional, Tuple, Any

# Optional Tuple for move: ((from_r, from_f), (to_r, to_f), promotion_piece)
Move = Tuple[Tuple[int, int], Tuple[int, int], int]

# Zobrist keys size
# 12 pieces (6 white, 6 black) * 64 squares
# 1 side to move (black)
# 16 castling rights (4 bits)
# 8 en passant files

random.seed(42) # Deterministic for debugging

ZOBRIST_PIECES = [[random.getrandbits(64) for _ in range(64)] for _ in range(13)]
ZOBRIST_SIDE = random.getrandbits(64)
ZOBRIST_CASTLE = [random.getrandbits(64) for _ in range(16)]
ZOBRIST_EP = [random.getrandbits(64) for _ in range(8)]

# TT Flags
FLAG_EXACT = 0
FLAG_ALPHA = 1 # Upperbound
FLAG_BETA = 2  # Lowerbound

class TTEntry:
    __slots__ = ['key', 'depth', 'score', 'flag', 'best_move']
    
    def __init__(self, key: int, depth: int, score: int, flag: int, best_move: Optional[Move]):
        self.key = key
        self.depth = depth
        self.score = score
        self.flag = flag
        self.best_move = best_move

class TranspositionTable:
    def __init__(self, size_mb: int = 64):
        # Python object overhead is large, so size_mb is approximate.
        # Let's allocate roughly size_mb * 1024 * 1024 / 64 bytes per entry
        self.num_entries = (size_mb * 1024 * 1024) // 64
        self.table = [None] * self.num_entries
        self.hits = 0

    def probe(self, key: int, depth: int, alpha: int, beta: int) -> Tuple[bool, int, Optional[Move]]:
        """Probe the TT. Returns (hit, score, best_move)"""
        index = key % self.num_entries
        entry = self.table[index]
        
        if entry is not None and entry.key == key:
            self.hits += 1
            if entry.depth >= depth:
                if entry.flag == FLAG_EXACT:
                    return True, entry.score, entry.best_move
                if entry.flag == FLAG_ALPHA and entry.score <= alpha:
                    return True, alpha, entry.best_move
                if entry.flag == FLAG_BETA and entry.score >= beta:
                    return True, beta, entry.best_move
            return False, 0, entry.best_move
            
        return False, 0, None

    def store(self, key: int, depth: int, score: int, flag: int, best_move: Optional[Move]):
        index = key % self.num_entries
        entry = self.table[index]
        
        # Depth-preferred replacement: replace if old depth is smaller or empty
        # Or always replace if we want a simpler scheme (we'll try depth-preferred first)
        if entry is None or entry.depth <= depth or entry.flag == FLAG_EXACT:
            self.table[index] = TTEntry(key, depth, score, flag, best_move)
