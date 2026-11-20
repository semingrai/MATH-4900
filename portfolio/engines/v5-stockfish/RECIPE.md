# v4 Stockfish (NNUE) — my recipe

**Source:** <https://github.com/official-stockfish/Stockfish>, release `sf_16`   **License:** GNU GPL v3 — I may run it, modify it and redistribute it, as long as what I redistribute stays GPL v3. I only run the official binary; nothing of Stockfish's is committed.

(The assignment calls this engine v4; the portfolio template had already made the folder `v5-stockfish`, so it lives here.)

**Stockfish is an alpha-beta search engine whose leaf evaluation is a small neural network, NNUE, instead of (or, in Stockfish 12–16, as an alternative to) a hand-written formula of material, mobility and king safety.** NNUE's first layer stores, for each side, an *accumulator*: the sum of one weight row per active HalfKP input — (my king's square, a non-king piece's square, that piece's type and colour) — and it is efficiently updatable because a move switches only a handful of those inputs on or off, so the accumulator is patched by adding and subtracting those rows instead of being recomputed: a quiet move subtracts one row (the piece on its old square) and adds one (the piece on its new square), a capture also subtracts the captured piece's row, so three in all, and a king move changes the *king square* in every single input of that side, so every row is different and that half of the accumulator has to be refreshed from scratch.

The notebook checks this by counting the rows (Task 1 cell): `Nc3` subtracts 1 and adds 1 in each half; `exd4` subtracts 2 and adds 1; `Kf1` leaves Black's half alone and changes all 30 of White's.

## What I did to get it running (exact commands, in order)
```
# Stockfish 19 (already on this machine) has no classical evaluation and no `Use NNUE` -- both were
# removed in 16.1 -- so I downloaded Stockfish 16 next to the scripts (gitignored by `stockfish*`):
cd engines/v5-stockfish
curl -L -o stockfish16/sf16.zip https://github.com/official-stockfish/Stockfish/releases/download/sf_16/stockfish-windows-x86-64-avx2.zip
unzip stockfish16/sf16.zip -d stockfish16
python scripts/play_stockfish.py --opponent you --nnue on        # Task 2.1
python scripts/play_stockfish.py --opponent you --nnue off       # Task 2.2
python scripts/run_experiments.py                                # Task 3 -> results.csv (about 10 min)
python -m jupyter nbconvert --to notebook --execute --inplace v4-stockfish-nnue.ipynb
```
`find_stockfish()` looks in `$STOCKFISH_PATH`, then `stockfish16/stockfish/`, then the PATH. `open_stockfish()` refuses any Stockfish without the `Use NNUE` option, so a newer one can't quietly turn "NNUE off" into "NNUE on".

## What broke and how I fixed it
- **Stockfish 19 cannot switch the network off.** Fixed by downloading `sf_16` (above).
- **python-chess could not start the engine from a relative path on Windows** (`FileNotFoundError: [WinError 2]`). `find_stockfish()` now returns an absolute path.
- **Windows + Jupyter needs `WindowsProactorEventLoopPolicy()`**, same as v1–v3; set inside `warnings.catch_warnings()` because Python 3.14 deprecates it.
- **My `python3` Jupyter kernel points at a Python 3.13 that is no longer installed**, so `nbconvert --execute` failed. I executed the notebook with a temporary kernelspec for the Python 3.14 that runs everything else.
- **Node counts must repeat.** One thread, `ucinewgame` (empty hash) before every speed-table search and every match game, fixed depth. With that, replaying a game from its PGN reproduces Stockfish's moves exactly, which is how the notebook re-runs the two games against me without anyone typing.

## How I ran a game through the harness
Stockfish 16 is White at **depth 10**; every Stockfish move prints its depth, nodes, nodes per second and score, then the final board and the PGN path. I asked Claude (the AI assistant that built this harness with me) to choose Black's moves in both games, one move at a time; the PGNs say "me" because that is the harness's name for the human side.

- **NNUE on:** `games/v4-stockfish-nnue-vs-me.pgn` — Italian, `4...exd4 5.cxd4 Bb4+`; Stockfish won the exchange with `18.Be7` (a fork of the queen and the f8 rook), traded down, and mated with `32.Re8#` when I let the back rank go. 32 Stockfish moves, 151,738 nodes.
- **NNUE off:** `games/v4-stockfish-classical-vs-me.pgn` — the classical evaluation chose `2.d4` (the network had chosen `2.Nf3`), so the games split on move 2. I was a pawn up after move 11 and level into the bishop-against-knight ending, then walked my king off the e-file (`30...Ke7`, `31.Rxe4+`) and into a knight fork (`41.Nd4+`). It promoted twice, both times to a rook, and mated with `57.Re6#`. 57 Stockfish moves, 945,669 nodes.

| White | result | SF moves | nodes / move | nodes / s | same move with the other eval |
|---|---|---|---|---|---|
| NNUE | 1-0 | 32 | 4,742 | 1,015,421 | 17 / 32 (53%) |
| classical | 1-0 | 57 | 16,591 | 1,756,137 | 35 / 57 (61%) |

**What the network bought and what it cost:** the network cost about 40% of the speed (1.0 M against 1.76 M nodes a second) but needed only about a third of the nodes per move at the same depth (4,742 against 16,591), and the move changed often: re-searched with the other evaluation, 15 of the 32 positions from the NNUE game and 22 of the 57 from the classical game got a different move.

## My one change
**Change:** `Use NNUE` **on → off** at the same depth, everything else identical: Stockfish 16, one thread, 64 MB hash, depth 10, an empty hash before every search, the same six positions, the same twenty games.

**Why this one:** it is the cleanest experiment on the menu. It is the only one that changes the evaluation alone; the extra-depth and the clock versions each change two things at once (the evaluation and how far it searches), and they only make sense once I know what the evaluation is worth at equal depth. `--classical-depth 12` and `--time 0.05` are in `scripts/run_experiments.py` for the next step.

## Results
`results.csv` (written by `scripts/run_experiments.py`, and again by the notebook):

```
experiment,setting,label,eval,depth,nodes,nps,time_ms,move,score,games,nnue_points,classical_points,decisive
speed,depth 10,start,NNUE,10,7548,1078285,23,e4,50,,,,
speed,depth 10,start,classical,10,23921,1993416,24,e4,17,,,,
speed,depth 10,Italian,NNUE,10,9052,1293142,15,O-O,41,,,,
speed,depth 10,Italian,classical,10,40458,2129368,25,O-O,0,,,,
speed,depth 10,open middle,NNUE,10,25714,1285700,27,h3,32,,,,
speed,depth 10,open middle,classical,10,57379,2125148,33,a3,17,,,,
speed,depth 10,Sicilian,NNUE,10,17303,1441916,18,Bg5,60,,,,
speed,depth 10,Sicilian,classical,10,64053,1883911,40,Bb5,31,,,,
speed,depth 10,rook endgame,NNUE,10,9932,1241500,15,Rc5,0,,,,
speed,depth 10,rook endgame,classical,10,5240,1746666,10,f4,0,,,,
speed,depth 10,king hunt,NNUE,10,8901,1271571,14,c5,38,,,,
speed,depth 10,king hunt,classical,10,32994,1940823,25,c5,22,,,,
match,depth 10,"NNUE vs classical, colours alternating, 10 openings x 2",,,,,,,,20,13.0,7.0,14
```

| position | NNUE nodes | NNUE n/s | move | classical nodes | classical n/s | move |
|---|---|---|---|---|---|---|
| start | 7,548 | 1,078,285 | e4 | 23,921 | 1,993,416 | e4 |
| Italian | 9,052 | 1,293,142 | O-O | 40,458 | 2,129,368 | O-O |
| open middle | 25,714 | 1,285,700 | h3 | 57,379 | 2,125,148 | a3 |
| Sicilian | 17,303 | 1,441,916 | Bg5 | 64,053 | 1,883,911 | Bb5 |
| rook endgame | 9,932 | 1,241,500 | Rc5 | 5,240 | 1,746,666 | f4 |
| king hunt | 8,901 | 1,271,571 | c5 | 32,994 | 1,940,823 | c5 |

**Match:** NNUE 13 – classical 7 over 20 games, colours alternating, ten openings each played once with each colour; 14 decisive. NNUE won 10, drew 6 and lost 4 (as White 5 wins, 3 draws, 2 losses; as Black 5, 3, 2).

**Speed:** with the network off Stockfish searches about 1.6× as many nodes a second (1.97 M against 1.27 M, mean of six positions) but needs 2.9× as many nodes to finish depth 10 (224,045 against 78,450), most likely because a sharper evaluation orders moves better and cuts off more; the best move was the same in only 3 of 6 positions.

**Match, in one sentence:** at equal depth the network scored 13–7 (65%, roughly +100 Elo, though twenty games put wide error bars on that), and it got there searching about a third of the nodes, so the network buys a better judgement of a smaller tree at about two-thirds of the speed.
