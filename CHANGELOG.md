# Changelog

All notable changes to `parasolpy` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (with
the understanding that during the `0.x` series, minor bumps may contain
breaking changes).

## [Unreleased]

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

[Unreleased]: https://github.com/jrkasprzyk/parasolpy/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/jrkasprzyk/parasolpy/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jrkasprzyk/parasolpy/releases/tag/v0.1.0
[0.0.2]: https://pypi.org/project/parasolpy/0.0.2/
