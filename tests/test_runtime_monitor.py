"""
Tests for the live-runtime layer: value-preserving snapshot parsing
(parasolpy.borg_runtime), incremental tailing and leaderboard state
(parasolpy.runtime_monitor), and the dashboard's render step
(parasolpy.runtime_dashboard).

The tailing tests write a runtime file in small, deliberately misaligned
chunks so that reads land in the middle of a line and in the middle of a
snapshot, which is the situation a live Borg run creates.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from parasolpy.borg_runtime import (
    Snapshot,
    parse_borg_runtime_snapshots,
    snapshot_delta,
)
from parasolpy.runtime_dashboard import build_monitor, render, resolve_sort_column
from parasolpy.runtime_monitor import (
    SORT_AGE,
    SORT_ID,
    STATUS_BORN,
    STATUS_DIED,
    STATUS_DOWN,
    STATUS_HELD,
    STATUS_UP,
    LeaderboardState,
    ReplaySource,
    RuntimeTail,
)

REPO = Path(__file__).parent.parent
SAMPLES = REPO / "parasolpy" / "data"
NO_HEADERS_FILE = SAMPLES / "RunTime_no-headers_NorthSouth.txt"
WITH_HEADERS_FILE = SAMPLES / "RunTime_with-headers.txt"


def _snapshot_text(nfe, rows, archive_size=None, header=None):
    """Render one snapshot block in Borg's runtime layout."""
    size = len(rows) if archive_size is None else archive_size
    lines = [
        f"Function evaluations  {nfe}",
        "Usage of recombination operators",
        "  SBX   50.00%",
        "  DE    50.00%",
        "Improvements     7",
        "Restarts         0",
        "Population size  10",
        f"Archive size     {size}",
    ]
    if header:
        lines.append(" ".join(f'"{name}"' for name in header))
    lines += [" ".join(str(value) for value in row) for row in rows]
    return "\n".join(lines) + "\n\n"


# Three snapshots: solution 5 survives throughout, 20 dies, 150 is born and
# then dies, and 300 is born at the end.
SYNTHETIC = (
    _snapshot_text(100, [(5, 1.5, 2.5), (20, 1.0, 3.0)])
    + _snapshot_text(200, [(5, 1.5, 2.5), (150, 0.5, 1.5)])
    + _snapshot_text(300, [(5, 1.5, 2.5), (300, 0.1, 0.9)])
)


class TestParseSnapshots(unittest.TestCase):
    """parse_borg_runtime_snapshots keeps the data values, not just the IDs."""

    def test_named_columns_from_header_row(self):
        snapshots = parse_borg_runtime_snapshots(WITH_HEADERS_FILE)
        self.assertTrue(all(isinstance(s, Snapshot) for s in snapshots))
        first = snapshots[0]
        self.assertEqual(first.nfe, 16)
        self.assertIn("Cora Avg Storage", first.frame.columns)
        self.assertEqual(first.frame.index.tolist(), [13])
        self.assertAlmostEqual(first.frame.loc[13, "Cora Avg Storage"], 8915.71, places=2)

    def test_unnamed_columns_get_positional_names(self):
        snapshots = parse_borg_runtime_snapshots(NO_HEADERS_FILE)
        self.assertEqual(snapshots[0].frame.columns[0], "col_1")
        self.assertEqual(len(snapshots[0].frame), snapshots[0].metadata["archive_size"])

    def test_columns_override_names_unnamed_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.txt"
            path.write_text(SYNTHETIC)
            snapshots = parse_borg_runtime_snapshots(path, columns=["cost", "reliability"])
        self.assertEqual(list(snapshots[0].frame.columns), ["cost", "reliability"])
        self.assertAlmostEqual(snapshots[0].frame.loc[20, "reliability"], 3.0)

    def test_ids_match_the_id_only_parser(self):
        from parasolpy.borg_runtime import parse_borg_runtime

        pairs = parse_borg_runtime(NO_HEADERS_FILE)
        snapshots = parse_borg_runtime_snapshots(NO_HEADERS_FILE)
        self.assertEqual(len(pairs), len(snapshots))
        for (nfe, ids), snapshot in zip(pairs, snapshots):
            self.assertEqual(nfe, snapshot.nfe)
            self.assertEqual(ids, snapshot.ids)

    def test_empty_archive_snapshot_is_emitted(self):
        text = _snapshot_text(50, [], archive_size=0) + _snapshot_text(60, [(1, 2.0)])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.txt"
            path.write_text(text)
            snapshots = parse_borg_runtime_snapshots(path)
        self.assertEqual([s.nfe for s in snapshots], [50, 60])
        self.assertTrue(snapshots[0].frame.empty)


class TestSnapshotDelta(unittest.TestCase):
    """snapshot_delta reports births, deaths and survivors between snapshots."""

    def test_delta_between_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.txt"
            path.write_text(SYNTHETIC)
            first, second, _ = parse_borg_runtime_snapshots(path)
        delta = snapshot_delta(first, second)
        self.assertEqual(delta["born"], {150})
        self.assertEqual(delta["died"], {20})
        self.assertEqual(delta["survived"], {5})

    def test_none_previous_makes_everything_born(self):
        delta = snapshot_delta(None, {1, 2})
        self.assertEqual(delta["born"], {1, 2})
        self.assertEqual(delta["died"], set())


class TestRuntimeTail(unittest.TestCase):
    """RuntimeTail follows a file that is still being written."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "runtime.txt"

    def tearDown(self):
        self._tmp.cleanup()

    def _write_in_chunks(self, tail, text, size=29):
        """Append ``text`` in small chunks, polling after each one."""
        collected = []
        for start in range(0, len(text), size):
            with open(self.path, "a") as handle:
                handle.write(text[start:start + size])
            collected.extend(tail.poll())
        return collected

    def test_missing_file_polls_empty(self):
        tail = RuntimeTail(self.path)
        self.assertEqual(tail.poll(), [])

    def test_chunked_writes_yield_whole_snapshots(self):
        self.path.write_text("")
        tail = RuntimeTail(self.path)
        snapshots = self._write_in_chunks(tail, SYNTHETIC)
        self.assertEqual([s.nfe for s in snapshots], [100, 200, 300])
        self.assertEqual([len(s.frame) for s in snapshots], [2, 2, 2])

    def test_partial_snapshot_is_not_emitted(self):
        self.path.write_text("")
        tail = RuntimeTail(self.path)
        # Everything up to the first snapshot's final data row.
        first_block = SYNTHETIC.split("\n\n")[0]
        cut = first_block.rfind("\n")
        self.path.write_text(first_block[:cut])
        self.assertEqual(tail.poll(), [])
        # Completing the row completes the snapshot.
        with open(self.path, "a") as handle:
            handle.write(first_block[cut:] + "\n")
        self.assertEqual([s.nfe for s in tail.poll()], [100])

    def test_only_new_bytes_are_reparsed(self):
        self.path.write_text(SYNTHETIC)
        tail = RuntimeTail(self.path)
        self.assertEqual(len(tail.poll()), 3)
        self.assertEqual(tail.poll(), [])
        with open(self.path, "a") as handle:
            handle.write(_snapshot_text(400, [(5, 1.5, 2.5)]))
        self.assertEqual([s.nfe for s in tail.poll()], [400])

    def test_truncation_restarts_the_reader(self):
        self.path.write_text(SYNTHETIC)
        tail = RuntimeTail(self.path)
        tail.poll()
        self.path.write_text(_snapshot_text(100, [(7, 9.0, 9.0)]))
        snapshots = tail.poll()
        self.assertTrue(tail.restarted)
        self.assertEqual([s.nfe for s in snapshots], [100])
        self.assertEqual(snapshots[0].frame.index.tolist(), [7])

    def test_columns_read_from_header_row(self):
        text = _snapshot_text(10, [(1, 2.0, 3.0)], header=["Solution ID", "Net Cost", "Rel"])
        self.path.write_text(text)
        tail = RuntimeTail(self.path)
        tail.poll()
        self.assertEqual(tail.columns, ["Net Cost", "Rel"])


class TestLeaderboardState(unittest.TestCase):
    """LeaderboardState turns snapshots into sorted, annotated rows."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "runtime.txt"
        path.write_text(SYNTHETIC)
        self.snapshots = parse_borg_runtime_snapshots(path, columns=["cost", "rel"])

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_snapshot_is_all_born(self):
        board = LeaderboardState()
        board.update(self.snapshots[0])
        self.assertEqual({row["status"] for row in board.rows()}, {STATUS_BORN})
        self.assertEqual(board.total_born, 2)

    def test_sorting_by_column(self):
        board = LeaderboardState(sort_column="cost", ascending=True)
        board.update(self.snapshots[0])
        rows = board.rows()
        self.assertEqual([row["id"] for row in rows], [20, 5])  # cost 1.0 then 1.5
        board.set_sorting("cost", ascending=False)
        self.assertEqual([row["id"] for row in board.rows()], [5, 20])

    def test_default_sort_is_oldest_first(self):
        board = LeaderboardState()
        board.update(self.snapshots[1])
        self.assertEqual([row["id"] for row in board.rows()], [5, 150])

    def test_sort_by_id_respects_direction(self):
        board = LeaderboardState(sort_column=SORT_ID, ascending=False)
        board.update(self.snapshots[1])
        self.assertEqual([row["id"] for row in board.rows()], [150, 5])

    def test_sort_by_age_is_the_inverse_of_id(self):
        # Age is nfe - id within a snapshot, so ascending age (youngest
        # first) must give the same order as descending ID.
        by_age = LeaderboardState(sort_column=SORT_AGE, ascending=True)
        by_id = LeaderboardState(sort_column=SORT_ID, ascending=False)
        by_age.update(self.snapshots[1])
        by_id.update(self.snapshots[1])
        self.assertEqual([row["id"] for row in by_age.rows()], [150, 5])
        self.assertEqual([row["id"] for row in by_age.rows()],
                         [row["id"] for row in by_id.rows()])
        # ...and oldest-first age matches ascending ID.
        by_age.set_sorting(SORT_AGE, ascending=False)
        self.assertEqual([row["id"] for row in by_age.rows()], [5, 150])

    def test_unknown_sort_column_falls_back_to_id(self):
        board = LeaderboardState(sort_column="not-a-column")
        board.update(self.snapshots[1])
        self.assertEqual([row["id"] for row in board.rows()], [5, 150])

    def test_age_is_nfe_minus_id(self):
        board = LeaderboardState()
        board.update(self.snapshots[1])
        ages = {row["id"]: row["age"] for row in board.rows()}
        self.assertEqual(ages[5], 195)
        self.assertEqual(ages[150], 50)

    def test_dead_solution_lingers_as_a_ghost(self):
        board = LeaderboardState(ghost_snapshots=1)
        board.update(self.snapshots[0])
        board.update(self.snapshots[1])
        ghosts = [row for row in board.rows() if row["status"] == STATUS_DIED]
        self.assertEqual([row["id"] for row in ghosts], [20])
        self.assertEqual(ghosts[0]["position"], "—")
        # One more snapshot and the ghost has aged out.
        board.update(self.snapshots[2])
        self.assertEqual([row["id"] for row in board.rows() if row["status"] == STATUS_DIED], [150])

    def test_ghosts_can_be_disabled(self):
        board = LeaderboardState(ghost_snapshots=0)
        board.update(self.snapshots[0])
        board.update(self.snapshots[1])
        self.assertEqual([row["status"] for row in board.rows() if row["status"] == STATUS_DIED], [])

    def test_movement_through_the_sort_order_is_reported(self):
        # Two solutions that swap places: 1 improves past 2 without either
        # entering or leaving the archive.
        text = (
            _snapshot_text(10, [(1, 3.0, 0.0), (2, 1.0, 0.0)])
            + _snapshot_text(20, [(1, 0.5, 0.0), (2, 1.0, 0.0)])
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.txt"
            path.write_text(text)
            first, second = parse_borg_runtime_snapshots(path, columns=["cost", "rel"])

        board = LeaderboardState(sort_column="cost", ascending=True)
        board.update(first)
        self.assertEqual([row["id"] for row in board.rows()], [2, 1])
        board.update(second)
        moves = {row["id"]: (row["status"], row["move"]) for row in board.rows()}
        self.assertEqual(moves[1], (STATUS_UP, 1))
        self.assertEqual(moves[2], (STATUS_DOWN, 1))

    def test_survivor_that_does_not_move_is_held(self):
        board = LeaderboardState(sort_column="cost", ascending=True)
        board.update(self.snapshots[0])   # 20 (1.0) first, 5 (1.5) second
        board.update(self.snapshots[1])   # 20 dies, 150 (0.5) leads, 5 still second
        moves = {row["id"]: (row["status"], row["move"]) for row in board.rows()}
        self.assertEqual(moves[5], (STATUS_HELD, 0))
        self.assertEqual(moves[150][0], STATUS_BORN)

    def test_history_frame_tracks_churn(self):
        board = LeaderboardState()
        for snapshot in self.snapshots:
            board.update(snapshot)
        history = board.history_frame()
        self.assertEqual(history["nfe"].tolist(), [100, 200, 300])
        self.assertEqual(history["born"].tolist(), [2, 1, 1])
        self.assertEqual(history["died"].tolist(), [0, 1, 1])

    def test_reset_clears_state(self):
        board = LeaderboardState()
        board.update(self.snapshots[0])
        board.reset()
        self.assertIsNone(board.nfe)
        self.assertEqual(board.rows(), [])
        self.assertEqual(board.total_born, 0)


class TestReplaySource(unittest.TestCase):
    """ReplaySource serves a finished file through the tail interface."""

    def test_one_snapshot_per_poll_then_exhausted(self):
        source = ReplaySource(WITH_HEADERS_FILE)
        nfes = []
        while not source.exhausted:
            nfes.extend(s.nfe for s in source.poll())
        self.assertEqual(nfes, [s.nfe for s in parse_borg_runtime_snapshots(WITH_HEADERS_FILE)])
        self.assertEqual(source.poll(), [])

    def test_speed_and_loop(self):
        total = len(parse_borg_runtime_snapshots(WITH_HEADERS_FILE))
        source = ReplaySource(WITH_HEADERS_FILE, snapshots_per_poll=5, loop=True)
        served = len(source.poll())
        self.assertEqual(served, 5)
        # Poll until the file is used up; the next poll wraps and says so.
        while served < total:
            served += len(source.poll())
            self.assertFalse(source.restarted)
        source.poll()
        self.assertTrue(source.restarted)


class TestDashboardRender(unittest.TestCase):
    """The dashboard's render step, exercised without a browser."""

    def test_render_produces_rows_and_figure(self):
        monitor = build_monitor(WITH_HEADERS_FILE, replay=True, snapshots_per_poll=8)
        rows, columns, tiles, figure, state = render(monitor)
        self.assertEqual(state, "live")
        self.assertTrue(rows)
        self.assertEqual(len(tiles), 8)
        self.assertEqual([trace.name for trace in figure.data],
                         ["archive size", "born", "died"])
        ids = [column["id"] for column in columns]
        self.assertEqual(ids[:5], ["position", "move_text", "status_label", "id", "age"])

    def test_sort_column_is_always_shown(self):
        monitor = build_monitor(WITH_HEADERS_FILE, replay=True, snapshots_per_poll=8)
        # A column late in the file, which the default column set omits.
        _, columns, _, _, _ = render(
            monitor, sort_column="Eco Vol Rel", value_columns=["Cora Avg Storage"]
        )
        self.assertEqual([column["id"] for column in columns][5], "Eco Vol Rel")

    def test_builtin_sort_keys_need_no_pinned_column(self):
        monitor = build_monitor(WITH_HEADERS_FILE, replay=True, snapshots_per_poll=8)
        _, columns, _, _, _ = render(
            monitor, sort_column=SORT_AGE, value_columns=["Cora Avg Storage"]
        )
        ids = [column["id"] for column in columns]
        self.assertEqual(ids, ["position", "move_text", "status_label", "id",
                               "age", "Cora Avg Storage"])

    def test_resolve_sort_column_aliases(self):
        self.assertEqual(resolve_sort_column(None), SORT_ID)
        self.assertEqual(resolve_sort_column("id"), SORT_ID)
        self.assertEqual(resolve_sort_column("Age"), SORT_AGE)
        self.assertEqual(resolve_sort_column("Cora Avg Storage"), "Cora Avg Storage")

    def test_paused_render_does_not_advance(self):
        monitor = build_monitor(WITH_HEADERS_FILE, replay=True)
        render(monitor)
        nfe = monitor.board.nfe
        render(monitor, paused=True)
        self.assertEqual(monitor.board.nfe, nfe)

    def test_waiting_state_before_first_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = build_monitor(Path(tmp) / "not-written-yet.txt")
            rows, _, _, _, state = render(monitor)
        self.assertEqual(rows, [])
        self.assertEqual(state, "waiting for first snapshot")

    def test_tail_restart_resets_the_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.txt"
            path.write_text(SYNTHETIC)
            monitor = build_monitor(path)
            render(monitor)
            self.assertEqual(monitor.board.snapshot_count, 3)
            path.write_text(_snapshot_text(100, [(7, 9.0, 9.0)]))
            render(monitor)
        self.assertEqual(monitor.restarts_seen, 1)
        self.assertEqual(monitor.board.snapshot_count, 1)


if __name__ == "__main__":
    unittest.main()
