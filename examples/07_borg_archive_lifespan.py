"""Borg archive lifespan visualization: birth and death of archive solutions.

Parses a Borg MOEA runtime file (repeated snapshots of the evolving archive)
and draws a survival chart: one horizontal bar per solution, running from the
function evaluation where the solution was created (its ID) to the point it
was removed from the archive, or to the final NFE if it survived the run.

Snapshot gaps larger than 50 NFE — which coincide with Borg restarts, during
which no runtime output is written — are shaded.
"""
from pathlib import Path

from parasolpy.borg_runtime import (
    parse_borg_runtime,
    solution_lifespans,
)
from parasolpy.plotting import plot_archive_lifespans
from parasolpy.util import ensure_dir

DATA = Path(__file__).parent.parent / "parasolpy" / "data" / "RunTime_NorthSouth.txt"
OUT = ensure_dir(Path(__file__).parent / "_output")


def main():
    snapshots = parse_borg_runtime(DATA)
    spans = solution_lifespans(snapshots)

    n_survivors = int(spans["in_final_archive"].sum())
    lifespan = spans["death"] - spans["birth"]
    print(f"Snapshots: {len(snapshots)} "
          f"(NFE {snapshots[0][0]} to {snapshots[-1][0]})")
    print(f"Solutions ever archived: {len(spans)}")
    print(f"In final archive: {n_survivors} "
          f"(removed during run: {len(spans) - n_survivors})")
    print(f"Median lifespan: {lifespan.median():.0f} NFE "
          f"(max {lifespan.max():.0f})")

    _, _, out_path = plot_archive_lifespans(snapshots, OUT)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
