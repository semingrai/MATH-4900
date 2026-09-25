"""CI green test: the environment can import python-chess, and the portfolio README is intact."""
import chess

def test_start_position():
    b = chess.Board()
    assert b.fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert b.legal_moves.count() == 20

def test_readme_has_engine_table():
    text = open("README.md", encoding="utf-8").read()
    assert "| v1 |" in text and "| v8 |" in text
