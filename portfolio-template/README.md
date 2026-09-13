# <Your Name> — AI Algorithms in Chess, Fall 2026

> My portfolio for the Gambit Lab: eight chess engines from eight eras, each one downloaded from GitHub, run on my machine, changed once, and measured.

## The engines I ran

| # | Engine | The algorithm it taught me | Got it running? | My one change | Result |
|---|---|---|---|---|---|
| v1 | [PyTuroChamp](https://github.com/stevexyz/PyTuroChamp) | Hand-crafted evaluation (1948) | | | |
| v2 | [Andoma](https://github.com/healeycodes/andoma) | Minimax with alpha-beta pruning | | | |
| v3 | [Sunfish](https://github.com/thomasahle/sunfish) | Transposition tables + iterative deepening | | | |
| v4 | [Syzygy tablebases](https://python-chess.readthedocs.io/en/latest/syzygy.html) | Retrograde analysis (perfect play) | | | |
| v5 | [Stockfish](https://github.com/official-stockfish/Stockfish) | NNUE learned evaluation | | | |
| v6 | [Leela Chess Zero](https://github.com/LeelaChessZero/lc0) | MCTS + policy/value network | | | |
| v7 | [Maia](https://github.com/CSSLab/maia-chess) | Imitation learning | | | |
| v8 | [searchless_chess](https://github.com/google-deepmind/searchless_chess) | Transformer without search | | | |

*Fill a row in the week you finish the engine. Link each row to its folder under `engines/`.*

## My own code
- `scripts/first_engine_game.py` — my first game against Stockfish (Week 2)
- `scripts/` — bots I wrote along the way (Greedy, Shannon A, alpha-beta)

## My games
- `games/` — PGNs of my games against the engines and at the Blend ladder

## About me
<!-- two or three lines: major, why chess + AI, what you want to do next -->

---
*Built in the Gambit Lab, Juice House Chess Blend, University of Toledo. Every engine above belongs to its original authors — see each folder's RECIPE.md for the license and link.*
