# Plotting Trace Ensembles

The `parasolpy.plotting` module provides static plotting helpers for wide-format trace DataFrames.

Input data should be a `pandas.DataFrame` where:

- rows are timesteps with a datetime-like index
- columns are simulation traces
- values are numeric

## Plot Types

```python
from parasolpy.plotting import (
    plot_trace_exceedance,
    plot_trace_fan_chart,
    plot_trace_heatmap,
    plot_trace_monthly_seasonality,
    plot_trace_spaghetti,
)
```

Each function saves a figure to disk and returns the Matplotlib figure, axes, and saved output path.

```python
import numpy as np
import pandas as pd
from parasolpy.plotting import plot_trace_fan_chart

dates = pd.date_range("2026-01-01", periods=24, freq="MS")
trace_df = pd.DataFrame(
    np.random.default_rng(42).normal(100, 10, size=(24, 20)),
    index=dates,
    columns=[f"run_{i}" for i in range(20)],
)

fig, ax, output_path = plot_trace_fan_chart(trace_df, "examples/_output")
```

## Example Script

```bash
python examples/04_trace_plots.py
```

The script writes heatmap, spaghetti, fan chart, seasonality, and exceedance figures to `examples/_output/`.

## Borg Archive Lifespans

`plot_archive_lifespans` draws a survival chart of a Borg MOEA archive. Its input is the snapshot list from `parasolpy.borg_runtime.parse_borg_runtime`, so it does not take a trace DataFrame like the plots above.

```python
from parasolpy.borg_runtime import parse_borg_runtime
from parasolpy.plotting import plot_archive_lifespans

snapshots = parse_borg_runtime("RunTime.txt")
fig, (ax_size, ax), output_path = plot_archive_lifespans(snapshots, "examples/_output")
```

The figure has two panels that share the x-axis (NFE):

- **Top:** archive size at each snapshot.
- **Bottom:** one horizontal bar per solution, ordered by birth, from birth NFE to death NFE. Solutions still in the final archive are drawn in a different color from solutions removed during the run.

Snapshot gaps wider than `restart_gap_threshold` NFE (default 50) are shaded. These gaps usually mark Borg restarts, when Borg writes no runtime output.

See [Borg Runtime Analysis](borg-runtime.md) for details on parsing runtime snapshots and interpreting solution lifespans.
