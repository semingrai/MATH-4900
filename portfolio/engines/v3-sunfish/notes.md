# v3-sunfish — 25 annotated lines

Line numbers are from `sunfish/sunfish.py` in this folder (`sunfish 2026`, cloned
2026-10-30). Everything the engine does is in that one 662-line file. I read it top to
bottom once and then came back for these, in the order the search uses them.

## The evaluation it searches with

```python
 32 | piece = {"P": 100, "N": 280, "B": 320, "R": 479, "Q": 929, "K": 60000}
```
Material in centipawns, a pawn = 100. The king is worth 60000 because Sunfish never
checks for checkmate: it is a **king-capture engine**, so losing the king has to be
worse than anything else that can happen on the board.

```python
 33 | pst = {
```
The piece-square tables start here: one 64-number table per piece, written out rank 8
first, so index 0 is a8. This is the whole of Sunfish's positional judgement — there is
no mobility term, no pawn structure, no king safety.

```python
 85 |     padrow = lambda row: (0,) + tuple(x + piece[k] for x in row) + (0,)
```
The material value is **folded into** the table, so one lookup gives "what is this piece
worth, standing here". That is why `pos.score` can be updated incrementally in `move()`
instead of recomputed.

```python
 86 |     pst[k] = sum((padrow(table[i * 8 : i * 8 + 8]) for i in range(8)), ())
```
Each 8-wide rank becomes 10 wide with a 0 at either end. The board is a 120-character
string, and the sentinel columns are what make an off-board move detectable without a
bounds check.

```python
546 |         pst["K"] = K_MID if "Q" in pos.board and "q" in pos.board else K_END
```
One table is swapped, per search, depending on whether both queens are still on. With the
queens off, the king's table changes to one that pulls it to the centre — that is all the
"endgame knowledge" the engine has, and it is enough for K+R vs K.

```python
160 | MATE_UPPER = piece["K"] + 10 * piece["Q"]
```
The ceiling of the score range: a king plus ten queens. Any score near it means a king
capture was seen, which is how mate is represented.

```python
169 | EVAL_ROUGHNESS = 15
```
The width the score search stops at, and what one ply of mate distance is worth. It is
why Sunfish's scores jump in steps rather than smoothly: it never bothers to narrow the
window below 15 centipawns.

## The transposition table

```python
320 | # lower <= s(pos) <= upper
```
The invariant the whole table rests on. A stored entry is never "the score"; it is a
sandwich, a pair of bounds that the true value lies between.

```python
321 | Entry = namedtuple("Entry", "lower upper")
```
So one entry carries **both** bounds at once. Most engines store a value plus a flag
saying exact/lower/upper; Sunfish stores the two numbers, and "exact" is just the case
where they meet.

```python
324 | class Searcher:
```
The search is one object so the tables can live across moves — the thing that makes
remembering worth anything.

```python
326 |         self.tp_score, self.tp_move, self.history = {}, {}, set()
```
**Two** transposition tables, which was the thing I had not understood before. `tp_score`
answers "how good is this position" and is keyed by `(pos, depth)`. `tp_move` answers
"what was the best move here" and is keyed by `pos` alone — a good move stays a good move
whatever depth you are searching to.

```python
329 |     def bound(self, pos, gamma, depth, root=False):
```
Not `alphabeta(pos, alpha, beta, depth)`. Sunfish searches with a single `gamma` and asks
one yes/no question — "is the score at least gamma?" — and `search()` binary-searches on
gamma. That is why one value function per key is enough, and why the table needs no
alpha/beta flag.

```python
380 |         depth = max(depth, 0)
```
Every negative depth collapses to 0. Quiescence search goes as deep as the captures run
regardless, so all those nodes share one key instead of filling the table with entries
that mean the same thing.

```python
399 |             entry = self.tp_score.get((pos, depth), Entry(-MATE_UPPER, MATE_UPPER))
```
**The depth test, done by the key.** Most engines store one entry per position and then
compare `stored_depth >= depth` before trusting it; Sunfish puts the depth *in the key*,
so a depth-4 entry is simply never read by a depth-5 probe. A miss defaults to the widest
possible sandwich, which no test can pass.

```python
400 |             if entry.lower >= gamma: return entry.lower
```
Reuse case one: the remembered lower bound already answers "yes, at least gamma", so the
sub-tree is skipped. This is the whole saving of a transposition table — the same position
reached by a different move order costs a dictionary lookup instead of a search.

```python
401 |             if entry.upper < gamma: return entry.upper
```
Reuse case two: the remembered upper bound already answers "no". **Either bound can end
the search, but only one can** — an exact value is the case where both tests would agree,
and a bound that does not straddle gamma is as good as an exact value for this question.

```python
410 |         killer = self.tp_move.get(pos)
```
The move memory read. Nothing about this changes the value of the sub-tree — it only
changes the order the moves are tried in, which is why it is sound to use an entry stored
by a shallower search.

```python
440 |             if killer and ((val := pos.value(killer)) >= QS or depth) and ceiling(val) >= gamma: yield val, killer
```
The remembered move is yielded **first**, before any move is generated. If it still cuts,
the move generator is never run at this node. This is the line I turned on and off for my
own experiment.

```python
444 |             yield from sorted(((v, m) for m in pos.gen_moves() if (v := pos.value(m)) >= QS or depth), reverse=True)
```
Everything else, sorted by what the piece-square tables say the move gains. Good ordering
is not cosmetic: alpha-beta only prunes when a good move is found early.

```python
493 |                     self.tp_move[pos] = move
```
The move memory write, on a fail-high. A move that was good enough to cut is the move to
try first next time — the next pass of iterative deepening, or the next time this position
turns up by another route.

```python
529 |             self.tp_score[pos, depth] = Entry(best, entry.upper) if best >= gamma else Entry(entry.lower, best)
```
The store, and the clearest statement of what a bound is. Failing high (`best >= gamma`)
tightens the **lower** bound and leaves the upper alone; failing low tightens the upper and
leaves the lower alone. One side of the sandwich at a time, which is why two searches of
the same key can only narrow it, never contradict each other.

```python
531 |             del self.tp_score[next(iter(self.tp_score))]
```
Eviction, once the table passes `TABLE_SIZE`: drop the oldest insertion. A real engine
would overwrite by hash bucket; Sunfish just lets Python's dict ordering be its
replacement policy.

## Iterative deepening

```python
552 |         for depth in range(1, 1000):
```
Iterative deepening in one line: search to depth 1, then 2, then 3, from scratch each
time. It looks wasteful, and it is not — the shallow pass fills `tp_move`, so the deep
pass gets its best move first and prunes far harder than it would have alone.

```python
558 |             while lower < upper - EVAL_ROUGHNESS:
```
The binary search on the score (MTD-bi). Each `bound()` call answers one yes/no question
about gamma and moves one end of the bracket; the loop stops once the bracket is
`EVAL_ROUGHNESS` wide, because narrowing further would not change the move played.

```python
562 |                 yield depth, gamma, score, self.tp_move.get(pos)
```
`search()` is a **generator**: it hands back the best move it has after every pass and then
carries on. That is the answer to "why can Sunfish be given a clock" — the caller keeps
pulling until the time is gone and plays the last thing yielded, so there is always a legal
answer ready, at whatever depth was reached.
