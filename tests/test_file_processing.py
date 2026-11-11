import pandas as pd
import pytest

from parasolpy.file_processing import (
    convert_solutions_csv_to_single_header,
    has_superheader,
    load_solutions_dataframe,
    split_solutions_csv,
    split_solutions_dataframe,
)

SUPERHEADER_CSV = (
    ",Decision Variables,,Objectives,\n"
    "Solution,x1,x2,cost,reliability\n"
    "1,0.1,0.2,10,0.9\n"
    "2,0.3,0.4,20,0.8\n"
)

PLAIN_CSV = (
    "Solution,x1,x2,cost,reliability\n"
    "1,0.1,0.2,10,0.9\n"
    "2,0.3,0.4,20,0.8\n"
)


@pytest.fixture
def superheader_csv(tmp_path):
    path = tmp_path / "solutions.csv"
    path.write_text(SUPERHEADER_CSV, encoding="utf-8")
    return path


@pytest.fixture
def plain_csv(tmp_path):
    path = tmp_path / "plain.csv"
    path.write_text(PLAIN_CSV, encoding="utf-8")
    return path


# --- has_superheader ---------------------------------------------------------

def test_has_superheader_detects_grouped_header(superheader_csv):
    assert has_superheader(superheader_csv) is True


def test_has_superheader_false_for_plain_csv(plain_csv):
    assert has_superheader(plain_csv) is False


def test_has_superheader_handles_utf8_bom(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_text(SUPERHEADER_CSV, encoding="utf-8-sig")
    assert has_superheader(path) is True


def test_has_superheader_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        has_superheader(tmp_path / "nope.csv")


# --- load_solutions_dataframe ------------------------------------------------

def test_load_superheader_flattens_columns_and_groups(superheader_csv):
    df, meta = load_solutions_dataframe(superheader_csv, return_metadata=True)

    assert list(df.columns) == ["Solution", "x1", "x2", "cost", "reliability"]
    assert len(df) == 2
    assert meta["has_superheader"] is True
    assert meta["groups_to_columns"] == {
        "Decision Variables": ["x1", "x2"],
        "Objectives": ["cost", "reliability"],
    }
    assert meta["column_to_group"]["Solution"] is None


def test_load_plain_csv_has_no_groups(plain_csv):
    df, meta = load_solutions_dataframe(plain_csv, return_metadata=True)

    assert list(df.columns) == ["Solution", "x1", "x2", "cost", "reliability"]
    assert meta["has_superheader"] is False
    assert meta["groups_to_columns"] == {}


def test_load_forced_superheader_no_reads_first_row_as_header(superheader_csv):
    df = load_solutions_dataframe(superheader_csv, superheader="no")
    # Row 2 of the file (the real column names) becomes data.
    assert len(df) == 3


def test_load_rejects_bad_superheader_arg(plain_csv):
    with pytest.raises(ValueError, match="superheader"):
        load_solutions_dataframe(plain_csv, superheader="maybe")


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_solutions_dataframe(tmp_path / "nope.csv")


def test_load_header_only_file_raises(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("Solution,x1,cost\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        load_solutions_dataframe(path)


# --- split_solutions_dataframe -----------------------------------------------

def test_split_uses_metadata_groups_and_keeps_id(superheader_csv):
    df, meta = load_solutions_dataframe(superheader_csv, return_metadata=True)
    out = split_solutions_dataframe(df, metadata=meta)

    assert list(out["decisions"].columns) == ["Solution", "x1", "x2"]
    assert list(out["objectives"].columns) == ["Solution", "cost", "reliability"]
    assert out["decisions"]["x2"].tolist() == [0.2, 0.4]
    assert out["objectives"]["cost"].tolist() == [10, 20]


def test_split_explicit_columns_without_ids(plain_csv):
    df = load_solutions_dataframe(plain_csv)
    out = split_solutions_dataframe(
        df,
        decision_columns=["x1"],
        objective_columns=["cost"],
        include_id_columns=False,
    )

    assert list(out["decisions"].columns) == ["x1"]
    assert list(out["objectives"].columns) == ["cost"]


def test_split_returns_copies(plain_csv):
    df = load_solutions_dataframe(plain_csv)
    out = split_solutions_dataframe(df, decision_columns=["x1"], objective_columns=["cost"])
    out["decisions"]["x1"] = -1
    assert df["x1"].tolist() == [0.1, 0.3]


def test_split_without_groups_or_columns_raises(plain_csv):
    df = load_solutions_dataframe(plain_csv)
    with pytest.raises(ValueError, match="Could not infer"):
        split_solutions_dataframe(df)


def test_split_missing_column_raises(plain_csv):
    df = load_solutions_dataframe(plain_csv)
    with pytest.raises(ValueError, match="Objective columns missing"):
        split_solutions_dataframe(df, decision_columns=["x1"], objective_columns=["nope"])


def test_split_rejects_non_list_columns(plain_csv):
    df = load_solutions_dataframe(plain_csv)
    with pytest.raises(TypeError, match="decision_columns"):
        split_solutions_dataframe(df, decision_columns="x1")


def test_split_rejects_non_dataframe():
    with pytest.raises(TypeError, match="DataFrame"):
        split_solutions_dataframe([1, 2, 3])


# --- file-writing wrappers ---------------------------------------------------

def test_split_solutions_csv_writes_default_paths(superheader_csv):
    result = split_solutions_csv(superheader_csv)

    assert result["decisions_path"] == superheader_csv.with_name("solutions.decisions.csv")
    assert result["objectives_path"] == superheader_csv.with_name("solutions.objectives.csv")
    assert list(pd.read_csv(result["decisions_path"]).columns) == ["Solution", "x1", "x2"]
    assert list(pd.read_csv(result["objectives_path"]).columns) == ["Solution", "cost", "reliability"]


def test_convert_to_single_header_round_trips(superheader_csv):
    out_path = convert_solutions_csv_to_single_header(superheader_csv)

    assert out_path == superheader_csv.with_name("solutions.single_header.csv")
    assert has_superheader(out_path) is False
    df = pd.read_csv(out_path)
    assert list(df.columns) == ["Solution", "x1", "x2", "cost", "reliability"]
    assert len(df) == 2
