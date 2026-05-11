"""Utility functions: unit conversions, path helpers, time-series pivoting, XML parsing."""

import inspect
from numbers import Real
from os import PathLike
from pathlib import Path

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd


def script_local_path(filename, must_exist=True, caller_file=None):
    """Resolve a path relative to the calling script file.

    Args:
        filename: File name or relative path from the script directory.
        must_exist: If True, raise FileNotFoundError when the resolved path does not exist.
        caller_file: Optional script path override; defaults to the caller's file.
    """
    if not isinstance(filename, (str, PathLike)):
        raise TypeError("Input 'filename' must be a path string or path-like object.")
    if isinstance(filename, str) and not filename.strip():
        raise ValueError("Input 'filename' cannot be an empty string.")
    if not isinstance(must_exist, bool):
        raise TypeError("Input 'must_exist' must be a boolean.")

    candidate = Path(filename)
    if candidate.is_absolute():
        resolved = candidate
    else:
        if caller_file is None:
            caller_file = inspect.stack()[1].filename
        script_dir = Path(caller_file).resolve().parent
        resolved = script_dir / candidate

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"File not found: {resolved}")

    return resolved


def ensure_dir(path):
    """Create a directory (and parents) if missing and return it as a Path."""
    if not isinstance(path, (str, PathLike)):
        raise TypeError("Input 'path' must be a path string or path-like object.")
    if isinstance(path, str) and not path.strip():
        raise ValueError("Input 'path' cannot be an empty string.")

    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _convert_with_factor(val, factor):
    """Apply a multiplicative conversion factor to scalar and vector-like numeric inputs."""
    if isinstance(val, bool):
        raise TypeError("Input 'val' must be numeric (bool is not allowed).")

    if isinstance(val, Real):
        return val * factor

    if isinstance(val, pd.Series):
        if pd.api.types.is_bool_dtype(val.dtype) or not pd.api.types.is_numeric_dtype(val.dtype):
            raise TypeError("Input 'val' pandas Series must have a numeric dtype.")
        return val * factor

    if isinstance(val, np.ndarray):
        if np.issubdtype(val.dtype, np.bool_) or not np.issubdtype(val.dtype, np.number):
            raise TypeError("Input 'val' NumPy array must have a numeric dtype.")
        return val * factor

    if isinstance(val, list):
        if any((isinstance(x, bool) or not isinstance(x, Real)) for x in val):
            raise TypeError("Input 'val' list must contain only real numbers.")
        return [x * factor for x in val]

    if isinstance(val, tuple):
        if any((isinstance(x, bool) or not isinstance(x, Real)) for x in val):
            raise TypeError("Input 'val' tuple must contain only real numbers.")
        return tuple(x * factor for x in val)

    raise TypeError(
        "Input 'val' must be a real number, pandas Series, numpy array, list, or tuple of real numbers."
    )


def convert_cfs_to_af(val):
    """Convert cubic feet per second (daily) to acre-feet for numeric scalar/vector inputs."""
    return _convert_with_factor(val, 1.98347)


def convert_cfs_to_cms(val):
    """Convert cubic feet per second to cubic meters per second for numeric scalar/vector inputs."""
    return _convert_with_factor(val, 0.028316831998814504)


def convert_cms_to_mcm(val):
    """Convert cubic meters per second (daily) to million cubic meters for numeric scalar/vector inputs."""
    return _convert_with_factor(val, 24 * 60 * 60 / 1e6)


def pivot_timeseries_by_year(data, value_column=None, aggfunc="mean"):
    """Pivot a DatetimeIndex time series into day-of-year (rows) by year (columns).

    Args:
        data: pandas Series or DataFrame with a DatetimeIndex.
        value_column: Required for multi-column DataFrames; ignored for Series.
        aggfunc: Aggregation used by pandas pivot_table when duplicate day/year
            entries occur. Common options: ``"mean"`` (good default for rate-like
            data), ``"sum"`` (additive quantities), ``"min"``, ``"max"``,
            ``"median"``, ``"first"``, ``"last"``. Any aggregation string
            accepted by pandas pivot_table is valid.
    """
    if not isinstance(data, (pd.Series, pd.DataFrame)):
        raise TypeError("Input 'data' must be a pandas Series or DataFrame.")

    if not isinstance(data.index, pd.DatetimeIndex):
        raise TypeError("Input 'data' must use a pandas DatetimeIndex.")

    if isinstance(data, pd.Series):
        values = data.copy(deep=True)
        if value_column is not None:
            raise ValueError("Input 'value_column' must be None when 'data' is a Series.")
    else:
        if value_column is None:
            if len(data.columns) != 1:
                raise ValueError(
                    "Input 'value_column' is required when 'data' is a DataFrame with multiple columns."
                )
            value_column = data.columns[0]
        if not isinstance(value_column, str) or value_column not in data.columns:
            raise ValueError("Input 'value_column' must name a column in 'data'.")
        values = data[value_column].copy(deep=True)

    if not isinstance(aggfunc, str) or not aggfunc.strip():
        raise ValueError("Input 'aggfunc' must be a non-empty string.")

    return pd.pivot_table(
        pd.DataFrame({"value": values}),
        values="value",
        index=values.index.dayofyear,
        columns=values.index.year,
        aggfunc=aggfunc,
    )


def read_xml(filename):
    """Read an XML file and return a BeautifulSoup XML document."""
    if not isinstance(filename, (str, PathLike)):
        raise TypeError("Input 'filename' must be a path string or path-like object.")
    if isinstance(filename, str) and not filename.strip():
        raise ValueError("Input 'filename' cannot be an empty string.")

    with open(filename, "r", encoding="utf-8") as f:
        data = f.read()

    if not data.strip():
        raise ValueError(f"XML file '{filename}' is empty.")

    return BeautifulSoup(data, "xml")


def process_xml(filename, include_objective_directions=False, default_objective_direction="minimize"):
    """Parse XML configuration into decision names, objective names, and optional objective directions.

    Args:
        filename: Path to XML configuration file.
        include_objective_directions: If True, also return objective direction values.
        default_objective_direction: Direction to use when an objective has no <sense> tag.
            Must be either "minimize" or "maximize".
    """
    if not isinstance(include_objective_directions, bool):
        raise TypeError("Input 'include_objective_directions' must be a boolean.")
    if not isinstance(default_objective_direction, str) or not default_objective_direction.strip():
        raise ValueError("Input 'default_objective_direction' must be a non-empty string.")

    default_direction = default_objective_direction.strip().lower()
    valid_directions = {"minimize", "maximize"}
    if default_direction not in valid_directions:
        raise ValueError("Input 'default_objective_direction' must be 'minimize' or 'maximize'.")

    bs_param = read_xml(filename)
    rw_inputs = bs_param.find_all("rwInput")
    objectives = bs_param.find_all("objective")

    objective_names = []
    objective_directions = []
    for objective in objectives:
        name_tag = objective.find("name")
        if name_tag is None or not name_tag.text or not name_tag.text.strip():
            raise ValueError("Each <objective> entry must contain a non-empty <name> tag.")
        objective_names.append(name_tag.text.strip())

        sense_tag = objective.find("sense")
        if sense_tag and sense_tag.text and sense_tag.text.strip():
            sense = sense_tag.text.strip().lower()
            if sense not in valid_directions:
                raise ValueError(
                    f"Objective sense '{sense_tag.text}' is invalid. Use 'Minimize' or 'Maximize'."
                )
            objective_directions.append(sense)
        else:
            objective_directions.append(default_direction)

    decision_variable_names = []
    for rw_input in rw_inputs:
        name_tag = rw_input.find("name")
        if name_tag is None or not name_tag.text or not name_tag.text.strip():
            raise ValueError("Each <rwInput> entry must contain a non-empty <name> tag.")
        decision_variable_names.append(name_tag.text.strip())

    if include_objective_directions:
        return decision_variable_names, objective_names, objective_directions

    return decision_variable_names, objective_names
