"""Tradeoff workflow: epsilon non-dominance, KMeans, HiPlot parallel coordinates.

Generates a synthetic 3-objective solution set, labels epsilon non-dominated
points, clusters them, and writes an interactive HiPlot HTML file.
"""
from pathlib import Path

import numpy as np
import pandas as pd

from parasolpy.tradeoff import (
    append_Kmeans,
    label_eps_nd,
    parallel_plot_hp,
)
from parasolpy.util import ensure_dir

OUT = ensure_dir(Path(__file__).parent / "_output")


def main():
    rng = np.random.default_rng(7)
    n = 400

    # Synthetic tradeoff: cost (min), reliability (max), environment (min).
    cost = rng.uniform(10, 100, n)
    reliability = 1.0 - 0.6 * (cost / cost.max()) + rng.normal(0, 0.08, n)
    reliability = np.clip(reliability, 0, 1)
    environment = 50 - 0.3 * cost + rng.normal(0, 5, n)

    df = pd.DataFrame({
        "cost": cost,
        "reliability": reliability,
        "environment": environment,
    })

    obj_names = ["cost", "reliability", "environment"]
    obj_directions = ["minimize", "maximize", "minimize"]
    epsilons = [2.0, 0.02, 1.0]

    df = label_eps_nd(df, "eps_nd", obj_names, obj_directions, epsilons)
    n_nd = int(df["eps_nd"].sum())
    print(f"Total solutions:           {len(df)}")
    print(f"Epsilon non-dominated:     {n_nd}")

    nd = df[df["eps_nd"]].copy().reset_index(drop=True)
    nd, _ = append_Kmeans(nd, num_clusters=3, cluster_columns=obj_names)

    exp = parallel_plot_hp(
        nd,
        obj_names=obj_names,
        obj_directions=obj_directions,
        color_column="Cluster",
        hide_columns=["eps_nd"],
    )
    html_path = OUT / "tradeoff_parallel.html"
    exp.to_html(html_path)

    csv_path = OUT / "tradeoff_nd.csv"
    nd.to_csv(csv_path, index=False)
    print(f"Saved HiPlot:   {html_path}")
    print(f"Saved CSV:      {csv_path}")


if __name__ == "__main__":
    main()
