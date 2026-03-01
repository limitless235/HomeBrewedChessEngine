import sys
import threading
import time
from .board import Board
from .search import Searcher
from .movegen import MoveGenerator
from .search import format_move

def run_search(searcher, soft_limit, hard_limit, target_depth, stop_event):
    best_move, nodes, pv = searcher.iterative_deepening(soft_limit, hard_limit, target_depth, stop_event)
    if best_move:
        best_move_str = format_move(best_move)
        print(f"bestmove {best_move_str}")
        sys.stdout.flush()

def uci_loop():
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    searcher = Searcher(board)
    search_thread = None
    stop_event = threading.Event()

    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            break
        
        if not line:
            break
            
        line = line.strip()
        if not line:
            continue
            
        # Logging to stderr so GUI doesn't parse it
        sys.stderr.write(f">> {line}\n")
        sys.stderr.flush()
        
        tokens = line.split()
        command = tokens[0]
        
        if command == "uci":
            print("id name AntiGravity")
            print("id author Limitless")
            print("uciok")
            sys.stdout.flush()
            
        elif command == "isready":
            print("readyok")
            sys.stdout.flush()
            
        elif command == "ucinewgame":
            board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
            searcher = Searcher(board)
            
        elif command == "position":
            idx = 1
            if len(tokens) > 1:
                if tokens[idx] == "startpos":
                    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
                    idx += 1
                elif tokens[idx] == "fen":
                    # FEN is next 6 tokens
                    if len(tokens) >= idx + 6:
                        fen = " ".join(tokens[idx+1:idx+7])
                        board = Board.from_fen(fen)
                        idx += 7
                        
                searcher.board = board
                
                if idx < len(tokens) and tokens[idx] == "moves":
                    idx += 1
                    for move_str in tokens[idx:]:
                        gen = MoveGenerator(board)
                        legal_moves = gen.generate_legal()
                        for m in legal_moves:
                            if format_move(m) == move_str:
                                board.make_move(m)
                                break
                                
        elif command == "go":
            if search_thread and search_thread.is_alive():
                continue
                
            wtime = btime = winc = binc = movetime = depth = 0
            infinite = False
            
            idx = 1
            while idx < len(tokens):
                sub = tokens[idx]
                if sub == "wtime" and idx + 1 < len(tokens):
                    wtime = int(tokens[idx+1])
                    idx += 2
                elif sub == "btime" and idx + 1 < len(tokens):
                    btime = int(tokens[idx+1])
                    idx += 2
                elif sub == "winc" and idx + 1 < len(tokens):
                    winc = int(tokens[idx+1])
                    idx += 2
                elif sub == "binc" and idx + 1 < len(tokens):
                    binc = int(tokens[idx+1])
                    idx += 2
                elif sub == "movetime" and idx + 1 < len(tokens):
                    movetime = int(tokens[idx+1])
                    idx += 2
                elif sub == "depth" and idx + 1 < len(tokens):
                    depth = int(tokens[idx+1])
                    idx += 2
                elif sub == "infinite":
                    infinite = True
                    idx += 1
                else:
                    idx += 1
                    
            soft_limit = 9999999
            hard_limit = 9999999
            
            if movetime > 0:
                soft_limit = movetime
                hard_limit = movetime
            elif wtime > 0 or btime > 0:
                my_time = wtime if board.turn == 'w' else btime
                my_inc = winc if board.turn == 'w' else binc
                
                moves_remaining = 30
                soft_limit = int(my_time / moves_remaining + my_inc * 0.8)
                hard_limit = soft_limit * 5
                
                # ensure we don't timeout
                if hard_limit > my_time - 50:
                    hard_limit = max(10, my_time - 50)
                if soft_limit > hard_limit:
                    soft_limit = hard_limit
            
            target_depth = depth if depth > 0 else 100
            
            stop_event.clear()
            search_thread = threading.Thread(target=run_search, args=(searcher, soft_limit, hard_limit, target_depth, stop_event))
            search_thread.start()
            
        elif command == "stop":
            if search_thread and search_thread.is_alive():
                stop_event.set()
                search_thread.join()
                
        elif command == "quit":
            if search_thread and search_thread.is_alive():
                stop_event.set()
                search_thread.join()
            break
