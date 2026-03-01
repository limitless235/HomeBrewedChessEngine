import asyncio
import urllib.parse
from server import compute_position_facts, identify_opening, moves_to_san_list, SYSTEM_PROMPT
import chess

fen_before = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
move_played = "e2e4"
fen_after = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
engine_best_move = "e2e4"
engine_score_before = 20
engine_score_after = 30
move_history = ["e2e4"]

facts = compute_position_facts(
    fen_before, 
    fen_after, 
    move_played, 
    engine_best_move, 
    engine_score_before, 
    engine_score_after
)
print("Facts computed successfully!")

delta = facts["score_delta_cp"]
c = "Mistake"
if move_played == engine_best_move: c = "Best Move"
elif delta >= -10: c = "Excellent"
elif delta >= -30: c = "Good"
elif delta >= -80: c = "Inaccuracy"
elif delta >= -200: c = "Mistake"
else: c = "Blunder"

if engine_score_before > 200 and -engine_score_after < -200: c = "Game-Losing Blunder"
if facts["move_results_in_checkmate"]: c = "Checkmate Blunder"

facts["classification"] = c

opening_data = identify_opening(move_history, fen_after)
facts["opening_name"] = opening_data["opening_name"] + (f", {opening_data['variation']}" if opening_data["variation"] else "")
facts["eco_code"] = opening_data["eco"]
facts["opening_ideas"] = opening_data["ideas"]

u_name = urllib.parse.quote_plus(facts["opening_name"])
u_search = urllib.parse.quote(facts["opening_name"])

san_list = moves_to_san_list("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", move_history)
moves_str = " ".join(san_list)
analysis_url = f"https://lichess.org/analysis#{urllib.parse.quote(moves_str)}"

facts["move_number"] = len(move_history) // 2 + 1
mc = len(move_history)
facts["game_phase"] = "Opening"
if mc > 10: facts["game_phase"] = "Middlegame"
mat_score = sum(len(chess.Board(fen_after).pieces(pt, color)) * v for pt, v in {1:1, 2:3, 3:3, 4:5, 5:9}.items() for color in [chess.WHITE, chess.BLACK])
if mc > 25 or mat_score < 30: facts["game_phase"] = "Endgame"

print("Trying user prompt...")
user_prompt = f"""{SYSTEM_PROMPT}

Use ONLY these verified facts. Do not reason beyond them.

YOU ARE COACHING: {facts['player_side']}
OPPONENT IS: {facts['opponent_side']}
THE PLAYER WHO JUST MOVED IS: {facts['player_side']}

MOVE FACTS:
Move played: {facts['move_played_san']} (from {facts['from_square']} to {facts['to_square']})
Piece that moved: {facts['piece_color']} {facts['piece_type']}
Was it a capture: {facts['move_is_capture']}
Piece captured: {facts['captured_piece']}
Was it a check: {facts['move_is_check']}
Was it castling: {facts['move_is_castling']}

ENGINE ASSESSMENT:
Classification: {facts['classification']}
Score before: {facts['score_before_display']}
Score after: {facts['score_after_display']}
Score change: {facts['score_delta_pawns']:+.2f} pawns
Engine preferred move: {facts['engine_best_move_san']}
Best move is for: {facts['player_side']} (same side as player — this is what {facts['player_side']} should have played instead)
Engine preferred piece: {facts['best_piece_type']} from {facts['best_from']} to {facts['best_to']}
Engine preferred move captures: {facts['best_captures_piece'] if facts['best_captures_piece'] else "nothing"}
Engine preferred move gives check: {facts['best_move_gives_check']}

TACTICAL FACTS:
Hanging piece situation: {facts['hanging_piece_description']}
Creates fork: {facts['creates_fork']['is_fork']}
Forked pieces: {facts['creates_fork']['forked_pieces']}
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

OPENING FACTS:
Opening name: {facts['opening_name']}
ECO code: {facts['eco_code'] if facts['eco_code'] and facts['eco_code'] != "—" else "not classified yet"}
Opening ideas: {facts['opening_ideas'] if facts['opening_ideas'] else "This opening has not been deeply studied yet. Focus on general principles: control the center, develop pieces, castle early."}

GAME CONTEXT:
Phase: {facts['game_phase']}
Move number: {facts['move_number']}
Player color: {facts['player_color']}

Write coaching feedback using ONLY the facts above."""

print("User prompt generated successfully!")
