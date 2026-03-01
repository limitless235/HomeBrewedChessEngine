import time
import math
import threading
from typing import Tuple, Optional, List
from .board import Board, QUEEN, ROOK, BISHOP, KNIGHT
from .movegen import MoveGenerator, Move
from .evaluate import evaluate, PIECE_VALUES, PAWN, KING
from .tt import TranspositionTable, FLAG_EXACT, FLAG_ALPHA, FLAG_BETA, ZOBRIST_EP, ZOBRIST_SIDE

INF = 9999999
MATE_SCORE = 1000000

# MVV-LVA (Most Valuable Victim - Least Valuable Attacker) base score for captures
# We create a large offset for captures to ensure they are searched before quiet moves.
CAPTURE_SCORE_BASE = 10000

CAPTURE_SCORE_BASE = 10000

def format_move(move: Move) -> str:
    if not move: return "0000"
    (fr, ff), (tr, tf), promo = move
    promo_char = ''
    p = abs(promo)
    if p == QUEEN: promo_char = 'q'
    elif p == ROOK: promo_char = 'r'
    elif p == BISHOP: promo_char = 'b'
    elif p == KNIGHT: promo_char = 'n'
    return f"{chr(97+ff)}{8-fr}{chr(97+tf)}{8-tr}{promo_char}"

class Searcher:
    def __init__(self, board: Board):
        self.board = board
        self.nodes = 0
        self.start_time = 0
        self.soft_limit_ms = 0
        self.hard_limit_ms = 0
        self.stop_event = None
        self.time_limit_reached = False
        
        # Transposition table
        self.tt = TranspositionTable(size_mb=64)
        
        # Killers: 2 slots per ply, 100 plies deep
        self.killers = [[None, None] for _ in range(100)]
        
        # History: indexed by [piece][sq_index]
        # piece is signed: -6 to 6 (we'll shift to 0-12 to index array)
        # sq_index is 0 to 63
        self.history = [[0] * 64 for _ in range(13)]

    def _piece_index(self, piece: int) -> int:
        return piece + 6

    def negamax(self, depth: int, alpha: int, beta: int, ply: int = 0, hash_move: Optional[Move] = None, make_null: bool = True) -> Tuple[int, List[Move]]:
        self.nodes += 1
        
        # Periodic thread/time check every 512 nodes
        if (self.nodes & 511) == 0:
            if self.stop_event and self.stop_event.is_set():
                self.time_limit_reached = True
            elif self.hard_limit_ms > 0 and (time.time() - self.start_time) * 1000 > self.hard_limit_ms:
                self.time_limit_reached = True

        if self.time_limit_reached:
            return 0, []
            
        # 50-move rule
        if self.board.halfmove_clock >= 100:
            return 0, []
            
        # Draw by Repetition (1 prior occurrence in history = 2-fold repetition)
        if self.board.halfmove_clock >= 4:
            zkey = self.board.zobrist_key
            hist_len = len(self.board._history)
            limit = max(0, hist_len - self.board.halfmove_clock)
            # Check backwards by 2 plys (so side to move matches)
            for i in range(hist_len - 2, limit - 1, -2):
                if self.board._history[i]['zobrist_key'] == zkey:
                    return 0, []
            
        if depth <= 0:
            return self.quiescence(alpha, beta), []
            
        alpha_orig = alpha
        
        # Probe TT
        tt_hit, tt_score, tt_move = self.tt.probe(self.board.zobrist_key, depth, alpha, beta)
        if tt_hit and ply > 0: # Don't pull exact score from TT at root so we can get PV
            # Adjust mate scores from TT relative to root
            if tt_score > MATE_SCORE - 1000:
                tt_score -= ply
            elif tt_score < -MATE_SCORE + 1000:
                tt_score += ply
                
            return tt_score, [tt_move] if tt_move else []
            
        in_check = self.board.is_in_check(self.board.turn)
        
        # Null Move Pruning
        if make_null and depth >= 3 and not in_check:
            turn_sign = 1 if self.board.turn == 'w' else -1
            has_pieces = False
            b = self.board.board
            for r in range(8):
                for f in range(8):
                    piece = b[r, f]
                    if piece * turn_sign > 0:
                        ptype = abs(piece)
                        if ptype != PAWN and ptype != KING:
                            has_pieces = True
                            break
                if has_pieces:
                    break
            
            if has_pieces:
                R = 3 if depth >= 6 else 2
                
                # Make null move
                state = {
                    'move': 'null',
                    'captured': 0,
                    'castling_rights': self.board.castling_rights,
                    'en_passant': self.board.en_passant,
                    'halfmove_clock': self.board.halfmove_clock,
                    'fullmove_number': self.board.fullmove_number,
                    'side_to_move': self.board.side_to_move,
                    'zobrist_key': self.board.zobrist_key,
                }
                self.board._history.append(state)
                
                if self.board.en_passant:
                    self.board.zobrist_key ^= ZOBRIST_EP[self.board.en_passant[1]]
                    self.board.en_passant = None
                    
                self.board.zobrist_key ^= ZOBRIST_SIDE
                self.board.side_to_move = 'b' if self.board.side_to_move == 'w' else 'w'
                
                # Search with null move
                null_score, _ = self.negamax(depth - 1 - R, -beta, -beta + 1, ply + 1, make_null=False)
                null_score = -null_score
                
                # Unmake null move
                state = self.board._history.pop()
                self.board.castling_rights = state['castling_rights']
                self.board.en_passant = state['en_passant']
                self.board.halfmove_clock = state['halfmove_clock']
                self.board.fullmove_number = state['fullmove_number']
                self.board.side_to_move = state['side_to_move']
                self.board.zobrist_key = state['zobrist_key']
                
                if null_score >= beta:
                    return beta, []

        # Futility Pruning prep
        futility_margin = 0
        static_eval = 0
        futility_pruning = False
        if depth <= 2 and not in_check:
            static_eval = evaluate(self.board)
            futility_margin = 200 if depth == 1 else 400
            if static_eval + futility_margin < alpha:
                futility_pruning = True

        gen = MoveGenerator(self.board)
        moves = gen.generate_legal()
        
        if not moves:
            if self.board.is_in_check(self.board.turn):
                return -MATE_SCORE + ply, [] # Prefer faster mates
            else:
                return 0, [] # Draw
                
        # Move ordering logic
        def move_score(move: Move) -> int:
            if tt_move is not None and move == tt_move:
                return 30000  # Try TT move absolutely first
            if move == hash_move:
                return 20000  # PV hash move next
                
            (fr, ff), (tr, tf), promo = move
            moving_piece = abs(self.board.board[fr, ff])
            captured_piece = abs(self.board.board[tr, tf])
            
            # 1. Captures (MVV-LVA)
            if captured_piece != 0:
                victim_val = PIECE_VALUES.get(captured_piece, 0)
                attacker_val = PIECE_VALUES.get(moving_piece, 0)
                return CAPTURE_SCORE_BASE + (victim_val * 10) - attacker_val
                
            # 2. King captures aren't possible legally, handled above
            # 3. Promotions
            if promo != 0:
                return CAPTURE_SCORE_BASE - 100 + PIECE_VALUES.get(abs(promo), 0)
                
            # 4. Killer moves (Quiet)
            if self.killers[ply][0] == move:
                return 9000
            elif self.killers[ply][1] == move:
                return 8000
                
            # 5. History heuristic (Quiet)
            sq_idx = tr * 8 + tf
            p_idx = self._piece_index(self.board.board[fr, ff])
            return self.history[p_idx][sq_idx]
            
        moves.sort(key=move_score, reverse=True)
        
        best_pv = []
        best_score = -INF
        best_move = None
        
        for move_idx, move in enumerate(moves):
            is_quiet = self.board.board[move[1][0], move[1][1]] == 0 and move[2] == 0
            
            # Futility Pruning
            if futility_pruning and is_quiet and not in_check:
                if move_score(move) < 8000: # not a killer or hash
                    continue
                    
            self.board.make_move(move)
            
            # Late Move Reductions
            needs_full_search = True
            if depth >= 3 and move_idx >= 3 and is_quiet and not in_check and not self.board.is_in_check(self.board.turn):
                # Don't reduce killers or hash moves
                if move_score(move) < 8000:
                    R = max(1, int(math.log(depth) * math.log(move_idx) / 2.5))
                    reduced_depth = max(1, depth - 1 - R)
                    score, pv = self.negamax(reduced_depth, -alpha - 1, -alpha, ply + 1, make_null=True)
                    score = -score
                    if score <= alpha:
                        needs_full_search = False
                    
            if needs_full_search:
                next_hash_move = None
                score, pv = self.negamax(depth - 1, -beta, -alpha, ply + 1, hash_move=next_hash_move)
                score = -score
                
            self.board.unmake_move()
            
            if self.time_limit_reached:
                return 0, []
                
            if score > best_score:
                best_score = score
                best_pv = [move] + pv
                best_move = move
                
            if best_score > alpha:
                alpha = best_score
                
            if alpha >= beta:
                # Cutoff found
                if is_quiet:
                    # Update killers
                    if move != self.killers[ply][0]:
                        self.killers[ply][1] = self.killers[ply][0]
                        self.killers[ply][0] = move
                    # Update history
                    (fr, ff), (tr, tf), promo = move
                    sq_idx = tr * 8 + tf
                    p_idx = self._piece_index(self.board.board[fr, ff])
                    self.history[p_idx][sq_idx] += depth * depth
                break # Prune
                
        # Store to TT
        if not self.time_limit_reached:
            flag = FLAG_EXACT
            if best_score <= alpha_orig:
                flag = FLAG_ALPHA
            elif best_score >= beta:
                flag = FLAG_BETA
                
            # Adjust mate scores for TT relative to current node
            store_score = best_score
            if store_score > MATE_SCORE - 1000:
                store_score += ply
            elif store_score < -MATE_SCORE + 1000:
                store_score -= ply
                
            self.tt.store(self.board.zobrist_key, depth, store_score, flag, best_move)
                
        return best_score, best_pv

    def iterative_deepening(self, soft_limit_ms: int, hard_limit_ms: int = 0, target_depth: int = 100, stop_event: Optional[threading.Event] = None) -> Tuple[Optional[Move], int, List[Move]]:
        """Run iterative deepening and return the best move, nodes searched, and PV."""
        self.start_time = time.time()
        self.soft_limit_ms = soft_limit_ms
        self.hard_limit_ms = hard_limit_ms if hard_limit_ms > 0 else soft_limit_ms * 5
        self.stop_event = stop_event
        self.time_limit_reached = False
        self.nodes = 0
        
        best_move = None
        best_pv = []
        depth = 1
        
        # We need a legal move generator just to ensure we have *some* fallback move.
        gen = MoveGenerator(self.board)
        moves = gen.generate_legal()
        if not moves:
            return None, 0, []
            
        last_completed_best_move = moves[0]
        
        alpha = -INF
        beta = INF
        prev_score = 0
        
        while not self.time_limit_reached and depth <= target_depth:
            if depth >= 2:
                # Aspiration Windows
                alpha = prev_score - 50
                beta = prev_score + 50
                
            hash_move = best_pv[0] if best_pv else None
            score, pv = self.negamax(depth, alpha, beta, ply=0, hash_move=hash_move)
            
            # Aspiration Window re-searches
            if not self.time_limit_reached:
                if score <= alpha or score >= beta:
                    if score <= alpha: alpha = -INF
                    if score >= beta:  beta = INF
                    score, pv = self.negamax(depth, alpha, beta, ply=0, hash_move=hash_move)
            
            if not self.time_limit_reached:
                prev_score = score
                if pv and len(pv) > 0:
                    last_completed_best_move = pv[0]
                    best_pv = pv
                    
                elapsed = (time.time() - self.start_time) * 1000
                pv_str = " ".join([format_move(m) for m in best_pv])
                
                # Format score correctly
                if abs(score) < MATE_SCORE - 1000:
                    score_str = f"cp {score}"
                else:
                    mate_dist = (MATE_SCORE - abs(score) + 1) // 2
                    if score < 0: mate_dist = -mate_dist
                    score_str = f"mate {mate_dist}"
                    
                print(f"info depth {depth} score {score_str} nodes {self.nodes} nps {int(self.nodes/((elapsed+1)/1000))} time {int(elapsed)} pv {pv_str}")

                if elapsed >= self.soft_limit_ms:
                    break
                    
            depth += 1
            
        return last_completed_best_move, self.nodes, best_pv

    def quiescence(self, alpha: int, beta: int) -> int:
        self.nodes += 1
        
        # Periodic time check
        if (self.nodes & 511) == 0:
            if self.stop_event and self.stop_event.is_set():
                self.time_limit_reached = True
            elif self.hard_limit_ms > 0 and (time.time() - self.start_time) * 1000 > self.hard_limit_ms:
                self.time_limit_reached = True

        if self.time_limit_reached:
            return 0
            
        stand_pat = evaluate(self.board)
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat

        gen = MoveGenerator(self.board)
        moves = gen.generate_legal()
        
        captures = []
        for move in moves:
            (fr, ff), (tr, tf), promo = move
            if self.board.board[tr, tf] != 0 or promo != 0:
                captures.append(move)
                
        def move_score(move: Move) -> int:
            (fr, ff), (tr, tf), promo = move
            moving_piece = abs(self.board.board[fr, ff])
            captured_piece = abs(self.board.board[tr, tf])
            
            if captured_piece != 0:
                victim_val = PIECE_VALUES.get(captured_piece, 0)
                attacker_val = PIECE_VALUES.get(moving_piece, 0)
                return CAPTURE_SCORE_BASE + (victim_val * 10) - attacker_val
                
            if promo != 0:
                return CAPTURE_SCORE_BASE - 100 + PIECE_VALUES.get(abs(promo), 0)
            return 0
            
        captures.sort(key=move_score, reverse=True)
        
        for move in captures:
            self.board.make_move(move)
            score = -self.quiescence(-beta, -alpha)
            self.board.unmake_move()
            
            if self.time_limit_reached:
                return 0
                
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
                
        return alpha
