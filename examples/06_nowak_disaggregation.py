"""Nowak et al. (2010) nonparametric annual-to-monthly disaggregation.

Given a historical record of annual totals Z and their month-wise proportion
vectors p, sample a simulated monthly trace for each of several synthetic
annual totals by finding KNN analog years and reusing their monthly shape.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from parasolpy.nowak import sim_multi_trace
from parasolpy.util import ensure_dir

OUT = ensure_dir(Path(__file__).parent / "_output")


def build_historical(rng, n_years=50):
    years = np.arange(1970, 1970 + n_years)
    shape = np.array([0.04, 0.05, 0.07, 0.12, 0.18, 0.16,
                      0.12, 0.09, 0.07, 0.05, 0.03, 0.02])
    # Annual totals vary; month shapes wobble a little around the mean shape.
    Z = rng.uniform(800, 1600, n_years)
    p = np.vstack([shape + rng.normal(0, 0.01, 12) for _ in range(n_years)])
    p = np.clip(p, 1e-4, None)
    p = p / p.sum(axis=1, keepdims=True)
    return years, Z, p


def main():
    rng = np.random.default_rng(2026)
    years, Z, p = build_historical(rng)

    # Simulated annual totals: 5 sequences of 10 future years each.
    num_seq, num_sim_years = 5, 10
    sim_Z = rng.uniform(Z.min(), Z.max(), (num_seq, num_sim_years))

    mat_sim = sim_multi_trace(rng, Z, p, years, sim_Z, repl=2)
    print(f"Historical years:   {len(years)}")
    print(f"Simulated matrix:   {mat_sim.shape} (months x sequences*replicates)")

    fig, ax = plt.subplots(figsize=(10, 5))
    months = np.arange(mat_sim.shape[0])
    for j in range(mat_sim.shape[1]):
        ax.plot(months, mat_sim[:, j], alpha=0.5, linewidth=0.8)
    ax.set_title("Nowak disaggregated monthly traces")
    ax.set_xlabel("Month (0 = start of first simulated year)")
    ax.set_ylabel("Monthly flow")
    fig.tight_layout()
    out_path = OUT / "nowak_traces.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved figure: {out_path}")


if __name__ == "__main__":
    main()
