# v1-pyturochamp — my recipe

**Source:** <(https://github.com/stevexyz/PyTuroChamp)>   **License:** <from RECON.md>

**PyturoChamp is the 1st handwritten engine, which was brute-forced with a flowchart of decisions on moves played by the bot, and it couldn't see more than once-twice move ahead. Rules are points for each move- capture, Castle, Piece Safety, Pawns, Checks, etc.- where it has higher points than its opponent.**

## What I did to get it running (exact commands, in order)
```
%pip install chess -q                                  # setup cell: python-chess
apt-get install -y -q stockfish                        # setup cell, Colab only
!git clone https://github.com/stevexyz/PyTuroChamp     # download the engine
# started PyTuroChamp as a UCI engine via PyTuroChamp/ptc_xboard.py
```

## What broke and how I fixed it
Nothing broke. The setup cell installed python-chess and Stockfish, and PyTuroChamp ran without changes.
## How I ran a game through the harness
- vs Stockfish: Stockfish at Elo 1350, 0.1seconds per move; PyTuroChamp played as White.
- Both games saved with save_pgn() to games/___.pgn and games/___.pgn.
## My one change (Week B)
**Change:** mobility weight 0.5 → 1.0 in turing_eval. Everything else identical (same bot, 20 games, max_plies=120, seed=1, colours alternating).
## Results
See `results.csv` in this folder.
