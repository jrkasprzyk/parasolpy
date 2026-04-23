"""Tests for package-level metadata and help() interface."""

import parasolpy


def test_version_string_present():
    assert isinstance(parasolpy.__version__, str)
    assert len(parasolpy.__version__) > 0


def test_help_string_present():
    assert isinstance(parasolpy.__help__, str)
    assert "parasolpy" in parasolpy.__help__


def test_help_callable(capsys):
    parasolpy.help()
    captured = capsys.readouterr()
    assert "parasolpy" in captured.out


def test_all_exports_importable():
    for name in parasolpy.__all__:
        assert hasattr(parasolpy, name), f"parasolpy.{name} not found"


def test_version_in_all():
    assert "__version__" in parasolpy.__all__


def test_help_in_all():
    assert "help" in parasolpy.__all__
    assert "__help__" in parasolpy.__all__
