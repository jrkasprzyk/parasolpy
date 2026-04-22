# parasolpy

Python tools for multi-objective decision analysis and visualization, continuing the Parasol project originally published as:

Raseman, W. J., Jacobson, J., & Kasprzyk, J. R. (2019). Parasol: An open source, interactive parallel coordinates library for multi-objective decision making. *Environmental Modelling & Software*, 116, 153–163. https://doi.org/10.1016/j.envsoft.2019.03.005

## Status

🚧 Early development. More documentation and functionality coming.

## Tradeoff explorer CLI

Once installed, launch an interactive parallel-coordinates explorer against a
results folder:

```bash
parasolpy-tradeoff path/to/output_folder
```

Equivalent module invocation (useful during development):

```bash
python -m parasolpy.dash_tools path/to/output_folder
```

Common options:

- `--config FILE` — override auto-discovered config XML
- `--solutions FILE` — override auto-discovered solutions CSV
- `--title TEXT` — heading shown above the plot
- `--colorscale NAME` — any Plotly named colorscale (default `viridis`)
- `--host HOST` / `--port PORT` — bind address (defaults `127.0.0.1:8050`)
- `--debug` — run Dash in debug mode

## Lineage

This package is developed by the Kasprzyk Research Group at CU Boulder. It is not affiliated with the unrelated `parasol` or `pyparasol` packages on PyPI, which are independent projects that share the name.

## License

MIT