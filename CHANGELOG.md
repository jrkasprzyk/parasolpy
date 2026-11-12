# Changelog

All notable changes to `parasolpy` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (with
the understanding that during the `0.x` series, minor bumps may contain
breaking changes).

## [Unreleased]

## [0.5.0] — 2026-11-11

### Added
- `parasolpy.som`: a self-organizing map toolkit built on MiniSom, extracting
  the core of the MAPS framework (Pernat, Kasprzyk, Zagona 2026,
  doi:10.1016/j.envsoft.2026.107118). Six composable functions, all exported
  from the package root:
  - `fit_som` trains a map and returns the `MiniSom` instance. It does no
    feature scaling and warns when column spreads differ by more than 100x or
    a column has zero variance.
  - `append_som` assigns rows (training rows or new rows) to neurons and adds
    `Neuron`, `Neuron_x`, `Neuron_y`, and `Neuron_dist` columns. Neuron IDs
    are 0-based: `Neuron = Neuron_y * x_dim + Neuron_x`. Non-finite feature
    values are rejected, as in `fit_som`.
  - `som_quality` returns quantization error, topographic error, and
    explained variance. It raises on zero-variance data, where explained
    variance is undefined.
  - `sweep_som` fits and scores a Latin hypercube sample of map
    configurations, for selection with `label_eps_nd`.
  - `plot_som_layer` draws any per-neuron value on the hexagonal or
    rectangular map grid.
  - `plot_som_node_traces` draws each neuron's member traces.
- `examples/08_som_maps_demo.py` and the bundled 500-SOW Colorado River Basin
  sample in `examples/data/crb_500_sow/`.
- `docs/user-guide/som.md` (core workflow plus eight standalone recipes),
  `docs/examples/som.md`, and the `parasolpy.som` API reference page.
- Tests for `parasolpy.som`.

### Changed
- `minisom (>=2.3.6,<3.0.0)` is a new core dependency.

### Removed
- The `dev/minisomwrapper/` prototype, superseded by `parasolpy.som`.

## [0.4.3] — 2026-11-11

### Added
- Tests for `parasolpy.file_processing`: superheader detection (including
  UTF-8 BOM), `load_solutions_dataframe`, `split_solutions_dataframe`,
  `split_solutions_csv`, `convert_solutions_csv_to_single_header`, and their
  error paths.
- Tests for `parasolpy.tradeoff.label_eps_nd`: dominance filtering, maximize
  direction, epsilon-box merging, index labels, and input validation.
- `docs/user-guide/borg-runtime.md`: user guide for the `borg_runtime`
  module (runtime file format and lifespan convention).
- `docs/examples/borg-archive-lifespan.md`: docs page for
  `examples/07_borg_archive_lifespan.py`.

### Changed
- `docs/user-guide/tradeoff.md` documents `parallel_plot_hp` usage and the
  `force_numerical_columns` axis-scaling option.
- `docs/user-guide/plotting.md` documents `plot_archive_lifespans`.

## [0.4.2] — 2026-07-21

### Added
- `force_numerical_columns` parameter on `parasolpy.tradeoff.parallel_plot_hp`,
  letting callers force specific columns to numeric (rather than categorical)
  HiPlot axis scaling. Defaults to all columns in `df`, so axes are numeric
  by default unless overridden.

### Fixed
- `parasolpy.util.script_local_path` docstring now explains that writing a
  Windows absolute path as a plain string literal (e.g. `"C:\Games\data.csv"`)
  triggers `SyntaxWarning: invalid escape sequence` at Python parse time, and
  documents the three safe alternatives: raw strings (`r"C:\Games\data.csv"`),
  forward slashes (`"C:/Games/data.csv"`), and doubled backslashes
  (`"C:\\Games\\data.csv"`).  The same guidance has been added to
  `docs/user-guide/utilities.md`.

## [0.4.1] — 2026-07-17

### Added
- `parasolpy.borg_runtime` module: Borg MOEA runtime-file parser
  (`parse_borg_runtime`, `parse_borg_runtime_metadata`), per-solution
  archive lifespan analysis (`solution_lifespans`) — all exported from the
  package root.
- `plot_archive_lifespans` in `parasolpy.plotting`: survival chart of
  archive solution birth/death with an archive-size panel, shaded
  restart windows.
- Bundled sample `parasolpy/data/RunTime_NorthSouth.txt`, demo script
  `examples/07_borg_archive_lifespan.py`, and `tests/test_borg_runtime.py`.
- `tests/test_util_paths.py` covering `script_local_path` and `ensure_dir`,
  and an expanded Paths section in `docs/user-guide/utilities.md`.

### Fixed
- `parasolpy.util.script_local_path` now normalizes backslash separators,
  so Windows-style relative paths (e.g. `data\input.csv`) resolve
  correctly on all platforms.

## [0.4.0] — 2026-05-29

### Added
- `parasolpy.rdf` module: RiverWare RDF parser (`parse_rdf`, `list_slots`,
  exported from the package root) and RDF-to-CSV converter, exposed via the
  new `parasolpy-rdf` CLI entry point with `info`/`slots`/`convert`
  subcommands (wide/stacked/long/enriched output formats).
- Bundled synthetic sample `parasolpy/data/sample_traces.rdf`, a Windows
  CLI demo (`examples/rdf_cli_commands.bat`), and `tests/test_rdf.py`.

### Changed
- Improved date parsing to handle single-digit days and months.

### Fixed
- Hardened robustness across `nowak`, `interactive`, `tradeoff`, `ism`,
  and `dash_tools`.
- Renamed a variable to avoid scope confusion with the builtin `id`.
- Docstring typo fix.

## [0.3.0] — 2026-05-14

### Added
- Sphinx documentation site with Read the Docs config (`.readthedocs.yaml`),
  GitHub Actions docs workflow, user guide, API reference (autosummary),
  examples, quickstart, installation, and CLI pages.
- `parasolpy.moea` module scaffold.
- `examples/_unrefactored_example_scripts/` legacy scripts ported from
  `borgRWproblems` pending refactor.
- `.gitattributes` enforcing LF line endings.

### Changed
- Repo-wide line-ending renormalization to LF.
- Expanded `.gitignore`.
- Docstring fixes in `parasolpy.ism.create_ism_traces` and
  `parasolpy.tradeoff.parallel_plot_hp`.

## [0.2.1] — 2026-04-23

### Changed
- Release workflow migrated to GitHub Actions + PyPI Trusted Publishing.
  Publishing now triggers on publishing a GitHub Release; no PyPI API
  token needed. New `scripts/release.py` (and `release.sh` wrapper)
  bump `pyproject.toml`, roll `CHANGELOG.md` `[Unreleased]` into a
  dated section, update link refs, commit, and push the tag.

## [0.2.0] — 2026-04-23

### Added
- 43-test suite covering `reservoir`, `ism`, `nowak`, `util`, and package
  import/version checks.
- PEP 257 docstrings, module-level docs, and `help()` API reference across
  all public modules.
- Water treatment worked example ported from original parasol project.
- `lxml >=4.9.0` dependency (required by `beautifulsoup4` XML parsing paths).

### Changed
- Dependency upper bounds relaxed: `pandas`, `plotly`, `dash`, `numpy`,
  `scikit-learn`, and `seaborn` now allow the next major version.
- Repo URL corrected from `kasprzyk-research/parasolpy` to
  `jrkasprzyk/parasolpy` in `pyproject.toml` and all references.
- PyPI classifiers, keywords, and `[project.urls]` block added to
  `pyproject.toml` for richer package discovery.

## [0.1.1] — 2026-04-22

### Changed
- `parasolpy.__version__` is now read from installed package metadata via
  `importlib.metadata`, so `pyproject.toml` is the single source of truth
  for the version number.

### Added
- `RELEASING.md` documenting the Poetry-based release workflow (version
  bump, build, publish to PyPI, tagging, and GitHub Releases), including
  notes on per-machine token setup and token scopes.
- `CHANGELOG.md` (this file).
- Expanded `README.md` with installation instructions, a module overview
  table, and pointers to the examples and release workflow.

## [0.1.0] — 2026-04-22

### Added
- `parasolpy-tradeoff` CLI entry point for launching the interactive
  parallel-coordinates tradeoff explorer against a results folder.
- Supporting documentation for the CLI in `README.md`.

## [0.0.2] — 2026-04-21

Initial PyPI release.

### Added
- Initial public release to PyPI.
- Core modules: `reservoir` (sequent-peak sizing), `ism` (index-sequential
  trace ensembles), `nowak` (nonparametric streamflow disaggregation),
  `tradeoff` (epsilon non-dominance, KMeans, HiPlot parallel coordinates),
  `plotting` (heatmap, spaghetti, fan chart, seasonality, exceedance),
  `dash_tools` (interactive Dash app), `interactive` (terminal prompts),
  `file_processing` (Borg / RiverWare CSV normalization), and `util`
  (path helpers, unit conversions, XML config parsing).
- Self-contained example scripts under `examples/`.

[Unreleased]: https://github.com/jrkasprzyk/parasolpy/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/jrkasprzyk/parasolpy/compare/v0.4.3...v0.5.0
[0.4.3]: https://github.com/jrkasprzyk/parasolpy/compare/v0.4.2...v0.4.3
[0.4.2]: https://github.com/jrkasprzyk/parasolpy/compare/v0.4.1...v0.4.2
[0.4.1]: https://github.com/jrkasprzyk/parasolpy/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/jrkasprzyk/parasolpy/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jrkasprzyk/parasolpy/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/jrkasprzyk/parasolpy/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/jrkasprzyk/parasolpy/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/jrkasprzyk/parasolpy/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jrkasprzyk/parasolpy/releases/tag/v0.1.0
[0.0.2]: https://pypi.org/project/parasolpy/0.0.2/
