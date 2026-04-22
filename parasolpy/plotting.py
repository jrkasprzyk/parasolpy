"""Plotting helpers for ensemble trace analysis using pandas DataFrames.

These helpers assume a wide-format DataFrame where:
- rows are timesteps (DatetimeIndex or datetime-like values)
- columns are simulation traces (numeric)

All plotting functions save a static figure to disk and return the matplotlib
figure/axes plus the saved output path.
"""

from os import PathLike
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from parasolpy.util import ensure_dir


def _coerce_datetime_index(index):
    """Coerce a pandas index to DatetimeIndex with clear errors on failure."""
    if isinstance(index, pd.DatetimeIndex):
        return index

    if isinstance(index, pd.PeriodIndex):
        return index.to_timestamp()

    try:
        return pd.to_datetime(index, errors="raise")
    except Exception as exc:
        raise ValueError(
            "Input index must be datetime-like or convertible to DatetimeIndex."
        ) from exc


def _validate_trace_dataframe(trace_df):
    """Validate and normalize a trace DataFrame for plotting."""
    if not isinstance(trace_df, pd.DataFrame):
        raise TypeError("Input 'trace_df' must be a pandas DataFrame.")

    if trace_df.empty:
        raise ValueError("Input 'trace_df' cannot be empty.")

    if trace_df.columns.empty:
        raise ValueError("Input 'trace_df' must contain at least one trace column.")

    non_numeric_cols = [col for col in trace_df.columns if not pd.api.types.is_numeric_dtype(trace_df[col])]
    if non_numeric_cols:
        raise TypeError(
            f"All trace columns must be numeric. Non-numeric columns found: {non_numeric_cols}"
        )

    validated = trace_df.copy(deep=True)
    validated.index = _coerce_datetime_index(validated.index)
    validated = validated.sort_index()

    if validated.isna().all(axis=1).any():
        raise ValueError("Input 'trace_df' contains one or more timesteps with all-NaN values.")

    return validated


def _subset_runs(trace_df, run_columns=None):
    """Optionally subset to a provided list of run columns."""
    if run_columns is None:
        return trace_df

    if not isinstance(run_columns, list) or not all(isinstance(name, str) for name in run_columns):
        raise TypeError("Input 'run_columns' must be a list of trace column names.")

    missing = [name for name in run_columns if name not in trace_df.columns]
    if missing:
        raise ValueError(f"Requested run columns not found in DataFrame: {missing}")

    return trace_df[run_columns]


def _resolve_output_path(output_dir, filename):
    """Build and create an output path for figure saving."""
    if not isinstance(output_dir, (str, PathLike)):
        raise TypeError("Input 'output_dir' must be a path string or path-like object.")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Input 'filename' must be a non-empty string.")

    output_path = ensure_dir(output_dir) / filename
    return output_path


def _save_figure(fig, output_path, dpi):
    """Save a matplotlib figure and return the saved path."""
    if not isinstance(dpi, int) or dpi <= 0:
        raise ValueError("Input 'dpi' must be a positive integer.")

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    return output_path


def plot_trace_heatmap(
    trace_df,
    output_dir,
    filename="trace_heatmap.png",
    run_columns=None,
    cmap="viridis",
    figsize=(14, 8),
    dpi=200,
    value_label="Value",
):
    """Plot an ensemble heatmap with time on x-axis and simulation runs on y-axis.

    Args:
        trace_df (pd.DataFrame): Wide trace DataFrame (rows=time, cols=runs).
        output_dir (str | PathLike): Directory where figure will be saved.
        filename (str, optional): Output image file name.
        run_columns (list of str, optional): Subset of run columns to include.
        cmap (str, optional): Matplotlib/seaborn colormap.
        figsize (tuple, optional): Figure size in inches.
        dpi (int, optional): Output image DPI.
        value_label (str, optional): Colorbar label.

    Returns:
        tuple: (fig, ax, output_path)
    """
    traces = _subset_runs(_validate_trace_dataframe(trace_df), run_columns)
    output_path = _resolve_output_path(output_dir, filename)

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        traces.T,
        cmap=cmap,
        ax=ax,
        cbar_kws={"label": value_label},
    )
    ax.set_title("Trace Ensemble Heatmap")
    ax.set_xlabel("Time")
    ax.set_ylabel("Simulation")

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


def plot_trace_spaghetti(
    trace_df,
    output_dir,
    filename="trace_spaghetti.png",
    run_columns=None,
    color="#1f77b4",
    alpha=0.15,
    linewidth=0.9,
    figsize=(14, 6),
    dpi=200,
    y_label="Value",
):
    """Plot a traditional spaghetti chart with all traces in one transparent color.

    Args:
        trace_df (pd.DataFrame): Wide trace DataFrame (rows=time, cols=runs).
        output_dir (str | PathLike): Directory where figure will be saved.
        filename (str, optional): Output image file name.
        run_columns (list of str, optional): Subset of run columns to include.
        color (str, optional): Single line color used for all traces.
        alpha (float, optional): Line transparency for each trace.
        linewidth (float, optional): Line width.
        figsize (tuple, optional): Figure size in inches.
        dpi (int, optional): Output image DPI.
        y_label (str, optional): Y-axis label.

    Returns:
        tuple: (fig, ax, output_path)
    """
    traces = _subset_runs(_validate_trace_dataframe(trace_df), run_columns)
    output_path = _resolve_output_path(output_dir, filename)

    if not isinstance(alpha, (int, float)) or not (0 < alpha <= 1):
        raise ValueError("Input 'alpha' must be in the interval (0, 1].")
    if not isinstance(linewidth, (int, float)) or linewidth <= 0:
        raise ValueError("Input 'linewidth' must be positive.")

    fig, ax = plt.subplots(figsize=figsize)
    for col in traces.columns:
        ax.plot(traces.index, traces[col], color=color, alpha=alpha, linewidth=linewidth)

    ax.set_title("Trace Spaghetti Plot")
    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


def plot_trace_fan_chart(
    trace_df,
    output_dir,
    filename="trace_fan_chart.png",
    run_columns=None,
    low_percentile=0.05,
    inner_low_percentile=0.25,
    median_percentile=0.50,
    inner_high_percentile=0.75,
    high_percentile=0.95,
    figsize=(14, 6),
    dpi=200,
    y_label="Value",
):
    """Plot percentile ribbons and median over time for ensemble traces.

    Args:
        trace_df (pd.DataFrame): Wide trace DataFrame (rows=time, cols=runs).
        output_dir (str | PathLike): Directory where figure will be saved.
        filename (str, optional): Output image file name.
        run_columns (list of str, optional): Subset of run columns to include.
        low_percentile (float, optional): Lower outer percentile.
        inner_low_percentile (float, optional): Lower inner percentile.
        median_percentile (float, optional): Median percentile, usually 0.50.
        inner_high_percentile (float, optional): Upper inner percentile.
        high_percentile (float, optional): Upper outer percentile.
        figsize (tuple, optional): Figure size in inches.
        dpi (int, optional): Output image DPI.
        y_label (str, optional): Y-axis label.

    Returns:
        tuple: (fig, ax, output_path)
    """
    traces = _subset_runs(_validate_trace_dataframe(trace_df), run_columns)
    output_path = _resolve_output_path(output_dir, filename)

    percentiles = [
        low_percentile,
        inner_low_percentile,
        median_percentile,
        inner_high_percentile,
        high_percentile,
    ]
    if any((not isinstance(p, (int, float))) or p < 0 or p > 1 for p in percentiles):
        raise ValueError("All percentile inputs must be numeric values in [0, 1].")
    if not (low_percentile < inner_low_percentile < median_percentile < inner_high_percentile < high_percentile):
        raise ValueError("Percentiles must be strictly increasing from low to high.")

    q = traces.quantile(percentiles, axis=1).T

    fig, ax = plt.subplots(figsize=figsize)
    ax.fill_between(
        q.index,
        q[low_percentile],
        q[high_percentile],
        color="#7aa6c2",
        alpha=0.25,
        label=f"P{int(low_percentile * 100)}-P{int(high_percentile * 100)}",
    )
    ax.fill_between(
        q.index,
        q[inner_low_percentile],
        q[inner_high_percentile],
        color="#2f6b8a",
        alpha=0.35,
        label=f"P{int(inner_low_percentile * 100)}-P{int(inner_high_percentile * 100)}",
    )
    ax.plot(
        q.index,
        q[median_percentile],
        color="#0f3d54",
        linewidth=2.0,
        label=f"P{int(median_percentile * 100)}",
    )

    ax.set_title("Trace Percentile Fan Chart")
    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)
    ax.legend(loc="best")

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


def plot_trace_monthly_seasonality(
    trace_df,
    output_dir,
    filename="trace_monthly_seasonality.png",
    run_columns=None,
    kind="box",
    figsize=(12, 6),
    dpi=200,
    y_label="Value",
):
    """Plot monthly distribution of ensemble values across all years and runs.

    Args:
        trace_df (pd.DataFrame): Wide trace DataFrame (rows=time, cols=runs).
        output_dir (str | PathLike): Directory where figure will be saved.
        filename (str, optional): Output image file name.
        run_columns (list of str, optional): Subset of run columns to include.
        kind (str, optional): Distribution plot type: 'box' or 'violin'.
        figsize (tuple, optional): Figure size in inches.
        dpi (int, optional): Output image DPI.
        y_label (str, optional): Y-axis label.

    Returns:
        tuple: (fig, ax, output_path)
    """
    traces = _subset_runs(_validate_trace_dataframe(trace_df), run_columns)
    output_path = _resolve_output_path(output_dir, filename)

    if kind not in ["box", "violin"]:
        raise ValueError("Input 'kind' must be either 'box' or 'violin'.")

    long_df = traces.copy(deep=True)
    long_df["month"] = long_df.index.month
    long_df = long_df.melt(id_vars=["month"], var_name="run", value_name="value").dropna()

    fig, ax = plt.subplots(figsize=figsize)
    if kind == "box":
        sns.boxplot(data=long_df, x="month", y="value", ax=ax, color="#5f8fa8", fliersize=1.5)
    else:
        sns.violinplot(data=long_df, x="month", y="value", ax=ax, color="#5f8fa8", cut=0)

    ax.set_title("Monthly Seasonality Across Ensemble Traces")
    ax.set_xlabel("Month")
    ax.set_ylabel(y_label)

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


def plot_trace_exceedance(
    trace_df,
    output_dir,
    filename="trace_exceedance.png",
    run_columns=None,
    alpha=0.12,
    linewidth=0.8,
    color="#1f77b4",
    show_median=True,
    figsize=(10, 6),
    dpi=200,
    y_label="Value",
):
    """Plot ensemble exceedance (flow-duration) curves for all simulation traces.

    Args:
        trace_df (pd.DataFrame): Wide trace DataFrame (rows=time, cols=runs).
        output_dir (str | PathLike): Directory where figure will be saved.
        filename (str, optional): Output image file name.
        run_columns (list of str, optional): Subset of run columns to include.
        alpha (float, optional): Transparency for individual trace curves.
        linewidth (float, optional): Line width for individual trace curves.
        color (str, optional): Color used for trace curves.
        show_median (bool, optional): If True, overlay median exceedance curve.
        figsize (tuple, optional): Figure size in inches.
        dpi (int, optional): Output image DPI.
        y_label (str, optional): Y-axis label.

    Returns:
        tuple: (fig, ax, output_path)
    """
    traces = _subset_runs(_validate_trace_dataframe(trace_df), run_columns)
    output_path = _resolve_output_path(output_dir, filename)

    if not isinstance(alpha, (int, float)) or not (0 < alpha <= 1):
        raise ValueError("Input 'alpha' must be in the interval (0, 1].")
    if not isinstance(linewidth, (int, float)) or linewidth <= 0:
        raise ValueError("Input 'linewidth' must be positive.")
    if not isinstance(show_median, bool):
        raise TypeError("Input 'show_median' must be a boolean.")

    sorted_vals = np.sort(traces.to_numpy(dtype=float), axis=0)[::-1, :]
    n = sorted_vals.shape[0]
    exceedance_pct = np.arange(1, n + 1) / (n + 1) * 100

    fig, ax = plt.subplots(figsize=figsize)
    for i in range(sorted_vals.shape[1]):
        ax.plot(exceedance_pct, sorted_vals[:, i], color=color, alpha=alpha, linewidth=linewidth)

    if show_median:
        median_curve = np.median(sorted_vals, axis=1)
        ax.plot(exceedance_pct, median_curve, color="#0f3d54", linewidth=2.3, label="Median")
        ax.legend(loc="best")

    ax.set_title("Trace Exceedance Curves")
    ax.set_xlabel("Exceedance Probability (%)")
    ax.set_ylabel(y_label)

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


__all__ = [
    "plot_trace_heatmap",
    "plot_trace_spaghetti",
    "plot_trace_fan_chart",
    "plot_trace_monthly_seasonality",
    "plot_trace_exceedance",
]
