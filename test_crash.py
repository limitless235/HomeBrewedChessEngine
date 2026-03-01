import requests

payload = {
  "fen_before": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "move_played": "e2e4",
  "fen_after": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "engine_best_move": "e2e4",
  "engine_score_before": 35,
  "engine_score_after": 45,
  "move_history": ["e2e4"],
  "analyzing_side": "player",
  "recent_history": [],
  "engine_pv": "",
  "game_patterns": {}
}

resp = requests.post("http://127.0.0.1:8001/analyze_move", json=payload)
print("STATUS:", resp.status_code)
print("RESPONSE:", resp.text)
