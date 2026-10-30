"""Task 3.3 -- measure the one change, twice.

Run it:   python scripts/run_experiments.py

1. The depth-4 node table before and after the change.  The change is Sunfish's `tp_move`:
   remember the best move in the transposition table and try it first on the next pass of
   iterative deepening.  Everything else is identical -- same evaluation, same three
   positions, same depth, same base move order, same table.

2. Thirty games of the port: Greedy with Sunfish's piece-square tables against plain
   Greedy, colours alternating.  Both bots look one ply ahead and take the move that
   leaves the best material; the only difference is that the ported bot breaks a tie in
   material with the piece-square table instead of at random.

Both land in engines/v3-sunfish/results.csv.  No engine is started, so this runs anywhere.
"""
import argparse
import csv
import os
import random
import sys

import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tt_search import POSITIONS, SUNFISH_PIECE, iterative_deepening, make_pst_eval

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "engines", "v3-sunfish", "results.csv")

MATERIAL = {chess.PAWN: 100, chess.KNIGHT: 280, chess.BISHOP: 320,
            chess.ROOK: 479, chess.QUEEN: 929, chess.KING: 0}


# --- part 1: the node table, tp_move off then on ------------------------------------

def node_table_before_after(depth=4, evaluate=None):
    evaluate = evaluate or make_pst_eval()
    rows = []
    for name, board in POSITIONS.items():
        answers = []
        for label, use_tt_move in (("TT + deepening (before)", False), ("+ tp_move first (after)", True)):
            value, move, nodes, hits = iterative_deepening(board, depth, evaluate, use_tt_move=use_tt_move)
            san = board.san(move)
            answers.append((san, round(value, 3)))
            rows.append(["tt_depth%d" % depth, "%s -- %s" % (name, label), depth, nodes, hits, san,
                         round(value, 1), "", "", ""])
            print("%-12s %-26s %8s nodes  %6s hits   %-6s %+8.1f"
                  % (name, label, format(nodes, ","), format(hits, ","), san, value))
        assert len(set(answers)) == 1, "the change moved the answer: %r" % (answers,)
        before, after = rows[-2][3], rows[-1][3]
        print("%-12s %-26s %8.1f%% of the nodes left, so %.1f%% saved\n"
              % ("", "after / before", 100.0 * after / before, 100.0 * (1 - after / before)))
    return rows


# --- part 2: the port, thirty games -------------------------------------------------

def material_score(board):
    """Material from the side to move's point of view."""
    total = sum(MATERIAL[p.piece_type] * (1 if p.color == chess.WHITE else -1)
                for p in board.piece_map().values())
    return total if board.turn == chess.WHITE else -total


def greedy(board, rng, evaluate=None):
    """One ply: the move that leaves the best material.  Ties go to the piece-square table
    when one is given (the port), and to the coin otherwise (plain Greedy)."""
    best, pool = None, []
    for move in board.legal_moves:
        board.push(move)
        mate = board.is_checkmate()
        key = 10 ** 6 if mate else -material_score(board)
        tie = 0.0 if (mate or evaluate is None) else (evaluate(board) * (1 if board.turn == chess.BLACK else -1))
        board.pop()
        score = (key, tie)
        if best is None or score > best:
            best, pool = score, [move]
        elif score == best:
            pool.append(move)
    return rng.choice(pool)


def match(games=30, max_plies=120, seed=1, evaluate=None):
    """The ported bot against plain Greedy, colours alternating.

    Returns (points, decisive, unfinished).  A game still going at max_plies is scored
    half a point, and counted so the write-up can say how many of those there were."""
    evaluate = evaluate or make_pst_eval()
    rng = random.Random(seed)
    points, decisive, unfinished = 0.0, 0, 0
    for g in range(games):
        port_is_white = (g % 2 == 0)
        board = chess.Board()
        while not board.is_game_over(claim_draw=True) and len(board.move_stack) < max_plies:
            port_to_move = (board.turn == chess.WHITE) == port_is_white
            board.push(greedy(board, rng, evaluate if port_to_move else None))
        result = board.result(claim_draw=True)
        if result == "1-0":
            got = 1.0 if port_is_white else 0.0
        elif result == "0-1":
            got = 0.0 if port_is_white else 1.0
        else:
            got = 0.5
        if result in ("1-0", "0-1"):
            decisive += 1
        if result == "*":
            unfinished += 1
        points += got
        print("  game %2d  port as %-5s  %-7s  port scores %.1f   (running %.1f/%d)"
              % (g + 1, "White" if port_is_white else "Black", result, got, points, g + 1))
    return points, decisive, unfinished


def write_results(rows, games, points, decisive, unfinished, max_plies=120, path=RESULTS):
    """One CSV with both measurements: the node table, then the match."""
    rows = list(rows)
    rows.append(["port_match", "pst-greedy vs plain greedy, colours alternating (%d unfinished at %d plies)"
                 % (unfinished, max_plies), "", "", "", "", "", games, points, decisive])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["experiment", "label", "depth", "nodes", "table_hits", "move", "score",
                    "games", "points_for_change", "decisive"])
        w.writerows(rows)
    print("wrote", os.path.relpath(path, ROOT))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=30)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--max-plies", type=int, default=120)
    a = ap.parse_args()

    print("1. Depth-%d node table, tp_move off -> on\n" % a.depth)
    rows = node_table_before_after(a.depth)

    print("2. The port: Greedy + Sunfish's piece-square tables vs plain Greedy, %d games\n" % a.games)
    points, decisive, unfinished = match(a.games, a.max_plies)
    print("\n  port scored %.1f / %d  (%d decisive, %d still going at %d plies and scored a draw)"
          % (points, a.games, decisive, unfinished, a.max_plies))
    print()
    write_results(rows, a.games, points, decisive, unfinished, a.max_plies)


if __name__ == "__main__":
    main()
