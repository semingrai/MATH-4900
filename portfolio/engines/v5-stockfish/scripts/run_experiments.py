"""Engine v4, Task 3: the network on -> off at the same depth, everything else identical.

Run it (from engines/v5-stockfish/):
          python scripts/run_experiments.py                       # depth 10 both sides
          python scripts/run_experiments.py --classical-depth 12  # give the classical side two more plies
          python scripts/run_experiments.py --time 0.05           # a clock instead of a depth

Two measurements, both written to results.csv:
  speed  -- six positions, searched with NNUE on and off: nodes, nodes per second, move, score.
  match  -- 20 games, NNUE against classical, colours alternating: ten openings, each played
            once with each colour, so a fixed-depth search does not just repeat one game.
"""
import argparse
import csv
import os
import sys
import time

import chess
import chess.engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_stockfish import HERE, open_stockfish                    # noqa: E402

POSITIONS = [
    ("start", chess.STARTING_FEN),
    ("Italian", "r1bqk2r/pppp1ppp/2n5/8/1bBPn3/2N2N2/PP3PPP/R1BQK2R w KQkq - 0 8"),
    ("open middle", "r2q1rk1/pp2bppp/2n1bn2/3p4/3P4/2NB1N2/PP3PPP/R1BQR1K1 w - - 4 11"),
    ("Sicilian", "r1bqkb1r/pp2pppp/2np1n2/8/3NP3/2N5/PPP2PPP/R1BQKB1R w KQkq - 2 6"),
    ("rook endgame", "8/5pk1/6p1/1R5p/r6P/6P1/5PK1/8 w - - 0 40"),
    ("king hunt", "r1b2rk1/pp1nqppp/2pbpn2/3p4/2PP4/2NBPN2/PPQ2PPP/R1B2RK1 w - - 0 9"),
]

OPENINGS = [                         # ten short book lines; each is played once with each colour
    "e4 e5 Nf3 Nc6 Bb5 a6",
    "e4 e5 Nf3 Nc6 Bc4 Bc5",
    "e4 c5 Nf3 d6 d4 cxd4",
    "e4 e6 d4 d5 Nc3 Bb4",
    "e4 c6 d4 d5 e5 Bf5",
    "d4 d5 c4 e6 Nc3 Nf6",
    "d4 Nf6 c4 g6 Nc3 Bg7",
    "d4 Nf6 c4 e6 Nc3 Bb4",
    "c4 e5 Nc3 Nf6 g3 d5",
    "Nf3 d5 g3 Nf6 Bg2 c6",
]


def limit_for(nnue, depth, classical_depth, seconds):
    if seconds:
        return chess.engine.Limit(time=seconds)
    return chess.engine.Limit(depth=depth if nnue else (classical_depth or depth))


def speed_table(depth=10, classical_depth=None, seconds=None):
    """Every position, NNUE on and off, from an empty hash each time."""
    rows = []
    engines = {True: open_stockfish(True), False: open_stockfish(False)}
    print("%-13s %-9s %5s %10s %10s %7s  %-6s %6s" % ("position", "eval", "depth", "nodes", "nodes/s", "ms", "move", "score"))
    for name, fen in POSITIONS:
        board = chess.Board(fen)
        for nnue in (True, False):
            eng = engines[nnue]
            eng.protocol.send_line("ucinewgame")
            t0 = time.time()
            r = eng.play(board, limit_for(nnue, depth, classical_depth, seconds), info=chess.engine.INFO_ALL)
            ms = (time.time() - t0) * 1000
            cp = r.info["score"].white().score(mate_score=100000)
            row = {"experiment": "speed", "label": name, "eval": "NNUE" if nnue else "classical",
                   "depth": r.info.get("depth"), "nodes": r.info.get("nodes"), "nps": r.info.get("nps"),
                   "time_ms": round(ms), "move": board.san(r.move), "score": cp}
            rows.append(row)
            print("%-13s %-9s %5s %10s %10s %7d  %-6s %+6d" % (name, row["eval"], row["depth"], format(row["nodes"], ","),
                                                               format(row["nps"], ","), ms, row["move"], cp))
    for e in engines.values():
        e.quit()
    return rows


def play_one(engines, nnue_white, opening, depth, classical_depth, seconds, max_plies=240):
    """One game from the opening line.  Returns the result from White's side and NNUE's points."""
    board = chess.Board()
    for san in opening.split():
        board.push_san(san)
    for e in engines.values():
        e.protocol.send_line("ucinewgame")
    while not board.is_game_over(claim_draw=True) and len(board.move_stack) < max_plies:
        nnue = (board.turn == chess.WHITE) == nnue_white
        board.push(engines[nnue].play(board, limit_for(nnue, depth, classical_depth, seconds)).move)
    result = board.result(claim_draw=True) if board.is_game_over(claim_draw=True) else "1/2-1/2"
    white_pts = {"1-0": 1.0, "0-1": 0.0}.get(result, 0.5)
    return result, white_pts if nnue_white else 1 - white_pts, len(board.move_stack)


def match(games=20, depth=10, classical_depth=None, seconds=None):
    """NNUE against classical, colours alternating, the openings each played with both colours."""
    engines = {True: open_stockfish(True), False: open_stockfish(False)}
    nnue_pts, decisive, rows = 0.0, 0, []
    for g in range(games):
        opening = OPENINGS[(g // 2) % len(OPENINGS)]
        nnue_white = g % 2 == 0
        result, pts, plies = play_one(engines, nnue_white, opening, depth, classical_depth, seconds)
        nnue_pts += pts
        decisive += result != "1/2-1/2"
        print("  game %2d  %-9s White  %-7s  %3d plies  NNUE %.1f   (%s)"
              % (g + 1, "NNUE" if nnue_white else "classical", result, plies, pts, opening))
    for e in engines.values():
        e.quit()
    print("\nNNUE %.1f -- classical %.1f   (%d of %d decisive)" % (nnue_pts, games - nnue_pts, decisive, games))
    return {"experiment": "match", "label": "NNUE vs classical, colours alternating, 10 openings x 2",
            "games": games, "nnue_points": nnue_pts, "classical_points": games - nnue_pts, "decisive": decisive}


def setting(depth, classical_depth, seconds):
    if seconds:
        return "%g s a move" % seconds
    return "depth %d" % depth + (" (classical %d)" % classical_depth if classical_depth else "")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="NNUE on vs off: the speed table and a 20-game match.")
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--classical-depth", type=int, default=None, help="give the classical side a different depth")
    ap.add_argument("--time", type=float, default=None, help="seconds a move instead of a depth")
    ap.add_argument("--games", type=int, default=20)
    ap.add_argument("--out", default=os.path.join(HERE, "results.csv"))
    a = ap.parse_args()

    label = setting(a.depth, a.classical_depth, a.time)
    print("== speed table, %s ==" % label)
    rows = speed_table(a.depth, a.classical_depth, a.time)
    print("\n== %d-game match, %s ==" % (a.games, label))
    rows.append(match(a.games, a.depth, a.classical_depth, a.time))
    for r in rows:
        r["setting"] = label

    fields = ["experiment", "setting", "label", "eval", "depth", "nodes", "nps", "time_ms", "move", "score",
              "games", "nnue_points", "classical_points", "decisive"]
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("\nwrote", os.path.relpath(a.out, HERE))
