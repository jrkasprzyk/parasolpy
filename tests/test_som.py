"""Tests for parasolpy.som (fit, assign, quality, sweep, plots)."""

import warnings

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from minisom import MiniSom

from parasolpy.som import (
    append_som,
    fit_som,
    plot_som_layer,
    plot_som_node_traces,
    som_quality,
    sweep_som,
)

N_PER_BLOB = 30
N_FEATURES = 4
SWEEP_COLUMNS = [
    "x_dim",
    "y_dim",
    "n_neurons",
    "sigma",
    "neighborhood_function",
    "quantization_error",
    "topographic_error",
    "explained_variance",
]


@pytest.fixture
def blobs():
    """Three well-separated Gaussian blobs, z-scored. Returns (Z, labels)."""
    rng = np.random.default_rng(0)
    centers = np.array([[0, 0, 0, 0], [10, 10, 0, 0], [0, 10, 10, 10]], dtype=float)
    X = np.vstack([c + rng.normal(0, 0.5, (N_PER_BLOB, N_FEATURES)) for c in centers])
    labels = np.repeat([0, 1, 2], N_PER_BLOB)
    Z = (X - X.mean(axis=0)) / X.std(axis=0)
    return Z, labels


@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")


# --- fit_som ---------------------------------------------------------------


def test_fit_som_returns_minisom_with_expected_weight_shape(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    assert isinstance(som, MiniSom)
    assert som.get_weights().shape == (6, 4, N_FEATURES)


def test_fit_som_accepts_dataframe(blobs):
    Z, _ = blobs
    som = fit_som(pd.DataFrame(Z), 5, 3)
    assert som.get_weights().shape == (5, 3, N_FEATURES)


def test_fit_som_rejects_unknown_init(blobs):
    Z, _ = blobs
    with pytest.raises(ValueError, match="init"):
        fit_som(Z, 6, 4, init="bogus")


def test_fit_som_random_init_runs(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4, init="random")
    assert np.isfinite(som.get_weights()).all()


def test_fit_som_rejects_nan(blobs):
    Z, _ = blobs
    Z = Z.copy()
    Z[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        fit_som(Z, 6, 4)


def test_fit_som_warns_on_unscaled_column(blobs):
    Z, _ = blobs
    X = Z.copy()
    X[:, 0] *= 1000
    with pytest.warns(UserWarning, match="Scale features"):
        fit_som(X, 6, 4)


def test_fit_som_warns_on_zero_variance_column(blobs):
    Z, _ = blobs
    X = Z.copy()
    X[:, 1] = 3.0
    with pytest.warns(UserWarning, match="zero variance"):
        fit_som(X, 6, 4)


def test_fit_som_silent_on_scaled_data(blobs):
    Z, _ = blobs
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fit_som(Z, 6, 4)


def test_fit_som_same_seed_gives_identical_weights(blobs):
    Z, _ = blobs
    first = fit_som(Z, 6, 4, random_seed=3).get_weights()
    second = fit_som(Z, 6, 4, random_seed=3).get_weights()
    np.testing.assert_array_equal(first, second)


def test_blobs_occupy_disjoint_neurons(blobs):
    Z, labels = blobs
    som = fit_som(Z, 6, 4)
    df = append_som(pd.DataFrame({"blob": labels}), som, Z)
    neuron_sets = [set(df.loc[df["blob"] == k, "Neuron"]) for k in range(3)]
    assert neuron_sets[0].isdisjoint(neuron_sets[1])
    assert neuron_sets[0].isdisjoint(neuron_sets[2])
    assert neuron_sets[1].isdisjoint(neuron_sets[2])


# --- append_som ------------------------------------------------------------


def test_append_som_adds_four_consistent_columns(blobs):
    Z, _ = blobs
    x_dim, y_dim = 6, 4
    som = fit_som(Z, x_dim, y_dim)
    df = pd.DataFrame({"row": range(len(Z))})

    out = append_som(df, som, Z)

    assert out is df
    for col in ["Neuron", "Neuron_x", "Neuron_y", "Neuron_dist"]:
        assert col in df.columns
    assert df["Neuron"].between(0, x_dim * y_dim - 1).all()
    assert df["Neuron_x"].between(0, x_dim - 1).all()
    assert df["Neuron_y"].between(0, y_dim - 1).all()
    assert (df["Neuron"] == df["Neuron_y"] * x_dim + df["Neuron_x"]).all()
    assert (df["Neuron_dist"] >= 0).all()
    assert pd.api.types.is_integer_dtype(df["Neuron"])


def test_append_som_matches_minisom_winner_and_weights(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    df = append_som(pd.DataFrame(index=range(len(Z))), som, Z)
    weights = som.get_weights()
    for i in (0, 31, 89):
        x, y = som.winner(Z[i])
        assert (df.loc[i, "Neuron_x"], df.loc[i, "Neuron_y"]) == (x, y)
        assert df.loc[i, "Neuron_dist"] == pytest.approx(np.linalg.norm(Z[i] - weights[x, y]))


def test_append_som_custom_column_name(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    df = append_som(pd.DataFrame(index=range(len(Z))), som, Z, column="Node")
    assert list(df.columns) == ["Node_x", "Node_y", "Node", "Node_dist"]


def test_append_som_length_mismatch_raises(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    with pytest.raises(ValueError, match="rows"):
        append_som(pd.DataFrame({"row": range(len(Z) - 1)}), som, Z)


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_append_som_rejects_non_finite_rows(blobs, bad):
    Z, _ = blobs
    som = fit_som(Z, 4, 3)
    held_out = Z[:5].copy()
    held_out[2, 0] = bad
    df = pd.DataFrame(index=range(5))
    with pytest.raises(ValueError, match="NaN or infinite"):
        append_som(df, som, held_out)
    assert df.columns.empty


def test_append_som_assigns_held_out_rows(blobs):
    Z, _ = blobs
    rng = np.random.default_rng(1)
    order = rng.permutation(len(Z))
    train, held_out = Z[order[:60]], Z[order[60:]]
    som = fit_som(train, 6, 4)

    df = append_som(pd.DataFrame({"row": range(len(held_out))}), som, held_out)

    assert len(df) == 30
    assert df["Neuron"].between(0, 23).all()
    assert np.isfinite(df["Neuron_dist"]).all()


# --- som_quality -----------------------------------------------------------


def test_som_quality_keys_and_ranges(blobs):
    Z, _ = blobs
    quality = som_quality(fit_som(Z, 6, 4), Z)
    assert set(quality) == {"quantization_error", "topographic_error", "explained_variance"}
    assert 0 <= quality["explained_variance"] <= 100
    assert 0 <= quality["topographic_error"] <= 1
    assert quality["quantization_error"] >= 0


def test_som_quality_explained_variance_matches_definition(blobs):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    df = append_som(pd.DataFrame(index=range(len(Z))), som, Z)
    expected = 100 * (1 - (df["Neuron_dist"] ** 2).sum() / ((Z - Z.mean(axis=0)) ** 2).sum())
    assert som_quality(som, Z)["explained_variance"] == pytest.approx(expected)


# --- sweep_som -------------------------------------------------------------


@pytest.mark.parametrize("rows", [1, 6])
def test_som_quality_rejects_zero_variance_data(blobs, rows):
    Z, _ = blobs
    som = fit_som(Z, 4, 3)
    constant = np.repeat(Z[:1], rows, axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(ValueError, match="zero total variance"):
            som_quality(som, constant)


def test_som_quality_rejects_nan(blobs):
    Z, _ = blobs
    som = fit_som(Z, 4, 3)
    bad = Z.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="NaN or infinite"):
        som_quality(som, bad)


def test_sweep_som_rejects_zero_variance_data(blobs):
    Z, _ = blobs
    with pytest.raises(ValueError, match="zero total variance"):
        sweep_som(np.repeat(Z[:1], 20, axis=0), n_samples=2)


def test_sweep_som_returns_one_row_per_configuration(blobs):
    Z, _ = blobs
    sweep = sweep_som(Z, n_samples=3)
    assert len(sweep) == 3
    assert list(sweep.columns) == SWEEP_COLUMNS
    assert (sweep["x_dim"] >= sweep["y_dim"]).all()
    assert (sweep["n_neurons"] == sweep["x_dim"] * sweep["y_dim"]).all()


def test_sweep_som_respects_ranges_and_bubble_sigma(blobs):
    Z, _ = blobs
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # MiniSom warns on bad bubble sigma
        sweep = sweep_som(Z, n_samples=12, num_epochs=2)

    assert sweep["y_dim"].between(3, 6).all()
    assert set(sweep["neighborhood_function"]) == {"gaussian", "bubble"}
    bubble_sigma = sweep.loc[sweep["neighborhood_function"] == "bubble", "sigma"]
    assert (bubble_sigma >= 1).all()
    assert (bubble_sigma == bubble_sigma.round()).all()


def test_sweep_som_is_repeatable(blobs):
    Z, _ = blobs
    pd.testing.assert_frame_equal(
        sweep_som(Z, n_samples=3, num_epochs=2),
        sweep_som(Z, n_samples=3, num_epochs=2),
    )


# --- plot_som_layer --------------------------------------------------------


@pytest.mark.parametrize("topology", ["hexagonal", "rectangular"])
@pytest.mark.parametrize("annotate", [None, "value", "id"])
def test_plot_som_layer_series_and_array_inputs(blobs, tmp_path, topology, annotate):
    Z, _ = blobs
    som = fit_som(Z, 6, 4, topology=topology)
    df = append_som(pd.DataFrame({"v": Z[:, 0]}), som, Z)

    for name, values in [
        ("series.png", df.groupby("Neuron")["v"].mean()),  # has unoccupied (NaN) neurons
        ("array.png", som.distance_map()),
    ]:
        result = plot_som_layer(som, values, tmp_path, filename=name, annotate=annotate)
        assert len(result) == 3
        fig, ax, output_path = result
        assert output_path == tmp_path / name
        assert output_path.exists()
        assert len(ax.patches) == 24


def test_plot_som_layer_places_series_values_by_neuron_id(blobs, tmp_path):
    Z, _ = blobs
    x_dim, y_dim = 6, 4
    som = fit_som(Z, x_dim, y_dim)
    ids = pd.Series(np.arange(x_dim * y_dim, dtype=float))

    _, ax, _ = plot_som_layer(som, ids, tmp_path, annotate="value")

    xx, yy = som.get_euclidean_coordinates()
    for text in ax.texts:
        y, x = divmod(int(text.get_text()), x_dim)
        assert text.get_position() == pytest.approx((xx[x, y], yy[x, y]))


def test_plot_som_layer_hexagonal_row_pitch(blobs, tmp_path):
    Z, _ = blobs
    som = fit_som(Z, 6, 4, topology="hexagonal")
    _, ax, _ = plot_som_layer(som, som.distance_map(), tmp_path)

    row_y = np.unique(np.round([patch.xy[1] for patch in ax.patches], 12))
    assert len(row_y) == 4
    np.testing.assert_allclose(np.diff(row_y), np.sqrt(3) / 2, atol=1e-9)


def test_plot_som_layer_rejects_bad_inputs(blobs, tmp_path):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    with pytest.raises(ValueError, match="shape"):
        plot_som_layer(som, np.zeros((4, 6)), tmp_path)
    with pytest.raises(ValueError, match="annotate"):
        plot_som_layer(som, som.distance_map(), tmp_path, annotate="bogus")


# --- plot_som_node_traces --------------------------------------------------


def _trace_inputs(Z):
    index = pd.date_range("2027-01-01", periods=N_FEATURES, freq="YS")
    columns = [f"t{i}" for i in range(len(Z))]
    return pd.DataFrame(Z.T, index=index, columns=columns), columns


def test_plot_som_node_traces_writes_file_and_returns_grid(blobs, tmp_path):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    trace_df, columns = _trace_inputs(Z)
    info = append_som(pd.DataFrame(index=columns), som, Z)

    fig, axes, output_path = plot_som_node_traces(som, trace_df, info["Neuron"], tmp_path)

    assert output_path.exists()
    assert axes.shape == (4, 6)
    # Neuron 0 is bottom-left, the last neuron is top-right.
    assert axes[3, 0].get_title() == "0"
    assert axes[0, 5].get_title() == "23"


def test_plot_som_node_traces_accepts_background(blobs, tmp_path):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    trace_df, columns = _trace_inputs(Z)
    info = append_som(pd.DataFrame(index=columns), som, Z)

    _, axes, output_path = plot_som_node_traces(
        som, trace_df, info["Neuron"], tmp_path, background_df=trace_df, sharey=False
    )

    assert output_path.exists()
    # Every panel carries the full background ensemble, occupied or not.
    assert all(len(ax.lines) >= len(columns) for ax in axes.ravel())


def test_plot_som_node_traces_rejects_unmatched_assignments(blobs, tmp_path):
    Z, _ = blobs
    som = fit_som(Z, 6, 4)
    trace_df, _ = _trace_inputs(Z)
    with pytest.raises(ValueError, match="assignments"):
        plot_som_node_traces(som, trace_df, pd.Series({"nope": 0}), tmp_path)
