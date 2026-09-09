"""Live monitoring of a Borg MOEA runtime file while the run is in progress.

``parasolpy.borg_runtime`` parses a finished runtime file. This module adds
the two pieces needed to watch one that is still being written:

* :class:`RuntimeTail` reads only the bytes appended since the last poll and
  yields whole archive snapshots as they complete, so a dashboard polling
  every couple of seconds does not re-parse the file from the top.
* :class:`LeaderboardState` folds that stream of snapshots into a sorted
  table with per-solution status — born, survived (moved up or down the
  order), or died — which is what turns the archive into a live leaderboard
  rather than a plain dump of the current archive.

:class:`ReplaySource` exposes the same ``poll()`` interface over a finished
file, feeding one snapshot per call. It lets the dashboard be demonstrated,
and its behavior tested, without a live optimization running.

Solution IDs equal the NFE at which the solution was created, so a
solution's age is simply ``current_nfe - id``.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from parasolpy.borg_runtime import (
    _SnapshotAssembler,
    parse_borg_runtime_snapshots,
    snapshot_delta,
)

#: Sort keys that are not data columns. Solution ID and age are properties of
#: the snapshot rather than fields in the file, but they are the two orderings
#: most often wanted, so they are selectable alongside the data columns. The
#: values are deliberately unlikely to collide with a real column name.
SORT_ID = "__id__"
SORT_AGE = "__age__"

#: Status assigned to each leaderboard row by :class:`LeaderboardState`.
STATUS_BORN = "born"
STATUS_UP = "up"
STATUS_DOWN = "down"
STATUS_HELD = "held"
STATUS_DIED = "died"


class RuntimeTail:
    """Incrementally read completed archive snapshots from a growing file.

    Each :meth:`poll` reads only the bytes appended since the previous call.
    A snapshot is returned once its declared ``Archive size`` rows have all
    arrived, so a snapshot that is still being written is never emitted
    half-full. The file need not exist yet: polling a missing path returns
    no snapshots, which lets a dashboard be started before the run is.

    If the file shrinks between polls the run is assumed to have restarted
    and been rewritten, so all reader state is discarded and parsing begins
    again from the top.

    Args:
        path (str | PathLike): Path to the Borg runtime file to follow.
        columns (list of str, optional): Names for the data columns after the
            solution ID, for files whose layout carries no column-header row.
        encoding (str, optional): Text encoding of the runtime file.

    Example:
        >>> tail = RuntimeTail("output/runtime.txt")
        >>> new_snapshots = tail.poll()  # doctest: +SKIP
    """

    def __init__(self, path, columns=None, encoding="utf-8"):
        self.path = Path(path)
        self._columns = list(columns) if columns is not None else None
        self._encoding = encoding
        self.restarted = False
        self._reset()

    def _reset(self):
        self._offset = 0
        self._carry = ""
        self._assembler = _SnapshotAssembler(columns=self._columns)

    @property
    def columns(self):
        """list of str | None: Column names seen so far, if the file names them."""
        return self._assembler.columns

    def poll(self):
        """Read newly appended bytes and return any snapshots they completed.

        Returns:
            list of parasolpy.borg_runtime.Snapshot: Completed snapshots in
            file order; empty if nothing new completed since the last call.
        """
        self.restarted = False
        if not self.path.is_file():
            return []

        size = self.path.stat().st_size
        if size < self._offset:
            # The file was truncated or replaced: a new run is writing here.
            self._reset()
            self.restarted = True
        if size == self._offset:
            return []

        with open(self.path, "rb") as handle:
            handle.seek(self._offset)
            chunk = handle.read()
        self._offset += len(chunk)

        text = self._carry + chunk.decode(self._encoding, errors="replace")
        lines = text.split("\n")
        # The final element is whatever follows the last newline: either an
        # empty string, or a line the writer has not finished yet.
        self._carry = lines.pop()

        snapshots = []
        for line in lines:
            snapshot = self._assembler.feed(line)
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots


class ReplaySource:
    """Replay a finished runtime file one snapshot per :meth:`poll`.

    Provides the same interface as :class:`RuntimeTail` so the dashboard can
    be driven by a recorded run. Useful for demonstrations and for exercising
    the leaderboard without waiting on a live optimization.

    Args:
        path (str | PathLike): Path to a complete Borg runtime file.
        columns (list of str, optional): Names for the data columns after the
            solution ID, for files with no column-header row.
        snapshots_per_poll (int, optional): How many snapshots to advance on
            each poll. Raise it to replay a long run faster.
        loop (bool, optional): Restart from the first snapshot after the last
            one is served, reporting a restart as :class:`RuntimeTail` does.
    """

    def __init__(self, path, columns=None, snapshots_per_poll=1, loop=False):
        self.path = Path(path)
        self._snapshots = parse_borg_runtime_snapshots(self.path, columns=columns)
        self._per_poll = max(1, int(snapshots_per_poll))
        self._loop = loop
        self._cursor = 0
        self.restarted = False

    @property
    def columns(self):
        """list of str: Data column names of the replayed file."""
        return list(self._snapshots[0].frame.columns)

    @property
    def exhausted(self):
        """bool: True once every snapshot has been served and looping is off."""
        return not self._loop and self._cursor >= len(self._snapshots)

    def poll(self):
        """Return the next batch of snapshots, or an empty list when exhausted."""
        self.restarted = False
        if self._cursor >= len(self._snapshots):
            if not self._loop:
                return []
            self._cursor = 0
            self.restarted = True
        batch = self._snapshots[self._cursor:self._cursor + self._per_poll]
        self._cursor += len(batch)
        return batch


class LeaderboardState:
    """Fold a stream of archive snapshots into a sorted, annotated table.

    Archive members are sorted by a chosen key, and each row records how it
    moved in that order since the previous snapshot. Solutions removed from
    the archive are kept for a few further snapshots as "ghost" rows so a
    death is visible rather than a row that silently vanishes between two
    refreshes.

    The sort is an ordering, not a verdict: the column and direction are the
    caller's choice, and nothing here treats a solution near the top of the
    table as better than one near the bottom.

    Args:
        sort_column (str, optional): Data column to sort by, or
            :data:`SORT_ID` / :data:`SORT_AGE` to sort by solution ID or by
            age. ``None`` (default) is treated as :data:`SORT_ID`.
        ascending (bool, optional): Sort direction, smallest value first when
            ``True``.
        ghost_snapshots (int, optional): How many snapshots a dead solution
            stays visible. ``0`` removes dead rows immediately.
        history (int, optional): Maximum number of snapshots retained for the
            churn history returned by :meth:`history_frame`.

    Attributes:
        nfe (int | None): NFE of the most recent snapshot applied.
        metadata (dict): Header fields of the most recent snapshot.
        born (set of int): IDs that entered the archive at the last update.
        died (set of int): IDs that left the archive at the last update.
    """

    def __init__(self, sort_column=None, ascending=True, ghost_snapshots=2, history=500):
        self.sort_column = sort_column or SORT_ID
        self.ascending = ascending
        self.ghost_snapshots = max(0, int(ghost_snapshots))
        self.nfe = None
        self.metadata = {}
        self.born = set()
        self.died = set()
        self.total_born = 0
        self.total_died = 0
        self.snapshot_count = 0
        self.columns = []
        self._frame = None
        self._positions = {}
        self._previous_positions = {}
        self._ghosts = {}
        self._history = deque(maxlen=history)

    def reset(self):
        """Forget every snapshot seen so far, as after a run restart."""
        self.__init__(
            sort_column=self.sort_column,
            ascending=self.ascending,
            ghost_snapshots=self.ghost_snapshots,
            history=self._history.maxlen,
        )

    def set_sorting(self, sort_column=None, ascending=True):
        """Change the sort key, re-sorting the current archive in place.

        Movement arrows are measured against the new order from the next
        snapshot onward, so switching sort keys does not report a field-wide
        reshuffle as real movement.

        Args:
            sort_column (str, optional): Data column, :data:`SORT_ID`, or
                :data:`SORT_AGE`. ``None`` is treated as :data:`SORT_ID`.
            ascending (bool, optional): Sort direction.
        """
        self.sort_column = sort_column or SORT_ID
        self.ascending = ascending
        if self._frame is not None:
            self._positions = self._sort(self._frame)
            self._previous_positions = dict(self._positions)

    def update(self, snapshot):
        """Apply one snapshot, updating positions, statuses and ghost rows.

        Args:
            snapshot (parasolpy.borg_runtime.Snapshot): The newly completed
                archive snapshot.

        Returns:
            dict: The ``born``/``died``/``survived`` ID sets for this step,
            as returned by ``parasolpy.borg_runtime.snapshot_delta``.
        """
        delta = snapshot_delta(self._frame, snapshot.frame)
        previous_positions = self._positions

        # Age out existing ghosts before adding this snapshot's deaths, so a
        # ghost survives exactly ``ghost_snapshots`` further updates.
        for sol_id in list(self._ghosts):
            self._ghosts[sol_id]["ttl"] -= 1
            if self._ghosts[sol_id]["ttl"] <= 0:
                del self._ghosts[sol_id]

        if self.ghost_snapshots and self._frame is not None:
            for sol_id in delta["died"]:
                self._ghosts[sol_id] = {
                    "values": self._frame.loc[sol_id].to_dict(),
                    "position": previous_positions.get(sol_id),
                    "died_at": snapshot.nfe,
                    "ttl": self.ghost_snapshots,
                }
        # A solution that re-enters the archive is alive again, not a ghost.
        for sol_id in delta["born"]:
            self._ghosts.pop(sol_id, None)

        self._frame = snapshot.frame
        self._previous_positions = previous_positions
        # nfe first: the sort may depend on it.
        self.nfe = snapshot.nfe
        self._positions = self._sort(snapshot.frame)
        self.columns = list(snapshot.frame.columns)
        self.metadata = dict(snapshot.metadata)
        self.born = delta["born"]
        self.died = delta["died"]
        self.total_born += len(delta["born"])
        self.total_died += len(delta["died"])
        self.snapshot_count += 1
        self._history.append(
            {
                "nfe": snapshot.nfe,
                "archive_size": len(snapshot.frame),
                "born": len(delta["born"]),
                "died": len(delta["died"]),
                "improvements": snapshot.metadata.get("improvements"),
                "restarts": snapshot.metadata.get("restarts"),
            }
        )
        return delta

    def _sort(self, frame):
        """Return ``{solution_id: position}`` (1 = first row) for ``frame``.

        Ties keep their previous relative order (a stable sort), so a column
        that is constant across the archive gives a steady list rather than
        one that reshuffles every snapshot.
        """
        if frame is None or frame.empty:
            return {}
        column = self.sort_column
        if column == SORT_AGE:
            # Age is ``nfe - id`` and nfe is fixed within a snapshot, so
            # ordering by age is ordering by ID reversed.
            order = sorted(frame.index, reverse=self.ascending)
        elif column in (None, SORT_ID):
            order = sorted(frame.index, reverse=not self.ascending)
        elif column in frame.columns:
            order = frame[column].sort_values(
                ascending=self.ascending, kind="mergesort"
            ).index
        else:
            # A column this snapshot does not carry: fall back to ID order
            # rather than dropping the ordering entirely.
            order = sorted(frame.index)
        return {sol_id: position for position, sol_id in enumerate(order, start=1)}

    def rows(self):
        """Build the table rows in sort order, ghosts at the place they left.

        Returns:
            list of dict: One row per archive member plus one per lingering
            ghost. Keys are ``order``, ``position``, ``id``, ``status``,
            ``move``, ``age``, ``born_nfe``, plus one key per data column.
            ``position`` is the display string, ``order`` the numeric sort key.
        """
        if self._frame is None:
            return []

        previous = self._previous_positions
        rows = []
        for sol_id, position in sorted(self._positions.items(), key=lambda item: item[1]):
            was = previous.get(sol_id)
            if sol_id in self.born or was is None:
                status, move = STATUS_BORN, None
            elif was > position:
                status, move = STATUS_UP, was - position
            elif was < position:
                status, move = STATUS_DOWN, position - was
            else:
                status, move = STATUS_HELD, 0
            row = {
                "order": float(position),
                "position": str(position),
                "id": int(sol_id),
                "status": status,
                "move": move,
                "age": int(self.nfe - sol_id),
                "born_nfe": int(sol_id),
            }
            row.update(self._frame.loc[sol_id].to_dict())
            rows.append(row)

        for sol_id, ghost in self._ghosts.items():
            last_position = ghost["position"] or len(self._positions) + 1
            row = {
                # Place a ghost just below the row it last held, so the eye
                # finds it where the solution dropped out of the list.
                "order": float(last_position) + 0.5,
                "position": "—",
                "id": int(sol_id),
                "status": STATUS_DIED,
                "move": None,
                "age": int(ghost["died_at"] - sol_id),
                "born_nfe": int(sol_id),
            }
            row.update(ghost["values"])
            rows.append(row)

        rows.sort(key=lambda row: row["order"])
        return rows

    def history_frame(self):
        """Return the retained per-snapshot churn history as a DataFrame.

        Returns:
            pd.DataFrame: Columns ``nfe``, ``archive_size``, ``born``,
            ``died``, ``improvements`` and ``restarts``, one row per snapshot
            (most recent ``history`` snapshots only).
        """
        import pandas as pd

        return pd.DataFrame(list(self._history))
