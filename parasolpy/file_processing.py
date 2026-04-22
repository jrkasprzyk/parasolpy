"""File-processing helpers for Borg/RiverWare solution CSVs.

This module focuses on common post-processing tasks for solution files,
including:
1) Normalizing two-line "superheader" CSVs to single-header CSVs.
2) Splitting decision-variable and objective columns for downstream analysis.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


_DECISION_GROUP_NAMES = {
    "decision variables",
    "decision variable",
    "decisions",
}

_OBJECTIVE_GROUP_NAMES = {
    "objectives",
    "objective",
    "objective functions",
}


def _normalize_text(value):
    """Normalize header/group labels for case-insensitive matching."""
    if value is None:
        return ""
    return str(value).strip()


def _is_number(value):
    """Return True when a string can be parsed as a finite float."""
    text = _normalize_text(value)
    if not text:
        return False
    try:
        float(text)
        return True
    except ValueError:
        return False


def _row_is_mostly_numeric(row):
    """Heuristic check used to distinguish header rows from data rows."""
    cells = [_normalize_text(cell) for cell in row if _normalize_text(cell) != ""]
    if not cells:
        return False
    numeric_count = sum(_is_number(cell) for cell in cells)
    return numeric_count / len(cells) >= 0.8


def _read_first_rows(csv_path, n_rows=2):
    """Read the first N rows from a CSV with UTF-8 BOM compatibility."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = []
        for _ in range(n_rows):
            try:
                rows.append(next(reader))
            except StopIteration:
                break
    return rows


def has_superheader(csv_path):
    """Detect whether a solutions CSV likely uses a two-line superheader.

    A superheader file usually has grouped labels on row 1 (for example,
    "Decision Variables", "Objectives") and the actual column names on row 2.
    """
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    rows = _read_first_rows(path, n_rows=2)
    if len(rows) < 2:
        return False

    row1 = [_normalize_text(cell) for cell in rows[0]]
    row2 = [_normalize_text(cell) for cell in rows[1]]

    if _row_is_mostly_numeric(row2):
        return False

    group_label_set = {
        "decision variables",
        "objectives",
        "metrics",
    }
    has_known_group_label = any(cell.lower() in group_label_set for cell in row1)

    first_cell_blank = bool(row1) and row1[0] == ""
    has_any_group_text = any(cell != "" for cell in row1[1:])

    return has_known_group_label or (first_cell_blank and has_any_group_text)


def _flatten_columns_and_groups(columns):
    """Flatten MultiIndex columns and capture per-column group labels."""
    flattened = []
    column_to_group = {}
    used = {}
    current_group = None

    for idx, column in enumerate(columns):
        if isinstance(column, tuple):
            top = _normalize_text(column[0])
            bottom = _normalize_text(column[1])
            if top.lower().startswith("unnamed"):
                top = ""
            if bottom.lower().startswith("unnamed"):
                bottom = ""

            if top:
                current_group = top
            group = current_group

            name = bottom or top or f"column_{idx + 1}"
        else:
            name = _normalize_text(column) or f"column_{idx + 1}"
            group = None

        count = used.get(name, 0) + 1
        used[name] = count
        unique_name = name if count == 1 else f"{name}__{count}"

        flattened.append(unique_name)
        column_to_group[unique_name] = group

    return flattened, column_to_group


def load_solutions_dataframe(csv_path, superheader="auto", return_metadata=False):
    """Load a solution CSV and normalize headers for downstream processing.

    Args:
        csv_path: Path to the input CSV.
        superheader: One of "auto", "yes", "no".
        return_metadata: If True, also returns a metadata dict with grouped column info.

    Returns:
        DataFrame, or (DataFrame, metadata) when return_metadata is True.
    """
    path = Path(csv_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    if superheader not in {"auto", "yes", "no"}:
        raise ValueError("Input 'superheader' must be one of: 'auto', 'yes', 'no'.")

    if superheader == "auto":
        has_multi_header = has_superheader(path)
    else:
        has_multi_header = superheader == "yes"

    if has_multi_header:
        df = pd.read_csv(path, header=[0, 1])
    else:
        df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"Solutions file is empty: {path}")

    flat_columns, column_to_group = _flatten_columns_and_groups(df.columns)
    df.columns = flat_columns

    groups_to_columns = {}
    for column in df.columns:
        group = column_to_group[column]
        if group is None:
            continue
        groups_to_columns.setdefault(group, []).append(column)

    metadata = {
        "has_superheader": has_multi_header,
        "column_to_group": column_to_group,
        "groups_to_columns": groups_to_columns,
    }

    if return_metadata:
        return df, metadata
    return df


def convert_solutions_csv_to_single_header(input_csv, output_csv=None, superheader="auto", index=False):
    """Convert a solutions CSV to a normalized single-header CSV file.

    Args:
        input_csv: Source CSV path.
        output_csv: Destination path. If None, writes next to input using
            '<stem>.single_header.csv'.
        superheader: One of "auto", "yes", "no".
        index: Whether to write DataFrame index to output CSV.

    Returns:
        pathlib.Path to the written CSV.
    """
    input_path = Path(input_csv)
    if output_csv is None:
        output_path = input_path.with_name(f"{input_path.stem}.single_header.csv")
    else:
        output_path = Path(output_csv)

    solutions = load_solutions_dataframe(input_path, superheader=superheader, return_metadata=False)
    solutions.to_csv(output_path, index=index)
    return output_path


def split_solutions_dataframe(
    solutions,
    metadata=None,
    decision_columns=None,
    objective_columns=None,
    id_columns=("Solution", "Solution ID"),
    include_id_columns=True,
):
    """Split a solutions DataFrame into decision and objective DataFrames.

    Args:
        solutions: Input DataFrame.
        metadata: Metadata returned from load_solutions_dataframe(..., return_metadata=True).
            Used to auto-detect grouped columns from a superheader.
        decision_columns: Explicit decision-variable columns. If None, inferred from metadata.
        objective_columns: Explicit objective columns. If None, inferred from metadata.
        id_columns: Candidate ID columns to preserve in each output DataFrame.
        include_id_columns: Whether to keep detected ID columns in outputs.

    Returns:
        dict with keys 'decisions', 'objectives', 'decision_columns', 'objective_columns'.
    """
    if not isinstance(solutions, pd.DataFrame):
        raise TypeError("Input 'solutions' must be a pandas DataFrame.")

    if decision_columns is not None:
        if not isinstance(decision_columns, list) or not all(isinstance(c, str) for c in decision_columns):
            raise TypeError("Input 'decision_columns' must be a list of strings or None.")
    if objective_columns is not None:
        if not isinstance(objective_columns, list) or not all(isinstance(c, str) for c in objective_columns):
            raise TypeError("Input 'objective_columns' must be a list of strings or None.")

    if decision_columns is None or objective_columns is None:
        groups_to_columns = {}
        if metadata is not None:
            groups_to_columns = metadata.get("groups_to_columns", {})

        if decision_columns is None:
            decision_columns = []
            for group, cols in groups_to_columns.items():
                if _normalize_text(group).lower() in _DECISION_GROUP_NAMES:
                    decision_columns.extend(cols)

        if objective_columns is None:
            objective_columns = []
            for group, cols in groups_to_columns.items():
                if _normalize_text(group).lower() in _OBJECTIVE_GROUP_NAMES:
                    objective_columns.extend(cols)

    missing_decision = [c for c in decision_columns if c not in solutions.columns]
    if missing_decision:
        raise ValueError(f"Decision columns missing from DataFrame: {missing_decision}")

    missing_objective = [c for c in objective_columns if c not in solutions.columns]
    if missing_objective:
        raise ValueError(f"Objective columns missing from DataFrame: {missing_objective}")

    if not decision_columns and not objective_columns:
        raise ValueError(
            "Could not infer decision/objective columns. Provide explicit column lists "
            "or load a CSV with a superheader for automatic grouping."
        )

    id_cols_present = [c for c in id_columns if c in solutions.columns]
    prefix = id_cols_present if include_id_columns else []

    decisions_df = solutions[prefix + decision_columns].copy()
    objectives_df = solutions[prefix + objective_columns].copy()

    return {
        "decisions": decisions_df,
        "objectives": objectives_df,
        "decision_columns": decision_columns,
        "objective_columns": objective_columns,
    }


def split_solutions_csv(
    input_csv,
    decisions_csv=None,
    objectives_csv=None,
    superheader="auto",
    decision_columns=None,
    objective_columns=None,
    id_columns=("Solution", "Solution ID"),
    include_id_columns=True,
    index=False,
):
    """Split a solutions CSV and write decisions-only and objectives-only CSVs.

    Args:
        input_csv: Source solutions CSV path.
        decisions_csv: Destination for decision-variable subset.
            Defaults to '<stem>.decisions.csv'.
        objectives_csv: Destination for objective subset.
            Defaults to '<stem>.objectives.csv'.
        superheader: One of "auto", "yes", "no".
        decision_columns: Explicit decision columns, optional.
        objective_columns: Explicit objective columns, optional.
        id_columns: Candidate ID columns to keep.
        include_id_columns: Include ID columns in both outputs.
        index: Whether to write DataFrame index to output CSVs.

    Returns:
        dict with output paths and detected column groupings.
    """
    input_path = Path(input_csv)
    if decisions_csv is None:
        decisions_path = input_path.with_name(f"{input_path.stem}.decisions.csv")
    else:
        decisions_path = Path(decisions_csv)

    if objectives_csv is None:
        objectives_path = input_path.with_name(f"{input_path.stem}.objectives.csv")
    else:
        objectives_path = Path(objectives_csv)

    solutions, metadata = load_solutions_dataframe(
        input_path,
        superheader=superheader,
        return_metadata=True,
    )

    split = split_solutions_dataframe(
        solutions,
        metadata=metadata,
        decision_columns=decision_columns,
        objective_columns=objective_columns,
        id_columns=id_columns,
        include_id_columns=include_id_columns,
    )

    split["decisions"].to_csv(decisions_path, index=index)
    split["objectives"].to_csv(objectives_path, index=index)

    return {
        "decisions_path": decisions_path,
        "objectives_path": objectives_path,
        "decision_columns": split["decision_columns"],
        "objective_columns": split["objective_columns"],
    }
