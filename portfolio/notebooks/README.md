# notebooks

Each one runs in Jupyter Notebook or Google Colab. Open in Colab with File → Open notebook → GitHub, or upload it. They move to the portfolio root in their first cell, so `scripts/`, `engines/` and `games/` are found either way.

- `setup_week.ipynb` — the Setup Week companion notebook
- `v1_pyturochamp.ipynb` — engine v1, hand-crafted evaluation
- `v3-sunfish.ipynb` — engine v3, transposition tables and iterative deepening

`v3-sunfish.ipynb` needs the Sunfish clone for its Task 1 cell:

```bash
git clone https://github.com/thomasahle/sunfish.git engines/v3-sunfish/sunfish
```

Everything else in it (the hand-written table, iterative deepening, the 30-game port match) runs with no engine installed.
