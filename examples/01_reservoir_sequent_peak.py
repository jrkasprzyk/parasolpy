"""Sequent-peak reservoir sizing on a synthetic inflow record.

The sequent-peak algorithm returns the storage deficit at each timestep given a
constant demand. The maximum of that series is the required active storage.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from parasolpy.reservoir import sequent_peak
from parasolpy.util import ensure_dir

OUT = ensure_dir(Path(__file__).parent / "_output")


def main():
    rng = np.random.default_rng(42)
    months = 240
    t = np.arange(months)
    seasonal = 100 + 60 * np.sin(2 * np.pi * t / 12)
    noise = rng.normal(0, 20, months)
    inflow = np.clip(seasonal + noise, 0, None)

    demand = inflow.mean() * 0.9
    K = sequent_peak(inflow, demand)

    required_storage = K.max()
    print(f"Mean inflow:       {inflow.mean():.1f}")
    print(f"Constant demand:   {demand:.1f}")
    print(f"Required storage:  {required_storage:.1f}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    ax1.plot(t, inflow, label="Inflow")
    ax1.axhline(demand, color="red", linestyle="--", label=f"Demand ({demand:.0f})")
    ax1.set_ylabel("Flow")
    ax1.legend()

    ax2.plot(t, K, color="C2")
    ax2.axhline(required_storage, color="black", linestyle=":",
                label=f"Required storage ({required_storage:.0f})")
    ax2.set_ylabel("Deficit K[t]")
    ax2.set_xlabel("Month")
    ax2.legend()

    fig.suptitle("Sequent-peak reservoir sizing")
    fig.tight_layout()
    out_path = OUT / "sequent_peak.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved figure: {out_path}")


if __name__ == "__main__":
    main()
