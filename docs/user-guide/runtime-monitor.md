# Watching a Borg Run Live

`parasolpy.borg_runtime` analyzes a Borg MOEA runtime file after the run
finishes. `parasolpy.runtime_monitor` and `parasolpy.runtime_dashboard` cover
the other case: watching the archive change while the optimization is still
writing the file.

The framing is a live leaderboard. Each archived solution is a row, sorted by
a key you choose. Solutions that just entered the archive are marked **born**;
solutions that just dropped out are marked **died** and linger for a few
snapshots so a death is visible rather than a row that quietly disappears.

Sorting is an ordering, not a verdict. Nothing in this module decides which
solutions are good: the sort key and direction are yours to pick, and a row
near the top is simply first in that order.

## The CLI

```bash
parasolpy-runtime path/to/RunTime.txt --sort-column "Cora Avg Storage" --descending
```

Open <http://127.0.0.1:8051>. The page polls the file every two seconds and
redraws. See [the CLI reference](../cli.md) for all options.

To see the widget move without a live run, replay a finished file:

```bash
parasolpy-runtime path/to/RunTime.txt --replay --speed 4
parasolpy-runtime --demo          # replays the bundled sample on a loop
```

## Reading the table

| Column | Meaning |
| --- | --- |
| `#` | Current position in the sort order. Ghost rows of dead solutions show `—`. |
| `Move` | `★ new`, `▲ n` / `▼ n` places moved since the last snapshot, `–` for no change, `✝ out` for a solution that left the archive. |
| `Status` | `born`, `up`, `down`, `held`, `died`. |
| `ID` | Solution ID, which is the NFE at which Borg created the solution. |
| `Age (NFE)` | How long the solution has survived: current NFE minus its ID. |

Green and red are reserved for birth and death. Movement through the sort
order is drawn with arrows and ink, so the two meanings never compete, and
every colored row also carries a text label.

**Sort by** offers `Solution ID` and `Age (NFE)` ahead of the file's data
columns, and **Direction** flips between ascending and descending. Changing
either re-sorts the current archive immediately; movement arrows are measured
against the new order from the next snapshot onward, so switching sort keys
does not report the whole table as having moved. When you sort by a data
column it is always shown as the first value column, since an order driven by
a hidden number is unreadable.

Sorting by ID and by age describe the same axis from opposite ends — a
solution's ID is its birth NFE, so age is `nfe - id` — but they read
differently, so both are offered:

| Sort by | Direction | Result |
| --- | --- | --- |
| `Solution ID` | ascending | Oldest first (the default) |
| `Solution ID` | descending | Newest first |
| `Age (NFE)` | descending | Oldest first |
| `Age (NFE)` | ascending | Newest first |

## Parsing snapshots with their values

`parse_borg_runtime` returns only solution IDs, which is all a lifespan
analysis needs. To keep the objectives and decision variables, use
`parse_borg_runtime_snapshots`:

```python
from parasolpy.borg_runtime import parse_borg_runtime_snapshots, snapshot_delta

snapshots = parse_borg_runtime_snapshots("output/RunTime.txt")
latest = snapshots[-1]
print(latest.nfe, latest.metadata["archive_size"])
print(latest.frame.head())          # indexed by solution ID

delta = snapshot_delta(snapshots[-2], latest)
print(sorted(delta["born"]), sorted(delta["died"]))
```

For the older runtime layout, which names no columns, pass `columns=` to
supply names (otherwise they are `col_1`, `col_2`, …):

```python
snapshots = parse_borg_runtime_snapshots(
    "output/RunTime.txt", columns=["cost", "reliability", "deficit"]
)
```

## Tailing a file yourself

`RuntimeTail` reads only the bytes appended since its last poll and returns
snapshots as they complete. A snapshot is emitted once its declared
`Archive size` rows have all arrived, so a snapshot that is still being
written is never returned half-full, and a read landing mid-line is buffered
until the rest of the line shows up.

```python
from parasolpy.runtime_monitor import LeaderboardState, RuntimeTail

tail = RuntimeTail("output/RunTime.txt")
board = LeaderboardState(sort_column="cost", ascending=True, ghost_snapshots=2)

for snapshot in tail.poll():
    board.update(snapshot)

for row in board.rows():
    print(row["position"], row["status"], row["id"], row["age"])
```

The file does not need to exist when you start: polling a missing path returns
nothing, so you can open the dashboard before launching the run. If the file
shrinks between polls, `RuntimeTail` treats it as a rewritten run, sets
`restarted`, and starts over — the dashboard resets its leaderboard when that
happens.

`board.history_frame()` returns the retained per-snapshot history (`nfe`,
`archive_size`, `born`, `died`, `improvements`, `restarts`), which is what the
dashboard's two charts are drawn from.

## Choosing what to sort by

Borg runtime files do not label which columns are objectives, so the sort key
is your choice:

- Sorting by a data column groups the archive along that metric. It says
  nothing about which solutions are preferable — an archive is by definition
  a set of mutually non-dominated solutions.
- `SORT_ID` (the default) puts the oldest solutions first, surfacing the ones
  that have resisted domination longest.
- `SORT_AGE` shows the same axis in the units you probably think in.

```python
from parasolpy.runtime_monitor import SORT_AGE, SORT_ID, LeaderboardState

board = LeaderboardState(sort_column=SORT_AGE, ascending=False)  # oldest first
board.set_sorting("cost", ascending=True)                        # switch keys
```

Ties keep their previous relative order, so a constraint column that is zero
for every solution produces a stable list rather than a shuffling one. A sort
column that a snapshot does not carry falls back to ID order rather than
losing the ordering.
