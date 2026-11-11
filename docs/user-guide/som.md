# Self-Organizing Maps

The `parasolpy.som` module is a small self-organizing map (SOM) toolkit built on [MiniSom](https://github.com/JustGlowing/minisom). It extracts the core of the MAPS framework:

> Pernat, M. R., Kasprzyk, J. R., Zagona, E. A. (2026). Negotiating management alternatives under uncertain future conditions using a self-organizing map framework. *Environmental Modelling & Software* 205, 107118. <https://doi.org/10.1016/j.envsoft.2026.107118>

The steps are composable. The core is three calls (fit, assign, layer); every other step is a standalone function or a short recipe, and you use only the ones you need.

```python
from parasolpy.som import (
    append_som,
    fit_som,
    plot_som_layer,
    plot_som_node_traces,
    som_quality,
    sweep_som,
)
```

These six functions are also available from the package root (`from parasolpy import ...`).

| Function | Returns |
|---|---|
| `fit_som(data, x_dim, y_dim, ...)` | The trained `MiniSom` instance. |
| `append_som(df, som, data, column="Neuron")` | `df` with `Neuron`, `Neuron_x`, `Neuron_y`, and `Neuron_dist` added in place. |
| `som_quality(som, data)` | Dict with `quantization_error`, `topographic_error`, and `explained_variance` (percent). |
| `sweep_som(data, n_samples=50, ...)` | DataFrame with one row per sampled map configuration. |
| `plot_som_layer(som, values, output_dir, ...)` | `(fig, ax, output_path)`: one value per neuron on the map grid. |
| `plot_som_node_traces(som, trace_df, assignments, output_dir, ...)` | `(fig, axes, output_path)`: one panel of member traces per neuron. |

## Core

### Fit

```python
Z = (features - features.mean()) / features.std()   # you scale; see below
som = fit_som(Z, x_dim=13, y_dim=4)
```

`data` has one row per sample and one column per feature. `fit_som` returns the `MiniSom` object itself, so the whole MiniSom API stays available.

**Scaling is your job.** The package does no feature scaling, because the right scaling is a domain decision (z-score, min-max, weighted feature groups). SOM distances are Euclidean, so an unscaled wide column dominates the map. `fit_som` warns when column standard deviations differ by more than a factor of 100, or when a column has zero variance, and does nothing else about it. Pass the same scaled table to `fit_som` and `append_som`.

**Map size.** `x_dim` and `y_dim` are required. A common starting point (Vesanto) is about `5 * sqrt(n_rows)` neurons in total; `sweep_som` handles the search from there. The default `sigma=1.5` suits maps near 13 × 4, so grow `sigma` with the map.

**Training.** Training uses MiniSom's online algorithm for `num_epochs` passes over the data in random order. Weights start on the plane of the first two principal components (`init="pca"`) or on random rows (`init="random"`). `random_seed` defaults to `0`, so repeated runs give identical maps.

### Assign

```python
append_som(info, som, Z)
```

`append_som` finds each row's best-matching neuron and writes four columns to `info`:

| Column | Meaning |
|---|---|
| `Neuron` | 0-based neuron ID. |
| `Neuron_x`, `Neuron_y` | Grid position of the neuron. |
| `Neuron_dist` | Euclidean distance from the row to its neuron's weight vector, in the scaled feature space. |

Rows of `data` align with rows of `df` by position; only the lengths are checked.

Neuron IDs have x varying fastest: `Neuron = Neuron_y * x_dim + Neuron_x`. IDs run left to right along the bottom row of the map, then upward, and `divmod(neuron, x_dim)` gives `(Neuron_y, Neuron_x)`. This matches the 0-based `Cluster` column of `append_Kmeans`. Figures in the MAPS paper use 1-based IDs.

### Layer

```python
plot_som_layer(
    som,
    info.groupby("Neuron")["demand"].mean(),
    "examples/_output",
    filename="som_layer_demand.png",
    colorbar_label="Demand (MAF/yr)",
)
```

`plot_som_layer` draws one value per neuron. `values` is either a `pd.Series` indexed by `Neuron` (so any `groupby("Neuron")` summary works directly) or an array of shape `(x_dim, y_dim)`. Neurons missing from the Series, or NaN in the array, are drawn light gray. `annotate="value"` prints the value in each cell and `annotate="id"` prints the neuron ID.

Any variable can be layered, including ones the SOM never saw during training. That is the point of the MAPS workflow: train on one set of features, then read other variables off the same map.

## Quality

```python
som_quality(som, Z)
# {'quantization_error': 1.46, 'topographic_error': 0.054, 'explained_variance': 91.6}
```

- `quantization_error`: mean distance from each row to its neuron.
- `topographic_error`: fraction of rows whose best and second-best neurons are not adjacent on the map.
- `explained_variance`: `100 * (1 - Σ‖x − w_bmu‖² / Σ‖x − x̄‖²)`, in percent.

## Member Traces

```python
plot_som_node_traces(
    som,
    trace_df,                              # rows = time, columns = traces
    info.set_index("Trace")["Neuron"],     # trace column -> Neuron
    "examples/_output",
    background_df=trace_df,
)
```

When the samples are time series, `plot_som_node_traces` draws one panel per neuron with that neuron's member traces, their mean in black, and (optionally) a background ensemble in gray. `trace_df` uses the same wide format as the [plotting](plotting.md) helpers. Panels are laid out so neuron 0 is bottom-left, as in `plot_som_layer`. The panel grid is rectangular: on a hexagonal map, the half-cell offset of alternate rows is not drawn. Panels get small on large maps; the plot suits maps up to roughly 100 neurons.

## Optional Recipes

Each recipe stands alone. All assume `som`, the scaled table `Z`, and a DataFrame `df` that has been through `append_som`.

### 1. Sweep and non-dominated selection

```python
from parasolpy.tradeoff import label_eps_nd, parallel_plot_hp

obj_names = ["n_neurons", "explained_variance", "topographic_error"]
obj_directions = ["minimize", "maximize", "minimize"]

sweep = sweep_som(Z, n_samples=50)
sweep = label_eps_nd(sweep, "eps_nd", obj_names, obj_directions, [1, 1.0, 0.01])
parallel_plot_hp(sweep[sweep["eps_nd"]], obj_names, obj_directions).to_html("sweep.html")
```

`sweep_som` draws a Latin hypercube over `y_dim`, the aspect ratio `x_dim / y_dim`, `sigma` as a fraction of the longer side, and the neighborhood function. It fits and scores each configuration and returns the table. It selects nothing: explained variance rises with the number of neurons, so the choice is a tradeoff among map size, explained variance, and topographic error.

### 2. Typical members of each neuron

```python
typical = df.sort_values("Neuron_dist").groupby("Neuron").head(3)
```

The rows closest to each neuron's weight vector.

### 3. Spread members of each neuron

```python
spread = df.sample(frac=1, random_state=0).groupby("Neuron").head(3)
```

A random draw within each neuron: shuffle the rows, then keep up to three per neuron. Neurons that hold fewer than three rows contribute all of them, which `df.groupby("Neuron").sample(n=3)` would reject with an error.

### 4. Grouping neurons into clusters

```python
from sklearn.cluster import AgglomerativeClustering

n_features = som.get_weights().shape[2]
codes = som.get_weights().transpose(1, 0, 2).reshape(-1, n_features)  # row i = neuron i
neuron_cluster = AgglomerativeClustering(n_clusters=5).fit_predict(codes)
df["Cluster"] = neuron_cluster[df["Neuron"]]
```

The `transpose(1, 0, 2)` puts the weight vectors in neuron-ID order.

### 5. U-matrix, hits, and component planes

All three are layers:

```python
plot_som_layer(som, som.distance_map(), out, filename="umatrix.png")
plot_som_layer(som, df["Neuron"].value_counts(), out, filename="hits.png", annotate="value")
plot_som_layer(som, som.get_weights()[:, :, k], out, filename=f"component_{k}.png")
```

### 6. Training on a subsample

```python
train = Z.sample(50_000, random_state=0)
som = fit_som(train, 20, 12)
append_som(df, som, Z)          # assigns every row
```

Online training is practical up to roughly 50,000–100,000 rows. For larger tables, fit on a random subsample and assign all rows afterward.

### 7. Projecting new data

```python
mean, std = features.mean(), features.std()       # from the training set
Z = (features - mean) / std
som = fit_som(Z, 13, 4)

Z_new = (new_features - mean) / std               # reuse mean and std
append_som(new_df, som, Z_new)
```

New rows must go through the training set's scaling. Recomputing the mean and standard deviation on the new data puts it in a different space, and the assignments are then meaningless.

### 8. Feature-group weights

```python
Z_weighted = Z.copy()
Z_weighted[group_a] *= 0.25
Z_weighted[group_b] *= 0.75
som = fit_som(Z_weighted, 13, 4)
```

Multiplying columns before fitting weights their contribution to the distance. MAPS used min-max scaling with group weights of 0.25 and 0.75. Group weights can legitimately trip the scaling warning from `fit_som`.

## Example Script

```bash
python examples/08_som_maps_demo.py
```

The script runs the core and a sweep on a 500-member Colorado River Basin sample. See the [SOM example](../examples/som.md).
