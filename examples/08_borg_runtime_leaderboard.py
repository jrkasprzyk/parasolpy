"""Borg archive leaderboard: watch solutions being born and dying, live.

Example 07 charts the birth and death of archive solutions after a run has
finished. This one covers the same events while the run is still going: it
tails a Borg runtime file, and after each new snapshot prints the archive as a
sorted leaderboard with solutions that just entered marked "born" and
solutions that just dropped out marked "died".

Run it with no arguments to replay the bundled sample file (there is no live
run to follow in a checkout), or pass the path to a runtime file that Borg is
currently writing::

    python examples/08_borg_runtime_leaderboard.py
    python examples/08_borg_runtime_leaderboard.py path/to/RunTime.txt

The same data drives the browser dashboard, which adds color, charts and
column pickers::

    parasolpy-runtime path/to/RunTime.txt --sort-column "Cora Avg Storage" --descending
    parasolpy-runtime --demo
"""
import sys
import time
from pathlib import Path

from parasolpy.runtime_monitor import (
    SORT_AGE,
    SORT_ID,
    LeaderboardState,
    ReplaySource,
    RuntimeTail,
)

DATA = Path(__file__).parent.parent / "parasolpy" / "data" / "RunTime_with-headers.txt"

# Sorted so the largest average storage comes first. Any column in the file
# works, as do SORT_ID and SORT_AGE; the sort is just an ordering, not a
# judgement about which solutions are better.
SORT_COLUMN = "Cora Avg Storage"
ASCENDING = False

# How many leaderboard rows to print per snapshot, and how long to wait
# between polls of a live file.
TOP_N = 8
POLL_SECONDS = 2.0

STATUS_MARK = {"born": "+", "died": "x", "up": "^", "down": "v", "held": " "}


def print_leaderboard(board):
    """Print one snapshot of the table: position, status, ID, age, sort value."""
    header = f"NFE {board.nfe:,}"
    churn = f"+{len(board.born)} born / -{len(board.died)} died"
    print(f"\n{header}  |  archive {board.metadata.get('archive_size')}  |  {churn}")
    label = {SORT_ID: "id", SORT_AGE: "age"}.get(SORT_COLUMN, SORT_COLUMN)
    print(f"  {'#':>3}  {'':1}  {'ID':>7}  {'AGE':>7}  {label}")
    for row in board.rows()[:TOP_N]:
        value = row.get(SORT_COLUMN, "")
        value = f"{value:,.2f}" if isinstance(value, float) else value
        mark = STATUS_MARK[row["status"]]
        print(f"  {row['position']:>3}  {mark:1}  {row['id']:>7}  {row['age']:>7}  {value}")


def main():
    live = len(sys.argv) > 1
    if live:
        source = RuntimeTail(sys.argv[1])
        print(f"Following {sys.argv[1]} (Ctrl-C to stop)")
    else:
        source = ReplaySource(DATA)
        print(f"Replaying {DATA.name} (pass a runtime file path to follow a live run)")

    board = LeaderboardState(
        sort_column=SORT_COLUMN,
        ascending=ASCENDING,
        ghost_snapshots=1,
    )

    try:
        while True:
            for snapshot in source.poll():
                board.update(snapshot)
                print_leaderboard(board)
            if not live and source.exhausted:
                break
            time.sleep(POLL_SECONDS if live else 0.4)
    except KeyboardInterrupt:
        print("\nStopped.")

    print(
        f"\nTotals over {board.snapshot_count} snapshots: "
        f"{board.total_born} solutions born, {board.total_died} died."
    )


if __name__ == "__main__":
    main()
