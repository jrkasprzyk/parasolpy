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
