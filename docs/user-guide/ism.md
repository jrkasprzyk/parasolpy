# Index-Sequential Method

The `parasolpy.ism` module builds synthetic trace ensembles from a historical inflow record using the index-sequential method.

## Public Function

```python
from parasolpy.ism import create_ism_traces
```

`create_ism_traces(inflow, k, trace_length)` slides a window over a doubled copy of the historical record so traces can wrap around the end of the sequence.

```python
import numpy as np
from parasolpy.ism import create_ism_traces

historical = np.arange(1, 25)
traces, indices = create_ism_traces(historical, k=4, trace_length=12)
```

The returned `traces` array has shape `(trace_length, num_traces)`, where `num_traces = floor(len(inflow) / k)`.

## Example Script

```bash
python examples/02_ism_traces.py
```

The script writes an ISM traces plot to `examples/_output/ism_traces.png`.
