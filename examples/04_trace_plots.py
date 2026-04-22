"""Ensemble trace visualization: heatmap, spaghetti, fan, seasonality, exceedance."""
from pathlib import Path

import numpy as np
import pandas as pd

from parasolpy.plotting import (
    plot_trace_exceedance,
    plot_trace_fan_chart,
    plot_trace_heatmap,
    plot_trace_monthly_seasonality,
    plot_trace_spaghetti,
)
from parasolpy.util import ensure_dir

OUT = ensure_dir(Path(__file__).parent / "_output")


def synthetic_ensemble(n_runs=40, n_months=120, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2000-01-01", periods=n_months, freq="MS")
    t = np.arange(n_months)
    seasonal = 80 + 40 * np.sin(2 * np.pi * t / 12)
    runs = {}
    for i in range(n_runs):
        drift = rng.normal(0, 0.1) * t
        noise = rng.normal(0, 10, n_months)
        runs[f"run_{i:03d}"] = np.clip(seasonal + drift + noise, 0, None)
    return pd.DataFrame(runs, index=dates)


def main():
    traces = synthetic_ensemble()
    print(f"Ensemble shape: {traces.shape}")

    plot_trace_heatmap(traces, OUT, filename="heatmap.png",
                       value_label="Flow")
    plot_trace_spaghetti(traces, OUT, filename="spaghetti.png",
                         y_label="Flow")
    plot_trace_fan_chart(traces, OUT, filename="fan.png",
                         y_label="Flow")
    plot_trace_monthly_seasonality(traces, OUT, filename="seasonality.png",
                                   y_label="Flow")
    plot_trace_exceedance(traces, OUT, filename="exceedance.png",
                          y_label="Flow")

    for name in ("heatmap", "spaghetti", "fan", "seasonality", "exceedance"):
        print(f"Saved: {OUT / (name + '.png')}")


if __name__ == "__main__":
    main()
