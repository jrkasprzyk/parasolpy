# Tradeoff Analysis

The `parasolpy.tradeoff` module supports multi-objective tradeoff workflows: converting DataFrames to Platypus solutions, labeling epsilon non-dominated points, clustering solutions, loading RiverWare/Borg output files, and creating interactive parallel coordinate plots.

## Core Workflow

```python
from parasolpy.tradeoff import (
    append_Kmeans,
    label_eps_nd,
    parallel_plot_hp,
)
```

Start with a DataFrame where rows are candidate solutions and objective columns contain numeric objective values.

```python
import pandas as pd
from parasolpy.tradeoff import append_Kmeans, label_eps_nd

solutions = pd.DataFrame({
    "Cost": [10.0, 12.0, 8.0],
    "Reliability": [0.95, 0.98, 0.90],
})

labeled = label_eps_nd(
    solutions,
    label_col="EpsND",
    obj_names=["Cost", "Reliability"],
    obj_directions=["minimize", "maximize"],
    epsilons=[1.0, 0.01],
)

clustered = append_Kmeans(labeled, num_clusters=2, cluster_columns=["Cost", "Reliability"])
```

## RiverWare/Borg Outputs

Use these helpers when a folder contains optimization outputs:

```python
from parasolpy.tradeoff import (
    load_objective_names,
    load_objectives_and_solutions,
    resolve_solutions_csv,
)
```

They combine XML objective metadata with normalized solution CSVs from `parasolpy.file_processing`.

## Interactive Plots

`parallel_plot_hp` returns a HiPlot experiment. The installed `parasolpy-tradeoff` CLI wraps related loading logic in a Dash app for interactive exploration.

## Example Script

```bash
python examples/03_tradeoff_parallel_plot.py
```

The script writes a nondominated-solution CSV and an HTML parallel-coordinate plot to `examples/_output/`.
