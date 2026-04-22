"""Index-Sequential Method (ISM) trace generation.

Given one historical inflow record, ISM produces a deterministic ensemble of
traces by shifting the starting index forward by `k` timesteps for each trace,
wrapping around the end of the record.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from parasolpy.ism import create_ism_traces
from parasolpy.util import ensure_dir

OUT = ensure_dir(Path(__file__).parent / "_output")


def main():
    rng = np.random.default_rng(0)
    n_years = 60
    t = np.arange(n_years)
    historical = 50 + 10 * np.sin(2 * np.pi * t / 11) + rng.normal(0, 3, n_years)

    k = 5                # shift between traces (in timesteps)
    trace_length = 30    # each trace is 30 years long

    traces, indices = create_ism_traces(historical, k=k, trace_length=trace_length)
    print(f"Historical length:     {len(historical)}")
    print(f"Number of traces:      {traces.shape[1]}")
    print(f"Each trace length:     {traces.shape[0]}")

    fig, ax = plt.subplots(figsize=(10, 5))
    for i in range(traces.shape[1]):
        ax.plot(traces[:, i], alpha=0.5, linewidth=1)
    ax.set_title(f"ISM traces (k={k}, length={trace_length})")
    ax.set_xlabel("Trace timestep")
    ax.set_ylabel("Annual inflow")
    fig.tight_layout()
    out_path = OUT / "ism_traces.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved figure: {out_path}")


if __name__ == "__main__":
    main()
