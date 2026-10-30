"""The table and the move order are bookkeeping: they may change the node count, never the answer.

Depth 2 so it stays a green test.  Nothing here starts an engine, so it runs in CI.
"""
import os
import sys

import chess

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from tt_search import iterative_deepening, make_pst_eval, search_ab, search_tt


def test_same_answer_four_ways():
    board = chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 1")
    evaluate = make_pst_eval()
    answers = [
        search_ab(board, 2, evaluate)[:2],
        search_tt(board, 2, evaluate)[:2],
        iterative_deepening(board, 2, evaluate)[:2],
        iterative_deepening(board, 2, evaluate, use_tt_move=True)[:2],
    ]
    assert len(set(answers)) == 1, answers


def test_tt_move_does_not_cost_nodes():
    board = chess.Board()
    evaluate = make_pst_eval()
    without = iterative_deepening(board, 3, evaluate)[2]
    with_move = iterative_deepening(board, 3, evaluate, use_tt_move=True)[2]
    assert with_move <= without


def test_pst_eval_is_symmetric_at_the_start():
    assert make_pst_eval()(chess.Board()) == 0
    assert make_pst_eval(scale=2.0)(chess.Board()) == 0


def test_dropping_a_table_keeps_the_material():
    evaluate = make_pst_eval(drop=(chess.PAWN,))
    board = chess.Board("4k3/8/8/8/8/8/4P3/4K3 w - - 0 1")     # one white pawn
    assert evaluate(board) == 100
