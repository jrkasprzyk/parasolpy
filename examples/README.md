# parasolpy examples

Self-contained scripts demonstrating the main modules. Each example generates
its own synthetic data so no external files are required.

Run any example from the repo root:

```bash
python examples/01_reservoir_sequent_peak.py
python examples/02_ism_traces.py
python examples/03_tradeoff_parallel_plot.py
python examples/04_trace_plots.py
python examples/05_unit_conversions.py
python examples/06_nowak_disaggregation.py
```

Figures and CSV/HTML outputs are written under `examples/_output/`.

| Script | Module(s) | What it shows |
| --- | --- | --- |
| `01_reservoir_sequent_peak.py` | `parasolpy.reservoir` | Sizing storage with the sequent-peak algorithm |
| `02_ism_traces.py` | `parasolpy.ism` | Building index-sequential method trace ensembles |
| `03_tradeoff_parallel_plot.py` | `parasolpy.tradeoff` | Epsilon non-dominance labeling, KMeans, HiPlot parallel coordinates |
| `04_trace_plots.py` | `parasolpy.plotting` | Heatmap, spaghetti, fan chart, seasonality, exceedance |
| `05_unit_conversions.py` | `parasolpy.util` | cfs / cms / acre-foot / MCM conversions and yearly pivot |
| `06_nowak_disaggregation.py` | `parasolpy.nowak` | Nonparametric annual-to-monthly streamflow disaggregation |
