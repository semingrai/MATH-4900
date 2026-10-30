"""Task 3.1 -- a transposition table and iterative deepening written by hand on top of
last week's alpha-beta.

Run it:   python scripts/tt_search.py

Four searches of the same three positions at depth 4:

    1. alpha-beta alone
    2. + the transposition table            (search_tt)
    3. + iterative deepening                (depths 1..4 sharing one table)
    4. + the remembered best move first     (Sunfish's tp_move)

The move and the value must be identical on every row -- a table and a move order are
bookkeeping, not a different opinion.  The node counts must not be: that is the point.
Nothing here starts an engine, so every row runs with no engine installed.

The piece-square tables are Sunfish's own (sunfish.py, Thomas Dybdahl Ahle, GPLv3 --
see engines/v3-sunfish/sunfish/LICENSE.md); they are copied here so this file runs
without the clone.  The king's material value is dropped to 0 because python-chess
knows about checkmate, so the engine has no king to capture.
"""
import csv
import os
import sys

import chess
import chess.polyglot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Sunfish's evaluation, ported to python-chess ----------------------------------

SUNFISH_PIECE = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 0}

# Copied verbatim from sunfish.py (index 0 is a8).  64 values per piece.
SUNFISH_PST = {
    'P': (   0,   0,   0,   0,   0,   0,   0,   0,
            78,  83,  86,  73, 102,  82,  85,  90,
             7,  29,  21,  44,  40,  31,  44,   7,
           -17,  16,  -2,  15,  14,   0,  15, -13,
           -26,   3,  10,   9,   6,   1,   0, -23,
           -22,   9,   5, -11, -10,  -2,   3, -19,
           -31,   8,  -7, -37, -36, -14,   3, -31,
             0,   0,   0,   0,   0,   0,   0,   0),
    'N': ( -66, -53, -75, -75, -10, -55, -58, -70,
            -3,  -6, 100, -36,   4,  62,  -4, -14,
            10,  67,   1,  74,  73,  27,  62,  -2,
            24,  24,  45,  37,  33,  41,  25,  17,
            -1,   5,  31,  21,  22,  35,   2,   0,
           -18,  10,  13,  22,  18,  15,  11, -14,
           -23, -15,   2,   0,   2,   0, -23, -20,
           -74, -23, -26, -24, -19, -35, -22, -69),
    'B': ( -59, -78, -82, -76, -23,-107, -37, -50,
           -11,  20,  35, -42, -39,  31,   2, -22,
            -9,  39, -32,  41,  52, -10,  28, -14,
            25,  17,  20,  34,  26,  25,  15,  10,
            13,  10,  17,  23,  17,  16,   0,   7,
            14,  25,  24,  15,   8,  25,  20,  15,
            19,  20,  11,   6,   7,   6,  20,  16,
            -7,   2, -15, -12, -14, -15, -10, -10),
    'R': (  35,  29,  33,   4,  37,  33,  56,  50,
            55,  29,  56,  67,  55,  62,  34,  60,
            19,  35,  28,  33,  45,  27,  25,  15,
             0,   5,  16,  13,  18,  -4,  -9,  -6,
           -28, -35, -16, -21, -13, -29, -46, -30,
           -42, -28, -42, -25, -25, -35, -26, -46,
           -53, -38, -31, -26, -29, -43, -44, -53,
           -30, -24, -18,   5,  -2, -18, -31, -32),
    'Q': (   6,   1,  -8,-104,  69,  24,  88,  26,
            14,  32,  60, -10,  20,  76,  57,  24,
            -2,  43,  32,  60,  72,  63,  43,   2,
             1, -16,  22,  17,  25,  20, -13,  -6,
           -14, -15,  -2,  -5,  -1, -10, -20, -22,
           -30,  -6, -13, -11, -16, -11, -16, -27,
           -36, -18,   0, -19, -15, -15, -21, -38,
           -39, -30, -31, -13, -31, -36, -34, -42),
    'K': (   4,  54,  47, -99, -99,  60,  83, -62,
           -32,  10,  55,  56,  56,  55,  10,   3,
           -62,  12, -57,  44, -67,  28,  37, -31,
           -55,  50,  11,  -4, -19,  13,   0, -49,
           -55, -43, -52, -28, -51, -47,  -8, -50,
           -47, -42, -43, -79, -64, -32, -29, -32,
            -4,   3, -14, -50, -57, -18,  13,   4,
            17,  30,  -3, -14,   6,  -1,  40,  18),
}

EXACT, LOWER, UPPER = 0, 1, 2          # what a stored value is: the score, or a bound on it
MATE = 1_000_000


def make_pst_eval(scale=1.0, drop=()):
    """evaluate(board) -> centipawns for White.

    scale  multiplies the positional part, so position counts more (2.0) or less (0.5)
           against material.
    drop   piece types whose table is switched off: they keep their material value only.
    """
    tables = {}
    for symbol, rows in SUNFISH_PST.items():
        piece_type = chess.Piece.from_symbol(symbol).piece_type
        material = SUNFISH_PIECE[symbol]
        squares = [0] * 64
        for index, bonus in enumerate(rows):               # index 0 is a8: Sunfish reads rank 8 first
            square = chess.square(index % 8, 7 - index // 8)
            squares[square] = material + (0 if piece_type in drop else scale * bonus)
        tables[piece_type] = squares

    def evaluate(board):
        total = 0.0
        for square, piece in board.piece_map().items():
            value = tables[piece.piece_type][square if piece.color else chess.square_mirror(square)]
            total += value if piece.color == chess.WHITE else -value
        return total

    return evaluate


def eval_stm(board, evaluate):
    """The evaluation from the side to move's point of view -- what negamax wants."""
    score = evaluate(board)
    return score if board.turn == chess.WHITE else -score


# --- the search --------------------------------------------------------------------

def order_moves(board, tt_move=None):
    """One fixed order for every configuration: captures first, biggest victim first, then
    the quiet moves alphabetically.  Config 4 adds the remembered move in front of it."""
    victim = lambda m: -(SUNFISH_PIECE.get((board.piece_at(m.to_square) or chess.Piece(1, True)).symbol().upper(), 0)
                         if board.is_capture(m) else 0)
    moves = sorted(board.legal_moves, key=lambda m: (not board.is_capture(m), victim(m), m.uci()))
    if tt_move is not None and tt_move in moves:
        moves.remove(tt_move)
        moves.insert(0, tt_move)
    return moves


class Searcher:
    """Alpha-beta, with the table and the move memory as switches so one body serves all four rows.

    The table is keyed by python-chess's Zobrist hash and stores, per position:
    the depth it was searched to, the value, whether that value is exact or only a
    bound, and the best move found there.
    """

    def __init__(self, evaluate, use_tt=True, use_tt_move=True):
        self.evaluate = evaluate
        self.use_tt = use_tt
        self.use_tt_move = use_tt_move
        self.tt = {}                 # zobrist -> (depth, value, flag, move)
        self.nodes = 0
        self.hits = 0

    def negamax(self, board, depth, alpha, beta):
        self.nodes += 1
        alpha_in = alpha
        key = chess.polyglot.zobrist_hash(board)
        tt_move = None

        if self.use_tt:
            entry = self.tt.get(key)
            if entry is not None:
                stored_depth, value, flag, move = entry
                tt_move = move
                if stored_depth >= depth:                       # the depth test: deep enough to trust
                    if flag == EXACT:
                        self.hits += 1
                        return value, move
                    if flag == LOWER and value >= beta:         # a lower bound that already fails high
                        self.hits += 1
                        return value, move
                    if flag == UPPER and value <= alpha:        # an upper bound that already fails low
                        self.hits += 1
                        return value, move

        outcome = board.outcome(claim_draw=False)
        if outcome is not None:
            # A mate's score depends on the depth still to spend, never on the distance from
            # the root, so a stored entry stays true whatever search put it there.
            if outcome.winner is None:
                return 0.0, None
            return -(MATE + depth), None
        if depth == 0:
            return eval_stm(board, self.evaluate), None

        best, best_move = -float("inf"), None
        for move in order_moves(board, tt_move if self.use_tt_move else None):
            board.push(move)
            value = -self.negamax(board, depth - 1, -beta, -alpha)[0]
            board.pop()
            if value > best:                                    # strict: ties go to the move searched first
                best, best_move = value, move
            alpha = max(alpha, value)
            if alpha >= beta:
                break                                           # the cut-off

        if self.use_tt:
            flag = EXACT if alpha_in < best < beta else (LOWER if best >= beta else UPPER)
            old = self.tt.get(key)
            if old is None or old[0] <= depth:
                self.tt[key] = (depth, best, flag, best_move)
        return best, best_move


def search_ab(board, depth, evaluate):
    """Row 1: last week's alpha-beta, no table at all."""
    s = Searcher(evaluate, use_tt=False, use_tt_move=False)
    value, move = s.negamax(board.copy(), depth, -float("inf"), float("inf"))
    return value, move, s.nodes, s.hits


def search_tt(board, depth, evaluate, use_tt_move=False):
    """Row 2: alpha-beta plus the transposition table, one pass at full depth."""
    s = Searcher(evaluate, use_tt=True, use_tt_move=use_tt_move)
    value, move = s.negamax(board.copy(), depth, -float("inf"), float("inf"))
    return value, move, s.nodes, s.hits


def iterative_deepening(board, depth, evaluate, use_tt_move=False, verbose=False):
    """Rows 3 and 4: depth 1, 2, ... depth, every pass sharing one table.

    With use_tt_move the best move the table remembers is tried first on the next pass --
    this is Sunfish's tp_move, and it is the one thing I switch on and off in Task 3.2.
    """
    s = Searcher(evaluate, use_tt=True, use_tt_move=use_tt_move)
    value, move = 0.0, None
    for d in range(1, depth + 1):
        value, move = s.negamax(board.copy(), d, -float("inf"), float("inf"))
        if verbose:
            print("      depth %d: %-6s %+8.0f   %7s nodes so far" % (d, move, value, format(s.nodes, ",")))
    return value, move, s.nodes, s.hits


# --- the three positions, at depth 4 -----------------------------------------------

POSITIONS = {
    "start":       chess.Board(),
    "Italian":     chess.Board("r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQ1RK1 w - - 0 1"),
    "open middle": chess.Board("r2qkb1r/ppp2ppp/2n2n2/3pp3/4P1b1/3P1N2/PPP1BPPP/RNBQK2R w KQkq - 0 1"),
}

CONFIGS = [
    ("alpha-beta alone",        lambda b, d, e: search_ab(b, d, e)),
    ("+ table",                 lambda b, d, e: search_tt(b, d, e)),
    ("+ deepening",             lambda b, d, e: iterative_deepening(b, d, e)),
    ("+ best move first",       lambda b, d, e: iterative_deepening(b, d, e, use_tt_move=True)),
]


def node_table(depth=4, evaluate=None, positions=None, check=True):
    """The depth-4 node table.  Returns rows of
    (position, config, nodes, table hits, move, value)."""
    evaluate = evaluate or make_pst_eval()
    positions = positions or POSITIONS
    rows = []
    for name, board in positions.items():
        answers = []
        for label, run in CONFIGS:
            value, move, nodes, hits = run(board, depth, evaluate)
            san = board.san(move) if move is not None else "-"
            answers.append((san, round(value, 3)))
            rows.append([name, label, nodes, hits, san, round(value, 1)])
            print("%-12s %-18s %8s nodes  %6s hits   %-6s %+8.1f"
                  % (name, label, format(nodes, ","), format(hits, ","), san, value))
        if check:
            assert len(set(answers)) == 1, "the table changed the answer: %r" % (answers,)
        print()
    return rows


def main():
    depth = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    print("Sunfish's piece-square evaluation, depth %d, three positions.\n" % depth)
    rows = node_table(depth)
    out = os.path.join(ROOT, "results", "v3-tt-nodes.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["position", "config", "nodes", "table_hits", "move", "score"])
        w.writerows(rows)
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
