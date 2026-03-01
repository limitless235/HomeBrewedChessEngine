import re
import os

with open("/Users/limitless/Documents/ChessEngine/server.py", "r") as f:
    orig = f.read()

# I will systematically replace parts of orig using python string replacement.

# 1. replace SYSTEM PROMPT ... up to uci_to_san
p1 = re.compile(r'SYSTEM_PROMPT = """(.*?)"""\n\napp = FastAPI\(\)', re.DOTALL)

sys_prompt_repl = """SYSTEM_PROMPT = \"\"\"
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
\"\"\"

app = FastAPI()"""

orig = p1.sub(sys_prompt_repl, orig)

# 2. Add `import csv` and replace OPENING_BOOK with new code
p2 = re.compile(r'OPENING_BOOK = \{.*?\nreturn \{"opening_name": "Unknown Opening", "variation": "", "eco": "—", "ideas": ""\}\n', re.DOTALL)

opening_repl = """
ECO_POSITION_MAP = {}   # epd -> {eco, name, pgn, uci}
ECO_MOVE_MAP = {}       # tuple of uci moves -> {eco, name}

def load_opening_book():
    import csv, os, sys
    openings_dir = os.path.join(os.path.dirname(__file__), "openings")
    for filename in ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]:
        filepath = os.path.join(openings_dir, filename)
        if not os.path.exists(filepath):
            print(f"[OPENING] Missing {filepath} — run download commands", file=sys.stderr)
            continue
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\\t')
            for row in reader:
                epd = row.get("epd", "").strip()
                uci_moves = row.get("uci", "").strip()
                if epd:
                    ECO_POSITION_MAP[epd] = {
                        "eco": row.get("eco", ""),
                        "name": row.get("name", ""),
                        "pgn": row.get("pgn", ""),
                        "uci": uci_moves
                    }
                if uci_moves:
                    move_tuple = tuple(uci_moves.split())
                    ECO_MOVE_MAP[move_tuple] = {
                        "eco": row.get("eco", ""),
                        "name": row.get("name", ""),
                    }
    print(f"[OPENING] Loaded {len(ECO_POSITION_MAP)} positions, {len(ECO_MOVE_MAP)} move sequences", file=sys.stderr)

# Call at startup
load_opening_book()

def identify_opening(move_history: list, current_fen: str = None) -> dict:
    import sys
    
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
        # EPD is FEN without halfmove clock and fullmove number
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
    import chess
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
"""

orig = p2.sub(opening_repl, orig)

with open("/Users/limitless/Documents/ChessEngine/server.py", "w") as f:
    f.write(orig)

