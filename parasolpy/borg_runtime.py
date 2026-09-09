"""Parsing and analysis of Borg MOEA runtime files.

A Borg runtime file records periodic snapshots of the evolving archive. Each
snapshot begins with a header block ("Function evaluations N", recombination
operator probabilities, improvement/restart counts, population and archive
sizes) followed by one whitespace-delimited row per archive member. The first
field of each data row is the solution ID, which equals the function
evaluation (NFE) at which the solution was created.

Two runtime layouts are supported. Older files (see
``parasolpy/data/RunTime_no-headers_NorthSouth.txt``) put the data rows
directly after the ``Archive size`` line. Newer files (see
``parasolpy/data/RunTime_with-headers.txt``) insert a column-header row
naming each field, with names quoted because they contain spaces::

    "Solution ID" "Roberto Flood Control Level" "Cora Avg Storage" ...

Both layouts are detected automatically; pass ``has_headers=True``/``False``
to the parsers to assert one instead, and use
:func:`parse_borg_runtime_columns` to read the column names themselves.

These helpers reconstruct the birth and death of every archived solution,
which supports questions like "how long do solutions survive in the archive?"
and "which saved solution files should have been cleaned up?" (see
``leaked_model_ids``). Use ``parasolpy.plotting.plot_archive_lifespans`` to
visualize the result.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pandas as pd

# Snapshot header lines, which appear in both layouts and are never data rows
# nor column headers. The second alternative matches the per-operator
# probability lines ("  SBX   16.67%"), whose names vary by Borg build.
_SNAPSHOT_HEADER = re.compile(
    r"^(?:Function evaluations|Improvements|Restarts|Population size"
    r"|Archive size|Usage of recombination operators)\b"
    r"|^[A-Za-z][A-Za-z0-9_-]*\s+[\d.]+\s*%$"
)


def _is_data_row(line):
    """Return True if ``line`` is an archive data row (starts with an ID)."""
    fields = line.split()
    if not fields:
        return False
    try:
        int(fields[0])
    except ValueError:
        return False
    return True


def _is_column_header(line):
    """Return True if ``line`` names the data columns rather than carrying data.

    A column-header row is any non-blank line that is neither a snapshot
    header line nor a data row, so both the quoted style written by
    Borg-RiverWare and a plain unquoted name row are recognized.
    """
    return bool(line) and not _SNAPSHOT_HEADER.match(line) and not _is_data_row(line)


def _read_lines(runtime_path):
    """Read and strip a runtime file, raising if it is missing."""
    path = Path(runtime_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Runtime file not found: {path}")
    return path, [line.strip() for line in path.read_text().splitlines()]


def _resolve_has_headers(path, lines, has_headers):
    """Reconcile the caller's ``has_headers`` with what the file contains.

    Args:
        path (Path): Runtime file path, used in error messages.
        lines (list of str): Stripped file lines.
        has_headers (bool | None): ``None`` to autodetect, otherwise the
            layout the caller asserts.

    Returns:
        bool: Whether the file carries a column-header row.

    Raises:
        ValueError: If ``has_headers`` contradicts the file's contents.
    """
    found = any(_is_column_header(line) for line in lines)
    if has_headers is None:
        return found
    if has_headers and not found:
        raise ValueError(
            f"has_headers=True but no column-header row was found in: {path}"
        )
    if not has_headers and found:
        raise ValueError(
            f"has_headers=False but a column-header row was found in: {path}. "
            "Pass has_headers=True (or None to autodetect)."
        )
    return bool(has_headers)


def parse_borg_runtime_columns(runtime_path):
    """Read the data column names from a Borg runtime file.

    Names are taken from the first column-header row in the file and parsed
    with :mod:`shlex`, so quoted names containing spaces (for example
    ``"Cora Min Level"``) survive intact.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.

    Returns:
        list of str | None: Column names in file order, or ``None`` for the
        older layout that has no column-header row.
    """
    _, lines = _read_lines(runtime_path)
    for line in lines:
        if _is_column_header(line):
            return shlex.split(line)
    return None


def parse_borg_runtime(runtime_path, has_headers=None):
    """Parse a Borg runtime file into archive snapshots.

    Snapshot header lines start with a word (for example "Improvements 41")
    while data rows start with an integer solution ID, which is how the two
    are told apart. A column-header row, when present, is recognized and
    skipped; use :func:`parse_borg_runtime_columns` to read the names.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.
        has_headers (bool, optional): ``None`` (default) autodetects whether
            the file carries a column-header row. Pass ``True`` or ``False``
            to assert the layout instead; a mismatch raises ``ValueError``.

    Returns:
        list of tuple: One ``(nfe, ids)`` pair per snapshot, in file order,
        where ``nfe`` is the function-evaluation count of the snapshot and
        ``ids`` is the set of solution IDs in the archive at that point.
    """
    path, lines = _read_lines(runtime_path)
    _resolve_has_headers(path, lines, has_headers)

    snapshots = []
    nfe = None
    ids = set()
    for line in lines:
        if not line:
            continue
        if line.startswith("Function evaluations"):
            if nfe is not None:
                snapshots.append((nfe, ids))
            nfe = int(line.split()[-1])
            ids = set()
            continue
        if _is_data_row(line):
            ids.add(int(line.split()[0]))
        # else: remaining snapshot header lines and the column-header row
    if nfe is not None:
        snapshots.append((nfe, ids))

    if not snapshots:
        raise ValueError(f"No snapshots found in runtime file: {path}")
    return snapshots


def parse_borg_runtime_metadata(runtime_path, has_headers=None):
    """Parse per-snapshot header metadata from a Borg runtime file.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.
        has_headers (bool, optional): ``None`` (default) autodetects whether
            the file carries a column-header row. Pass ``True`` or ``False``
            to assert the layout instead; a mismatch raises ``ValueError``.

    Returns:
        pd.DataFrame: Indexed by ``nfe`` with columns ``improvements``,
        ``restarts``, ``population_size``, and ``archive_size``.
    """
    path, lines = _read_lines(runtime_path)
    _resolve_has_headers(path, lines, has_headers)

    patterns = {
        "nfe": r"Function evaluations\s+(\d+)",
        "improvements": r"Improvements\s+(\d+)",
        "restarts": r"Restarts\s+(\d+)",
        "population_size": r"Population size\s+(\d+)",
        "archive_size": r"Archive size\s+(\d+)",
    }
    columns = {name: [] for name in patterns}
    for line in lines:
        for name, pattern in patterns.items():
            match = re.match(pattern, line)
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


def leaked_model_ids(models_dir, spans, pattern="Solution*.mdl"):
    """Find saved solution-model files whose IDs appear in no snapshot.

    Borg-RiverWare saves a model file per archived solution and is expected
    to delete it when the solution is removed from the archive. Solutions
    that enter and leave the archive between two runtime snapshots (for
    example during a restart, when no runtime output is written) are
    invisible to snapshot-based cleanup and their files leak.

    Args:
        models_dir (str | PathLike): Folder containing saved model files
            named with the solution ID (for example ``Solution123.mdl``).
        spans (pd.DataFrame): Output of :func:`solution_lifespans`.
        pattern (str, optional): Glob pattern for model files.

    Returns:
        list of int: Sorted solution IDs with a file on disk but no record
        in any runtime snapshot.
    """
    directory = Path(models_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Models directory not found: {directory}")

    disk_ids = set()
    for path in directory.glob(pattern):
        match = re.search(r"\d+", path.stem)
        if match:
            disk_ids.add(int(match.group()))
    return sorted(disk_ids - set(spans.index))
