import sys
import subprocess
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chess
import httpx
import os
import urllib.parse
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = "local-model"  # LM Studio ignores this, uses loaded model
LM_STUDIO_TIMEOUT = 90.0
COACH_ENABLED = os.getenv("COACH_ENABLED", "true").lower() == "true"
COACH_MAX_TOKENS = 350
COACH_TEMPERATURE = 0.2

SYSTEM_PROMPT = """
You are a chess coach writing structured feedback for an amateur player.
You will receive VERIFIED CHESS FACTS computed by a chess engine and python-chess.
Your ONLY job is to convert these labeled facts into clear educational English.

ABSOLUTE RULES:
1. Never mention any move, piece, square, or plan not explicitly in the provided facts
2. Never perform chess calculations yourself
3. Never invent threats, tactics, or continuations beyond what is in the facts
4. Every chess claim must map to a specific labeled fact provided to you
5. Use only the move names given in facts — never convert or re-express them
6. If a fact field is empty or "unknown", do not mention that topic
7. You are a transcription assistant converting data to English, not a chess analyst

{move_context}

Use this EXACT format. Include every section. Do not add sections not listed here.

VERDICT: [classification from facts exactly as given]

WHAT THIS MOVE DOES:
[1-2 sentences using only: piece_type, piece_color, from_square, to_square,
move_played_san, move_is_capture, captured_piece, move_is_check, move_is_castling.
Describe only what physically happened. Nothing else.]

WHY IT IS [GOOD/PROBLEMATIC]:
[2-3 sentences using only: score_delta_pawns, piece_is_hanging, creates_fork,
exposes_king, piece_is_pinned, pawn_facts, king_safety, piece_activity.
Name the exact chess concept: hanging piece, fork, pin, exposed king,
isolated pawn, passed pawn, central control. Be specific.
If recent_history_summary shows a pattern, mention it in one sentence.]

WHAT YOUR OPPONENT CAN DO NOW:
[1-2 sentences using only hanging_piece_description and creates_fork.
Copy hanging_piece_description verbatim if piece is hanging.
If fork: name the forked pieces and squares from forked_pieces list.
If neither: write exactly "The position is stable after this move."
Never invent a specific opponent move.]

BETTER MOVE:
[If classification is Best Move or Excellent: write "You found the best move."
Otherwise: write "The engine preferred [engine_best_move_san] — 
moving the [best_piece_type] from [best_from] to [best_to]
[capturing the [best_captures_piece]]." 
Then one sentence on the principle this serves based only on provided facts.
Never explain why it is better beyond what the facts show.]

OPENING INSIGHT:
[State opening_name and eco_code. Then quote opening_ideas verbatim.
If opening_name is Unknown Opening write: "The opening is not yet classified.
Focus on center control, piece development, and early castling."
Do not add anything beyond the provided opening facts.]

WHAT TO EXPECT NEXT:
[Only include this section if engine_pv_summary is not empty.
Write: "The engine anticipates: [engine_pv_summary]"
Then one sentence describing what strategic idea these moves represent.
Use only the engine_pv_summary string — do not expand or modify the moves.]

PRINCIPLE TO REMEMBER:
[One sentence. One chess principle tied directly to what happened.
If player_patterns shows recurring issues (hanging_piece_count >= 2,
king_exposure_count >= 2, consecutive_poor_moves >= 3), address that pattern.
Make it personal and actionable.]
"""

ECO_POSITION_MAP = {}
ECO_MOVE_MAP = {}

def load_opening_book():
    openings_dir = os.path.join(PROJECT_ROOT, "openings")
    import io
    import chess.pgn
    for filename in ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]:
        filepath = os.path.join(openings_dir, filename)
        if not os.path.exists(filepath):
            print(f"[OPENING] Missing {filepath} — run download commands", file=sys.stderr)
            continue
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                pgn_text = row.get("pgn", "")
                if not pgn_text: continue
                try:
                    pgn_io = io.StringIO(pgn_text)
                    game = chess.pgn.read_game(pgn_io)
                    if not game: continue
                    uci_moves = []
                    board = game.board()
                    for move in game.mainline_moves():
                        uci_moves.append(move.uci())
                        board.push(move)
                    
                    eco = row.get("eco", "")
                    name = row.get("name", "")
                    
                    if uci_moves:
                        epd = ' '.join(board.fen().split()[:4])
                        ECO_POSITION_MAP[epd] = {
                            "eco": eco,
                            "name": name,
                            "pgn": pgn_text,
                            "uci": " ".join(uci_moves)
                        }
                        move_tuple = tuple(uci_moves)
                        ECO_MOVE_MAP[move_tuple] = {
                            "eco": eco,
                            "name": name,
                        }
                except Exception:
                    pass
    print(f"[OPENING] Loaded {len(ECO_POSITION_MAP)} positions, {len(ECO_MOVE_MAP)} move sequences", file=sys.stderr)

# Call at startup
load_opening_book()

def identify_opening(move_history: list, current_fen: str = None) -> dict:
    if not move_history:
        return default_opening()
    
    # Method 1: Try exact move sequence match (longest prefix first)
    normalized = [m.strip() for m in move_history]
    for length in range(len(normalized), 0, -1):
        prefix = tuple(normalized[:length])
        if prefix in ECO_MOVE_MAP:
            entry = ECO_MOVE_MAP[prefix]
            return {
                "opening_name": entry["name"],
                "eco_code": entry["eco"],
                "variation": "",
                "ideas": get_opening_ideas(entry["name"])
            }
    
    # Method 2: Position hash lookup (handles transpositions)
    if current_fen:
        epd = ' '.join(current_fen.split()[:4])
        if epd in ECO_POSITION_MAP:
            entry = ECO_POSITION_MAP[epd]
            return {
                "opening_name": entry["name"],
                "eco_code": entry["eco"],
                "variation": "",
                "ideas": get_opening_ideas(entry["name"])
            }
    
    # Method 3: Walk back through position history to find last known opening
    try:
        board = chess.Board()
        last_known = None
        for uci in normalized:
            board.push(chess.Move.from_uci(uci))
            epd = ' '.join(board.fen().split()[:4])
            if epd in ECO_POSITION_MAP:
                last_known = ECO_POSITION_MAP[epd]
        if last_known:
            return {
                "opening_name": last_known["name"],
                "eco_code": last_known["eco"],
                "variation": "",
                "ideas": get_opening_ideas(last_known["name"])
            }
    except Exception as e:
        print(f"[OPENING] Walkback error: {e}", file=sys.stderr)
    
    print(f"[OPENING] No match for {len(move_history)} moves", file=sys.stderr)
    return default_opening()

def default_opening():
    return {
        "opening_name": "Unknown Opening",
        "eco_code": "—",
        "variation": "",
        "ideas": "Focus on opening principles: control the center, develop all pieces before attacking, castle early to protect your king."
    }

def get_opening_ideas(name: str) -> str:
    ideas_map = {
        "Sicilian": "Black fights for the center asymmetrically. White typically attacks on the kingside while Black counterattacks on the queenside. Leads to sharp, unbalanced positions.",
        "Ruy Lopez": "White pressures Black's e5 pawn and fights for long-term positional advantage. One of the oldest and most deeply studied openings in chess.",
        "French": "Black accepts a cramped position in exchange for a solid pawn structure. The key tension is the pawn chain on d5 vs e4.",
        "Caro-Kann": "Similar to the French but Black avoids locking in the light-squared bishop. Solid and positional, favored by defensive players.",
        "King's Indian": "Black allows White a large pawn center then counterattacks it. Leads to complex double-edged positions with attacks on both wings.",
        "Queen's Gambit": "White offers a pawn to gain central control. One of the most classical openings — fights for d4 and e4 dominance.",
        "Catalan": "White combines the Queen's Gambit with a kingside fianchetto. Long-term positional pressure on the d5 square.",
        "English": "White controls d5 from the flank. Flexible and transposes into many other openings.",
        "Italian": "White develops naturally and fights for the center. The Giuoco Piano aims for slow positional play while the Evans Gambit is sharp.",
        "Scotch": "White opens the center early with d4. Leads to open positions with active piece play.",
        "Dutch": "Black fights for kingside space immediately. Aggressive and unbalancing from move one.",
        "Nimzo-Indian": "Black prevents White from establishing a strong pawn center by pinning the knight. One of the most theoretically rich openings.",
        "Grunfeld": "Black allows White a large center then attacks it with pieces. Hypermodern strategy at its finest.",
        "Benoni": "Black fights back against White's d4 with c5, creating immediate imbalance and counterplay.",
    }
    for key, ideas in ideas_map.items():
        if key.lower() in name.lower():
            return ideas
    return "A complex position requiring careful piece coordination and adherence to core opening principles."


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/opening_stats")
async def opening_stats(moves: str = ""):
    """Fetch opening stats from Lichess explorer API — no API key needed."""
    if not moves:
        return {"error": "no moves provided"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://explorer.lichess.ovh/lichess",
                params={
                    "play": moves,          # comma-separated UCI moves
                    "ratings": "1600,1800,2000,2200,2500",
                    "speeds": "rapid,classical",
                    "moves": 5,            # top 5 continuations
                },
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                total = data.get("white", 0) + data.get("draws", 0) + data.get("black", 0)
                top_moves = []
                for m in data.get("moves", [])[:3]:
                    move_total = m.get("white", 0) + m.get("draws", 0) + m.get("black", 0)
                    top_moves.append({
                        "move": m.get("san", m.get("uci", "")),
                        "games": move_total,
                        "white_win_pct": round(m.get("white", 0) / move_total * 100) if move_total > 0 else 0,
                        "draw_pct": round(m.get("draws", 0) / move_total * 100) if move_total > 0 else 0,
                        "black_win_pct": round(m.get("black", 0) / move_total * 100) if move_total > 0 else 0,
                    })
                opening_name = data.get("opening", {}).get("name", "") if data.get("opening") else ""
                return {
                    "opening_name": opening_name,
                    "total_games": total,
                    "top_continuations": top_moves,
                    "white_win_pct": round(data.get("white", 0) / total * 100) if total > 0 else 0,
                    "draw_pct": round(data.get("draws", 0) / total * 100) if total > 0 else 0,
                    "black_win_pct": round(data.get("black", 0) / total * 100) if total > 0 else 0,
                }
    except Exception as e:
        print(f"[Lichess API error] {e}", file=sys.stderr)
        return {"error": str(e), "total_games": 0, "top_continuations": []}

class EngineManager:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        
    def start(self):
        self.process = subprocess.Popen(
            [os.path.join(PROJECT_ROOT, "engine", "engine")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, # Ignore stderr to prevent buffer blockages
            text=True,
            bufsize=1
        )
        self.send_command("uci")
        self.wait_for("uciok")
        
    def stop(self):
        if self.process:
            self.send_command("quit")
            self.process.terminate()
            self.process.wait()
            
    def send_command(self, cmd: str):
        if not self.process: return
        with self.lock:
            try:
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
            except Exception as e:
                print(f"FAILED TO SEND COMMAND: {e}", file=sys.stderr)
            
    def wait_for(self, target: str) -> str:
        if not self.process: return ""
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                break
            if line == target or line.startswith(target):
                return line
        return ""
                
    def get_bestmove(self, time_limit: int) -> tuple[str, int, str]:
        self.send_command(f"go movetime {time_limit}")
        print(f"[DEBUG] Sent go movetime {time_limit}", file=sys.stderr)
        last_score = 0
        last_pv = ""
        while True:
            line = self.process.stdout.readline().strip()
            if not line:
                break
            if line.startswith("info"):
                parts = line.split()
                if "score" in parts:
                    idx = parts.index("score")
                    if idx + 2 < len(parts):
                        if parts[idx+1] == "cp":
                            last_score = int(parts[idx+2])
                        elif parts[idx+1] == "mate":
                            mate_in = int(parts[idx+2])
                            last_score = 10000 if mate_in > 0 else -10000
                if "pv" in parts:
                    idx = parts.index("pv")
                    last_pv = " ".join(parts[idx+1:])
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1], last_score, last_pv
        print("[DEBUG] Exited loop without finding bestmove", file=sys.stderr)
        return "", last_score, last_pv

engine = EngineManager()

# Global game state using python-chess for validation and history tracking
board = chess.Board()

@app.on_event("startup")
def startup():
    engine.start()

@app.on_event("shutdown")
def shutdown():
    engine.stop()

class MoveRequest(BaseModel):
    move: str
    
class FenRequest(BaseModel):
    fen: str

dist_dir = os.path.join(PROJECT_ROOT, "frontend", "static", "chessground", "dist")
assets_dir = os.path.join(PROJECT_ROOT, "frontend", "static", "chessground", "assets")
if os.path.exists(dist_dir):
    app.mount("/dist", StaticFiles(directory=dist_dir), name="dist")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
def serve_index():
    index_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Backend API is running. UI is hosted on Vercel."}

class NewGameRequest(BaseModel):
    player_color: str = "white"

@app.post("/new_game")
def new_game(req: NewGameRequest = NewGameRequest()):
    global board
    board = chess.Board()
    engine.send_command("ucinewgame")
    engine.send_command("isready")
    engine.wait_for("readyok")
    engine.send_command("position startpos")
    return {"status": "ok", "fen": board.fen(), "player_color": req.player_color}

def format_game_over(b: chess.Board, last_engine_move: str, engine_pv: str = ""):
    status = "draw"
    winner = None
    if b.is_checkmate():
        status = "checkmate"
        winner = "white" if b.turn == chess.BLACK else "black"
    elif b.is_stalemate():
        status = "stalemate"
    elif b.is_insufficient_material():
        status = "insufficient_material"
    elif b.can_claim_fifty_moves():
        status = "50_move_rule"
    elif b.can_claim_threefold_repetition():
        status = "repetition"
    
    return {
        "engine_move": last_engine_move,
        "engine_pv": engine_pv,
        "fen": b.fen(),
        "status": status,
        "winner": winner
    }

@app.post("/move")
def make_move(req: MoveRequest):
    global board
    try:
        move = chess.Move.from_uci(req.move)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UCI format")
        
    if move not in board.legal_moves:
        legal = [m.uci() for m in board.legal_moves]
        raise HTTPException(status_code=400, detail={"error": "Illegal move", "legal_moves": legal})
        
    # Get score before player's move
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}" if moves_str else "position startpos")
    _, raw_score_before, _ = engine.get_bestmove(100)
    score_before = raw_score_before if board.turn == chess.WHITE else -raw_score_before
        
    player_move_san = board.san(move)    
    board.push(move)
    fen_after_player = board.fen()
    
    if board.is_game_over():
        result = format_game_over(board, None)
        result["score_before"] = score_before
        result["score_after"] = score_before
        result["fen_after_player"] = fen_after_player
        result["player_move_san"] = player_move_san
        return result
        
    # Sync engine position
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}")
    
    # Let engine think for 1 second
    best_move_uci, raw_score_after, engine_pv = engine.get_bestmove(1000)
    score_after = raw_score_after if board.turn == chess.WHITE else -raw_score_after
    
    if best_move_uci and best_move_uci != "0000":
        engine_move = chess.Move.from_uci(best_move_uci)
        if engine_move in board.legal_moves:
            board.push(engine_move)
        else:
            print(f"ENGINE ILLEGAL MOVE: {best_move_uci}", file=sys.stderr)
            pass
            
    if board.is_game_over():
        result = format_game_over(board, best_move_uci, engine_pv)
        result["score_before"] = score_before
        result["score_after"] = score_after
        result["fen_after_player"] = fen_after_player
        return result
        
    return {
        "engine_move": best_move_uci,
        "engine_pv": engine_pv,
        "player_move_san": player_move_san,
        "engine_move_san": board.san(engine_move) if best_move_uci and best_move_uci != "0000" and engine_move in board.legal_moves else "",
        "fen": board.fen(),
        "fen_after_player": fen_after_player,
        "status": "ongoing",
        "winner": None,
        "score_before": score_before,
        "score_after": score_after
    }

class EngineMoveRequest(BaseModel):
    movetime: int = 1000

@app.post("/engine_move")
def make_engine_move(req: EngineMoveRequest = EngineMoveRequest()):
    global board
    
    if board.is_game_over():
        return format_game_over(board, None)
        
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}" if moves_str else "position startpos")
    
    best_move_uci, raw_score_after, engine_pv = engine.get_bestmove(req.movetime)
    score_after = raw_score_after if board.turn == chess.WHITE else -raw_score_after
    
    engine_move_san = ""
    if best_move_uci and best_move_uci != "0000":
        engine_move = chess.Move.from_uci(best_move_uci)
        if engine_move in board.legal_moves:
            engine_move_san = board.san(engine_move)
            board.push(engine_move)
            
    if board.is_game_over():
        res = format_game_over(board, best_move_uci, engine_pv)
        res["score_after"] = score_after
        return res
        
    return {
        "engine_move": best_move_uci,
        "engine_pv": engine_pv,
        "engine_move_san": engine_move_san,
        "fen": board.fen(),
        "status": "ongoing",
        "score_after": score_after
    }

@app.get("/fen")
def get_fen():
    return {"fen": board.fen()}

@app.get("/debug_openings")
def debug_openings():
    import glob
    sizes = {}
    try:
        paths = glob.glob(os.path.join(PROJECT_ROOT, "openings", "*.tsv"))
        for p in paths:
            sizes[os.path.basename(p)] = os.path.getsize(p)
    except Exception as e:
        sizes["error"] = str(e)
    return {
        "file_sizes": sizes,
        "loaded_positions": len(ECO_POSITION_MAP),
        "loaded_move_sequences": len(ECO_MOVE_MAP)
    }

@app.get("/legal_moves")
def get_legal_moves(fen: str = None):
    try:
        b = chess.Board(fen) if fen else board
        moves = [m.uci() for m in b.legal_moves]
        return {"moves": moves}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN")

@app.post("/set_position")
def set_position(req: FenRequest):
    global board
    try:
        board = chess.Board(req.fen)
        engine.send_command(f"position fen {req.fen}")
        return {"status": "ok", "fen": board.fen()}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid FEN")


def uci_to_san(fen: str, uci_move: str) -> str:
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci_move)
        return board.san(move)
    except Exception:
        return uci_move

def moves_to_san_list(start_fen: str, uci_moves: list[str]) -> list[str]:
    board = chess.Board(start_fen) if start_fen else chess.Board()
    san_list = []
    for uci in uci_moves:
        try:
            move = chess.Move.from_uci(uci)
            san_list.append(board.san(move))
            board.push(move)
        except Exception:
            san_list.append(uci)
    return san_list

def compute_material_balance(fen: str) -> dict:
    board = chess.Board(fen)
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
              chess.ROOK: 5, chess.QUEEN: 9}
    white = sum(values.get(pt, 0) * len(board.pieces(pt, chess.WHITE))
                for pt in values)
    black = sum(values.get(pt, 0) * len(board.pieces(pt, chess.BLACK))
                for pt in values)
    delta = white - black
    if abs(delta) < 1:
        balance = "Equal material"
    else:
        side = "White" if delta > 0 else "Black"
        balance = f"{side} is up {abs(delta)} point{'s' if abs(delta)!=1 else ''}"
    return {"white_total": white, "black_total": black, "balance": balance}

def extract_pv_from_engine(pv_uci_string: str, fen: str, max_moves: int = 4) -> dict:
    if not pv_uci_string:
        return {"moves": [], "summary": ""}
    
    board = chess.Board(fen)
    pv_moves = pv_uci_string.strip().split()[:max_moves]
    readable = []
    
    for i, uci in enumerate(pv_moves):
        try:
            move = chess.Move.from_uci(uci)
            san = board.san(move)
            side = "White" if board.turn == chess.WHITE else "Black"
            readable.append({
                "san": san,
                "uci": uci,
                "side": side,
                "move_number": board.fullmove_number
            })
            board.push(move)
        except Exception:
            break
    
    if not readable:
        return {"moves": [], "summary": ""}
    
    summary_parts = []
    for m in readable:
        summary_parts.append(f"{m['side']}: {m['san']}")
    
    return {
        "moves": readable,
        "summary": " → ".join(summary_parts)
    }

def build_history_summary(recent_history: list) -> str:
    if not recent_history:
        return "This is the start of the game."
    lines = []
    for entry in recent_history[-6:]:
        move = entry.get("move_san", "?")
        classification = entry.get("classification", "")
        was_player = entry.get("was_player_move", False)
        who = "You" if was_player else "Engine"
        if classification:
            lines.append(f"{who} played {move} ({classification})")
        else:
            lines.append(f"{who} played {move}")
    return " → ".join(lines)


def compute_position_facts(fen_before, fen_after, move_played_uci, engine_best_move_uci, score_before_cp, score_after_cp, analyzing_side="player", recent_history=None):
    if recent_history is None:
        recent_history = []
    
    facts = {}
    board_before = chess.Board(fen_before)
    move = chess.Move.from_uci(move_played_uci)

    board_side = board_before.turn
    facts["player_side"] = "White" if board_side == chess.WHITE else "Black"
    facts["opponent_side"] = "Black" if board_side == chess.WHITE else "White"

    facts["move_played_san"] = board_before.san(move)
    facts["move_is_capture"] = board_before.is_capture(move)
    facts["move_is_check"] = board_before.gives_check(move)
    facts["move_is_castling"] = board_before.is_castling(move)
    facts["move_is_en_passant"] = board_before.is_en_passant(move)
    facts["move_is_promotion"] = (move.promotion is not None)

    piece_moved = board_before.piece_at(move.from_square)
    facts["piece_type"] = chess.piece_name(piece_moved.piece_type) if piece_moved else "unknown"
    facts["piece_color"] = "White" if piece_moved and piece_moved.color == chess.WHITE else "Black"
    facts["from_square"] = chess.square_name(move.from_square)
    facts["to_square"] = chess.square_name(move.to_square)

    if facts["move_is_capture"]:
        if facts["move_is_en_passant"]:
            facts["captured_piece"] = "pawn"
        else:
            captured = board_before.piece_at(move.to_square)
            facts["captured_piece"] = chess.piece_name(captured.piece_type) if captured else "unknown"
    else:
        facts["captured_piece"] = None

    board_after = chess.Board(fen_after)
    facts["piece_is_hanging"] = is_piece_hanging(board_after, move.to_square)

    facts["analyzing_side"] = analyzing_side
    facts["move_context"] = (
        "This is YOUR move — here is coaching on what you played." 
        if analyzing_side == "player" 
        else "This is the ENGINE's move — here is an explanation of what it did and why, so you can learn from it."
    )
    facts["recent_history"] = recent_history
    facts["recent_history_summary"] = build_history_summary(recent_history)

    if facts["piece_is_hanging"]:
        attackers = board_after.attackers(not board_side, move.to_square)
        attacker_list = []
        for sq in attackers:
            p = board_after.piece_at(sq)
            if p:
                attacker_list.append(f"{chess.piece_name(p.piece_type)} on {chess.square_name(sq)}")
        facts["opponent_can_capture_with"] = attacker_list
        facts["hanging_piece_description"] = (
            f"Your {facts['piece_type']} on {facts['to_square']} is attacked by "
            f"{', '.join(attacker_list) if attacker_list else 'opponent pieces'} "
            f"and has no defenders. {facts['opponent_side']} can capture it for free."
        )
    else:
        facts["opponent_can_capture_with"] = []
        facts["hanging_piece_description"] = "No pieces are hanging after this move."

    try:
        board_for_best = chess.Board(fen_before)
        best_move = chess.Move.from_uci(engine_best_move_uci)
        facts["engine_best_move_san"] = board_for_best.san(best_move)
        best_piece = board_for_best.piece_at(best_move.from_square)
        facts["best_piece_type"] = chess.piece_name(best_piece.piece_type) if best_piece else "unknown"
        facts["best_from"] = chess.square_name(best_move.from_square)
        facts["best_to"] = chess.square_name(best_move.to_square)
        if board_for_best.is_capture(best_move):
            best_captured = board_for_best.piece_at(best_move.to_square)
            facts["best_captures_piece"] = chess.piece_name(best_captured.piece_type) if best_captured else None
            facts["best_is_capture"] = True
        else:
            facts["best_captures_piece"] = None
            facts["best_is_capture"] = False
        facts["best_move_gives_check"] = board_for_best.gives_check(best_move)
    except Exception as e:
        print(f"[best move parse error] {e} — uci={engine_best_move_uci} fen={fen_before}", file=sys.stderr)
        facts["engine_best_move_san"] = engine_best_move_uci
        facts["best_piece_type"] = "unknown"
        facts["best_from"] = "unknown"
        facts["best_to"] = "unknown"
        facts["best_captures_piece"] = None
        facts["best_move_gives_check"] = False
        facts["best_is_capture"] = False

    if board_before.turn == chess.WHITE:
        delta_cp = score_after_cp - score_before_cp
    else:
        delta_cp = -(score_after_cp - score_before_cp)
    
    facts["score_delta_cp"] = delta_cp
    facts["score_delta_pawns"] = round(delta_cp / 100, 2)
    facts["score_before_display"] = format_score(score_before_cp)
    facts["score_after_display"] = format_score(score_after_cp)

    facts["creates_fork"] = detects_fork(board_before, board_after, move)
    facts["exposes_king"] = exposes_own_king(board_before, board_after, move)
    facts["piece_is_pinned"] = is_piece_pinned(board_after, move.to_square)
    facts["move_results_in_checkmate"] = board_after.is_checkmate()
    facts["side_in_check_after"] = board_after.is_check()
    facts["material_balance_before"] = compute_material_balance(fen_before)
    facts["material_balance_after"] = compute_material_balance(fen_after)
    facts["material_changed"] = facts["material_balance_before"]["balance"] != facts["material_balance_after"]["balance"]
    facts["pawn_facts"] = compute_pawn_facts(board_before, board_after, move)
    facts["king_safety"] = compute_king_safety(board_before, board_after)
    facts["piece_activity"] = compute_piece_activity(board_after, move)
    
    return facts

def format_score(cp):
    pawns = cp / 100
    if cp > 0: return f"White is better by {abs(pawns):.1f} pawns"
    elif cp < 0: return f"Black is better by {abs(pawns):.1f} pawns"
    else: return "Position is equal"

def is_piece_hanging(board, square):
    piece = board.piece_at(square)
    if not piece: return False
    return len(board.attackers(not piece.color, square)) > 0 and len(board.attackers(piece.color, square)) == 0

def detects_fork(board_before, board_after, move):
    piece = board_after.piece_at(move.to_square)
    if not piece: return {"is_fork": False, "forked_pieces": []}
    values = {chess.QUEEN:9, chess.ROOK:5, chess.BISHOP:3, chess.KNIGHT:3, chess.PAWN:1, chess.KING:100}
    attacked = []
    for sq in board_after.attacks(move.to_square):
        target = board_after.piece_at(sq)
        if target and target.color != piece.color and values.get(target.piece_type,0) >= values.get(piece.piece_type,0):
            attacked.append({"piece": chess.piece_name(target.piece_type), "square": chess.square_name(sq)})
    if len(attacked) >= 2: return {"is_fork": True, "forked_pieces": attacked}
    return {"is_fork": False, "forked_pieces": []}

def exposes_own_king(board_before, board_after, move):
    piece = board_before.piece_at(move.from_square)
    if not piece: return False
    color = piece.color
    king_sq = board_after.king(color)
    if king_sq is None: return False
    return len(board_after.attackers(not color, king_sq)) > len(board_before.attackers(not color, king_sq))

def is_piece_pinned(board, square):
    piece = board.piece_at(square)
    if not piece: return False
    return board.is_pinned(piece.color, square)

def compute_pawn_facts(board_before, board_after, move):
    piece = board_before.piece_at(move.from_square)
    if not piece or piece.piece_type != chess.PAWN:
        return {"pawn_moved": False, "creates_isolated_pawn": False, "is_passed_pawn": False}
    color = piece.color
    file_idx = chess.square_file(move.to_square)
    adj_files = [f for f in [file_idx-1, file_idx+1] if 0 <= f <= 7]
    has_neighbor = any(
        board_after.piece_at(chess.square(f, r)) and
        board_after.piece_at(chess.square(f, r)).piece_type == chess.PAWN and
        board_after.piece_at(chess.square(f, r)).color == color
        for f in adj_files for r in range(8)
    )
    return {
        "pawn_moved": True,
        "creates_isolated_pawn": not has_neighbor,
        "is_passed_pawn": is_passed_pawn(board_after, move.to_square, color),
        "pawn_rank": chess.square_rank(move.to_square) + 1 if color == chess.WHITE else 8 - chess.square_rank(move.to_square)
    }

def is_passed_pawn(board, square, color):
    file_idx = chess.square_file(square)
    rank_idx = chess.square_rank(square)
    for f in [file_idx-1, file_idx, file_idx+1]:
        if not 0 <= f <= 7: continue
        for r in range(8):
            sq = chess.square(f, r)
            p = board.piece_at(sq)
            if p and p.piece_type == chess.PAWN and p.color != color:
                if color == chess.WHITE and r > rank_idx: return False
                if color == chess.BLACK and r < rank_idx: return False
    return True

def compute_king_safety(board_before, board_after):
    facts = {}
    for name, color in [("white", chess.WHITE), ("black", chess.BLACK)]:
        king_sq = board_after.king(color)
        if king_sq is None: continue
        facts[f"{name}_king_attackers"] = len(board_after.attackers(not color, king_sq))
        facts[f"{name}_king_square"] = chess.square_name(king_sq)
        if color == chess.WHITE: facts["white_king_castled"] = king_sq in [chess.G1, chess.C1]
        else: facts["black_king_castled"] = king_sq in [chess.G8, chess.C8]
    return facts

def compute_piece_activity(board_after, move):
    piece = board_after.piece_at(move.to_square)
    if not piece: return {"squares_controlled": 0, "controls_center": False}
    attacks = board_after.attacks(move.to_square)
    center = chess.SquareSet([chess.E4, chess.E5, chess.D4, chess.D5])
    return {
        "squares_controlled": len(attacks),
        "controls_center": bool(attacks & center),
        "to_square_name": chess.square_name(move.to_square)
    }

def validate_coach_response(response, facts):
    import re
    legitimate = set()
    if facts.get("move_played_san"): legitimate.add(facts["move_played_san"].rstrip("+#"))
    if facts.get("engine_best_move_san"): legitimate.add(facts["engine_best_move_san"].rstrip("+#"))
    found = re.findall(r'\b([KQRBN]?x?[a-h][1-8](?:=[QRBN])?[+#]?)\b', response)
    suspicious = [m for m in found if re.search(r'[a-h][1-8]', m.rstrip("+#").replace("x",""))
                  and not any(m.rstrip("+#").replace("x","") in l or l in m.rstrip("+#").replace("x","") for l in legitimate)]
    if suspicious:
        print(f"[COACH WARNING] Hallucinated moves: {suspicious}", file=sys.stderr)
    return response

class AnalyzeMoveRequest(BaseModel):
    fen_before: str
    move_played: str
    fen_after: str
    engine_best_move: str
    engine_score_before: int
    engine_score_after: int
    move_history: list[str]
    analyzing_side: str = "player"
    recent_history: list[dict] = []
    engine_pv: str = ""
    game_patterns: dict = {}

@app.post("/analyze_move")
async def analyze_move(req: AnalyzeMoveRequest):
    facts = compute_position_facts(
        req.fen_before, 
        req.fen_after, 
        req.move_played, 
        req.engine_best_move, 
        req.engine_score_before, 
        req.engine_score_after,
        req.analyzing_side,
        req.recent_history
    )
    facts["engine_pv"] = extract_pv_from_engine(req.engine_pv, req.fen_after, max_moves=4)
    
    delta = facts["score_delta_cp"]
    
    c = "Mistake"
    if req.move_played == req.engine_best_move: c = "Best Move"
    elif delta >= -10: c = "Excellent"
    elif delta >= -30: c = "Good"
    elif delta >= -80: c = "Inaccuracy"
    elif delta >= -200: c = "Mistake"
    else: c = "Blunder"
    
    if req.engine_score_before > 200 and -req.engine_score_after < -200: c = "Game-Losing Blunder"
    if facts["move_results_in_checkmate"]: c = "Checkmate Blunder"
    
    facts["classification"] = c
    
    opening_data = identify_opening(req.move_history, req.fen_after)
    facts["opening_name"] = opening_data["opening_name"] + (f", {opening_data['variation']}" if opening_data["variation"] else "")
    facts["eco_code"] = opening_data["eco_code"]
    facts["opening_ideas"] = opening_data["ideas"]
    
    u_name = urllib.parse.quote(facts["opening_name"].replace(" ", "_"))
    u_search = urllib.parse.quote_plus(facts["opening_name"])
    
    san_list = moves_to_san_list("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", req.move_history)
    moves_str = "_".join(san_list)
    analysis_url = f"https://lichess.org/analysis/pgn/{urllib.parse.quote(moves_str)}"
    
    facts["move_number"] = len(req.move_history) // 2 + 1
    mc = len(req.move_history)
    facts["game_phase"] = "Opening"
    if mc > 10: facts["game_phase"] = "Middlegame"
    mat_score = sum(len(chess.Board(req.fen_after).pieces(pt, color)) * v for pt, v in {1:1, 2:3, 3:3, 4:5, 5:9}.items() for color in [chess.WHITE, chess.BLACK])
    if mc > 25 or mat_score < 30: facts["game_phase"] = "Endgame"

    patterns = req.game_patterns
    blunders = patterns.get("blunders", 0)
    mistakes = patterns.get("mistakes", 0)
    hangingPieceCount = patterns.get("hangingPieceCount", 0)
    kingExposureCount = patterns.get("kingExposureCount", 0)
    consecutivePoorMoves = patterns.get("consecutivePoorMoves", 0)

    actual_system_prompt = SYSTEM_PROMPT.replace("{move_context}", facts.get("move_context", ""))

    if facts.get("analyzing_side") == "engine":
        actual_system_prompt = actual_system_prompt.replace(
            "BETTER MOVE:\n[If classification is Best Move or Excellent: write \"You found the best move.\"\nOtherwise: write \"The engine preferred [engine_best_move_san] — \nmoving the [best_piece_type] from [best_from] to [best_to]\n[capturing the [best_captures_piece]].\" \nThen one sentence on the principle this serves based only on provided facts.\nNever explain why it is better beyond what the facts show.]\n\n",
            ""
        )

    user_prompt = f"""{actual_system_prompt}
Use ONLY these verified facts. Do not reason beyond them.

CONTEXT:
You are coaching: {facts['player_side']}
Opponent is: {facts['opponent_side']}
Move context: {facts.get('move_context', '')}
Game phase: {facts['game_phase']}
Move number: {facts['move_number']}

MOVE FACTS:
Move played: {facts['move_played_san']} (from {facts['from_square']} to {facts['to_square']})
Piece that moved: {facts['piece_color']} {facts['piece_type']}
Was it a capture: {facts['move_is_capture']}
Piece captured: {facts['captured_piece']}
Was it a check: {facts['move_is_check']}
Was it castling: {facts['move_is_castling']}
Was it en passant: {facts['move_is_en_passant']}
Was it a promotion: {facts['move_is_promotion']}

ENGINE ASSESSMENT:
Classification: {facts['classification']}
Score before: {facts['score_before_display']}
Score after: {facts['score_after_display']}
Score change: {facts.get('score_delta_pawns', 0.0):+.2f} pawns (positive = good for {facts['player_side']})
Best move is for: {facts['player_side']}
Engine preferred move: {facts.get('engine_best_move_san', 'unknown')}
Engine preferred piece: {facts.get('best_piece_type', 'unknown')} from {facts.get('best_from', 'unknown')} to {facts.get('best_to', 'unknown')}
Engine preferred move captures: {facts.get('best_captures_piece', 'nothing')}
Engine preferred move gives check: {facts.get('best_move_gives_check', False)}

TACTICAL FACTS:
Hanging piece situation: {facts['hanging_piece_description']}
Creates fork: {facts['creates_fork']['is_fork']}
Forked pieces (if any): {facts['creates_fork']['forked_pieces']}
Exposes own king: {facts['exposes_king']}
Moved piece is pinned: {facts['piece_is_pinned']}
Results in checkmate: {facts['move_results_in_checkmate']}
Opponent is in check after move: {facts['side_in_check_after']}

PAWN FACTS:
Pawn was moved: {facts['pawn_facts']['pawn_moved']}
Creates isolated pawn: {facts['pawn_facts']['creates_isolated_pawn']}
Creates passed pawn: {facts['pawn_facts']['is_passed_pawn']}

MATERIAL FACTS:
Material before: {facts['material_balance_before']['balance']}
Material after: {facts['material_balance_after']['balance']}
Material changed: {facts['material_changed']}

PIECE ACTIVITY:
Squares now controlled by moved piece: {facts['piece_activity']['squares_controlled']}
Controls central squares (d4/d5/e4/e5): {facts['piece_activity']['controls_center']}

KING SAFETY:
White king on: {facts['king_safety'].get('white_king_square', 'None')}
Black king on: {facts['king_safety'].get('black_king_square', 'None')}
Pieces attacking white king: {facts['king_safety'].get('white_king_attackers', 0)}
Pieces attacking black king: {facts['king_safety'].get('black_king_attackers', 0)}

RECENT GAME HISTORY:
{facts.get('recent_history_summary', '')}

ENGINE PLANNED CONTINUATION:
{facts.get('engine_pv', {}).get('summary', 'No continuation available')}

OPENING FACTS:
Opening: {facts['opening_name']}
ECO: {facts['eco_code']}
Ideas: {facts['opening_ideas']}

PLAYER PATTERNS THIS GAME:
Blunders so far: {blunders}
Mistakes so far: {mistakes}
Times leaving pieces hanging: {hangingPieceCount}
Times exposing king: {kingExposureCount}
Consecutive poor moves: {consecutivePoorMoves}

Write coaching feedback using ONLY the facts above.
Do not mention any move, piece, square, or plan not explicitly listed here.
"""

    coach_feedback = None
    if COACH_ENABLED:
        try:
            headers = {"ngrok-skip-browser-warning": "true"}
            async with httpx.AsyncClient(timeout=LM_STUDIO_TIMEOUT, headers=headers) as client:
                resp = await client.post(
                    f"{LM_STUDIO_BASE_URL}/chat/completions",
                    json={
                        "model": LM_STUDIO_MODEL,
                        "messages": [
                            {"role": "user", "content": user_prompt}
                        ],
                        "temperature": COACH_TEMPERATURE,
                        "max_tokens": COACH_MAX_TOKENS,
                        "stream": False
                    }
                )
                if resp.status_code == 200:
                    coach_feedback = resp.json()["choices"][0]["message"]["content"]
                    coach_feedback = validate_coach_response(coach_feedback, facts)
                elif resp.status_code in [400, 500]:
                    try:
                        err_msg = resp.json().get("error", "Unknown LM Studio Error")
                        coach_feedback = f"LM Studio API Error (Status {resp.status_code}): {err_msg}"
                    except Exception:
                        coach_feedback = f"No model loaded in LM Studio, or prompt template rejected (Status {resp.status_code}). Open LM Studio, select a model, and click Start Server."
        except Exception as e:
            coach_feedback = f"Analysis timed out or connection failed ({e}). Ensure LM Studio server is running."

    tactical_flags = {
        "piece_is_hanging": facts["piece_is_hanging"],
        "creates_fork": facts["creates_fork"],
        "exposes_king": facts["exposes_king"],
        "piece_is_pinned": facts["piece_is_pinned"]
    }

    return {
        "classification": c,
        "score_delta": delta,
        "opening_name": facts["opening_name"],
        "eco_code": facts["eco_code"],
        "opening_ideas": facts["opening_ideas"],
        "opening_url": f"https://lichess.org/opening/{u_name}",
        "study_url": f"https://lichess.org/study/search?q={u_search}",
        "analysis_url": analysis_url,
        "coach_feedback": coach_feedback,
        "engine_best_move": req.engine_best_move,
        "engine_best_move_san": facts.get("engine_best_move_san", req.engine_best_move),
        "move_played": req.move_played,
        "move_played_san": facts.get("move_played_san", req.move_played),
        "game_phase": facts["game_phase"],
        "material_balance": facts["material_balance_after"]["balance"],
        "tactical_flags": tactical_flags
    }

@app.get("/opening")
def get_opening(moves: str = ""):
    move_list = moves.split(",") if moves else []
    
    b = chess.Board()
    for m in move_list:
        try:
            b.push(chess.Move.from_uci(m))
        except:
            pass
            
    opening_data = identify_opening(move_list, b.fen())
    main_name = opening_data["opening_name"]
    var_name = opening_data["variation"]
    eco_code = opening_data["eco_code"]
    ideas = opening_data["ideas"]
    
    opening_name = main_name + (f", {var_name}" if var_name else "")
    u_name = urllib.parse.quote(opening_name.replace(" ", "_"))
    u_search = urllib.parse.quote_plus(opening_name)
    san_list = moves_to_san_list("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", move_list)
    moves_str = "_".join(san_list)
    return {
       "opening_name": main_name,
       "variation": var_name,
       "eco_code": eco_code,
       "opening_url": f"https://lichess.org/opening/{u_name}",
       "study_url": f"https://lichess.org/study/search?q={u_search}",
       "analysis_url": f"https://lichess.org/analysis/pgn/{urllib.parse.quote(moves_str)}",
       "opening_ideas": ideas
    }

@app.get("/coach_status")
async def get_coach_status():
    try:
        headers = {"ngrok-skip-browser-warning": "true"}
        async with httpx.AsyncClient(timeout=2.0, headers=headers) as client:
            resp = await client.get(f"{LM_STUDIO_BASE_URL}/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                mname = models[0]["id"] if len(models) > 0 else "Unknown Model"
                return {
                   "lmstudio_running": True,
                   "model_loaded": len(models) > 0,
                   "model_name": mname,
                   "api_url": LM_STUDIO_BASE_URL,
                   "status_message": f"Coach Active — {mname} loaded" if len(models)>0 else "No model loaded"
                }
    except Exception:
        pass
    
    return {
       "lmstudio_running": False,
       "model_loaded": False,
       "status_message": "LM Studio not running — open LM Studio and start the local server"
    }