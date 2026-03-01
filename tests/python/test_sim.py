import sys
import os

from chess_engine.board import Board
from chess_engine.movegen import MoveGenerator
from chess_engine.search import format_move

board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

moves = [
    "e2e4", "e7e5",
    "d1h5", "b8c6",
    "f1c4", "g7g6",
    "h5f3", "d8f6",
    "b1c3", "c6d4",
    "f3f6", "g8f6",
    "c4d3", "f8b4",
    "a2a3", "b4c5",
    "b2b4", "c5b6",
    "c1b2", "a7a5",
    "g1e2", "a5b4",
    "e2d4", "b4c3",
    "d2c3", "e5d4",
    "c3d4", "d7d5",
    "e4d5", "f6d5",
    "e1g1", "e8e7",
    "f1e1"
]

for move_str in moves:
    gen = MoveGenerator(board)
    legal_moves = gen.generate_legal()
    found = False
    for m in legal_moves:
        if format_move(m) == move_str:
            board.make_move(m)
            found = True
            break
    if not found:
        print(f"FAILED TO FIND {move_str}")
        sys.exit(1)

print("ALL MOVES WORKED!")
