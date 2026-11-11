"""Parsing and analysis of Borg MOEA runtime files.

A Borg runtime file records periodic snapshots of the evolving archive. Each
snapshot begins with a header block ("Function evaluations N", recombination
operator probabilities, improvement/restart counts, population and archive
sizes) followed by one whitespace-delimited row per archive member. The first
field of each data row is the solution ID, which equals the function
evaluation (NFE) at which the solution was created.

These helpers reconstruct the birth and death of every archived solution,
which supports questions like "how long do solutions survive in the archive?"
Use ``parasolpy.plotting.plot_archive_lifespans`` to visualize the result.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def parse_borg_runtime(runtime_path):
    """Parse a Borg runtime file into archive snapshots.

    Header lines start with a word (for example "Improvements 41") while data
    rows start with an integer solution ID, which is how the two are told
    apart.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.

    Returns:
        list of tuple: One ``(nfe, ids)`` pair per snapshot, in file order,
        where ``nfe`` is the function-evaluation count of the snapshot and
        ``ids`` is the set of solution IDs in the archive at that point.
    """
    path = Path(runtime_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Runtime file not found: {path}")

    snapshots = []
    nfe = None
    ids = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("Function evaluations"):
            if nfe is not None:
                snapshots.append((nfe, ids))
            nfe = int(line.split()[-1])
            ids = set()
            continue
        try:
            ids.add(int(line.split()[0]))
        except ValueError:
            continue  # remaining header lines (operators, improvements, ...)
    if nfe is not None:
        snapshots.append((nfe, ids))

    if not snapshots:
        raise ValueError(f"No snapshots found in runtime file: {path}")
    return snapshots


def parse_borg_runtime_metadata(runtime_path):
    """Parse per-snapshot header metadata from a Borg runtime file.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.

    Returns:
        pd.DataFrame: Indexed by ``nfe`` with columns ``improvements``,
        ``restarts``, ``population_size``, and ``archive_size``.
    """
    path = Path(runtime_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Runtime file not found: {path}")

    patterns = {
        "nfe": r"Function evaluations\s+(\d+)",
        "improvements": r"Improvements\s+(\d+)",
        "restarts": r"Restarts\s+(\d+)",
        "population_size": r"Population size\s+(\d+)",
        "archive_size": r"Archive size\s+(\d+)",
    }
    columns = {name: [] for name in patterns}
    for line in path.read_text().splitlines():
        for name, pattern in patterns.items():
            match = re.match(pattern, line.strip())
            if match:
                columns[name].append(int(match.group(1)))
                break

    lengths = {name: len(values) for name, values in columns.items()}
    if len(set(lengths.values())) != 1 or lengths["nfe"] == 0:
        raise ValueError(
            f"Malformed runtime file (inconsistent header counts {lengths}): {path}"
        )
    return pd.DataFrame(columns).set_index("nfe")


def solution_lifespans(snapshots):
    """Build a per-solution lifespan table from archive snapshots.

    A solution's ID is the NFE at which it was born, so birth always equals
    the ID. Snapshots are periodic, so a removed solution's true death lies
    between the last snapshot that contains it and the next snapshot; by
    convention ``death`` is the next snapshot's NFE (or the final NFE for
    solutions still present at the end of the run).

    Args:
        snapshots (list of tuple): ``(nfe, ids)`` pairs from
            :func:`parse_borg_runtime`.

    Returns:
        pd.DataFrame: Indexed by solution ``id`` with columns ``birth``,
        ``death``, and ``in_final_archive``.
    """
    if not snapshots:
        raise ValueError("Input 'snapshots' cannot be empty.")

    nfes = [nfe for nfe, _ in snapshots]
    last_seen_idx = {}
    for si, (_, ids) in enumerate(snapshots):
        for sol_id in ids:
            last_seen_idx[sol_id] = si

    final_nfe = nfes[-1]
    final_ids = snapshots[-1][1]
    rows = []
    for sol_id, si in sorted(last_seen_idx.items()):
        survived = sol_id in final_ids
        if survived:
            death = final_nfe
        else:
            death = nfes[si + 1] if si + 1 < len(nfes) else final_nfe
        rows.append((sol_id, sol_id, death, survived))
    return pd.DataFrame(
        rows, columns=["id", "birth", "death", "in_final_archive"]
    ).set_index("id")
