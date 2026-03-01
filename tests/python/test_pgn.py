import io
import chess.pgn

pgn_text = "1. Nh3 d5 2. g3 e5 3. f4 Bxh3 4. Bxh3 exf4 5. O-O fxg3 6. hxg3"
pgn = io.StringIO(pgn_text)
game = chess.pgn.read_game(pgn)

uci_moves = []
board = game.board()
for move in game.mainline_moves():
    uci_moves.append(move.uci())
    board.push(move)

print(uci_moves)
epd = ' '.join(board.fen().split()[:4])
print(epd)
