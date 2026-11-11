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

```python
from parasolpy.tradeoff import parallel_plot_hp

exp = parallel_plot_hp(
    clustered,
    obj_names=["Cost", "Reliability"],
    obj_directions=["minimize", "maximize"],
    color_column="Cost",
)
exp.to_html("tradeoff_parallel.html")
```

### Axis scaling

HiPlot infers each axis type from the data, and it can treat a numeric column with few distinct values (such as a cluster ID or an integer decision variable) as categorical. To avoid this, `parallel_plot_hp` gives every column a numeric axis by default.

To keep some axes categorical, pass `force_numerical_columns` with only the columns that should be numeric:

```python
exp = parallel_plot_hp(
    clustered,
    obj_names=["Cost", "Reliability"],
    obj_directions=["minimize", "maximize"],
    force_numerical_columns=["Cost", "Reliability"],
)
```

Columns not in the list fall back to HiPlot's inferred type. Columns that hold text labels must be left out of the list, because a numeric axis cannot place non-numeric values.

## Example Script

```bash
python examples/03_tradeoff_parallel_plot.py
```

The script writes a nondominated-solution CSV and an HTML parallel-coordinate plot to `examples/_output/`.
