import re
import os

with open("/Users/limitless/Documents/ChessEngine/server.py", "r") as f:
    orig = f.read()

# 1. opening_stats endpoint
opening_stats = """
@app.get("/opening_stats")
async def opening_stats(moves: str = ""):
    \"\"\"Fetch opening stats from Lichess explorer API — no API key needed.\"\"\"
    import httpx
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
        import sys
        print(f"[Lichess API error] {e}", file=sys.stderr)
    return {"error": "Failed", "total_games": 0, "top_continuations": []}

"""

orig = orig.replace("class EngineManager", opening_stats + "class EngineManager")


old_get_bestmove = """    def get_bestmove(self, time_limit: int) -> tuple[str, int]:
        self.send_command(f"go movetime {time_limit}")
        print(f"[DEBUG] Sent go movetime {time_limit}", file=sys.stderr)
        last_score = 0
        while True:
            line = self.process.stdout.readline().strip()
            print(f"[DEBUG ENGINE] {line}", file=sys.stderr)
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
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1], last_score
        print("[DEBUG] Exited loop without finding bestmove", file=sys.stderr)
        return "", last_score"""

new_get_bestmove = """    def get_bestmove(self, time_limit: int) -> tuple[str, int, str]:
        self.send_command(f"go movetime {time_limit}")
        import sys
        print(f"[DEBUG] Sent go movetime {time_limit}", file=sys.stderr)
        last_score = 0
        last_pv = ""
        while True:
            line = self.process.stdout.readline().strip()
            # print(f"[DEBUG ENGINE] {line}", file=sys.stderr)
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
        return "", last_score, last_pv"""

orig = orig.replace(old_get_bestmove, new_get_bestmove)

orig = orig.replace("def format_game_over(b: chess.Board, last_engine_move: str):", "def format_game_over(b: chess.Board, last_engine_move: str, engine_pv: str = \"\"):")

orig = orig.replace("\"engine_move\": last_engine_move,", "\"engine_move\": last_engine_move,\n        \"engine_pv\": engine_pv,")

old_make_move_engine = """    # Get score before player's move
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}" if moves_str else "position startpos")
    _, raw_score_before = engine.get_bestmove(100)
    score_before = raw_score_before if board.turn == chess.WHITE else -raw_score_before
        
    board.push(move)
    
    if board.is_game_over():
        result = format_game_over(board, None)
        result["score_before"] = score_before
        result["score_after"] = score_before
        return result
        
    # Sync engine position
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}")
    
    # Let engine think for 1 second
    best_move_uci, raw_score_after = engine.get_bestmove(1000)
    score_after = raw_score_after if board.turn == chess.WHITE else -raw_score_after
    
    if best_move_uci and best_move_uci != "0000":
        engine_move = chess.Move.from_uci(best_move_uci)
        if engine_move in board.legal_moves:
            board.push(engine_move)
        else:
            print(f"ENGINE ILLEGAL MOVE: {best_move_uci}", file=sys.stderr)
            # Failsafe
            pass
            
    if board.is_game_over():
        result = format_game_over(board, best_move_uci)
        result["score_before"] = score_before
        result["score_after"] = score_after
        return result
        
    return {
        "engine_move": best_move_uci,
        "fen": board.fen(),
        "status": "ongoing",
        "winner": None,
        "score_before": score_before,
        "score_after": score_after
    }"""

new_make_move_engine = """    # Get score before player's move
    moves_str = " ".join([m.uci() for m in board.move_stack])
    engine.send_command(f"position startpos moves {moves_str}" if moves_str else "position startpos")
    _, raw_score_before, _ = engine.get_bestmove(100)
    score_before = raw_score_before if board.turn == chess.WHITE else -raw_score_before
        
    board.push(move)
    
    if board.is_game_over():
        result = format_game_over(board, None)
        result["score_before"] = score_before
        result["score_after"] = score_before
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
            import sys
            print(f"ENGINE ILLEGAL MOVE: {best_move_uci}", file=sys.stderr)
            # Failsafe
            pass
            
    if board.is_game_over():
        result = format_game_over(board, best_move_uci, engine_pv)
        result["score_before"] = score_before
        result["score_after"] = score_after
        return result
        
    return {
        "engine_move": best_move_uci,
        "engine_pv": engine_pv,
        "fen": board.fen(),
        "status": "ongoing",
        "winner": None,
        "score_before": score_before,
        "score_after": score_after
    }"""

orig = orig.replace(old_make_move_engine, new_make_move_engine)

old_make_engine_move = """    best_move_uci, raw_score_after = engine.get_bestmove(req.movetime)
    score_after = raw_score_after if board.turn == chess.WHITE else -raw_score_after
    
    engine_move_san = ""
    if best_move_uci and best_move_uci != "0000":
        engine_move = chess.Move.from_uci(best_move_uci)
        if engine_move in board.legal_moves:
            engine_move_san = board.san(engine_move)
            board.push(engine_move)
            
    if board.is_game_over():
        res = format_game_over(board, best_move_uci)
        res["score_after"] = score_after
        return res
        
    return {
        "engine_move": best_move_uci,
        "engine_move_san": engine_move_san,
        "fen": board.fen(),
        "status": "ongoing",
        "score_after": score_after
    }"""

new_make_engine_move = """    best_move_uci, raw_score_after, engine_pv = engine.get_bestmove(req.movetime)
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
        "engine_move_san": engine_move_san,
        "engine_pv": engine_pv,
        "fen": board.fen(),
        "status": "ongoing",
        "score_after": score_after
    }"""

orig = orig.replace(old_make_engine_move, new_make_engine_move)

old_compute = "def compute_position_facts(fen_before, fen_after, move_played_uci, engine_best_move_uci, score_before_cp, score_after_cp):"
new_compute = "def compute_position_facts(fen_before, fen_after, move_played_uci, engine_best_move_uci, score_before_cp, score_after_cp, analyzing_side='player', recent_history=None):\\n    if recent_history is None:\\n        recent_history = []\\n"
orig = orig.replace(old_compute, new_compute)

orig = orig.replace("""    facts["piece_is_hanging"] = is_piece_hanging(board_after, move.to_square)

    # Describe what the opponent can capture in plain English""", """    facts["piece_is_hanging"] = is_piece_hanging(board_after, move.to_square)
    facts["analyzing_side"] = analyzing_side
    facts["move_context"] = (
        "This is YOUR move — here is coaching on what you played." 
        if analyzing_side == "player" 
        else "This is the ENGINE's move — here is an explanation of what it did and why, so you can learn from it."
    )
    facts["recent_history"] = recent_history
    facts["recent_history_summary"] = build_history_summary(recent_history)

    # Describe what the opponent can capture in plain English""")

old_best_validate = """    # Validate best move is from same side as player
    board_check = chess.Board(fen_before)
    try:
        best_move = chess.Move.from_uci(engine_best_move_uci)
        best_piece_check = board_check.piece_at(best_move.from_square)
        if best_piece_check and best_piece_check.color != board_check.turn:
            import sys
            print(f"[BUG] engine_best_move {engine_best_move_uci} is from wrong side in FEN {fen_before}", file=sys.stderr)
            facts["engine_best_move_san"] = "unknown"
            facts["best_is_capture"] = False
            facts["best_piece_type"] = "unknown"
            facts["best_from"] = "unknown"
            facts["best_to"] = "unknown"
            facts["best_captures_piece"] = None
            facts["best_move_gives_check"] = False
        else:
            facts["engine_best_move_san"] = board_check.san(best_move)
            facts["best_is_capture"] = board_check.is_capture(best_move)
            best_piece = board_check.piece_at(best_move.from_square)
            facts["best_piece_type"] = chess.piece_name(best_piece.piece_type) if best_piece else "unknown"
            facts["best_from"] = chess.square_name(best_move.from_square)
            facts["best_to"] = chess.square_name(best_move.to_square)
            if facts["best_is_capture"]:
                best_captured = board_check.piece_at(best_move.to_square)
                facts["best_captures_piece"] = chess.piece_name(best_captured.piece_type) if best_captured else "unknown"
            else:
                facts["best_captures_piece"] = None
            facts["best_move_gives_check"] = board_check.gives_check(best_move)
    except Exception as e:
        import sys
        print(f"[BUG] Failed to validate best move: {e}", file=sys.stderr)
        facts["engine_best_move_san"] = "unknown"
        facts["best_is_capture"] = False
        facts["best_piece_type"] = "unknown"
        facts["best_from"] = "unknown"
        facts["best_to"] = "unknown"
        facts["best_captures_piece"] = None
        facts["best_move_gives_check"] = False"""

new_best_validate = """    try:
        board_for_best = chess.Board(fen_before)  # always use fen_before
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
        import sys
        print(f"[best move parse error] {e} — uci={engine_best_move_uci} fen={fen_before}", file=sys.stderr)
        facts["engine_best_move_san"] = engine_best_move_uci
        facts["best_piece_type"] = "unknown"
        facts["best_from"] = ""
        facts["best_to"] = ""
        facts["best_captures_piece"] = None
        facts["best_move_gives_check"] = False
        facts["best_is_capture"] = False"""

orig = orig.replace(old_best_validate, new_best_validate)

old_score_conv = """    side_multiplier = 1 if board_before.turn == chess.WHITE else -1
    delta_cp = (score_after_cp - score_before_cp) * side_multiplier
    facts["score_delta_cp"] = delta_cp
    facts["score_delta_pawns"] = round(delta_cp / 100, 2)"""

new_score_conv = """    # We need delta from the perspective of whoever just moved
    if board_before.turn == chess.WHITE:
        # White just moved — positive delta means white gained
        delta_cp = score_after_cp - score_before_cp
    else:
        # Black just moved — negative change in white score means black gained
        delta_cp = -(score_after_cp - score_before_cp)
    
    facts["score_delta_cp"] = delta_cp
    facts["score_delta_pawns"] = round(delta_cp / 100, 2)"""

orig = orig.replace(old_score_conv, new_score_conv)

helpers = """
def extract_pv_from_engine(pv_uci_string: str, fen: str, max_moves: int = 4) -> dict:
    import chess
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
    for entry in recent_history[-6:]:  # last 6 half-moves
        side = entry.get("side", "Unknown")
        move = entry.get("move_san", "?")
        classification = entry.get("classification", "")
        was_player = entry.get("was_player_move", False)
        who = "You" if was_player else "Engine"
        lines.append(f"{who} played {move} ({classification})")
    return " → ".join(lines)
"""

orig = orig.replace("class AnalyzeMoveRequest(BaseModel):", helpers + "\\nclass AnalyzeMoveRequest(BaseModel):")

old_analyze_req = """class AnalyzeMoveRequest(BaseModel):
    fen_before: str
    move_played: str
    fen_after: str
    engine_best_move: str
    engine_score_before: int
    engine_score_after: int
    move_history: list[str]"""

new_analyze_req = """class AnalyzeMoveRequest(BaseModel):
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
    game_patterns: dict = {}"""
orig = orig.replace(old_analyze_req, new_analyze_req)

old_analyze_call = """    # Compute base factual data prior to any prompt engineering
    facts = compute_position_facts(
        req.fen_before, 
        req.fen_after, 
        req.move_played, 
        req.engine_best_move, 
        req.engine_score_before, 
        req.engine_score_after
    )"""

new_analyze_call = """    # Compute base factual data prior to any prompt engineering
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
    facts["engine_pv"] = extract_pv_from_engine(req.engine_pv, req.fen_after, max_moves=4)"""
orig = orig.replace(old_analyze_call, new_analyze_call)

import re

# We will just replace the prompt entirely in analyze_move
p = re.compile(r'    user_prompt = f\"\"\"\{SYSTEM_PROMPT\}.*?Write coaching feedback using ONLY the facts above\.\"\"\"', re.DOTALL)
new_user_prompt = """    patterns = req.game_patterns
    blunders = patterns.get("blunders", 0)
    mistakes = patterns.get("mistakes", 0)
    hangingPieceCount = patterns.get("hangingPieceCount", 0)
    kingExposureCount = patterns.get("kingExposureCount", 0)
    consecutivePoorMoves = patterns.get("consecutivePoorMoves", 0)

    actual_system_prompt = SYSTEM_PROMPT.replace("{move_context}", facts.get("move_context", ""))

    user_prompt = f\"\"\"{actual_system_prompt}
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
\"\"\""""

orig = p.sub(new_user_prompt, orig)

with open("/Users/limitless/Documents/ChessEngine/server.py", "w") as f:
    f.write(orig)

