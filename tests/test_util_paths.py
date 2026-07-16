"""Tests for script_local_path and ensure_dir path helpers."""

import pytest
from pathlib import Path

from parasolpy.util import ensure_dir, script_local_path


class TestScriptLocalPath:
    def test_simple_filename_resolves_relative_to_caller(self, tmp_path):
        """A plain filename should resolve relative to the given caller_file."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()
        data_file = tmp_path / "data.csv"
        data_file.touch()

        result = script_local_path("data.csv", caller_file=str(fake_script))
        assert result == tmp_path / "data.csv"

    def test_forward_slash_subdirectory(self, tmp_path):
        """Forward-slash paths should resolve into subdirectories."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()
        subdir = tmp_path / "inputs"
        subdir.mkdir()
        data_file = subdir / "input.csv"
        data_file.touch()

        result = script_local_path("inputs/input.csv", caller_file=str(fake_script))
        assert result == subdir / "input.csv"

    def test_backslash_path_treated_as_subdirectory(self, tmp_path):
        """Backslash-separated paths should work the same as forward slashes."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()
        subdir = tmp_path / "inputs"
        subdir.mkdir()
        data_file = subdir / "input.csv"
        data_file.touch()

        result = script_local_path("inputs\\input.csv", caller_file=str(fake_script))
        assert result == subdir / "input.csv"

    def test_absolute_path_returned_as_is(self, tmp_path):
        """An absolute path should be returned unchanged."""
        abs_file = tmp_path / "absolute.csv"
        abs_file.touch()

        result = script_local_path(str(abs_file), must_exist=True)
        assert result == abs_file

    def test_must_exist_false_does_not_raise(self, tmp_path):
        """must_exist=False should not raise even when the file is missing."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()

        result = script_local_path("nonexistent.csv", must_exist=False, caller_file=str(fake_script))
        assert result == tmp_path / "nonexistent.csv"

    def test_must_exist_true_raises_when_missing(self, tmp_path):
        """must_exist=True (default) should raise FileNotFoundError for missing files."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()

        with pytest.raises(FileNotFoundError):
            script_local_path("nonexistent.csv", must_exist=True, caller_file=str(fake_script))

    def test_pathlike_input_accepted(self, tmp_path):
        """A Path object should be accepted as the filename argument."""
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()
        data_file = tmp_path / "data.csv"
        data_file.touch()

        result = script_local_path(Path("data.csv"), caller_file=str(fake_script))
        assert result == tmp_path / "data.csv"

    def test_rejects_non_path_type(self):
        with pytest.raises(TypeError):
            script_local_path(123)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            script_local_path("   ")

    def test_rejects_non_bool_must_exist(self, tmp_path):
        fake_script = tmp_path / "myscript.py"
        fake_script.touch()
        with pytest.raises(TypeError):
            script_local_path("data.csv", must_exist="yes", caller_file=str(fake_script))


class TestEnsureDir:
    def test_creates_new_directory(self, tmp_path):
        new_dir = tmp_path / "outputs"
        result = ensure_dir(new_dir)
        assert result.is_dir()
        assert result == new_dir

    def test_creates_nested_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        result = ensure_dir(nested)
        assert result.is_dir()

    def test_existing_directory_does_not_raise(self, tmp_path):
        result = ensure_dir(tmp_path)
        assert result == tmp_path

    def test_returns_path_object(self, tmp_path):
        result = ensure_dir(tmp_path / "new")
        assert isinstance(result, Path)

    def test_accepts_string(self, tmp_path):
        new_dir = str(tmp_path / "string_dir")
        result = ensure_dir(new_dir)
        assert result.is_dir()

    def test_rejects_non_path_type(self):
        with pytest.raises(TypeError):
            ensure_dir(42)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            ensure_dir("  ")
