from chess_engine.board import Board
from chess_engine.search import Searcher
import traceback

board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")

# We will patch is_in_check to print the move stack before failing
original_is_in_check = board.is_in_check
def debug_is_in_check(colour):
    try:
        return original_is_in_check(colour)
    except ValueError as e:
        print("ValueError caught! Board history:")
        for state in board._history:
            if state['move'] == 'null':
                print("NULL")
            else:
                (fr, ff), (tr, tf), promo = state['move']
                piece = state.get('moving_piece', '?') # wait, we didn't store moving piece
                print(f"Move: ({fr},{ff}) -> ({tr},{tf}) promo {promo}")
        print("\nBoard State:")
        print(board)
        raise e

board.is_in_check = debug_is_in_check

searcher = Searcher(board)
try:
    searcher.negamax(8, -9999999, 9999999, ply=0)
except Exception as e:
    pass
