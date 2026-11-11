# Colorado River Basin 500-SOW sample

500 states of the world (SOWs) subsampled from the ensemble used in the MAPS
framework paper. Used by `examples/08_som_maps_demo.py`.

## Files

| File | Shape | Contents |
| --- | --- | --- |
| `500_sow_cumulative_supply.csv` | 30 rows x 500 columns | Cumulative supply for each SOW, in million acre-feet (MAF). Rows are years 2027–2056; columns are SOWs. |
| `500_sow_info.csv` | 500 rows x 15 columns | One row of metadata per SOW. |

Column `k` of the supply file corresponds to row `k` of the info file. The
supply file's header (`0` … `499`) is that position, not a trace ID.

## Cumulative supply

```
supply[t, k] = InitCombinedStorage_k + cumsum(LeesFerryFlow[Trace_k] − demand_k)[t]
```

with all terms in MAF: the initial combined storage of the SOW, plus the
running sum of annual Lees Ferry natural flow for the SOW's hydrology trace
minus the SOW's annual demand.

## Info columns

| Column | Meaning |
| --- | --- |
| `Trace` | Hydrology trace ID in the MAPS ensemble (unique across the 500 SOWs). |
| `Scenario` | Hydrology scenario the trace comes from (`npc_cmip3`, `npc_adjusted`, `cmip5`, `paleo_drought`, `stress_test`). |
| `TraceNumber` | Trace number within its scenario. |
| `Median`, `Max`, `Min`, `SD`, `IQR` | Statistics of the trace's annual Lees Ferry natural flow (MAF/yr). |
| `MaxDroughtLength`, `Driest10yr`, `Wettest10yr` | Drought and 10-year-window statistics of the same trace. |
| `demand` | Annual demand (MAF/yr). |
| `mead`, `powell` | Sampled initial reservoir pool elevations (ft). |
| `InitCombinedStorage` | Initial combined storage (MAF). |

The scenario mix is lopsided (`npc_cmip3` 432, `npc_adjusted` 37, `cmip5` 20,
`paleo_drought` 10, `stress_test` 1), so `Scenario` makes a poor map layer.

The original file carried `Neuron` and `Cluster` columns from a map trained in
R (`kohonen`). They were removed: a differently trained map gives different
neurons.

## Source and license

Derived from the public MAPS-Framework repository (MIT license):
https://github.com/madrpernat/MAPS-Framework

Pernat, M. R., Kasprzyk, J. R., Zagona, E. A. (2026). Negotiating management
alternatives under uncertain future conditions using a self-organizing map
framework. *Environmental Modelling & Software* 205, 107118.
https://doi.org/10.1016/j.envsoft.2026.107118
