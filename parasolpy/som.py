"""Self-organizing map (SOM) toolkit built on MiniSom.

This module extracts the core of the MAPS framework:

    Pernat, M. R., Kasprzyk, J. R., Zagona, E. A. (2026). Negotiating
    management alternatives under uncertain future conditions using a
    self-organizing map framework. Environmental Modelling & Software 205,
    107118. https://doi.org/10.1016/j.envsoft.2026.107118

The core is three steps:

1. Fit a SOM to a table of features (``fit_som``).
2. Assign each row to a neuron (``append_som``).
3. Layer any per-row variable onto the map as a per-neuron summary
   (``plot_som_layer``).

Everything else (``som_quality``, ``sweep_som``, ``plot_som_node_traces``) is
optional and composes with the core.

Conventions:

- The package does no feature scaling. Scale ``data`` yourself and pass the
  same scaled table to ``fit_som`` and ``append_som``.
- Neuron IDs are 0-based with x varying fastest:
  ``Neuron = Neuron_y * x_dim + Neuron_x``. IDs run left to right along the
  bottom row of the map, then upward. The inverse is
  ``Neuron_y, Neuron_x = divmod(neuron, x_dim)``.
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import RegularPolygon
from minisom import MiniSom
from scipy.stats import qmc

from parasolpy.plotting import (
    _resolve_output_path,
    _save_figure,
    _validate_trace_dataframe,
)

_SCALE_RATIO_LIMIT = 100.0


def _as_feature_array(data):
    """Convert a feature table to a 2-D float array."""
    X = np.asarray(data, dtype=float)
    if X.ndim != 2:
        raise ValueError("Input 'data' must be 2-D (rows = samples, columns = features).")
    return X


def _warn_if_unscaled(X):
    """Warn when feature columns have zero variance or very different spreads."""
    std = X.std(axis=0)
    zero = std == 0
    if zero.any():
        warnings.warn(
            f"{int(zero.sum())} feature column(s) have zero variance and carry no "
            "information for the SOM. Drop them or scale features before fitting.",
            stacklevel=3,
        )
    nonzero = std[~zero]
    if nonzero.size and nonzero.max() / nonzero.min() > _SCALE_RATIO_LIMIT:
        warnings.warn(
            "Feature standard deviations differ by more than a factor of "
            f"{_SCALE_RATIO_LIMIT:g}; the widest column will dominate SOM distances. "
            "Scale features (for example z-score or min-max) before fitting.",
            stacklevel=3,
        )


def fit_som(
    data,
    x_dim,
    y_dim,
    sigma=1.5,
    learning_rate=0.5,
    neighborhood_function="gaussian",
    topology="hexagonal",
    num_epochs=10,
    init="pca",
    random_seed=0,
):
    """Train a self-organizing map and return the MiniSom instance.

    The caller scales features. This function does no scaling; it only warns
    when column spreads differ by more than a factor of 100 or a column has
    zero variance. Pass the same scaled table to ``append_som``.

    The default ``sigma=1.5`` suits maps near 13 x 4. Grow ``sigma`` with map
    size (``sweep_som`` parameterizes it as a fraction of the longer side).

    Args:
        data (array-like): Feature table, shape (n_rows, n_features). Already
            scaled by the caller.
        x_dim (int): Number of neurons along x.
        y_dim (int): Number of neurons along y.
        sigma (float, optional): Initial neighborhood radius in grid units.
        learning_rate (float, optional): Initial learning rate.
        neighborhood_function (str, optional): MiniSom neighborhood function,
            for example "gaussian" or "bubble".
        topology (str, optional): "hexagonal" or "rectangular".
        num_epochs (int, optional): Number of passes over ``data``.
        init (str, optional): "pca" (deterministic, spans the first two
            principal components) or "random" (samples rows of ``data``).
        random_seed (int, optional): Seed for sample order and random init.
            The default 0 makes runs repeatable.

    Returns:
        MiniSom: The trained map. Weights have shape (x_dim, y_dim, n_features).

    Raises:
        ValueError: If ``data`` is not 2-D, contains non-finite values, or
            ``init`` is not "pca" or "random".
    """
    X = _as_feature_array(data)
    if not np.isfinite(X).all():
        raise ValueError("Input 'data' contains NaN or infinite values.")
    if init not in ("pca", "random"):
        raise ValueError(f"Input 'init' must be 'pca' or 'random', got {init!r}.")
    _warn_if_unscaled(X)

    som = MiniSom(
        x_dim,
        y_dim,
        X.shape[1],
        sigma=sigma,
        learning_rate=learning_rate,
        neighborhood_function=neighborhood_function,
        topology=topology,
        random_seed=random_seed,
    )
    if init == "pca":
        som.pca_weights_init(X)
    else:
        som.random_weights_init(X)

    # ponytail: online training costs about 30 µs per row per epoch, so the
    # practical ceiling is about 1e5 rows. Upgrade path: fit on data.sample(n)
    # and assign all rows with append_som. MiniSom.train_batch_offline (new in
    # 2.3.6) is seed-independent given PCA init and is the candidate if
    # order-independence is wanted.
    som.train(X, num_epochs, random_order=True, use_epochs=True)
    return som


def append_som(df, som, data, column="Neuron"):
    """Assign each row of ``data`` to its best-matching neuron.

    Writes four columns to ``df`` (mutated in place): ``Neuron`` (0-based ID,
    ``Neuron_y * x_dim + Neuron_x``), ``Neuron_x``, ``Neuron_y``, and
    ``Neuron_dist`` (Euclidean distance from the row to its neuron's weight
    vector, in the scaled feature space). Works for rows the SOM trained on
    and for new rows alike, provided ``data`` uses the training scaling.

    Rows of ``data`` align with rows of ``df`` by position; only the lengths
    are checked.

    Args:
        df (pd.DataFrame): Table that receives the columns.
        som (MiniSom): Trained map from ``fit_som``.
        data (array-like): Scaled feature table, shape (len(df), n_features).
        column (str, optional): Base name of the new columns.

    Returns:
        pd.DataFrame: ``df``, with the four columns added.

    Raises:
        ValueError: If ``data`` and ``df`` have different numbers of rows.
    """
    X = _as_feature_array(data)
    if len(X) != len(df):
        raise ValueError(
            f"'data' has {len(X)} rows but 'df' has {len(df)}; they must align by position."
        )
    x_dim = som.get_weights().shape[0]

    # ponytail: the som.winner loop handles about 1e6 rows per minute. Upgrade
    # path: scipy.spatial.distance.cdist(X, codes).argmin(axis=1).
    winners = np.array([som.winner(x) for x in X], dtype=int).reshape(-1, 2)
    dist = np.linalg.norm(X - som.quantization(X), axis=1)

    df[f"{column}_x"] = winners[:, 0]
    df[f"{column}_y"] = winners[:, 1]
    df[column] = winners[:, 1] * x_dim + winners[:, 0]
    df[f"{column}_dist"] = dist
    return df


def som_quality(som, data):
    """Score a trained map against a feature table.

    Args:
        som (MiniSom): Trained map from ``fit_som``.
        data (array-like): Scaled feature table, shape (n_rows, n_features).

    Returns:
        dict: ``quantization_error`` (mean distance from each row to its
        neuron), ``topographic_error`` (fraction of rows whose best and
        second-best neurons are not adjacent), and ``explained_variance`` in
        percent, ``100 * (1 - sum ||x - w_bmu||^2 / sum ||x - mean||^2)``.
    """
    X = _as_feature_array(data)
    residual = ((X - som.quantization(X)) ** 2).sum()
    total = ((X - X.mean(axis=0)) ** 2).sum()
    return {
        "quantization_error": float(som.quantization_error(X)),
        "topographic_error": float(som.topographic_error(X)),
        "explained_variance": float(100.0 * (1.0 - residual / total)),
    }


def sweep_som(
    data,
    n_samples=50,
    y_dim_range=(3, 6),
    x_y_ratio_range=(1.0, 4.0),
    sigma_fraction_range=(0.1, 0.5),
    neighborhood_functions=("gaussian", "bubble"),
    topology="hexagonal",
    num_epochs=10,
    random_seed=0,
):
    """Fit and score a Latin hypercube sample of map configurations.

    Four parameters are sampled: integer ``y_dim``, the aspect ratio
    ``x_dim / y_dim``, ``sigma`` as a fraction of the longer map side, and the
    neighborhood function. Each configuration is fit with ``fit_som`` and
    scored with ``som_quality``.

    This function does no selection. ``explained_variance`` rises with
    ``n_neurons``, so choosing a map is a multi-objective decision: minimize
    ``n_neurons``, maximize ``explained_variance``, minimize
    ``topographic_error``. Label the non-dominated configurations with::

        from parasolpy.tradeoff import label_eps_nd

        sweep = sweep_som(Z)
        sweep = label_eps_nd(
            sweep,
            "eps_nd",
            ["n_neurons", "explained_variance", "topographic_error"],
            ["minimize", "maximize", "minimize"],
            [1, 1.0, 0.01],
        )

    and inspect them with ``parallel_plot_hp``.

    Args:
        data (array-like): Scaled feature table, shape (n_rows, n_features).
        n_samples (int, optional): Number of configurations.
        y_dim_range (tuple, optional): Inclusive integer range for ``y_dim``.
        x_y_ratio_range (tuple, optional): Range for ``x_dim / y_dim``.
        sigma_fraction_range (tuple, optional): Range for
            ``sigma / max(x_dim, y_dim)``.
        neighborhood_functions (sequence of str, optional): Candidates.
        topology (str, optional): "hexagonal" or "rectangular".
        num_epochs (int, optional): Passes over ``data`` per fit.
        random_seed (int, optional): Seed for the Latin hypercube and for
            every fit.

    Returns:
        pd.DataFrame: One row per configuration with columns ``x_dim``,
        ``y_dim``, ``n_neurons``, ``sigma``, ``neighborhood_function``,
        ``quantization_error``, ``topographic_error``, ``explained_variance``.
    """
    X = _as_feature_array(data)
    unit = qmc.LatinHypercube(d=4, seed=random_seed).random(n_samples)

    y_lo, y_hi = y_dim_range
    n_funcs = len(neighborhood_functions)
    rows = []
    for u_y, u_ratio, u_sigma, u_func in unit:
        y_dim = min(y_hi, y_lo + int(u_y * (y_hi - y_lo + 1)))
        ratio = x_y_ratio_range[0] + u_ratio * (x_y_ratio_range[1] - x_y_ratio_range[0])
        fraction = sigma_fraction_range[0] + u_sigma * (
            sigma_fraction_range[1] - sigma_fraction_range[0]
        )
        func = neighborhood_functions[min(n_funcs - 1, int(u_func * n_funcs))]

        x_dim = max(y_dim, round(y_dim * ratio))
        sigma = fraction * max(x_dim, y_dim)
        if func == "bubble":
            # MiniSom warns on non-integer bubble widths and widths below 1.
            sigma = float(max(1, round(sigma)))

        som = fit_som(
            X,
            x_dim,
            y_dim,
            sigma=sigma,
            neighborhood_function=func,
            topology=topology,
            num_epochs=num_epochs,
            random_seed=random_seed,
        )
        rows.append(
            {
                "x_dim": x_dim,
                "y_dim": y_dim,
                "n_neurons": x_dim * y_dim,
                "sigma": sigma,
                "neighborhood_function": func,
                **som_quality(som, X),
            }
        )

    return pd.DataFrame(rows)


def _values_to_grid(values, x_dim, y_dim):
    """Return per-neuron values as a float array of shape (x_dim, y_dim)."""
    if isinstance(values, pd.Series):
        flat = values.reindex(range(x_dim * y_dim)).to_numpy(dtype=float)
        return flat.reshape(y_dim, x_dim).T

    grid = np.asarray(values, dtype=float)
    if grid.shape != (x_dim, y_dim):
        raise ValueError(
            f"Array 'values' must have shape (x_dim, y_dim) = {(x_dim, y_dim)}, "
            f"got {grid.shape}. Pass a pd.Series indexed by Neuron for per-neuron values."
        )
    return grid


def plot_som_layer(
    som,
    values,
    output_dir,
    filename="som_layer.png",
    annotate=None,
    cmap="viridis",
    colorbar_label=None,
    vmin=None,
    vmax=None,
    figsize=None,
    dpi=200,
):
    """Draw one value per neuron on the map grid.

    This is the single map plot: any per-neuron quantity is a layer. Typical
    inputs are ``df.groupby("Neuron")[col].mean()`` (a variable layered onto
    the map), ``df["Neuron"].value_counts()`` (hits), ``som.distance_map()``
    (U-matrix), and ``som.get_weights()[:, :, k]`` (component plane).

    Args:
        som (MiniSom): Trained map from ``fit_som``.
        values (pd.Series | array-like): A Series indexed by ``Neuron`` ID
            (missing neurons become NaN), or an array of shape (x_dim, y_dim).
        output_dir (str | PathLike): Directory where the figure is saved.
        filename (str, optional): Output image file name.
        annotate (str, optional): "value" prints the value in each cell, "id"
            prints the neuron ID, None prints nothing.
        cmap (str, optional): Matplotlib colormap.
        colorbar_label (str, optional): Colorbar label.
        vmin (float, optional): Lower color limit. Defaults to the data minimum.
        vmax (float, optional): Upper color limit. Defaults to the data maximum.
        figsize (tuple, optional): Figure size in inches. Defaults to a size
            that scales with the map dimensions.
        dpi (int, optional): Output image DPI.

    Returns:
        tuple: (fig, ax, output_path). Neurons with NaN are drawn light gray.
    """
    if annotate not in (None, "value", "id"):
        raise ValueError(f"Input 'annotate' must be None, 'value', or 'id', got {annotate!r}.")

    x_dim, y_dim = som.get_weights().shape[:2]
    grid = _values_to_grid(values, x_dim, y_dim)
    output_path = _resolve_output_path(output_dir, filename)

    # MiniSom's hexagonal coordinates already carry the sqrt(3)/2 row pitch;
    # use them unchanged.
    xx, yy = som.get_euclidean_coordinates()
    if som.topology == "hexagonal":
        shape = {"numVertices": 6, "radius": 0.95 / np.sqrt(3)}
    else:
        shape = {"numVertices": 4, "radius": 0.95 / np.sqrt(2), "orientation": np.pi / 4}

    finite = grid[np.isfinite(grid)]
    if vmin is None:
        vmin = finite.min() if finite.size else 0.0
    if vmax is None:
        vmax = finite.max() if finite.size else 1.0
    norm = Normalize(vmin=vmin, vmax=vmax)
    colormap = plt.get_cmap(cmap)
    integer_valued = finite.size > 0 and np.all(finite == np.round(finite))

    if figsize is None:
        figsize = (max(4.0, 0.9 * x_dim + 2.0), max(3.0, 0.9 * y_dim + 1.0))
    fig, ax = plt.subplots(figsize=figsize)

    for x in range(x_dim):
        for y in range(y_dim):
            value = grid[x, y]
            missing = not np.isfinite(value)
            face = "lightgray" if missing else colormap(norm(value))
            center = (xx[x, y], yy[x, y])
            ax.add_patch(RegularPolygon(center, facecolor=face, edgecolor="white", **shape))

            if annotate == "id":
                text = str(y * x_dim + x)
            elif annotate == "value" and not missing:
                text = f"{value:.0f}" if integer_valued else f"{value:.3g}"
            else:
                continue
            # Pick the text color from the cell's luminance so it stays legible.
            red, green, blue = (0.83, 0.83, 0.83) if missing else face[:3]
            dark_cell = 0.299 * red + 0.587 * green + 0.114 * blue < 0.5
            ax.text(*center, text, ha="center", va="center", fontsize=8,
                    color="white" if dark_cell else "black")

    ax.set_xlim(xx.min() - 0.7, xx.max() + 0.7)
    ax.set_ylim(yy.min() - 0.7, yy.max() + 0.7)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.colorbar(ScalarMappable(norm=norm, cmap=colormap), ax=ax, label=colorbar_label,
                 shrink=0.8)

    saved_path = _save_figure(fig, output_path, dpi)
    return fig, ax, saved_path


def plot_som_node_traces(
    som,
    trace_df,
    assignments,
    output_dir,
    filename="som_node_traces.png",
    background_df=None,
    sharey=True,
    color="tab:blue",
    figsize=None,
    dpi=200,
):
    """Draw one small subplot per neuron with that neuron's member traces.

    Panels form a rectangular ``y_dim`` x ``x_dim`` grid with neuron (x, y) at
    row ``y_dim - 1 - y``, column ``x``, so neuron 0 is bottom-left as in
    ``plot_som_layer``. The grid is rectangular for every topology: the
    half-cell offset of alternate rows on a hexagonal map is not drawn.
    Panels get small on large maps; this plot suits maps up to roughly 100
    neurons.

    Args:
        som (MiniSom): Trained map from ``fit_som``.
        trace_df (pd.DataFrame): Wide trace DataFrame (rows = time, columns =
            traces), as used throughout ``parasolpy.plotting``.
        assignments (pd.Series): Maps each trace column name to its ``Neuron``
            ID. Columns of ``trace_df`` without an assignment are not drawn.
        output_dir (str | PathLike): Directory where the figure is saved.
        filename (str, optional): Output image file name.
        background_df (pd.DataFrame, optional): Wide trace DataFrame drawn in
            light gray behind every panel, typically the full ensemble.
        sharey (bool, optional): Share the y-axis across panels.
        color (str, optional): Color of the member traces.
        figsize (tuple, optional): Figure size in inches. Defaults to a size
            that scales with the map dimensions.
        dpi (int, optional): Output image DPI.

    Returns:
        tuple: (fig, axes, output_path), with ``axes`` of shape (y_dim, x_dim).
    """
    traces = _validate_trace_dataframe(trace_df)
    background = None if background_df is None else _validate_trace_dataframe(background_df)
    if not isinstance(assignments, pd.Series):
        raise TypeError("Input 'assignments' must be a pandas Series (trace column -> Neuron).")
    assigned = assignments[assignments.index.isin(traces.columns)]
    if assigned.empty:
        raise ValueError("No index label of 'assignments' matches a column of 'trace_df'.")
    output_path = _resolve_output_path(output_dir, filename)

    x_dim, y_dim = som.get_weights().shape[:2]
    if figsize is None:
        figsize = (max(6.0, 1.6 * x_dim), max(4.0, 1.3 * y_dim))
    fig, axes = plt.subplots(
        y_dim, x_dim, figsize=figsize, sharex=True, sharey=sharey, squeeze=False
    )

    for x in range(x_dim):
        for y in range(y_dim):
            neuron = y * x_dim + x
            ax = axes[y_dim - 1 - y, x]
            if background is not None:
                ax.plot(background.index, background.to_numpy(), color="lightgray",
                        linewidth=0.3, alpha=0.5)
            members = traces[assigned.index[assigned == neuron]]
            if not members.columns.empty:
                ax.plot(members.index, members.to_numpy(), color=color, linewidth=0.5,
                        alpha=0.6)
                ax.plot(members.index, members.mean(axis=1), color="black", linewidth=1.2)
            ax.set_title(str(neuron), fontsize=7, pad=2)
            ax.tick_params(labelsize=6)

    fig.autofmt_xdate()
    fig.tight_layout()
    saved_path = _save_figure(fig, output_path, dpi)
    return fig, axes, saved_path
