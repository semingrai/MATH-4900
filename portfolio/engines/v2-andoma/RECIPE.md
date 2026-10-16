# v2-andoma — my recipe

**Source:** <https://github.com/healeycodes/andoma>   **License:** MIT

**Andoma is a small Python engine built on python-chess: minimax (negamax) search with alpha-beta pruning, captures-first move ordering, and an evaluation from piece values plus piece-square tables. It speaks UCI through `main.py`.**

## What I did to get it running (exact commands, in order)
```
%pip install chess -q                                   # setup cell: python-chess (already had 1.11.2)
git clone https://github.com/healeycodes/andoma.git     # download the engine (did NOT pip install its requirements.txt)
# started Andoma as a UCI engine from inside its folder:
#   chess.engine.SimpleEngine.popen_uci([sys.executable, "main.py", "--depth", "3"], cwd="andoma")
```

## What broke and how I fixed it
- Stockfish was "NOT FOUND" in the setup cell, so I set `STOCKFISH_PATH` to my Windows binary (as in v1).
- On Windows, Jupyter needs `asyncio.WindowsProactorEventLoopPolicy()` before python-chess can start engine subprocesses, so I added it to the setup cell (as in v1).
- I skipped `pip install -r requirements.txt` because it pins python-chess 1.6.1 and would downgrade my install.

## How I ran a game through the harness
- I ran Andoma at `--depth 2` and at `--depth 3`, one game each against me and against Stockfish. It ignores the clock, so `Limit(time=1)` only satisfies python-chess. Andoma played White in every game.
- vs me: I played Black, entering moves by hand.
  - depth 2: I won 0-1 by mate on move 27 (27...Qxf2#). Saved to `games/v2-d2-vs-me.pgn`.
  - depth 3: Andoma won 1-0 by mate on move 41 (41. Rc8#). Saved to `games/v2-d3-vs-me.pgn`.
- vs Stockfish: Stockfish at Elo 1350 with 0.1 s per move, the same as in v1.
  - depth 2: Stockfish won 0-1 by mate on move 68 (68...Rc6#). Saved to `games/v2-d2-vs-stockfish.pgn`.
  - depth 3: Stockfish won 0-1 by mate on move 32 (32...Qxc2#). Saved to `games/v2-d3-vs-stockfish.pgn`.

## My one change (Week B)
**Change:** search depth 2 → 3 in `ab_bot`. Everything else stayed the same: material-only eval, alpha-beta with captures first, 6 games, max_plies=80, seed=1, colours alternating.

**Why this one:** this week is about looking ahead, so I wanted to test whether one more ply actually wins games.

## Results
See `results.csv` in this folder.
```
position,depth,nodes_without_pruning,nodes_with_pruning,nodes_with_pruning_and_ordering,ratio_or_points
start,3,9323,581,581,16.0
Italian,3,46477,3645,2338,19.9
open middle,3,42942,1633,1953,22.0
match depth3 vs depth2 (6 games),,,,,3.5
```
**Nodes:** at depth 3, alpha-beta with ordering visited 16–22× fewer nodes than plain negamax and gave the same answer. Ordering helped in the Italian (3,645 → 2,338) but not at the start, where there are no captures, or in the open middlegame (1,633 → 1,953).

**Match:** depth 3 scored 3.5/6 against depth 2 (3 decisive games). Six games are too few to show that depth 3 is stronger.
