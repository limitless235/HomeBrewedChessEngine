import pytest
import time
from chess_engine.board import Board
from chess_engine.search import Searcher

board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
searcher = Searcher(board)
best_move, nodes, pv = searcher.iterative_deepening(500)
print(f"Nodes: {nodes}, PV length: {len(pv)}")
