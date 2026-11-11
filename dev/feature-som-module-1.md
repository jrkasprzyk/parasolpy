---
goal: Add Self-Organizing Map (SOM) clustering, diagnostics, and plotting to parasolpy, built on MiniSom
version: 1.0
date_created: 2026-11-11
last_updated: 2026-11-11
owner: Joseph Kasprzyk
status: 'Planned'
tags: [feature, architecture, clustering, som, brainstorm]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan moves the SOM prototype code in `dev/minisomwrapper/` into a supported module, `parasolpy/som.py`. The prototype covers two jobs. `examples/basic_usage.py` is the MiniSom seeds tutorial (a rectangular U-matrix with labelled hits). `examples/crbexample/crbexample.py` clusters 500 Colorado River Basin states of the world (SOWs) by their 30-year cumulative supply traces on a 13x4 hexagonal map. The CRB folder also holds results made outside Python, apparently with R `kohonen` + `aweSOM`:

- `param_metrics.csv`: 500-row random hyperparameter sweep with columns `x_dim, y_dim, x_y_ratio, n_neurons, radius, dist_fnc, neighbor_fnc, radius_fraction, err.quant, err.varratio, err.topo, err.kaski`.
- `best_params.yaml`: the chosen configuration (`x_dim: 13`, `y_dim: 4`, `neighbor_func: gaussian`, `dist_func: sumofsquares`, `radius: 10.5357`, `radius_fraction: 0.9647`).
- `500_sow_info.csv`: per-SOW metadata (`Scenario` ∈ {cmip5, npc_adjusted, npc_cmip3, paleo_drought, stress_test}, hydrologic statistics, `Neuron` ∈ 1..52, `Cluster` ∈ 0..11).

The goal is to make that whole workflow (fit, assign, diagnose, sweep, second-stage cluster, plot, pick representatives) run in Python inside parasolpy. It should follow the existing conventions: `append_Kmeans`-style column appending, and `plotting.py`-style `(fig, ax, output_path)` returns. Section 3 holds the brainstorm of SOM uses beyond the prototype, and Section 7 lists the open decisions that need the owner's input.

## 1. Requirements & Constraints

- **REQ-001**: Provide `parasolpy.som.append_som(df, x_dim, y_dim, feature_columns=None, standardize=True, **som_kwargs)` that fits a MiniSom and appends integer node columns to `df`, mirroring `parasolpy.tradeoff.append_Kmeans` (`parasolpy/tradeoff.py:417`).
- **REQ-002**: Node numbering must match the R `kohonen` convention used in `500_sow_info.csv` so legacy results stay comparable. For MiniSom node `(i, j)` (`i` = x index in `0..x_dim-1`, `j` = y index in `0..y_dim-1`), `Neuron = j * x_dim + i + 1` (1-based, x varies fastest).
- **REQ-003**: Support `topology="hexagonal"` (default, matches CRB) and `topology="rectangular"` (matches seeds example).
- **REQ-004**: Provide quality metrics: quantization error, topographic error, and explained variance (%) as `100 * (1 - Σ‖x − w_bmu‖² / Σ‖x − x̄‖²)`, the equivalent of `err.varratio`.
- **REQ-005**: Provide a hyperparameter sweep that returns a `pd.DataFrame` with columns `x_dim, y_dim, n_neurons, sigma, learning_rate, neighborhood_function, activation_distance, quantization_error, topographic_error, explained_variance`.
- **REQ-006**: Provide second-stage clustering of SOM codebook vectors into `num_clusters` groups (reproduces the `Neuron → Cluster` mapping in `500_sow_info.csv`).
- **REQ-007**: Provide representative-member selection: for each non-empty node, return the row index of the member closest to that node's codebook vector.
- **REQ-008**: Plot functions must follow `parasolpy/plotting.py`: signature `(..., output_dir, filename=..., figsize=..., dpi=200)`, save via `_save_figure`, return `(fig, ax, output_path)`.
- **CON-001**: Python `>=3.12`, Poetry-managed. All commands run through `poetry run`.
- **CON-002**: Use MiniSom (single-file, numpy-only). No R or rpy2 dependency.
- **CON-003**: Results will not reproduce R `kohonen` numerically (different RNG, update rules, and radius schedule). Only qualitative agreement is expected.
- **CON-004**: `random_seed` must be exposed on every function that trains a SOM. Default `0`.
- **GUD-001**: Do not add classes or wrapper objects around `MiniSom`. Return the `MiniSom` instance directly.
- **GUD-002**: Use `sklearn` (already a core dependency) for standardization helpers and agglomerative clustering. Add no other new libraries.
- **PAT-001**: Public functions get Google-style docstrings (Args / Returns), matching the existing modules.
- **PAT-002**: New public names get exported in `parasolpy/__init__.py` and listed in `__help__`.

## 2. Implementation Steps

### Implementation Phase 1: Dependency and core fit/assign

- GOAL-001: `parasolpy.som` exists, can fit a SOM, and can append node assignments to a DataFrame.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Run `poetry add "minisom>=2.3.2,<3.0.0"` (2.3.2 is the version pinned in `dev/minisomwrapper/minisomwrapper_env.yaml`). Confirm that `pyproject.toml` `[project].dependencies` and `poetry.lock` are both updated. Placement (core vs. extra) depends on DEC-001; the default is core. | | |
| TASK-002 | Create `parasolpy/som.py` with a module docstring and these imports: `numpy as np`, `pandas as pd`, `from minisom import MiniSom`. | | |
| TASK-003 | Implement `fit_som(data, x_dim, y_dim, sigma=1.5, learning_rate=0.5, neighborhood_function="gaussian", topology="hexagonal", activation_distance="euclidean", num_iteration=1000, init="pca", random_seed=0)`. `data` is `np.ndarray` or `pd.DataFrame` (converted with `np.asarray(data, dtype=float)`). Build `MiniSom(x_dim, y_dim, data.shape[1], sigma=..., learning_rate=..., neighborhood_function=..., topology=..., activation_distance=..., random_seed=...)`. If `init == "pca"`, call `som.pca_weights_init(data)`. If `init == "random"`, call `som.random_weights_init(data)`. Any other value raises `ValueError`. Then call `som.train(data, num_iteration, random_order=True)` and return `som`. | | |
| TASK-004 | Implement private `_node_number(i, j, x_dim)`, which returns `j * x_dim + i + 1` (REQ-002). Implement the public `node_to_grid(neuron, x_dim)`, which returns `((neuron - 1) % x_dim, (neuron - 1) // x_dim)`. | | |
| TASK-005 | Implement `append_som(df, x_dim, y_dim, feature_columns=None, standardize=True, column="Neuron", **som_kwargs)`. Select `X = df[feature_columns]` (or the whole `df` when `None`). If `standardize`, set `X = (X - X.mean()) / X.std(ddof=0)` (matches the prototype's `np.std` default). Call `som = fit_som(X, x_dim, y_dim, **som_kwargs)` and compute the winners with `[som.winner(x) for x in X.to_numpy()]`. Write `df[column]` (int, REQ-002 numbering), `df[f"{column}_x"]`, and `df[f"{column}_y"]`. Return `(df, som)` (in-place mutation, same contract as `append_Kmeans`). | | |
| TASK-006 | Export `fit_som`, `append_som`, and `node_to_grid` from `parasolpy/__init__.py`, and add a `som :` line to `__help__`. | | |

### Implementation Phase 2: Diagnostics and hyperparameter sweep

- GOAL-002: Users can score a SOM and replace the R `param_metrics.csv` workflow in Python.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Implement `som_quality(som, data)` → `dict` with keys `quantization_error` (`som.quantization_error(data)`), `topographic_error` (`som.topographic_error(data)`), and `explained_variance` (REQ-004, computed with `som.quantization(data)` as the BMU weights). | | |
| TASK-008 | Implement `sweep_som(data, n_samples=100, x_dim_range=(3, 40), y_dim_range=(2, 8), sigma_range=(0.5, 10.0), neighborhood_functions=("gaussian", "bubble"), activation_distances=("euclidean", "manhattan"), topology="hexagonal", num_iteration=1000, random_seed=0)`. Use `rng = np.random.default_rng(random_seed)` to draw `n_samples` configurations uniformly (integer dims, float sigma, categorical choices). Fit each with `fit_som(..., random_seed=random_seed)`, score it with `som_quality`, and return one DataFrame row per configuration (REQ-005 columns). Clamp `sigma` to `< max(x_dim, y_dim)`; otherwise MiniSom warns and the neighborhood saturates. | | |
| TASK-009 | Add a `# ponytail:` comment on `sweep_som` noting that the Kaski-Lagus error (`err.kaski`) is deliberately omitted. It needs shortest-path distances over the codebook graph; add it if model selection actually needs it (see DEC-004). | | |
| TASK-010 | Export `som_quality` and `sweep_som` from `parasolpy/__init__.py` and update `__help__`. | | |

### Implementation Phase 3: Second-stage clustering and representatives

- GOAL-003: Reduce the map to a few macro-clusters and pick one representative member per node.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-011 | Implement `cluster_som_nodes(som, num_clusters, linkage="ward")` → `np.ndarray` of shape `(x_dim * y_dim,)` that maps `Neuron - 1` to a cluster label (0-based). Use `sklearn.cluster.AgglomerativeClustering(n_clusters=num_clusters, linkage=linkage)` on `som.get_weights().reshape(-1, n_features)`. The reshape order must match REQ-002: reshape after `np.transpose(weights, (1, 0, 2))` so the flat index is `j * x_dim + i`. | | |
| TASK-012 | Extend `append_som` with `num_clusters=None`. When it is set, also write `df["Cluster"] = labels[df[column] - 1]` and return `(df, som)` unchanged otherwise. | | |
| TASK-013 | Implement `som_representatives(som, data, index=None)` → `pd.Series` indexed by `Neuron` whose values are the row label (from `index`, or the positional index) of the member with the smallest Euclidean distance to its node's codebook vector. Empty nodes are omitted. | | |
| TASK-014 | Export `cluster_som_nodes` and `som_representatives` and update `__help__`. | | |

### Implementation Phase 4: Plotting

- GOAL-004: Static SOM figures that match `parasolpy/plotting.py` conventions.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-015 | In `parasolpy/som.py`, implement private `_draw_grid(ax, som, values, cmap, alpha)`. For hexagonal topology, draw `matplotlib.patches.RegularPolygon` hexagons at `som.get_euclidean_coordinates()` with y scaled by `np.sqrt(3) / 2` and `radius=0.95 / np.sqrt(3)` (lifted from `crbexample.py`). For rectangular topology, use `ax.pcolormesh(values.T)`. Return the `ScalarMappable` for the colorbar. | | |
| TASK-016 | Implement `plot_som_umatrix(som, output_dir, filename="som_umatrix.png", data=None, labels=None, cmap="Blues", figsize=(10, 6), dpi=200)`. Background = `som.distance_map()`. If `data` is given, overlay a jittered marker per sample at its BMU, colored by `labels` (categorical) when given. Return `(fig, ax, output_path)`. | | |
| TASK-017 | Implement `plot_som_hits(som, data, output_dir, filename="som_hits.png", ...)`. Color = `som.activation_response(data)` and annotate each cell with its count. | | |
| TASK-018 | Implement `plot_som_component_planes(som, feature_names, output_dir, filename="som_components.png", ncols=4, ...)`. Draw one subplot per feature, colored by `som.get_weights()[:, :, k]`. Return `(fig, axes, output_path)`. | | |
| TASK-019 | Implement `plot_som_node_traces(trace_df, assignments, x_dim, y_dim, output_dir, filename="som_node_traces.png", ...)`. `trace_df` uses the `plotting.py` wide format (rows = time, columns = traces). `assignments` is a `pd.Series` that maps trace column → `Neuron`. Draw a `y_dim × x_dim` subplot grid (row `y_dim-1-j` so `j=0` sits at the bottom), with grey member traces and a black mean per node. Reuse `_validate_trace_dataframe` from `parasolpy/plotting.py`. | | |
| TASK-020 | Import `_save_figure` and `_resolve_output_path` from `parasolpy.plotting`. Do not duplicate them. | | |
| TASK-021 | Export all four `plot_som_*` functions and update `__help__`. | | |

### Implementation Phase 5: Example, docs, prototype retirement

- GOAL-005: A runnable CRB example replaces `dev/minisomwrapper`, and the docs cover the module.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-022 | Move `dev/minisomwrapper/examples/crbexample/500_sow_cumulative_supply.csv` and `500_sow_info.csv` to `examples/data/crb_500_sow/` with `git mv`. Do not move `_scaled.csv` (`append_som(standardize=True)` replaces it). Do not move `param_metrics.csv` (`sweep_som` regenerates it). | | |
| TASK-023 | Create `examples/08_som_sow_clustering.py`. Load the supply CSV and transpose it (rows = SOW, columns = year). Join `500_sow_info.csv` without its `Neuron` and `Cluster` columns. Run `sweep_som(n_samples=20)` and print the top 5 rows by `explained_variance`. Run `append_som(x_dim=13, y_dim=4, num_clusters=12)`. Print `pd.crosstab(df["Cluster"], df["Scenario"])`. Write `plot_som_umatrix` (labels = `Scenario`), `plot_som_hits`, and `plot_som_node_traces` to `examples/_output/`. Print `som_representatives(...)`. Use `script_local_path` for all paths, following existing examples. | | |
| TASK-024 | Create `docs/user-guide/som.md` and `docs/examples/som.md`, and add both to their toctrees in `docs/index.md` / `docs/examples/index.md`. Run `sphinx-apidoc` or add `docs/api/generated/parasolpy.som.rst`, matching the existing generated files. | | |
| TASK-025 | Add a `## [Unreleased]` → `### Added` entry for `parasolpy.som` to `CHANGELOG.md`. | | |
| TASK-026 | Delete `dev/minisomwrapper/` (`__init__.py`, `minisomwrapper_env.yaml`, `examples/basic_usage.py`, `examples/crbexample/crbexample.py`, `best_params.yaml`, `param_metrics.csv`, `500_sow_cumulative_supply_scaled.csv`) after TASK-023 runs successfully. This is gated on DEC-005. | | |

## 3. Alternatives

- **ALT-001**: Wrap MiniSom in a `SomModel` class that holds the scaler, codebook, and assignments. Rejected: it adds a second API to learn, and `MiniSom` is already a usable object. If DEC-003 needs to map new data, the scaler can be returned instead.
- **ALT-002**: Call R `kohonen`/`aweSOM` through `rpy2` to exactly reproduce the legacy results. Rejected: it requires an R install, Windows support is fragile, and CON-003 accepts qualitative parity.
- **ALT-003**: `sklearn-som` or `somoclu`. Rejected: `sklearn-som` has no hexagonal topology or U-matrix. `somoclu` needs compiled binaries and is overkill for maps of 500 rows and about 50 nodes.
- **ALT-004**: Put SOM functions in `parasolpy/tradeoff.py` beside `append_Kmeans`. Rejected: `tradeoff.py` is already about 750 lines, and SOM use spans traces as well as tradeoffs. A separate `som.py` keeps the imports local.
- **ALT-005**: Interactive Plotly/Dash SOM (hover a node to see its traces and SOW metadata). Deferred; it fits the existing `dash_tools.py` well and is a good Phase 6 once the static API settles.

**Brainstorm: other SOM uses parasolpy could enable** (candidates only; none are scheduled)

- **IDEA-001 Pareto-set clustering**: `append_som(solutions, feature_columns=objective_names)`, then `parallel_plot_hp(..., color_by="Neuron")`. This is a topology-preserving alternative to `append_Kmeans`. It costs no extra code beyond Phase 1, just a docs example.
- **IDEA-002 Representative-SOW subsetting**: `som_representatives` reduces 500 SOWs to ≤52 for expensive RiverWare/Borg re-evaluation. It is in scope (TASK-013).
- **IDEA-003 Scenario discovery**: cross-tab nodes/clusters against robustness metrics or vulnerability flags (`pd.crosstab` / `groupby`). It needs only docs, no new function.
- **IDEA-004 RDF → SOM pipeline**: `parse_rdf` → wide trace DataFrame → transpose → `append_som`. This ties `rdf.py` to SOM; it is a docs example.
- **IDEA-005 Generated-trace validation**: train on observed or paleo traces, then project ISM (`ism.py`) or Nowak (`nowak.py`) synthetic traces onto the map and compare hit distributions. This needs DEC-003 (persisting the scaler).
- **IDEA-006 Borg archive evolution**: map `borg_runtime` snapshots onto a fixed SOM to see how the archive moves across objective space over NFE.
- **IDEA-007 Kaski-Lagus error and other quality metrics** (DEC-004).

## 4. Dependencies

- **DEP-001**: `minisom>=2.3.2,<3.0.0` (pure Python and numpy; required for `topology="hexagonal"`, `get_euclidean_coordinates`, and `convert_map_to_euclidean`).
- **DEP-002**: `scikit-learn` (existing core dependency) for `AgglomerativeClustering`.
- **DEP-003**: `matplotlib` and `numpy`/`pandas` (existing).
- **DEP-004**: `parasolpy.plotting` private helpers `_save_figure`, `_resolve_output_path`, and `_validate_trace_dataframe` (TASK-019, TASK-020).

## 5. Files

- **FILE-001**: `parasolpy/som.py`: new module (all phases).
- **FILE-002**: `parasolpy/__init__.py`: exports and `__help__` (TASK-006, 010, 014, 021).
- **FILE-003**: `pyproject.toml`, `poetry.lock`: MiniSom dependency (TASK-001).
- **FILE-004**: `tests/test_som.py`: new tests (Section 6).
- **FILE-005**: `examples/08_som_sow_clustering.py`: new example (TASK-023).
- **FILE-006**: `examples/data/crb_500_sow/500_sow_cumulative_supply.csv`, `500_sow_info.csv`: moved data (TASK-022).
- **FILE-007**: `docs/user-guide/som.md`, `docs/examples/som.md`, `docs/api/generated/parasolpy.som.rst`, `docs/index.md`, `docs/examples/index.md` (TASK-024).
- **FILE-008**: `CHANGELOG.md` (TASK-025).
- **FILE-009**: `dev/minisomwrapper/**`: removed (TASK-026).

## 6. Testing

All tests live in `tests/test_som.py` and use synthetic data: three Gaussian blobs, 30 rows each, 4 features, built with `np.random.default_rng(0)`. Run them with `poetry run pytest tests/test_som.py`.

- **TEST-001**: `fit_som` returns `MiniSom`, and `get_weights().shape == (x_dim, y_dim, n_features)`.
- **TEST-002**: `fit_som(init="bogus")` raises `ValueError`.
- **TEST-003**: `append_som` adds `Neuron`, `Neuron_x`, and `Neuron_y`. The values satisfy `1 <= Neuron <= x_dim*y_dim` and `Neuron == Neuron_y * x_dim + Neuron_x + 1`.
- **TEST-004**: The round trip `node_to_grid(_node_number(i, j, x), x) == (i, j)` holds for all nodes of a 13x4 grid.
- **TEST-005**: Determinism: two `append_som` calls with the same `random_seed` produce identical `Neuron` columns.
- **TEST-006**: Blob separation: with a 6x4 map, each blob's rows occupy a node set disjoint from the other blobs' rows.
- **TEST-007**: `som_quality` returns all three keys, and `0 <= explained_variance <= 100`.
- **TEST-008**: `sweep_som(n_samples=3)` returns 3 rows with the REQ-005 columns and `sigma < max(x_dim, y_dim)` in every row.
- **TEST-009**: `cluster_som_nodes(som, 3)` returns length `x_dim*y_dim` with exactly 3 unique labels. On blob data, `append_som(num_clusters=3)` gives an adjusted Rand index ≥ 0.9 against the true blob labels (`sklearn.metrics.adjusted_rand_score`).
- **TEST-010**: Every value in `som_representatives` is a member of its own node.
- **TEST-011**: Each `plot_som_*` function, run in `tmp_path`, returns a 3-tuple whose path exists. Use the `matplotlib.use("Agg")` pattern from the existing plotting tests, or set it at module top.
- **TEST-012**: `tests/test_package.py` still passes, which means the new names are importable from `parasolpy`.
- **TEST-013**: `poetry run python examples/08_som_sow_clustering.py` exits with code 0 and writes the three PNGs to `examples/_output/`.

## 7. Risks & Assumptions

- **RISK-001**: The R `best_params.yaml` values do not translate one-to-one. R `radius` uses kohonen's linear-decay radius in grid units, while MiniSom `sigma` is a Gaussian width with asymptotic decay. R `dist_fnc: sumofsquares` maps to MiniSom `activation_distance="euclidean"` (same BMU ordering). Mitigation: re-select parameters with `sweep_som` instead of copying R values.
- **RISK-002**: MiniSom's hexagonal `distance_map` and `topographic_error` behavior changed across 2.3.x releases. Mitigation: pin `>=2.3.2` and run TEST-011 in CI.
- **RISK-003**: `sweep_som` at 500 samples × 1000 iterations on 500×30 data takes minutes. Mitigation: the example uses `n_samples=20`, and the docs note the cost. Add `joblib` parallelism only if users ask for it.
- **ASSUMPTION-001**: The legacy `Neuron` column in `500_sow_info.csv` uses kohonen's 1-based, x-fastest numbering. This is consistent with its observed range of 1..52 on a 13x4 map, but it has not been verified against the R script.
- **ASSUMPTION-002**: `Cluster` in `500_sow_info.csv` (0..11) came from hierarchical clustering of the codebook. TASK-011 assumes Ward linkage.

**Open decisions (owner input needed before execution)**

- **DEC-001**: Should MiniSom be a core dependency (default; it is tiny and numpy-only) or an optional extra `parasolpy[som]` with a lazy import and a helpful `ImportError`?
- **DEC-002**: Should `append_som` default to `standardize=True` (z-score, matching the prototype), or should it require callers to pre-scale?
- **DEC-003**: Does the package need to project *new* data onto a trained map (IDEA-005)? If yes, `append_som` must also return the column means/stds, or `fit_som` must accept a fitted `sklearn.preprocessing.StandardScaler`. If no, skip it.
- **DEC-004**: Is `err.kaski` needed for model selection? If yes, add it to `som_quality` using `scipy.sparse.csgraph.shortest_path` on the codebook adjacency graph.
- **DEC-005**: Should `dev/minisomwrapper/` be deleted after migration, or kept as a historical reference?
- **DEC-006**: Which of IDEA-001…IDEA-007 should be promoted into scheduled phases? The owner noted that more functionality is coming, so list it here.

## 8. Related Specifications / Further Reading

- MiniSom source and docs: https://github.com/JustGlowing/minisom
- Kohonen, T. (2001). *Self-Organizing Maps*, 3rd ed. Springer.
- R `kohonen` package (legacy numbering and radius semantics): https://cran.r-project.org/package=kohonen
- R `aweSOM` quality measures (`err.quant`, `err.varratio`, `err.topo`, `err.kaski`): https://cran.r-project.org/package=aweSOM
- Existing parasolpy conventions: `parasolpy/tradeoff.py` (`append_Kmeans`), `parasolpy/plotting.py` (`(fig, ax, output_path)` contract)
