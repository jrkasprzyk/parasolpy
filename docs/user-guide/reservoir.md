# Reservoir Sizing

The `parasolpy.reservoir` module implements the sequent-peak algorithm for estimating the storage required to meet a constant demand from an inflow sequence.

## Public Function

```python
from parasolpy.reservoir import sequent_peak
```

`sequent_peak(inflow, demand)` accepts an array-like inflow sequence and a constant demand in matching units. It returns a NumPy array of cumulative shortage values.

```python
import numpy as np
from parasolpy.reservoir import sequent_peak

inflow = np.array([12.0, 8.0, 6.0, 15.0, 10.0])
demand = 10.0

storage = sequent_peak(inflow, demand)
capacity = storage.max()
```

The maximum value in `storage` is the required reservoir capacity for the given sequence.

## Example Script

Run the self-contained example from the repository root:

```bash
python examples/01_reservoir_sequent_peak.py
```

The script writes a figure to `examples/_output/sequent_peak.png`.
