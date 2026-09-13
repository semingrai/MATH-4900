"""Week 1 green test: prove your Python environment and python-chess work.

Run it:   python scripts/print_board.py
Expect:   the starting position drawn in text, the FEN string, and 20 legal moves.
"""
import chess

board = chess.Board()                 # a brand-new game, White to move

print(board)                          # 8x8 text board (uppercase = White)
print()
print("FEN:", board.fen())            # the one-line description of a position
print("Legal moves for White:", board.legal_moves.count())
print("python-chess version:", chess.__version__)
print()
print("OK -- your environment is ready for the Gambit Lab.")
