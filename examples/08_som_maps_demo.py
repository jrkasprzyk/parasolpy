"""MAPS-style self-organizing map demo on Colorado River Basin supply traces.

Fits a 13 x 4 hexagonal SOM to 500 states of the world (SOWs), each a 30-year
cumulative-supply trace, then layers SOW attributes onto the map:

1. fit      -- fit_som on z-scored traces
2. assign   -- append_som writes Neuron / Neuron_x / Neuron_y / Neuron_dist
3. layer    -- plot_som_layer draws per-neuron summaries

It also draws per-neuron member traces and runs a small hyperparameter sweep
with non-dominated selection.

This is a demo on a 500-SOW subsample of the MAPS ensemble (Pernat, Kasprzyk,
Zagona 2026, doi:10.1016/j.envsoft.2026.107118). It does not reproduce the
paper's figures: a differently trained map has different neurons.
"""
import pandas as pd

from parasolpy.som import (
    append_som,
    fit_som,
    plot_som_layer,
    plot_som_node_traces,
    som_quality,
    sweep_som,
)
from parasolpy.tradeoff import label_eps_nd
from parasolpy.util import ensure_dir, script_local_path

SUPPLY_CSV = script_local_path("data/crb_500_sow/500_sow_cumulative_supply.csv")
INFO_CSV = script_local_path("data/crb_500_sow/500_sow_info.csv")
OUT = ensure_dir(script_local_path("_output", must_exist=False))

X_DIM, Y_DIM = 13, 4
FIRST_YEAR = 2027


def main():
    info = pd.read_csv(INFO_CSV)
    supply = pd.read_csv(SUPPLY_CSV)  # rows = years, columns = SOWs

    # Column k of the supply file is row k of the info file (positional
    # alignment), so label the supply columns with the info table's trace IDs.
    supply.columns = info["Trace"]
    supply.index = pd.to_datetime(
        [f"{FIRST_YEAR + i}-01-01" for i in range(len(supply))]
    )

    # Features: one row per SOW, one column per year. The package does no
    # scaling, so z-score each year column here.
    features = supply.T
    Z = (features - features.mean(axis=0)) / features.std(axis=0)

    # 1. Fit, 2. assign.
    som = fit_som(Z, X_DIM, Y_DIM)
    append_som(info, som, Z)

    quality = som_quality(som, Z)
    print(f"Map: {X_DIM} x {Y_DIM} hexagonal, {len(info)} SOWs")
    print(f"Quantization error:  {quality['quantization_error']:.3f}")
    print(f"Topographic error:   {quality['topographic_error']:.3f}")
    print(f"Explained variance:  {quality['explained_variance']:.1f} %")
    print(f"Occupied neurons:    {info['Neuron'].nunique()} of {X_DIM * Y_DIM}")

    # 3. Layer SOW attributes onto the map as per-neuron means.
    layers = {
        "Median": "Median Lees Ferry flow (MAF/yr)",
        "demand": "Demand (MAF/yr)",
        "InitCombinedStorage": "Initial combined storage (MAF)",
    }
    for column, label in layers.items():
        _, _, path = plot_som_layer(
            som,
            info.groupby("Neuron")[column].mean(),
            OUT,
            filename=f"som_layer_{column}.png",
            colorbar_label=label,
        )
        print(f"Saved: {path}")

    # Hits: number of SOWs per neuron.
    _, _, path = plot_som_layer(
        som,
        info["Neuron"].value_counts(),
        OUT,
        filename="som_layer_hits.png",
        annotate="value",
        cmap="Blues",
        colorbar_label="SOWs per neuron",
    )
    print(f"Saved: {path}")

    # Member traces per neuron, with the full ensemble in the background.
    _, _, path = plot_som_node_traces(
        som,
        supply,
        info.set_index("Trace")["Neuron"],
        OUT,
        background_df=supply,
    )
    print(f"Saved: {path}")

    # Optional: sweep map configurations and keep the non-dominated ones.
    # Explained variance rises with map size, so this is a three-objective
    # choice rather than a single best score.
    sweep = sweep_som(Z, n_samples=30)
    sweep = label_eps_nd(
        sweep,
        "eps_nd",
        ["n_neurons", "explained_variance", "topographic_error"],
        ["minimize", "maximize", "minimize"],
        [1, 1.0, 0.01],
    )
    nd = sweep[sweep["eps_nd"]].sort_values("n_neurons").drop(columns="eps_nd")
    print(f"\nSweep: {len(nd)} of {len(sweep)} configurations are non-dominated")
    print(nd.round(3).to_string(index=False))

    csv_path = OUT / "som_sweep.csv"
    sweep.to_csv(csv_path, index=False)
    print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
