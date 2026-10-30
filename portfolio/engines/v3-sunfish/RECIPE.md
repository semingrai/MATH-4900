# v3-sunfish — my recipe

**Source:** <https://github.com/thomasahle/sunfish>   **License:** GNU GPL v3 (`sunfish/LICENSE.md`) — I may run it, modify it and redistribute it, as long as what I redistribute stays GPL v3 and says what I changed. Version cloned: `sunfish 2026`, on 2026-10-30.

**Sunfish is a whole chess engine in one 662-line Python file: a 120-character string for the board, piece-square tables for the entire evaluation, and a search that is given a clock rather than a depth. Its two ideas are the transposition table — a dictionary of positions it has already searched — and iterative deepening, searching to depth 1, then 2, then 3, so there is always an answer ready when the clock runs out.**

**What the table stores, and when an entry may be reused.** `tp_score` stores, for a position *and the depth it was searched to*, a pair of numbers `Entry(lower, upper)` that the true score lies between; `tp_move` stores, for the position alone, the best move found there. An entry may be reused only if it was searched at least as deeply as the search now asking — Sunfish does that **depth test by putting the depth in the key** (`self.tp_score[pos, depth]`, line 399), so a depth-3 entry is simply never read by a depth-4 probe, where most engines store one entry per position and compare `stored_depth >= depth` instead. The difference between an exact value and a bound is what you are allowed to conclude from it: an **exact** value is the score, usable as the answer; a **bound** only rules out one side — a lower bound ends the search when it already reaches the window (`entry.lower >= gamma`, line 400) and an upper bound ends it when it already falls short (`entry.upper < gamma`, line 401), and if neither test fires, the entry is still useful as a move hint but the position has to be searched again. `tp_move` needs no depth test at all, because a remembered move only changes the *order* moves are tried in, never the value of the sub-tree.

## What I did to get it running (exact commands, in order)
```
python -m pip install "chess>=1.11"                               # already had 1.11.2
git clone https://github.com/thomasahle/sunfish.git               # cloned into the portfolio root
mv sunfish engines/v3-sunfish/sunfish                             # then moved in, to match v1 and v2
export STOCKFISH_PATH=~/Downloads/stockfish/stockfish-windows-x86-64-universal.exe
python scripts/print_board.py                                     # green test still passes
python scripts/play_sunfish.py --opponent stockfish --time 0.2 \
    --out engines/v3-sunfish/games/v3-sunfish-vs-stockfish-0.2s.pgn
python scripts/play_sunfish.py --opponent stockfish --time 2 \
    --out engines/v3-sunfish/games/v3-sunfish-vs-stockfish-2s.pgn
python scripts/play_sunfish.py --clock-experiment                  # Task 2.3
python scripts/tt_search.py                                        # Task 3.1
python scripts/run_experiments.py                                  # Task 3.2 and 3.3
```
I did **not** run `pip install -e .` or touch `pyproject.toml`: `sunfish.py` imports nothing but the standard library, so the clone needs no install at all.

The clone itself is **not committed** — it is 18 MB of somebody else's GPL v3 code and it carries its own `.git`, so it is in `.gitignore`. Get it back with the `git clone` line above. Everything of mine runs without it except the Task 1 cell in the notebook, which prints lines straight out of `sunfish.py`; `scripts/tt_search.py` carries its own copy of the piece-square tables for that reason.

## What broke and how I fixed it
- **`sunfish.py` would not answer UCI when I started it from the portfolio root.** Its `main()` imports `sunfish_ui.uci`, which only resolves when Python's working directory is the clone. Fixed by launching it with `cwd=` set to the folder that holds `sunfish.py` (`open_sunfish()` in `scripts/play_sunfish.py`), which is also why the script finds `sunfish.py` first and derives the folder from it.
- **Stockfish was not on my PATH**, same as in v1 and v2. `find_stockfish()` now checks `$STOCKFISH_PATH`, the PATH, the usual Linux/macOS locations, and `~/Downloads/stockfish/stockfish*.exe` so it works on this machine without an environment variable.
- **Windows + Jupyter needs `WindowsProactorEventLoopPolicy()`** before python-chess can start an engine subprocess (v1 and v2 hit this too). New this time: on Python 3.14 `asyncio.set_event_loop_policy` raises a `DeprecationWarning`, which printed above every run, so I set it inside `warnings.catch_warnings()`.
- **The clone landed in the wrong place.** The notebook in the assignment expects `sunfish/sunfish.py` at the portfolio root, but v1 and v2 keep each engine's source inside its own folder. I moved it to `engines/v3-sunfish/sunfish/` and made the harness look in both places, so either layout works.

## How I ran a game through the harness
Sunfish played White in every game, at Elo-limited Stockfish 1350 with 0.1 s a move on the other side — the same opponent settings as v1 and v2, so the three engines are comparable.

- **0.2 s a move:** Sunfish won 1-0, mate on move 32 (`32. Qg7#`). 63 plies in 10 s; 70,396 nodes in all, at depth 2–7, median 4. Saved to `games/v3-sunfish-vs-stockfish-0.2s.pgn`.
- **2 s a move:** Sunfish won 1-0, mate on move 33 (`33. Rd7#`). 65 plies in 60 s; 641,511 nodes, at depth 4–9, median 6. Saved to `games/v3-sunfish-vs-stockfish-2s.pgn`.
- **Against me:** `python scripts/play_sunfish.py --opponent you` — moves typed in SAN, saved to `games/v3-sunfish-vs-me.pgn`.

Worth saying plainly: these are the two games the notebook saved, and **they are not repeatable**. Sunfish is given a clock, not a depth, so it searches as far as the machine got in 0.2 s; Stockfish at `UCI_LimitStrength` picks among its own moves at random. I ran the same two games earlier in the afternoon from the command line and Sunfish *lost* both, mated on move 22 and move 32. One game each way says nothing about which engine is stronger — Stockfish at 1350 is deliberately weak, and the only thing both runs agree on is where the moves come from.

**Task 2.3 — what the extra time bought.** Fifteen times the clock bought four plies and thirteen times the nodes, but not a different move: from the Week 4 Italian middlegame Sunfish played `Qb3` at every clock — depth 3 / 2,228 nodes / −38 at 0.2 s, depth 5 / 12,849 / −37 at 1 s, depth 5 / 18,179 / −24 at 2 s, depth 7 / 29,971 / +69 at 3 s. So the time did not buy a better move; it bought a different *opinion* of the same move, from −38 to +69 as the search got deep enough to see the compensation, and in the games it bought about two plies on average (median depth 4 at 0.2 s, 6 at 2 s). Note 2 s reaching the same depth 5 as 1 s on 40% more nodes: the extra went into narrowing the MTD-bi bracket at depth 5, not into a sixth ply.

## My one change (Week B)
**Change:** Sunfish's `tp_move` — remember the best move in the transposition table and try it first on the next pass of iterative deepening (`sunfish.py` line 440) — ported onto my own search and switched **on → off**. In `scripts/tt_search.py` this is the single flag `use_tt_move`; everything else is identical between the two rows: the same Sunfish piece-square evaluation, the same three positions from last week, depth 4, the same base move order (captures first by victim value, then quiet moves alphabetically), the same table, the same depth test.

**Why this one:** of the three ideas in Sunfish, this is the one that costs nothing. The table and iterative deepening both have an obvious price — memory, and re-searching the shallow plies — but reordering moves cannot change the answer at all, only how much work it takes to get there. I wanted to see whether something that provably does not change the result is worth anything, and by how much.

## Results
See `results.csv` in this folder (and `../../results/v3-tt-nodes.csv` for the full four-row Task 3.1 table).

```
experiment,label,depth,nodes,table_hits,move,score,games,points_for_change,decisive
tt_depth4,start -- TT + deepening (before),4,18077,408,Nf3,-5.0,,,
tt_depth4,start -- + tp_move first (after),4,8013,138,Nf3,-5.0,,,
tt_depth4,Italian -- TT + deepening (before),4,21141,373,Bg5,-93.0,,,
tt_depth4,Italian -- + tp_move first (after),4,9082,365,Bg5,-93.0,,,
tt_depth4,open middle -- TT + deepening (before),4,13089,440,Nfd2,-197.0,,,
tt_depth4,open middle -- + tp_move first (after),4,11310,418,Nfd2,-197.0,,,
port_match,"pst-greedy vs plain greedy, colours alternating (1 unfinished at 120 plies)",,,,,,30,15.5,11
```

The full Task 3.1 table, all four configurations at depth 4:

| position | alpha-beta alone | + table | + deepening | + best move first |
|---|---|---|---|---|
| start | 17,862 | 15,807 (398 hits) | 18,077 (408) | **8,013** (138) |
| Italian | 19,722 | 19,013 (362) | 21,141 (373) | **9,082** (365) |
| open middle | 12,219 | 11,745 (440) | 13,089 (440) | **11,310** (418) |

The move and the value are identical on all twelve rows — `Nf3` / −5, `Bg5` / −93, `Nfd2` / −197 — which is the check that the table is bookkeeping and not a second opinion. `scripts/tt_search.py` asserts it rather than leaving it to the eye.

**Nodes:** trying the remembered move first cut the depth-4 search by 56% at the start (18,077 → 8,013) and 57% in the Italian (21,141 → 9,082) but only 14% in the open middlegame (13,089 → 11,310), where captures already dominate the base ordering and the table has little left to add. Worth noticing on the way: the table **alone** saved almost nothing (about 4–12%), and iterative deepening on its own cost 11–14% *more* nodes than the table alone — the two ideas only pay off together, through the move order, which is exactly why Sunfish stores `tp_move` separately from `tp_score`.

**Match:** the port — Greedy breaking ties in material with Sunfish's piece-square tables instead of at random — scored **15.5 / 30** against plain Greedy with colours alternating (11 games decisive, 1 still going at the 120-ply cap and scored as a draw). That is dead level, and thirty games cannot support any claim stronger than "if the tables help a one-ply bot at all, the effect is smaller than thirty games can see".

## For the Blend presentation
**The prediction, and what actually happened.** The search is sound, so the mistake had to come from the evaluation: a piece-square table knows nothing about king safety, so I predicted a king walking into an attack the table scores as fine. Sunfish won both of the games it saved, so the prediction looks wrong — but the behaviour is there in both, it just went unpunished by a 1350 opponent.

- **It volunteers its own king.** In the 2 s game Sunfish castled on move 6 and then pushed `9. g4`, `10. g5` and `11. f4` — every pawn in front of its own king, because the tables pay for those squares and nothing charges for the holes they leave. In the 0.2 s game it did the same with `24. g3`. Both times it was already winning, so nothing came of it; in the two games I played earlier from the command line this is exactly what killed it (`29... Qf2+ 30. Kh3 Rh6+ 31. Kg4 Rh4+ 32. Kg5 Qf6#`, with Sunfish reporting −47,983 at depth 12 — the search saw the mate perfectly well, four moves too late to matter).
- **The score swings in quiet positions.** `6. Bd3 +77`, `7. O-O −59`, `8. Be2 +53`, `10. Bb2 −25`, `11. axb3 +65`, with nothing happening on the board. The number is the last completed pass at whatever depth the clock allowed, and the MTD-bi bracket stops `EVAL_ROUGHNESS` (15 centipawns) wide, so a shallow score is only ever roughly right.
- **What it is genuinely good at is taking material.** Both wins are the same game, a bishop raid: Stockfish at 1350 left pieces loose, and the tables, which price a piece by where it stands, pushed the bishop to the square that paid. At 0.2 s that was `17. Bxd7`, `18. Bc6`, `19. Bxb7`, `20. Bxa6`, and then `21. Nc6` trapping the queen; at 2 s it was `14. Bxh5`, `16. Bxe6+`, `19. Bd5`, `20. Bxa8`, `22. Bxd7`. No king safety required.

**What to say in two minutes.** A transposition is the same position reached by a different move order, and remembering it costs nothing but a dictionary. Iterative deepening buys an answer that is ready at every instant and a better-ordered next pass — which is why Sunfish can be handed a clock at all. And the measurement above says which of the two is doing the work: the better ordering, not the remembered score.
