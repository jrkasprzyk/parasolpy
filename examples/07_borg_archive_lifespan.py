"""Borg archive lifespan visualization: birth and death of archive solutions.

Parses a Borg MOEA runtime file (repeated snapshots of the evolving archive)
and draws a survival chart: one horizontal bar per solution, running from the
function evaluation where the solution was created (its ID) to the point it
was removed from the archive, or to the final NFE if it survived the run.

Optionally, pass a path to a Borg-RiverWare ``SolutionModels`` folder as the
first command-line argument. Model files (``Solution<ID>.mdl``) whose IDs
never appear in any runtime snapshot are drawn as a third category
("leaked"), and snapshot gaps larger than 50 NFE — which coincide with Borg
restarts, during which no runtime output is written — are shaded.
"""
import sys
from pathlib import Path

from parasolpy.borg_runtime import (
    leaked_model_ids,
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

    leaked = None
    if len(sys.argv) > 1:
        leaked = leaked_model_ids(sys.argv[1], spans)
        print(f"Model files on disk with no snapshot record: {len(leaked)}")

    _, _, out_path = plot_archive_lifespans(snapshots, OUT, leaked_ids=leaked)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
