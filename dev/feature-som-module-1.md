---
goal: Add a small, composable Self-Organizing Map (SOM) toolkit to parasolpy, built on MiniSom
version: 2.1
date_created: 2026-11-11
last_updated: 2026-11-11
owner: Joseph Kasprzyk
status: 'Completed'
tags: [feature, architecture, som, maps]
---

# Introduction

![Status: Completed](https://img.shields.io/badge/status-Completed-brightgreen)

This plan adds `parasolpy/som.py`, a general SOM toolkit that extracts the core of the MAPS framework (Pernat, Kasprzyk, Zagona 2026, *Environmental Modelling & Software* 205, 107118, doi:10.1016/j.envsoft.2026.107118; code at https://github.com/madrpernat/MAPS-Framework).

The core is three steps:

1. **Fit** a SOM to a table of features (`fit_som`).
2. **Assign** each row to a neuron (`append_som`).
3. **Layer** any per-row variable onto the map as a per-neuron summary (`plot_som_layer`).

Every other MAPS step (hyperparameter tuning, subsampling, grouping neurons) is optional. Each optional step is a standalone function or a short documented recipe, and users compose the steps they need.

Version 2.0 of this plan records the outcome of a design review held on 2026-11-11. The public surface is six functions (version 1.0 had twelve). Section 7 lists the facts verified during that review. Section 3 lists what was cut and the trigger for adding each item later.

## 1. Requirements & Constraints

- **REQ-001**: `fit_som(data, x_dim, y_dim, ...)` trains a MiniSom and returns the `MiniSom` instance.
- **REQ-002**: `append_som(df, som, data, column="Neuron")` assigns each row of `data` to its best-matching neuron and writes four columns to `df`: `Neuron`, `Neuron_x`, `Neuron_y`, `Neuron_dist`. The same function assigns rows the SOM never trained on.
- **REQ-003**: Neuron IDs are 0-based with x varying fastest: `Neuron = Neuron_y * x_dim + Neuron_x`. IDs run left to right along the bottom row, then upward. The inverse is `divmod(neuron, x_dim)` → `(Neuron_y, Neuron_x)`. This matches the 0-based `Cluster` column of `append_Kmeans`. MAPS paper figures use 1-based IDs; the docs say so in one sentence.
- **REQ-004**: The package performs no feature scaling. The caller scales `data` and passes the same scaled table to `fit_som` and `append_som`. Scaling choices (z-score, min-max, feature-group weights) are domain decisions; MAPS itself used min-max scaling with group weights 0.25 / 0.75.
- **REQ-005**: `fit_som` emits `warnings.warn` when the ratio of the largest to the smallest column standard deviation exceeds 100, and when any column has zero variance. The message tells the caller to scale features.
- **REQ-006**: `som_quality(som, data)` returns a dict with `quantization_error`, `topographic_error`, and `explained_variance` (percent) computed as `100 * (1 - Σ‖x − w_bmu‖² / Σ‖x − x̄‖²)`.
- **REQ-007**: `sweep_som(data, n_samples, ...)` samples configurations by Latin hypercube, fits and scores each, and returns one DataFrame row per configuration. It contains no selection logic. Selection uses the existing `label_eps_nd` and `parallel_plot_hp` on three objectives: minimize `n_neurons`, maximize `explained_variance`, minimize `topographic_error`.
- **REQ-008**: `plot_som_layer(som, values, output_dir, ...)` draws one value per neuron on the map grid. `values` is a `pd.Series` indexed by `Neuron`, or an array of shape `(x_dim, y_dim)`.
- **REQ-009**: `plot_som_node_traces(som, trace_df, assignments, output_dir, ...)` draws one small subplot per neuron with that neuron's member traces.
- **REQ-010**: Plot functions follow `parasolpy/plotting.py`: `(..., output_dir, filename=..., figsize=..., dpi=200)`, save through `_save_figure`, return `(fig, ax_or_axes, output_path)`.
- **CON-001**: Python `>=3.12`, Poetry-managed. All commands run through `poetry run`.
- **CON-002**: MiniSom is a core dependency, pinned `minisom (>=2.3.6,<3.0.0)`. Already added to `pyproject.toml` and `poetry.lock`.
- **CON-003**: Design target is training on up to about 50,000 rows. Larger ensembles train on a random subsample and assign every row afterward.
- **CON-004**: Training uses MiniSom's online algorithm with `use_epochs=True`. One code path.
- **CON-005**: `random_seed` defaults to `0` in every function that trains a SOM, so figures and reported numbers are reproducible by default.
- **CON-006**: The CRB example is a MAPS-style demo on a 500-SOW subsample. It makes no claim to reproduce the paper's figures or the R `kohonen` results.
- **GUD-001**: No classes or wrapper objects around `MiniSom`.
- **GUD-002**: New code uses only existing dependencies plus MiniSom: `numpy`, `pandas`, `matplotlib`, `scipy` (`scipy.stats.qmc.LatinHypercube`).
- **GUD-003**: Use MiniSom's public API only (`winner`, `quantization`, `quantization_error`, `topographic_error`, `distance_map`, `get_weights`, `get_euclidean_coordinates`).
- **PAT-001**: Public functions get Google-style docstrings (Args / Returns).
- **PAT-002**: Public names are exported in `parasolpy/__init__.py`, listed in `__all__`, and named on a `som :` line in `__help__`.
- **PAT-003**: Deliberate simplifications carry a `# ponytail:` comment that names the ceiling and the upgrade path.

## 2. Implementation Steps

### Implementation Phase 1: Fit, assign, quality

- GOAL-001: `parasolpy.som` can train a SOM, assign rows, and score the map.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Add `minisom (>=2.3.6,<3.0.0)` to `[project].dependencies` and update `poetry.lock`. | ✅ | 2026-11-11 |
| TASK-002 | Create `parasolpy/som.py` with a module docstring that cites the MAPS paper and states the fit → assign → layer core. Imports: `warnings`, `numpy as np`, `pandas as pd`, `from minisom import MiniSom`. | ✅ | 2026-11-11 |
| TASK-003 | Implement `fit_som(data, x_dim, y_dim, sigma=1.5, learning_rate=0.5, neighborhood_function="gaussian", topology="hexagonal", num_epochs=10, init="pca", random_seed=0)`. Convert with `X = np.asarray(data, dtype=float)`. Run the REQ-005 scale check on `X.std(axis=0)`. Build `MiniSom(x_dim, y_dim, X.shape[1], sigma=..., learning_rate=..., neighborhood_function=..., topology=..., random_seed=...)`. `init="pca"` calls `som.pca_weights_init(X)`; `init="random"` calls `som.random_weights_init(X)`; any other value raises `ValueError`. Train with `som.train(X, num_epochs, random_order=True, use_epochs=True)`. Return `som`. The docstring states that the caller scales features, that `sigma` should grow with map size, and that `random_seed=0` makes runs repeatable. | ✅ | 2026-11-11 |
| TASK-004 | Add a `# ponytail:` comment in `fit_som`: online training costs about 30 µs per row per epoch, so the practical ceiling is about 1e5 rows; upgrade path is to fit on `data.sample(n)` and assign all rows with `append_som`. Note that `MiniSom.train_batch_offline` (new in 2.3.6) is seed-independent given PCA init and is the candidate if order-independence is wanted. | ✅ | 2026-11-11 |
| TASK-005 | Implement `append_som(df, som, data, column="Neuron")`. Convert `X = np.asarray(data, dtype=float)`. Raise `ValueError` when `len(X) != len(df)`. Read `x_dim = som.get_weights().shape[0]`. Compute winners with `[som.winner(x) for x in X]` and distances with `np.linalg.norm(X - som.quantization(X), axis=1)`. Write `df[f"{column}_x"]`, `df[f"{column}_y"]`, `df[column] = y * x_dim + x` (int), and `df[f"{column}_dist"]` (float). Return `df` (mutated in place). Rows of `data` align with rows of `df` by position. | ✅ | 2026-11-11 |
| TASK-006 | Add a `# ponytail:` comment in `append_som`: the `som.winner` loop handles about 1e6 rows per minute; upgrade path is `scipy.spatial.distance.cdist(X, codes).argmin(axis=1)`. | ✅ | 2026-11-11 |
| TASK-007 | Implement `som_quality(som, data)` → `dict` with `quantization_error` (`som.quantization_error(X)`), `topographic_error` (`som.topographic_error(X)`), and `explained_variance` (REQ-006, using `som.quantization(X)`). | ✅ | 2026-11-11 |
| TASK-008 | Export `fit_som`, `append_som`, `som_quality` from `parasolpy/__init__.py`; add them to `__all__` under a `# som` comment; add a `som :` line to `__help__`. | ✅ | 2026-11-11 |
| TASK-009 | Write the Phase 1 tests in `tests/test_som.py` (TEST-001 through TEST-007). | ✅ | 2026-11-11 |

### Implementation Phase 2: Sweep and plots

- GOAL-002: Users can explore map configurations and draw layers and per-neuron traces.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-010 | Implement `sweep_som(data, n_samples=50, y_dim_range=(3, 6), x_y_ratio_range=(1.0, 4.0), sigma_fraction_range=(0.1, 0.5), neighborhood_functions=("gaussian", "bubble"), topology="hexagonal", num_epochs=10, random_seed=0)`. Draw `scipy.stats.qmc.LatinHypercube(d=4, seed=random_seed).random(n_samples)`. Map the four unit columns to: integer `y_dim` (inclusive range), float `x_y_ratio`, float `sigma_fraction`, and a categorical neighborhood function. Derive `x_dim = max(y_dim, round(y_dim * x_y_ratio))` and `sigma = sigma_fraction * max(x_dim, y_dim)`. For `"bubble"`, set `sigma = max(1, round(sigma))` because MiniSom warns on non-integer bubble widths. Fit each configuration with `fit_som(..., random_seed=random_seed)`, score with `som_quality`, and return a DataFrame with columns `x_dim, y_dim, n_neurons, sigma, neighborhood_function, quantization_error, topographic_error, explained_variance`. | ✅ | 2026-11-11 |
| TASK-011 | In the `sweep_som` docstring, state that `explained_variance` rises with `n_neurons`, so selection is a multi-objective choice, and show the `label_eps_nd` call from REQ-007. | ✅ | 2026-11-11 |
| TASK-012 | Implement `plot_som_layer(som, values, output_dir, filename="som_layer.png", annotate=None, cmap="viridis", colorbar_label=None, vmin=None, vmax=None, figsize=None, dpi=200)`. Accept `values` as a Series indexed by `Neuron` (reindex to `range(x_dim * y_dim)`, then map to grid with REQ-003) or as an array of shape `(x_dim, y_dim)`. Read cell centers from `som.get_euclidean_coordinates()` and use them unchanged. Draw one `matplotlib.patches.RegularPolygon` per neuron: hexagonal topology uses `numVertices=6, radius=0.95 / np.sqrt(3)`; rectangular topology uses `numVertices=4, radius=0.95 / np.sqrt(2), orientation=np.pi / 4`. Neurons with NaN draw in light gray. `annotate="value"` prints the value in each cell; `annotate="id"` prints the neuron ID. Set equal aspect, add a colorbar, and return `(fig, ax, output_path)`. | ✅ | 2026-11-11 |
| TASK-013 | Implement `plot_som_node_traces(som, trace_df, assignments, output_dir, filename="som_node_traces.png", background_df=None, sharey=True, color="tab:blue", figsize=None, dpi=200)`. `trace_df` uses the `plotting.py` wide format (rows = time, columns = traces). `assignments` is a Series mapping trace column → `Neuron`. Build a `y_dim × x_dim` subplot grid and place neuron `(x, y)` at row `y_dim - 1 - y`, column `x`, so the layout matches `plot_som_layer`. In each panel, draw `background_df` (when given) in light gray, then member traces in `color`, then the member mean in black. Title each panel with its neuron ID. Validate with `_validate_trace_dataframe`. The docstring states that the grid is rectangular and omits the hexagonal half-row offset. Return `(fig, axes, output_path)`. | ✅ | 2026-11-11 |
| TASK-014 | Import `_save_figure`, `_resolve_output_path`, and `_validate_trace_dataframe` from `parasolpy.plotting`. | ✅ | 2026-11-11 |
| TASK-015 | Export `sweep_som`, `plot_som_layer`, `plot_som_node_traces`; update `__all__` and `__help__`. | ✅ | 2026-11-11 |
| TASK-016 | Write the Phase 2 tests (TEST-008 through TEST-012). | ✅ | 2026-11-11 |

### Implementation Phase 3: Example, docs, prototype retirement, release

- GOAL-003: A runnable CRB demo and a docs page cover the module; `dev/minisomwrapper/` is gone.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-017 | `git mv` `dev/minisomwrapper/examples/crbexample/500_sow_cumulative_supply.csv` and `500_sow_info.csv` to `examples/data/crb_500_sow/`. Remove the legacy `Neuron` and `Cluster` columns from the moved `500_sow_info.csv`; they describe a map trained in R. | ✅ | 2026-11-11 |
| TASK-018 | Create `examples/data/crb_500_sow/README.md`: 500 states of the world subsampled from the MAPS ensemble; units MAF; years 2027–2056; `supply[t, k] = InitCombinedStorage_k + cumsum(LeesFerryFlow[Trace_k] − demand_k)`; column `k` of the supply file corresponds to row `k` of the info file; citation of Pernat et al. (2026) and the MAPS-Framework repository (MIT). | ✅ | 2026-11-11 |
| TASK-019 | Create `examples/08_som_maps_demo.py`. Load both CSVs. Set the supply columns to `info["Trace"]` with a comment noting positional alignment, then transpose so rows are SOWs. Z-score the 30 year columns explicitly. Run `fit_som(Z, 13, 4)`, `append_som(info, som, Z)`, and print `som_quality`. Write layers for `Median`, `demand`, and `InitCombinedStorage` via `info.groupby("Neuron")[col].mean()`, a hits layer via `info["Neuron"].value_counts()` with `annotate="value"`, and `plot_som_node_traces` with the full ensemble as `background_df`. Run `sweep_som(Z, n_samples=30)`, label with `label_eps_nd`, and print the non-dominated rows. Use `script_local_path` and write to `examples/_output/`. | ✅ | 2026-11-11 |
| TASK-020 | Create `docs/user-guide/som.md`. Open with the MAPS citation and a sentence that the steps are composable. Section "Core": fit → assign → layer, including a scaling note and the Vesanto starting hint for map size (about `5 * sqrt(n_rows)` neurons). Section "Optional recipes", each standalone: (1) sweep and non-dominated selection; (2) typical members, `df.sort_values("Neuron_dist").groupby("Neuron").head(n)`; (3) spread members, `df.groupby("Neuron").sample(...)` with a guard for neurons holding fewer than `n` rows; (4) grouping neurons with `sklearn.cluster.AgglomerativeClustering` on `som.get_weights().transpose(1, 0, 2).reshape(-1, n_features)`; (5) U-matrix (`som.distance_map()`), hits (`value_counts()`), and component planes (`som.get_weights()[:, :, k]`) through `plot_som_layer`; (6) training on a subsample and assigning all rows; (7) projecting new data with the training set's scaling; (8) feature-group weights by multiplying columns before fitting. | ✅ | 2026-11-11 |
| TASK-021 | Create `docs/examples/som.md` for the demo script and `docs/api/generated/parasolpy.som.rst` matching the existing generated files. Add the pages to the toctrees in `docs/index.md`, `docs/examples/index.md`, and `docs/api/index.rst`. | ✅ | 2026-11-11 |
| TASK-022 | Delete `dev/minisomwrapper/` in full after TASK-019 runs cleanly. Git history keeps the prototype. | ✅ | 2026-11-11 |
| TASK-023 | Add the `parasolpy.som` entry under `### Added` in `CHANGELOG.md`, note the new MiniSom core dependency, and bump the version to `0.5.0` in `pyproject.toml`. | ✅ | 2026-11-11 |

## 3. Alternatives

Decisions made in the 2026-11-11 review, each with the trigger for revisiting.

- **ALT-001 Named plot wrappers** (`plot_som_umatrix`, `plot_som_hits`, `plot_som_component_planes`): replaced by `plot_som_layer` plus docs recipes. Add a wrapper when users need sample-marker overlays on the U-matrix or a multi-panel component grid in one figure.
- **ALT-002 `cluster_som_nodes` and a `Cluster` column**: cut. MAPS analyzes at neuron level throughout. The docs carry a three-line recipe. Add a function when the recipe gets copied into a second project.
- **ALT-003 `som_representatives` and conditioned Latin hypercube sampling**: replaced by the `Neuron_dist` column and two pandas recipes. cLHS needs a new dependency or about 100 lines of simulated annealing. Add it when random within-neuron sampling proves inadequate on a real case.
- **ALT-004 Scaling inside the package** (`standardize=True`): cut. It blocked projection of new data and imposed z-scoring on workflows that need other scaling.
- **ALT-005 One-call fit-and-append** (the `append_Kmeans` shape): replaced by the fit / assign split so one function serves training rows and new rows.
- **ALT-006 R `kohonen` numbering and numeric parity**: dropped. A differently trained map gives different neurons, so matching IDs would mislead.
- **ALT-007 Kaski-Lagus error and an `activation_distance` sweep axis**: dropped. MAPS abandoned both; Euclidean distance is fixed.
- **ALT-008 Successive non-dominated pruning**: skipped. It exists to make tuning affordable on millions of rows; at the CON-003 scale every configuration trains on the full table.
- **ALT-009 Automatic map-size heuristic**: skipped. `x_dim` and `y_dim` are required arguments; the docs give a starting hint and `sweep_som` handles the search.
- **ALT-010 Batch training** (`train_batch_offline`): deferred until it has more field time. Measured on synthetic 500×30 data: 78.6 % explained variance and topographic error 0.058, against 82.9 % and 0.114 for online training.
- **ALT-011 MiniSom as an optional extra**: rejected. `parasolpy/__init__.py` imports every submodule eagerly, so an extra would need import guards and a doubled test matrix. If MiniSom loses maintenance, vendor its single MIT file.
- **ALT-012 Wrapper class around MiniSom, `rpy2`, `sklearn-som`, `somoclu`**: rejected in version 1.0 of this plan; unchanged.
- **ALT-013 Interactive Plotly/Dash map** (hover a neuron to see traces and metadata): deferred until the static API settles; fits `dash_tools.py`.

Uses that need no new code once Phases 1–2 land: Pareto-set clustering colored by `Neuron` in `parallel_plot_hp`; scenario discovery via `pd.crosstab` on neurons; `parse_rdf` output fed to `fit_som`; projecting ISM or Nowak synthetic traces onto a map trained on observed data; mapping `borg_runtime` archive snapshots onto a fixed map.

## 4. Dependencies

- **DEP-001**: `minisom (>=2.3.6,<3.0.0)`. Pure Python, single file, needs only numpy. Installed.
- **DEP-002**: `scipy` (existing) for `scipy.stats.qmc.LatinHypercube`.
- **DEP-003**: `numpy`, `pandas`, `matplotlib` (existing).
- **DEP-004**: `parasolpy.plotting` private helpers `_save_figure`, `_resolve_output_path`, `_validate_trace_dataframe`.
- **DEP-005**: `parasolpy.tradeoff.label_eps_nd` and `parallel_plot_hp`, used by the example and docs for sweep selection.

## 5. Files

- **FILE-001**: `parasolpy/som.py`: new module.
- **FILE-002**: `parasolpy/__init__.py`: exports, `__all__`, `__help__`.
- **FILE-003**: `pyproject.toml`, `poetry.lock`: MiniSom dependency (done) and version bump to `0.5.0`.
- **FILE-004**: `tests/test_som.py`: new tests.
- **FILE-005**: `examples/08_som_maps_demo.py`: new example.
- **FILE-006**: `examples/data/crb_500_sow/500_sow_cumulative_supply.csv`, `500_sow_info.csv`, `README.md`.
- **FILE-007**: `docs/user-guide/som.md`, `docs/examples/som.md`, `docs/api/generated/parasolpy.som.rst`, `docs/index.md`, `docs/examples/index.md`, `docs/api/index.rst`.
- **FILE-008**: `CHANGELOG.md`.
- **FILE-009**: `dev/minisomwrapper/**`: removed.

## 6. Testing

Tests live in `tests/test_som.py` and use synthetic data: three Gaussian blobs, 30 rows each, 4 features, from `np.random.default_rng(0)`. Plot tests use the Agg backend. Run with `poetry run pytest tests/test_som.py`.

- **TEST-001**: `fit_som` returns a `MiniSom` whose `get_weights().shape == (x_dim, y_dim, n_features)`.
- **TEST-002**: `fit_som(init="bogus")` raises `ValueError`.
- **TEST-003**: `fit_som` warns when one column is multiplied by 1000, warns on a zero-variance column, and stays silent on z-scored data.
- **TEST-004**: `append_som` adds four columns; `0 <= Neuron < x_dim * y_dim`; `Neuron == Neuron_y * x_dim + Neuron_x`; `Neuron_dist >= 0`. A length mismatch between `df` and `data` raises `ValueError`.
- **TEST-005**: A SOM trained on 60 rows assigns the 30 held-out rows through `append_som` and yields valid IDs.
- **TEST-006**: Two `fit_som` calls with the same `random_seed` give identical weights. On a 6×4 map, each blob occupies a neuron set disjoint from the other blobs.
- **TEST-007**: `som_quality` returns the three keys and `0 <= explained_variance <= 100`.
- **TEST-008**: `sweep_som(n_samples=3)` returns 3 rows with the REQ-007 columns; every `"bubble"` row has an integer `sigma >= 1`; `x_dim >= y_dim` in every row.
- **TEST-009**: `plot_som_layer` writes a file in `tmp_path` and returns a 3-tuple for a Series input, an `(x_dim, y_dim)` array input, each `annotate` mode, and both topologies.
- **TEST-010**: Hex geometry guard: for a hexagonal map, patch centers drawn by `plot_som_layer` in adjacent rows differ in y by `sqrt(3) / 2` (tolerance 1e-9).
- **TEST-011**: `plot_som_node_traces` writes a file, returns axes of shape `(y_dim, x_dim)`, and accepts `background_df`.
- **TEST-012**: `tests/test_package.py` passes, confirming the new names import from `parasolpy`.
- **TEST-013**: `poetry run python examples/08_som_maps_demo.py` exits 0 and writes its PNGs to `examples/_output/`.

## 7. Risks & Assumptions

**Verified on 2026-11-11 against MiniSom 2.3.6**

- **FACT-001**: MiniSom already scales hexagonal y-coordinates by `sqrt(3) / 2`; the measured row pitch is 0.866. The prototype `crbexample.py` applied that factor a second time, which gives a pitch of 0.75 and overlapping rows. `plot_som_layer` uses the coordinates unchanged, and TEST-010 guards this.
- **FACT-002**: `use_epochs` and hexagonal `topographic_error` exist from 2.3.2 onward; `topographic_error` and `distance_map` are byte-identical between 2.3.2 and 2.3.6. Version 2.3.3 changed `decay_function` from a callable to a string name and added `sigma_decay_function`. The 2.3.6 floor gives one API.
- **FACT-003**: Online training of a 13×4 map on 500×30 data for 10 epochs takes 0.15 s. A 50-configuration sweep on the CRB data takes roughly 8 s; 50,000 rows take roughly 15 s per fit.
- **FACT-004**: Same seed gives identical weights; different seeds give different weights.
- **FACT-005**: MiniSom warns when `neighborhood_function="bubble"` has a non-integer sigma or sigma below 1.
- **FACT-006**: Example data provenance. The 500-SOW supply file reconstructs from the public MAPS-Framework raw data to within 5e-8 using the TASK-018 formula. `Trace`, `Scenario`, `TraceNumber`, and `Median` match `natural_flow_traces.csv`; all 500 `(mead, powell, demand)` rows appear in `initial_condition_demand_samples.csv`. The paper's Data Availability statement points to that MIT-licensed repository, and parasolpy is MIT.
- **FACT-007**: The scenario mix in the 500 SOWs is lopsided (`npc_cmip3` 432, `npc_adjusted` 37, `cmip5` 20, `paleo_drought` 10, `stress_test` 1), so the demo layers use `Median`, `demand`, and `InitCombinedStorage`.

**Risks**

- **RISK-001**: A caller forgets to scale features and one column dominates distances. Mitigation: REQ-005 warning, explicit scaling in every example, docstring note.
- **RISK-002**: A caller applies different scaling at fit time and at assignment time. Mitigation: the docs recipe for projecting new data reuses the training mean and standard deviation by name.
- **RISK-003**: `sigma=1.5` suits maps near 13×4 and is narrow for much larger maps. Mitigation: docstring note and `sigma_fraction` in `sweep_som`.
- **RISK-004**: `plot_som_node_traces` produces very small panels on large maps. Mitigation: default `figsize` scales with `(x_dim, y_dim)`; the docstring suggests it for maps up to roughly 100 neurons.

**Assumptions**

- **ASSUMPTION-001**: Users train on at most about 50,000 rows (CON-003). Larger native fits are out of scope for this version.
- **ASSUMPTION-002**: Rows of `data` and `df` passed to `append_som` share order. The function checks length only.

**Open decisions**

None. All decisions from version 1.0 (DEC-001 through DEC-006) are resolved in Sections 1 and 3.

## 8. Related Specifications / Further Reading

- Pernat, M. R., Kasprzyk, J. R., Zagona, E. A. (2026). Negotiating management alternatives under uncertain future conditions using a self-organizing map framework. *Environmental Modelling & Software* 205, 107118. https://doi.org/10.1016/j.envsoft.2026.107118
- MAPS-Framework code and data: https://github.com/madrpernat/MAPS-Framework
- MiniSom source and docs: https://github.com/JustGlowing/minisom
- Kohonen, T. (2013). Essentials of the self-organizing map. *Neural Networks* 37, 52–65.
- Existing parasolpy conventions: `parasolpy/tradeoff.py` (`append_Kmeans`, `label_eps_nd`, `parallel_plot_hp`), `parasolpy/plotting.py` (`(fig, ax, output_path)` contract)

## 9. Implementation Notes

Recorded on 2026-11-11 after implementation. All 23 tasks are complete; TEST-001 through TEST-013 pass (157 tests in the full suite), and the Sphinx docs build without warnings.

**Deviations from the plan**

- **NOTE-001 (TASK-020, recipe 3)**: The spread-members recipe is `df.sample(frac=1, random_state=0).groupby("Neuron").head(n)`. The planned `groupby("Neuron").sample(...)` raises on neurons holding fewer than `n` rows, and the guarded `groupby("Neuron").apply(...)` form drops the `Neuron` column under pandas 3.
- **NOTE-002 (TASK-003)**: `fit_som` also raises `ValueError` when `data` is not 2-D or contains NaN or infinite values. MiniSom otherwise trains silently to NaN weights.
- **NOTE-003 (TASK-012)**: `plot_som_layer` raises `ValueError` for an `annotate` value other than `None`, `"value"`, or `"id"`, and for an array whose shape is not `(x_dim, y_dim)`. Annotation text switches between black and white by cell luminance.
- **NOTE-004 (TASK-013)**: `plot_som_node_traces` draws only the `trace_df` columns that have an entry in `assignments`, and raises `ValueError` when none match.
- **NOTE-005 (TASK-019)**: The demo also writes `examples/_output/som_sweep.csv`. Its figures and that CSV are committed, as for the other examples.
- **NOTE-006 (REQ-005)**: The zero-variance warning and the spread-ratio warning are separate; the ratio is computed over the non-constant columns.

**Measured on the CRB demo** (13×4 hexagonal, 500 SOWs, defaults): explained variance 91.6 %, topographic error 0.054, quantization error 1.459, all 52 neurons occupied. The 30-configuration sweep yields 12 non-dominated configurations at epsilons `[1, 1.0, 0.01]`. The whole script runs in about 30 s.

**Open follow-ups**

- **TODO-001**: `pytest` is not a declared dependency, so `poetry run pytest` (CON-001, RELEASING.md) fails on a clean install by falling through to a global pytest. Add a Poetry dev dependency group.
- **TODO-002**: `parasolpy/__init__.py` was stored with CRLF line endings; the commit that added the exports normalized it to LF per `.gitattributes`, so that diff touches every line.
