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

## Calculate Required Capacity using Sequent Peak

```python
inflow = np.array([12.0, 8.0, 6.0, 15.0, 10.0])
demand = 10.0

storage = sequent_peak(inflow, demand)
required_capacity = storage.max()
```

For a sequence of flows given in `inflow`, this uses the Sequent Peak method to find the required storage needed to meet `demand` at each timestep. The method calculates running tallies of shortage for time periods when demand cannot be met. The entire timeseries of shortage values is saved in `storage`. The method assumes that its maximum is the required storage capacity for the sequence. 

To test whether the `required_capacity` is enough, you can perform a basic mass balance calculation where the 'new' reservoir starts full, accepts inflow, and releases demand (or spills). The storage within the reservoir should never go below 0, and `demand` should be able to be met over the sequence.

## Stochastic Streamflow: Index Sequential Method

```python
historical = np.arange(1, 13)
traces, source_indices = create_ism_traces(historical, k=3, trace_length=6)
```

In this example, the `historical` trace is simply the numbers from 1-12. To create Index Sequential Method (ISM) traces, we use the `create_ism_traces` function, passing in the `historical` data, indicating we want to skip 3 timesteps between each sequence (`k=3`) and we want traces that are 6 units long (`trace_length=6`). Each column in `traces` is one index-sequential trace. `source_indices` records which positions from the original historical record were used.

## Unit Conversion and Yearly Pivot

`parasolpy` also contains common utility functions that can help when processing reservoir timeseries:

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
