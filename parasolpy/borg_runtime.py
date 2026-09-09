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

    patterns = {"nfe": _NFE_PATTERN, **_META_PATTERNS}
    columns = {name: [] for name in patterns}
    for line in lines:
        for name, pattern in patterns.items():
            match = pattern.match(line)
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


# Per-snapshot header fields, shared by the metadata parser and the snapshot
# assembler. "Function evaluations" is kept separate because it also acts as
# the delimiter that starts a new snapshot.
_NFE_PATTERN = re.compile(r"Function evaluations\s+(\d+)")
_META_PATTERNS = {
    "improvements": re.compile(r"Improvements\s+(\d+)"),
    "restarts": re.compile(r"Restarts\s+(\d+)"),
    "population_size": re.compile(r"Population size\s+(\d+)"),
    "archive_size": re.compile(r"Archive size\s+(\d+)"),
}


class Snapshot:
    """One archive snapshot with its data rows retained.

    Unlike the ``(nfe, ids)`` pairs from :func:`parse_borg_runtime`, which
    keep only solution IDs, a ``Snapshot`` carries the full archive table so
    objective and decision-variable values can be shown alongside the IDs.

    Attributes:
        nfe (int): Function-evaluation count of the snapshot.
        frame (pd.DataFrame): Archive members, indexed by integer solution
            ID, one column per data field.
        metadata (dict): Snapshot header fields present in the file, among
            ``improvements``, ``restarts``, ``population_size`` and
            ``archive_size``.
    """

    __slots__ = ("nfe", "frame", "metadata")

    def __init__(self, nfe, frame, metadata):
        self.nfe = nfe
        self.frame = frame
        self.metadata = metadata

    @property
    def ids(self):
        """set of int: Solution IDs present in this snapshot."""
        return set(self.frame.index)

    def __repr__(self):
        return f"Snapshot(nfe={self.nfe}, n_solutions={len(self.frame)})"


def _parse_data_row(line):
    """Split a data row into ``(solution_id, values)``.

    Fields that are not numeric are kept as strings so a stray text column
    cannot abort a live parse.
    """
    fields = line.split()
    values = []
    for field in fields[1:]:
        try:
            values.append(float(field))
        except ValueError:
            values.append(field)
    return int(fields[0]), values


class _SnapshotAssembler:
    """Line-at-a-time state machine that emits complete :class:`Snapshot` objects.

    Feeding lines one by one (rather than parsing a whole file) is what lets
    the same logic serve both a finished file and a file Borg is still
    appending to. A snapshot is emitted as soon as its ``Archive size`` line
    has been matched by that many data rows, so a live reader does not have
    to wait for the next snapshot's header to know the current one is whole.

    Args:
        columns (list of str, optional): Names for the data columns *after*
            the solution ID. Overrides any column-header row in the file;
            when neither is available, columns are named ``col_1``, ``col_2``,
            and so on.
    """

    def __init__(self, columns=None):
        self._override = list(columns) if columns is not None else None
        self._header = None
        self._reset()

    def _reset(self):
        self._nfe = None
        self._metadata = {}
        self._expected = None
        self._rows = []

    @property
    def columns(self):
        """list of str | None: Data column names discovered so far, if any."""
        if self._override is not None:
            return list(self._override)
        return list(self._header[1:]) if self._header else None

    def feed(self, line):
        """Consume one line; return a completed :class:`Snapshot` or ``None``."""
        line = line.strip()
        if not line:
            return None

        match = _NFE_PATTERN.match(line)
        if match:
            # A new snapshot starts here; anything still buffered belonged to
            # a partially written snapshot and is dropped.
            self._reset()
            self._nfe = int(match.group(1))
            return None

        if self._nfe is None:
            return None  # text before the first snapshot header

        for name, pattern in _META_PATTERNS.items():
            match = pattern.match(line)
            if match:
                value = int(match.group(1))
                self._metadata[name] = value
                if name == "archive_size":
                    self._expected = value
                    if value == 0:
                        return self._emit()
                return None

        if _is_data_row(line):
            self._rows.append(_parse_data_row(line))
            if self._expected is not None and len(self._rows) >= self._expected:
                return self._emit()
            return None

        if _is_column_header(line):
            self._header = shlex.split(line)
        return None

    def flush(self):
        """Emit a trailing snapshot at end of input, or ``None`` if there is none.

        Only for finished files. A live reader must not call this: a snapshot
        that has not reached its declared archive size is still being written.
        """
        if self._nfe is None:
            return None
        return self._emit()

    def _emit(self):
        nfe, metadata, rows = self._nfe, self._metadata, self._rows
        self._reset()

        width = max((len(values) for _, values in rows), default=0)
        names = self._override
        if names is None and self._header:
            names = list(self._header[1:])
        if names is None:
            names = [f"col_{i}" for i in range(1, width + 1)]
        # Reconcile the declared names with the rows actually present, so a
        # header that disagrees with the data cannot raise mid-run.
        if width > len(names):
            names = list(names) + [f"col_{i}" for i in range(len(names) + 1, width + 1)]
        elif width:
            names = list(names[:width])
        else:
            names = list(names)

        index = pd.Index([sol_id for sol_id, _ in rows], name="id", dtype="int64")
        data = [values[: len(names)] for _, values in rows]
        frame = pd.DataFrame(data, index=index, columns=names)
        return Snapshot(nfe, frame, metadata)


def parse_borg_runtime_snapshots(runtime_path, has_headers=None, columns=None):
    """Parse a Borg runtime file into snapshots that keep their data values.

    This is the value-preserving counterpart to :func:`parse_borg_runtime`,
    which returns only solution IDs. Use it when you need the archive's
    objectives or decision variables per snapshot, for example to rank
    archive members as a run progresses.

    Args:
        runtime_path (str | PathLike): Path to the Borg runtime text file.
        has_headers (bool, optional): ``None`` (default) autodetects whether
            the file carries a column-header row. Pass ``True`` or ``False``
            to assert the layout instead; a mismatch raises ``ValueError``.
        columns (list of str, optional): Names for the data columns after the
            solution ID, used when the file carries no column-header row (the
            older layout names nothing). Overrides the file's own names.

    Returns:
        list of Snapshot: One entry per snapshot, in file order.

    Raises:
        FileNotFoundError: If the runtime file does not exist.
        ValueError: If no snapshots are found, or ``has_headers`` contradicts
            the file's contents.
    """
    path, lines = _read_lines(runtime_path)
    _resolve_has_headers(path, lines, has_headers)

    assembler = _SnapshotAssembler(columns=columns)
    snapshots = []
    for line in lines:
        snapshot = assembler.feed(line)
        if snapshot is not None:
            snapshots.append(snapshot)
    trailing = assembler.flush()
    if trailing is not None:
        snapshots.append(trailing)

    if not snapshots:
        raise ValueError(f"No snapshots found in runtime file: {path}")
    return snapshots


def _ids_of(snapshot):
    """Coerce a snapshot, DataFrame, or ID collection to a set of IDs."""
    if snapshot is None:
        return set()
    if isinstance(snapshot, Snapshot):
        return snapshot.ids
    if isinstance(snapshot, pd.DataFrame):
        return set(snapshot.index)
    return set(snapshot)


def snapshot_delta(previous, current):
    """Compare two archive snapshots and report what changed.

    Args:
        previous: The earlier snapshot, as a :class:`Snapshot`, a DataFrame
            indexed by solution ID, or any collection of IDs. ``None`` means
            there is no earlier snapshot, so every current ID counts as born.
        current: The later snapshot, in any of the same forms.

    Returns:
        dict: ``{"born": set, "died": set, "survived": set}`` of solution IDs.
    """
    before = _ids_of(previous)
    after = _ids_of(current)
    return {
        "born": after - before,
        "died": before - after,
        "survived": after & before,
    }
