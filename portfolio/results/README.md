# results — every benchmark as a CSV with a one-line README

- `v3-tt-nodes.csv` — Task 3.1: three positions at depth 4, four ways (alpha-beta alone, + the transposition table, + iterative deepening, + the table's best move tried first). Nodes and table hits differ; the move and the score do not. Written by `scripts/tt_search.py`.

Each engine's own before/after numbers live with the engine, e.g. [`engines/v3-sunfish/results.csv`](../engines/v3-sunfish/results.csv).
