"""Engine v4 harness: play Stockfish (White, NNUE on or off) through python-chess, save the PGN.

Run it (from engines/v5-stockfish/):
          python scripts/play_stockfish.py --opponent you --nnue on
          python scripts/play_stockfish.py --opponent you --nnue off
          python scripts/play_stockfish.py --opponent you --nnue on --moves-from games/v4-stockfish-nnue-vs-me.pgn

Stockfish is always White and searches to a fixed depth (10 by default), so the network
and the classical evaluation build trees of the same depth.  Every Stockfish move is printed
with the depth, nodes, nodes per second and score it reports; the final board and the PGN
path are printed at the end.

It needs Stockfish 12-16: Stockfish 16.1 removed the classical evaluation, and the
`Use NNUE` option with it.  Found through $STOCKFISH_PATH, ./stockfish16/, or the PATH.
"""
import argparse
import asyncio
import datetime
import glob
import os
import random
import shutil
import sys
import time
import warnings

import chess
import chess.engine
import chess.pgn

if sys.platform == "win32":                       # Jupyter installs a Selector loop; python-chess needs Proactor
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # engines/v5-stockfish
GAMES = os.path.join(HERE, "games")


def find_stockfish():
    """A Stockfish that still has `Use NNUE` -- 16 first, then whatever else is around."""
    cands = [os.environ.get("STOCKFISH_PATH")]
    cands += sorted(glob.glob(os.path.join(HERE, "stockfish16", "stockfish", "stockfish*.exe")))
    cands += sorted(glob.glob(os.path.join(HERE, "stockfish16", "stockfish", "stockfish*")))
    cands += [shutil.which("stockfish"), "/usr/games/stockfish", "/usr/local/bin/stockfish",
              "/opt/homebrew/bin/stockfish"]
    for p in cands:
        if p and os.path.isfile(p):
            return os.path.abspath(p)
    raise SystemExit("Stockfish not found -- download sf_16 into stockfish16/ or set STOCKFISH_PATH")


def open_stockfish(nnue=True, path=None):
    """Start Stockfish with the network on or off.  One thread, so node counts repeat run to run."""
    eng = chess.engine.SimpleEngine.popen_uci(path or find_stockfish())
    if "Use NNUE" not in eng.options:
        name = eng.id.get("name", "this Stockfish")
        eng.quit()
        raise SystemExit(f"{name} has no 'Use NNUE' option -- use Stockfish 12-16 "
                         "(github.com/official-stockfish/Stockfish/releases/tag/sf_16)")
    eng.configure({"Threads": 1, "Hash": 64, "Use NNUE": nnue})
    return eng


def moves_from_pgn(path):
    """Black's moves from a saved game, in SAN -- to replay a game against me without retyping it."""
    with open(path, encoding="utf-8") as f:
        game = chess.pgn.read_game(f)
    board, black = game.board(), []
    for move in game.mainline_moves():
        if board.turn == chess.BLACK:
            black.append(board.san(move))
        board.push(move)
    return black


def human_mover(scripted=()):
    """Black = you: typed at the keyboard, or replayed from --moves until the list runs out."""
    queue = list(scripted)

    def move(board):
        while True:
            if queue:
                text = queue.pop(0)
            else:
                try:
                    text = input("  your move (%d... SAN like Nf6, or 'resign'): " % board.fullmove_number).strip()
                except EOFError:                       # no keyboard: stop here, keep the PGN
                    raise KeyboardInterrupt
            if text.lower() in ("resign", "quit"):
                raise KeyboardInterrupt
            for parse in (board.parse_san, board.parse_uci):
                try:
                    return parse(text)
                except ValueError:
                    pass
            print("  %r is not legal here -- try again" % text)
    return move


def report(info):
    """What one search said: depth, nodes, nodes per second, and the score from White's side."""
    score = info.get("score")
    nodes, nps = info.get("nodes", 0) or 0, info.get("nps", 0) or 0
    text = "depth %2s  %9s nodes  %9s n/s" % (info.get("depth", "?"), format(nodes, ","), format(nps, ","))
    if score is not None:
        w = score.white()
        text += "  mate %+d" % w.mate() if w.is_mate() else "  score %+d" % w.score()
    return text, nodes, nps


def play_stockfish(opponent="you", nnue=True, depth=10, seconds=None, elo=1350, moves=(),
                   max_moves=150, out=None, quiet=False):
    """Stockfish (White) against 'you', 'stockfish' (rating-limited) or 'random'.

    Returns (board, searches): searches is one (fen, move, nodes, nps) per Stockfish move."""
    engine = open_stockfish(nnue)
    print("engine.id =", engine.id, "| Use NNUE =", nnue)

    sf = None
    if opponent == "stockfish":
        sf = chess.engine.SimpleEngine.popen_uci(find_stockfish())
        opt = sf.options["UCI_Elo"]
        elo = max(opt.min, min(opt.max, elo))
        sf.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})
        opponent_move = lambda b: sf.play(b, chess.engine.Limit(time=0.1)).move
        opponent_name = "Stockfish (%d)" % elo
    elif opponent == "random":
        random.seed(1)
        opponent_move, opponent_name = (lambda b: random.choice(list(b.legal_moves))), "random mover"
    else:
        opponent_move, opponent_name = human_mover(moves), "me"

    limit = chess.engine.Limit(time=seconds) if seconds else chess.engine.Limit(depth=depth)
    setting = "%s, %s" % ("NNUE" if nnue else "classical", "%g s a move" % seconds if seconds else "depth %d" % depth)
    white_name = "Stockfish 16 (%s)" % setting
    print("White: %s    Black: %s\n" % (white_name, opponent_name))

    board, t_start, searches, stopped = chess.Board(), time.time(), [], None
    try:
        while not board.is_game_over(claim_draw=True) and board.fullmove_number <= max_moves:
            t0 = time.time()
            if board.turn == chess.WHITE:
                fen = board.fen()
                result = engine.play(board, limit, info=chess.engine.INFO_ALL)
                move, who = result.move, "SF "
                note, nodes, nps = report(result.info)
                searches.append((fen, move, nodes, nps))
                note = "  " + note
            else:
                move, who, note = opponent_move(board), "opp", ""
            num = "%d." % board.fullmove_number if board.turn == chess.WHITE else "   "
            san = board.san(move)
            board.push(move)
            if not quiet:
                print("  %4s %s %-8s (%4.1fs)%s" % (num, who, san, time.time() - t0, note))
    except KeyboardInterrupt:
        stopped = "stopped by hand"
    finally:
        engine.quit()
        if sf:
            sf.quit()

    over = board.is_game_over(claim_draw=True)
    outcome = board.outcome(claim_draw=True)
    total = sum(s[2] for s in searches)
    print("\n%s\n" % board)
    print("%d plies in %.0fs.  Result %s  (%s)   Stockfish searched %s nodes in %d moves."
          % (len(board.move_stack), time.time() - t_start,
             board.result(claim_draw=True) if over else "*",
             outcome.termination.name.lower() if outcome else stopped or "unfinished",
             format(total, ","), len(searches)))

    game = chess.pgn.Game.from_board(board)
    game.headers.update({"Event": "Engine v4 -- Stockfish (NNUE)", "Site": "Toledo, OH",
                         "Date": datetime.date.today().strftime("%Y.%m.%d"), "Round": "-",
                         "White": white_name, "Black": opponent_name,
                         "Result": board.result(claim_draw=True) if over else "*"})
    if stopped:
        game.headers["Termination"] = stopped
    os.makedirs(GAMES, exist_ok=True)
    who = "me" if opponent == "you" else opponent
    path = out or os.path.join(GAMES, "v4-stockfish-%s-vs-%s.pgn" % ("nnue" if nnue else "classical", who))
    with open(path, "w", encoding="utf-8") as f:
        print(game, file=f, end="\n\n")
    print("saved game ->", os.path.relpath(path, HERE))
    return board, searches


def summarize(searches):
    """Nodes per move and nodes per second over one game's Stockfish searches."""
    n = max(1, len(searches))
    return sum(s[2] for s in searches) / n, sum(s[3] for s in searches) / n


def same_move(searches, nnue, depth=10):
    """Re-search every position Stockfish faced with the *other* evaluation: how often is the move the same?"""
    engine = open_stockfish(not nnue)
    same = 0
    for fen, move, _, _ in searches:
        engine.protocol.send_line("ucinewgame")
        if engine.play(chess.Board(fen), chess.engine.Limit(depth=depth)).move == move:
            same += 1
    engine.quit()
    return same, len(searches)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Play Stockfish (White, NNUE on or off) through the harness.")
    ap.add_argument("--opponent", default="you", choices=["you", "stockfish", "random"])
    ap.add_argument("--nnue", default="on", choices=["on", "off"], help="White's evaluation")
    ap.add_argument("--depth", type=int, default=10, help="Stockfish's fixed depth")
    ap.add_argument("--time", type=float, default=None, help="seconds a move instead of a depth")
    ap.add_argument("--elo", type=int, default=1350, help="rating limit for --opponent stockfish")
    ap.add_argument("--moves", default="", help="Black's moves to replay, in SAN")
    ap.add_argument("--moves-from", default=None, help="replay Black's moves from a saved PGN")
    ap.add_argument("--max-moves", type=int, default=150)
    ap.add_argument("--out", default=None, help="where to write the PGN")
    a = ap.parse_args()
    black = moves_from_pgn(a.moves_from) if a.moves_from else a.moves.split()
    board, searches = play_stockfish(opponent=a.opponent, nnue=a.nnue == "on", depth=a.depth, seconds=a.time,
                                     elo=a.elo, moves=black, max_moves=a.max_moves, out=a.out)
    per_move, nps = summarize(searches)
    print("nodes per move %s   nodes per second %s" % (format(round(per_move), ","), format(round(nps), ",")))
