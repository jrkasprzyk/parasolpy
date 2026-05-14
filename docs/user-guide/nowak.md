# Nowak Disaggregation

The `parasolpy.nowak` module implements nonparametric stochastic disaggregation after Nowak et al. (2010). It converts simulated annual flows into sub-annual flows by selecting historical analog years with K-nearest-neighbor weighting.

## Public Functions

```python
from parasolpy.nowak import choose_analog_index, sim_single_year, sim_multi_trace
```

Use `choose_analog_index` when you need direct access to the weighted analog selection. Use `sim_single_year` for one simulated annual value and `sim_multi_trace` for a matrix of annual traces.

```python
import numpy as np
from parasolpy.nowak import sim_multi_trace

rng = np.random.default_rng(42)
observed_annual = np.array([100.0, 120.0, 90.0, 110.0])
proportions = np.array([
    [0.20, 0.30, 0.25, 0.25],
    [0.25, 0.25, 0.25, 0.25],
    [0.30, 0.20, 0.25, 0.25],
    [0.22, 0.28, 0.26, 0.24],
])
years = np.array([2020, 2021, 2022, 2023])
simulated_annual = np.array([[105.0, 115.0]])

subannual = sim_multi_trace(rng, observed_annual, proportions, years, simulated_annual)
```

## Example Script

```bash
python examples/06_nowak_disaggregation.py
```

The script writes a disaggregated trace plot to `examples/_output/nowak_traces.png`.
