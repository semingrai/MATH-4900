"""Your First Engine Game -- play Stockfish from Python.

Run it:   python scripts/first_engine_game.py
          python scripts/first_engine_game.py --elo 1400 --black
          python scripts/first_engine_game.py --engine "C:/stockfish/stockfish.exe"

How it works (the whole idea of the course in 80 lines):
  1. python-chess keeps the board and knows the rules.
  2. Stockfish is a separate program; we talk to it over UCI (text in, text out).
  3. Your script is the conversation manager: show board -> take your move ->
     ask the engine for its move -> repeat -> save the game as PGN.
"""
import argparse, datetime, os, shutil, sys
import chess, chess.engine, chess.pgn

# ---------------------------------------------------------------- 1. find the engine
CANDIDATES = [
    os.environ.get("STOCKFISH_PATH"),          # set this if the engine lives somewhere odd
    shutil.which("stockfish"),                 # on PATH? (brew / apt / winget installs)
    "/usr/games/stockfish",                    # Debian/Ubuntu apt install
    "/usr/local/bin/stockfish", "/opt/homebrew/bin/stockfish",
    "./stockfish", "./stockfish.exe",          # dropped next to this script
]

def find_engine(explicit=None):
    for path in ([explicit] if explicit else []) + CANDIDATES:
        if path and os.path.isfile(path):
            return path
    sys.exit("Stockfish not found. Install it (see the Week 1 guide) or run with "
             "--engine <path to stockfish>.")

# ---------------------------------------------------------------- 2. read your move
def ask_move(board):
    """Return a legal move typed in SAN (e4, Nf3, O-O) or UCI (e2e4)."""
    while True:
        text = input("Your move (or 'quit'): ").strip()
        if text.lower() == "quit":
            return None
        try:
            return board.parse_san(text)       # SAN first ...
        except ValueError:
            try:
                move = chess.Move.from_uci(text)   # ... then UCI
                if move in board.legal_moves:
                    return move
            except ValueError:
                pass
        print("  Not a legal move here. Examples: e4  Nf3  O-O  or  e2e4")

# ---------------------------------------------------------------- 3. the game loop
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elo", type=int, default=1350, help="engine strength (Elo)")
    ap.add_argument("--black", action="store_true", help="play Black instead of White")
    ap.add_argument("--engine", help="path to the Stockfish executable")
    ap.add_argument("--think", type=float, default=0.5, help="engine seconds per move")
    args = ap.parse_args()

    engine = chess.engine.SimpleEngine.popen_uci(find_engine(args.engine))

    # Ask the engine what strength range it supports, then clamp our request to it.
    opt = engine.options["UCI_Elo"]
    elo = max(opt.min, min(opt.max, args.elo))
    engine.configure({"UCI_LimitStrength": True, "UCI_Elo": elo})
    print(f"Engine: {engine.id.get('name', 'unknown')}   strength: Elo {elo}")

    board = chess.Board()
    me = chess.BLACK if args.black else chess.WHITE

    while not board.is_game_over():
        print("\n" + str(board) + "\n")
        if board.turn == me:
            move = ask_move(board)
            if move is None:
                print("You resigned. Thanks for playing!")
                break
        else:
            result = engine.play(board, chess.engine.Limit(time=args.think))
            move = result.move
            print(f"Engine plays: {board.san(move)}")
        board.push(move)

    if board.is_game_over():
        print("\n" + str(board))
        print("\nGame over:", board.result(), "--", board.outcome().termination.name)

    # ------------------------------------------------------------ 4. save the game
    game = chess.pgn.Game.from_board(board)
    game.headers["Event"] = "Gambit Lab -- first engine game"
    game.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
    game.headers["White"] = "Student" if me == chess.WHITE else f"Stockfish {elo}"
    game.headers["Black"] = f"Stockfish {elo}" if me == chess.WHITE else "Student"
    with open("my_games.pgn", "a") as f:
        print(game, file=f, end="\n\n")
    print("Saved to my_games.pgn -- paste it into lichess.org/paste to review.")
    engine.quit()

if __name__ == "__main__":
    main()
