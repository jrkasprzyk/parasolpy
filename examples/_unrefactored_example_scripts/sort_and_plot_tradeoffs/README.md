# Sort and Plot Tradeoffs (Notebook)

This folder is the notebook version of `example_scripts/sort_and_plot_tradeoffs.py`.

## Structure
- `data/`: real RedRiver context files copied from `problems/RedRiverHaydenCarson/`
- `output/`: HTML plots and other generated outputs
- `sort_and_plot_tradeoffs.ipynb`: the converted example notebook

## Included Context
- `Plot.HiPlot.csv`
- `redriver_v1.8.3.xml`
- `RedRiver-HaydenCarsonExample.v3.mdl.gz`

## Important
The original script logic expects `data/AllPolicies.csv`, which is not currently present in this repository.
The notebook preserves that logic and reports a clear message if `AllPolicies.csv` is missing.
