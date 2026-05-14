# parasolpy

[![Documentation Status](https://readthedocs.org/projects/parasolpy/badge/?version=latest)](https://parasolpy.readthedocs.io/en/latest/?badge=latest)

Python tools for multi-objective decision analysis and visualization, continuing the
Parasol project originally published as:

> Raseman, W. J., Jacobson, J., & Kasprzyk, J. R. (2019). Parasol: An open
> source, interactive parallel coordinates library for multi-objective
> decision making. *Environmental Modelling & Software*, 116, 153–163.
> <https://doi.org/10.1016/j.envsoft.2019.03.005>

Developed by the [Kasprzyk Research Group](https://www.colorado.edu/lab/kasprzyk/)
at CU Boulder.

## Status

🚧 Active development. APIs are mostly stable but may change between 0.x releases.

## Installation

### From PyPI:

```bash
pip install parasolpy
```

Requires Python ≥ 3.12.

### From source (for development):

Requires [Poetry](https://python-poetry.org/docs/#installation)
to be installed on your system (e.g. `pipx install poetry`):

```bash
git clone https://github.com/jrkasprzyk/parasolpy.git
cd parasolpy
poetry install
```

## What's inside

`parasolpy` bundles several modules for reservoir analysis, streamflow
synthesis, multi-objective tradeoff exploration, and supporting plotting
and file utilities.

| Module | Purpose |
| --- | --- |
| [`parasolpy.reservoir`](parasolpy/reservoir.py) | Sequent-peak reservoir sizing |
| [`parasolpy.ism`](parasolpy/ism.py) | Index-sequential method (ISM) trace ensembles |
| [`parasolpy.nowak`](parasolpy/nowak.py) | Nowak et al. (2010) nonparametric streamflow disaggregation |
| [`parasolpy.tradeoff`](parasolpy/tradeoff.py) | Epsilon non-dominance, KMeans labeling, HiPlot parallel coordinates |
| [`parasolpy.plotting`](parasolpy/plotting.py) | Heatmap, spaghetti, fan chart, seasonality, exceedance plots |
| [`parasolpy.dash_tools`](parasolpy/dash_tools.py) | Interactive Dash app powering the `parasolpy-tradeoff` CLI |
| [`parasolpy.interactive`](parasolpy/interactive.py) | Terminal prompts for epsilon-experiment workflows |
| [`parasolpy.file_processing`](parasolpy/file_processing.py) | Borg / RiverWare solution CSV normalization |
| [`parasolpy.util`](parasolpy/util.py) | Path helpers, unit conversions, XML config parsing |

## Tradeoff explorer CLI

Once installed, launch an interactive parallel-coordinates explorer
against a results folder:

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

## Examples

The [`examples/`](examples/) directory contains self-contained scripts that
generate their own synthetic data — no external files needed. Run any of
them from the repo root:

```bash
python examples/01_reservoir_sequent_peak.py
python examples/03_tradeoff_parallel_plot.py
# ...etc.
```

Figures and CSV/HTML outputs land in `examples/_output/`. See
[`examples/README.md`](examples/README.md) for the full script list.

## Lineage and related packages

This package is developed by the Kasprzyk Research Group at CU Boulder. It
is **not affiliated** with the unrelated `parasol` or `pyparasol` packages on
PyPI, which are independent projects that share the name.

## Citation

If you use `parasolpy` in academic work, please cite the original Parasol
paper linked above.

## Development

- Documentation is hosted on [Read the Docs](https://parasolpy.readthedocs.io/).
  Build it locally with `pip install ".[docs]"` and
  `sphinx-build -W -b html docs docs/_build/html`.
- Cutting a release? See [RELEASING.md](RELEASING.md) for the Poetry-based
  workflow (version bump, build, publish to PyPI, tag, GitHub Release).
- Issues and pull requests are welcome on GitHub.

## License

[MIT](LICENSE)
