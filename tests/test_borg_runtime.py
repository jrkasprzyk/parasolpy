"""
Tests for parasolpy.borg_runtime (Borg runtime file parsing and lifespans).

Uses small synthetic runtime files written to a temporary directory, plus
the two bundled samples in parasolpy/data/ (one per file layout).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from parasolpy.borg_runtime import (
    leaked_model_ids,
    parse_borg_runtime,
    parse_borg_runtime_columns,
    parse_borg_runtime_metadata,
    solution_lifespans,
)

REPO = Path(__file__).parent.parent
SAMPLES = REPO / "parasolpy" / "data"

# Older layout: data rows follow the "Archive size" line directly.
NO_HEADERS_FILE = SAMPLES / "RunTime_no-headers_NorthSouth.txt"
# Newer layout: a quoted column-header row precedes each snapshot's data rows.
WITH_HEADERS_FILE = SAMPLES / "RunTime_with-headers.txt"

SYNTHETIC_RUNTIME = """\
Function evaluations  100
Usage of recombination operators
  SBX   16.67%
  DE    16.67%
Improvements     10
Restarts         0
Population size  100
Archive size     2
5 1.5 2.5 0.10 0.20
20 1.0 3.0 0.30 0.40

Function evaluations  200
Usage of recombination operators
  SBX   50.00%
  DE    50.00%
Improvements     15
Restarts         1
Population size  100
Archive size     2
5 1.5 2.5 0.10 0.20
150 0.5 1.5 0.50 0.60

Function evaluations  300
Usage of recombination operators
  SBX   40.00%
  DE    60.00%
Improvements     22
Restarts         1
Population size  120
Archive size     2
150 0.5 1.5 0.50 0.60
250 0.4 1.0 0.70 0.80
"""

# Same run in the newer layout: a quoted column-header row (names contain
# spaces) sits between the snapshot header block and the data rows.
SYNTHETIC_RUNTIME_WITH_HEADERS = """\
Function evaluations  100
Usage of recombination operators
  SBX   16.67%
  DE    16.67%
Improvements     10
Restarts         0
Population size  100
Archive size     2

"Solution ID" "Flood Level" "Min Level" "Vol Rel" "Flood Damage"
5 1.5 2.5 0.10 0.20
20 1.0 3.0 0.30 0.40

Function evaluations  200
Usage of recombination operators
  SBX   50.00%
  DE    50.00%
Improvements     15
Restarts         1
Population size  100
Archive size     2

"Solution ID" "Flood Level" "Min Level" "Vol Rel" "Flood Damage"
5 1.5 2.5 0.10 0.20
150 0.5 1.5 0.50 0.60
"""


class TestBorgRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.runtime_path = Path(cls.tmpdir.name) / "runtime.txt"
        cls.runtime_path.write_text(SYNTHETIC_RUNTIME)
        cls.snapshots = parse_borg_runtime(cls.runtime_path)
        cls.spans = solution_lifespans(cls.snapshots)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_snapshot_count_and_nfes(self):
        self.assertEqual([nfe for nfe, _ in self.snapshots], [100, 200, 300])

    def test_snapshot_ids(self):
        self.assertEqual(self.snapshots[0][1], {5, 20})
        self.assertEqual(self.snapshots[1][1], {5, 150})
        self.assertEqual(self.snapshots[2][1], {150, 250})

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            parse_borg_runtime(Path(self.tmpdir.name) / "nope.txt")

    def test_empty_file_raises(self):
        empty = Path(self.tmpdir.name) / "empty.txt"
        empty.write_text("no snapshots here\n")
        with self.assertRaises(ValueError):
            parse_borg_runtime(empty)

    def test_lifespan_birth_equals_id(self):
        self.assertTrue((self.spans["birth"] == self.spans.index).all())

    def test_lifespan_death_convention(self):
        # removed solutions die at the next snapshot after last sighting
        self.assertEqual(self.spans.loc[20, "death"], 200)
        self.assertEqual(self.spans.loc[5, "death"], 300)
        # survivors die at the final NFE
        self.assertEqual(self.spans.loc[150, "death"], 300)
        self.assertEqual(self.spans.loc[250, "death"], 300)

    def test_final_archive_flags(self):
        self.assertEqual(
            self.spans["in_final_archive"].to_dict(),
            {5: False, 20: False, 150: True, 250: True},
        )

    def test_metadata(self):
        meta = parse_borg_runtime_metadata(self.runtime_path)
        self.assertEqual(list(meta.index), [100, 200, 300])
        self.assertEqual(list(meta["improvements"]), [10, 15, 22])
        self.assertEqual(list(meta["restarts"]), [0, 1, 1])
        self.assertEqual(list(meta["population_size"]), [100, 100, 120])
        self.assertEqual(list(meta["archive_size"]), [2, 2, 2])

    def test_leaked_model_ids(self):
        models = Path(self.tmpdir.name) / "SolutionModels"
        models.mkdir(exist_ok=True)
        for sol_id in (5, 175, 250):
            (models / f"Solution{sol_id}.mdl").write_text("model")
        # 5 and 250 appear in snapshots; 175 never does
        self.assertEqual(leaked_model_ids(models, self.spans), [175])

    def test_leaked_missing_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            leaked_model_ids(Path(self.tmpdir.name) / "no_dir", self.spans)


class TestColumnHeaders(unittest.TestCase):
    """Both runtime layouts parse, and the flag asserts which one is expected."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.with_headers = Path(cls.tmpdir.name) / "runtime_headers.txt"
        cls.with_headers.write_text(SYNTHETIC_RUNTIME_WITH_HEADERS)
        cls.no_headers = Path(cls.tmpdir.name) / "runtime_plain.txt"
        cls.no_headers.write_text(SYNTHETIC_RUNTIME)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def test_header_row_is_not_parsed_as_a_solution(self):
        snapshots = parse_borg_runtime(self.with_headers)
        self.assertEqual([nfe for nfe, _ in snapshots], [100, 200])
        self.assertEqual(snapshots[0][1], {5, 20})
        self.assertEqual(snapshots[1][1], {5, 150})

    def test_metadata_unaffected_by_header_row(self):
        meta = parse_borg_runtime_metadata(self.with_headers)
        self.assertEqual(list(meta.index), [100, 200])
        self.assertEqual(list(meta["archive_size"]), [2, 2])

    def test_columns_keep_quoted_names_with_spaces(self):
        self.assertEqual(
            parse_borg_runtime_columns(self.with_headers),
            ["Solution ID", "Flood Level", "Min Level", "Vol Rel",
             "Flood Damage"],
        )

    def test_columns_none_without_header_row(self):
        self.assertIsNone(parse_borg_runtime_columns(self.no_headers))

    def test_has_headers_true_matches_layout(self):
        snapshots = parse_borg_runtime(self.with_headers, has_headers=True)
        self.assertEqual(len(snapshots), 2)

    def test_has_headers_false_matches_layout(self):
        snapshots = parse_borg_runtime(self.no_headers, has_headers=False)
        self.assertEqual(len(snapshots), 3)

    def test_has_headers_true_on_plain_file_raises(self):
        with self.assertRaises(ValueError):
            parse_borg_runtime(self.no_headers, has_headers=True)
        with self.assertRaises(ValueError):
            parse_borg_runtime_metadata(self.no_headers, has_headers=True)

    def test_has_headers_false_on_header_file_raises(self):
        with self.assertRaises(ValueError):
            parse_borg_runtime(self.with_headers, has_headers=False)
        with self.assertRaises(ValueError):
            parse_borg_runtime_metadata(self.with_headers, has_headers=False)

    def test_operator_lines_are_not_mistaken_for_headers(self):
        # "  SBX   16.67%" also fails the integer-first test, so it must be
        # excluded explicitly or the plain layout would look header-bearing.
        self.assertIsNone(parse_borg_runtime_columns(self.no_headers))


class TestBundledSamples(unittest.TestCase):
    """Smoke-test the two bundled runtime files, one per layout."""

    def test_no_headers_sample(self):
        snapshots = parse_borg_runtime(NO_HEADERS_FILE, has_headers=False)
        meta = parse_borg_runtime_metadata(NO_HEADERS_FILE)
        self.assertEqual(len(snapshots), len(meta))
        self.assertIsNone(parse_borg_runtime_columns(NO_HEADERS_FILE))
        # archive sizes reported in the header block match the rows parsed
        sizes = [len(ids) for _, ids in snapshots]
        self.assertEqual(sizes, list(meta["archive_size"]))

    def test_with_headers_sample(self):
        snapshots = parse_borg_runtime(WITH_HEADERS_FILE, has_headers=True)
        meta = parse_borg_runtime_metadata(WITH_HEADERS_FILE)
        self.assertEqual(len(snapshots), len(meta))
        sizes = [len(ids) for _, ids in snapshots]
        self.assertEqual(sizes, list(meta["archive_size"]))

        columns = parse_borg_runtime_columns(WITH_HEADERS_FILE)
        self.assertEqual(columns[0], "Solution ID")
        self.assertIn("Cora Min Level", columns)
        # one name per field in a data row
        self.assertEqual(len(columns), 19)


if __name__ == "__main__":
    unittest.main()
