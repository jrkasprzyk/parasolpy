# Quickstart

Import from the top-level package for common tasks:

```python
import numpy as np
import pandas as pd

from parasolpy import (
    convert_cfs_to_af,
    create_ism_traces,
    pivot_timeseries_by_year,
    sequent_peak,
)
```

## Reservoir Storage

```python
inflow = np.array([12.0, 8.0, 6.0, 15.0, 10.0])
demand = 10.0

storage = sequent_peak(inflow, demand)
required_capacity = storage.max()
```

`storage` is the cumulative shortage at each timestep. Its maximum is the required storage capacity for the sequence.

## ISM Trace Generation

```python
historical = np.arange(1, 13)
traces, source_indices = create_ism_traces(historical, k=3, trace_length=6)
```

Each column in `traces` is one index-sequential trace. `source_indices` records which positions from the historical record were used.

## Unit Conversion and Yearly Pivot

```python
daily_cfs = pd.Series(
    [100.0, 120.0, 95.0],
    index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
)

daily_af = convert_cfs_to_af(daily_cfs)
by_year = pivot_timeseries_by_year(daily_af)
```

## More Examples

The `examples/` directory contains runnable scripts that generate synthetic inputs and write outputs to `examples/_output/`.
