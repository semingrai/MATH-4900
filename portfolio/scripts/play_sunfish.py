"""Week v3 harness: play Sunfish (White) through python-chess and save the game as a PGN.

Run it:   python scripts/play_sunfish.py --opponent you
          python scripts/play_sunfish.py --opponent stockfish --time 0.2
          python scripts/play_sunfish.py --opponent stockfish --time 2
          python scripts/play_sunfish.py --clock-experiment

Sunfish is always White.  Every move is printed with the depth, node count and score
Sunfish reports over UCI; the final board and the PGN path are printed at the end.
Stockfish is found through $STOCKFISH_PATH or the PATH.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the portfolio root
GAMES = os.path.join(ROOT, "engines", "v3-sunfish", "games")


def find_sunfish():
    """sunfish.py, wherever the clone landed."""
    for p in [os.environ.get("SUNFISH_PATH"),
              os.path.join(ROOT, "engines", "v3-sunfish", "sunfish", "sunfish.py"),
              os.path.join(ROOT, "sunfish", "sunfish.py")]:
        if p and os.path.isfile(p):
            return p
    raise SystemExit("sunfish.py not found -- git clone https://github.com/thomasahle/sunfish.git")


def find_stockfish():
    cands = [os.environ.get("STOCKFISH_PATH"), shutil.which("stockfish"),
             "/usr/games/stockfish", "/usr/local/bin/stockfish", "/opt/homebrew/bin/stockfish",
             "./stockfish", "./stockfish.exe"]
    cands += sorted(glob.glob(os.path.expanduser("~/Downloads/stockfish/stockfish*.exe")))
    for p in cands:
        if p and os.path.isfile(p):
            return p
    return None


def open_sunfish(sunfish=None):
    """Start sunfish.py as a UCI engine.  It must run from its own folder: it imports sunfish_ui."""
    sunfish = sunfish or find_sunfish()
    return chess.engine.SimpleEngine.popen_uci([sys.executable, os.path.basename(sunfish)],
                                               cwd=os.path.dirname(os.path.abspath(sunfish)))


def human_mover(scripted=()):
    """Black = you: typed at the keyboard, or replayed from --moves until the list runs out."""
    queue = list(scripted)

    def move(board):
        while True:
            text = queue.pop(0) if queue else input("  your move (%d... SAN like Nf6): " % board.fullmove_number).strip()
            for parse in (board.parse_san, board.parse_uci):
                try:
                    return parse(text)
                except ValueError:
                    pass
            print("  not legal here -- try again")
    return move


def greedy_bot(board):
    """The Setup-Week baseline: one ply, take the move that leaves the best material, random tie-break."""
    values = {chess.PAWN: 100, chess.KNIGHT: 280, chess.BISHOP: 320,
              chess.ROOK: 479, chess.QUEEN: 929, chess.KING: 0}

    def material(b):
        s = sum(values[p.piece_type] * (1 if p.color == chess.WHITE else -1) for p in b.piece_map().values())
        return s if b.turn == chess.WHITE else -s

    best, moves = None, []
    for m in board.legal_moves:
        board.push(m)
        s = 10 ** 6 if board.is_checkmate() else -material(board)
        board.pop()
        if best is None or s > best:
            best, moves = s, [m]
        elif s == best:
            moves.append(m)
    return random.choice(moves)


def play_sunfish(opponent="you", seconds=0.2, depth_limit=None, elo=1350, moves="",
                 sunfish=None, max_moves=150, out=None, quiet=False):
    """Sunfish (White) against 'you', 'stockfish', 'greedy' or 'random'.  Returns the finished board."""
    engine = open_sunfish(sunfish)
    print("engine.id =", engine.id)                                  # the proof it answered

    sf = None
    if opponent == "stockfish":
        path = find_stockfish()
        if not path:
            raise SystemExit("Stockfish not found -- set STOCKFISH_PATH or put it on your PATH")
        sf = chess.engine.SimpleEngine.popen_uci(path)
        opt = sf.options["UCI_Elo"]
        elo = max(opt.min, min(opt.max, elo))
        sf.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})
        opponent_move = lambda b: sf.play(b, chess.engine.Limit(time=0.1)).move
        opponent_name = "Stockfish (%d)" % elo
    elif opponent == "greedy":
        random.seed(1)
        opponent_move, opponent_name = greedy_bot, "greedy bot (one ply)"
    elif opponent == "random":
        random.seed(1)
        opponent_move, opponent_name = (lambda b: random.choice(list(b.legal_moves))), "random mover"
    else:
        opponent_move, opponent_name = human_mover(moves.split()), "me"

    limit = chess.engine.Limit(depth=depth_limit) if depth_limit else chess.engine.Limit(time=seconds)
    setting = "depth %d" % depth_limit if depth_limit else "%g s a move" % seconds
    print("White: Sunfish (%s)    Black: %s\n" % (setting, opponent_name))

    board, t_start, total_nodes, stopped = chess.Board(), time.time(), 0, None
    try:
        while not board.is_game_over(claim_draw=True) and board.fullmove_number <= max_moves:
            t0 = time.time()
            if board.turn == chess.WHITE:
                result = engine.play(board, limit, info=chess.engine.INFO_ALL)
                move, who = result.move, "SUN"
                depth, nodes = result.info.get("depth", "?"), result.info.get("nodes", 0)
                score = result.info.get("score")
                cp = score.white().score(mate_score=100000) if score is not None else None
                total_nodes += nodes or 0
                note = "  depth %2s  %7s nodes  score %+d" % (depth, format(nodes or 0, ","), cp) if cp is not None else ""
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
    print("\n%s\n" % board)
    print("%d plies in %.0fs.  Result %s  (%s)   Sunfish searched %s nodes in all."
          % (len(board.move_stack), time.time() - t_start,
             board.result(claim_draw=True) if over else "*",
             outcome.termination.name.lower() if outcome else "unfinished",
             format(total_nodes, ",")))

    game = chess.pgn.Game.from_board(board)
    game.headers.update({"Event": "Engine v3 -- Sunfish", "Site": "Toledo, OH",
                         "Date": datetime.date.today().strftime("%Y.%m.%d"), "Round": "-",
                         "White": "Sunfish (%s)" % setting, "Black": opponent_name,
                         "Result": board.result(claim_draw=True) if over else "*"})
    if stopped:
        game.headers["Termination"] = stopped
    os.makedirs(GAMES, exist_ok=True)
    path = out or os.path.join(GAMES, "v3-sunfish-vs-%s.pgn" % ("me" if opponent == "you" else opponent))
    with open(path, "w", encoding="utf-8") as f:
        print(game, file=f, end="\n\n")
    print("saved game ->", os.path.relpath(path, ROOT))
    return board


def clock_experiment(fen="r1bqk2r/pppp1ppp/2n5/8/1bBPn3/2N2N2/PP3PPP/R1BQK2R w KQkq - 0 8",
                     clocks=(0.2, 1.0, 2.0, 3.0), sunfish=None):
    """Task 2.3: the same position at several clocks -- what does the extra time buy?"""
    engine = open_sunfish(sunfish)
    position = chess.Board(fen)
    rows = []
    for seconds in clocks:
        t0 = time.time()
        r = engine.play(position, chess.engine.Limit(time=seconds), info=chess.engine.INFO_ALL)
        cp = r.info["score"].white().score(mate_score=100000)
        rows.append((seconds, position.san(r.move), r.info.get("depth", 0), r.info.get("nodes", 0), cp))
        print("%4s s: %-6s depth %2s  %7s nodes  score %+d   (%.1fs)"
              % (seconds, position.san(r.move), r.info.get("depth", "?"),
                 format(r.info.get("nodes", 0), ","), cp, time.time() - t0))
    engine.quit()
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Play Sunfish (White) through the harness.")
    ap.add_argument("--opponent", default="you", choices=["you", "stockfish", "greedy", "random"])
    ap.add_argument("--time", type=float, default=0.2, help="Sunfish's clock per move, in seconds")
    ap.add_argument("--depth", type=int, default=None, help="fixed depth instead of a clock")
    ap.add_argument("--elo", type=int, default=1350, help="Stockfish's rating limit")
    ap.add_argument("--moves", default="", help="Black's moves to replay, in SAN")
    ap.add_argument("--max-moves", type=int, default=150)
    ap.add_argument("--out", default=None, help="where to write the PGN")
    ap.add_argument("--clock-experiment", action="store_true", help="Task 2.3 instead of a game")
    a = ap.parse_args()
    if a.clock_experiment:
        clock_experiment()
    else:
        play_sunfish(opponent=a.opponent, seconds=a.time, depth_limit=a.depth, elo=a.elo,
                     moves=a.moves, max_moves=a.max_moves, out=a.out)
