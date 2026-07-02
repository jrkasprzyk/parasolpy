"""
Tests for parasolpy.borg_runtime (Borg runtime file parsing and lifespans).

Uses a small synthetic runtime file written to a temporary directory.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from parasolpy.borg_runtime import (
    leaked_model_ids,
    parse_borg_runtime,
    parse_borg_runtime_metadata,
    solution_lifespans,
)

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


if __name__ == "__main__":
    unittest.main()
