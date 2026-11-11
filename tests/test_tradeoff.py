import hiplot as hip
import pandas as pd
import pytest

from parasolpy.tradeoff import label_eps_nd, parallel_plot_hp


def _sample_df():
    return pd.DataFrame(
        {
            "obj": [1.0, 2.0, 3.0],
            "few_values": [0, 1, 0],
            "category_like": [10, 20, 10],
        }
    )


def test_parallel_plot_hp_defaults_to_all_columns_numeric():
    exp = parallel_plot_hp(_sample_df())

    assert exp.parameters_definition["obj"].type == hip.ValueType.NUMERIC
    assert exp.parameters_definition["few_values"].type == hip.ValueType.NUMERIC
    assert exp.parameters_definition["category_like"].type == hip.ValueType.NUMERIC


def test_parallel_plot_hp_force_numerical_columns_sets_numeric_type():
    exp = parallel_plot_hp(_sample_df(), force_numerical_columns=["few_values"])

    assert exp.parameters_definition["few_values"].type == hip.ValueType.NUMERIC


def test_parallel_plot_hp_force_numerical_columns_allows_forced_range():
    exp = parallel_plot_hp(
        _sample_df(),
        force_numerical_columns=["category_like"],
        forced_ranges_columns=["category_like"],
        force_min=[0],
        force_max=[100],
    )

    assert exp.parameters_definition["category_like"].type == hip.ValueType.NUMERIC
    assert exp.parameters_definition["category_like"].force_value_min == 0
    assert exp.parameters_definition["category_like"].force_value_max == 100


def test_parallel_plot_hp_force_numerical_columns_rejects_bad_type():
    with pytest.raises(TypeError, match="force_numerical_columns"):
        parallel_plot_hp(_sample_df(), force_numerical_columns="few_values")


def test_parallel_plot_hp_force_numerical_columns_rejects_missing_column():
    with pytest.raises(ValueError, match="force numeric"):
        parallel_plot_hp(_sample_df(), force_numerical_columns=["missing"])


# --- label_eps_nd ------------------------------------------------------------

def _label(df, directions=("minimize", "minimize"), eps=(0.1, 0.1)):
    return label_eps_nd(df, "nd", ["a", "b"], list(directions), list(eps))["nd"].tolist()


def test_label_eps_nd_excludes_dominated_point():
    df = pd.DataFrame({"a": [1.0, 5.0, 6.0], "b": [5.0, 1.0, 6.0]})
    assert _label(df) == [True, True, False]


def test_label_eps_nd_respects_maximize_direction():
    # Minimize a, maximize b: row 0 has the lowest a and the highest b.
    df = pd.DataFrame({"a": [1.0, 5.0, 1.0], "b": [5.0, 1.0, 1.0]})
    assert _label(df, directions=("minimize", "maximize")) == [True, False, False]


def test_label_eps_nd_coarse_epsilon_merges_box():
    # Both points fall in the same 1.0-wide box, so only one survives.
    df = pd.DataFrame({"a": [1.0, 1.9], "b": [1.9, 1.0]})
    assert sum(_label(df.copy(), eps=(0.1, 0.1))) == 2
    assert sum(_label(df.copy(), eps=(1.0, 1.0))) == 1


def test_label_eps_nd_uses_index_labels():
    df = pd.DataFrame({"a": [6.0, 1.0, 5.0], "b": [6.0, 5.0, 1.0]}, index=[10, 20, 30])
    out = label_eps_nd(df, "nd", ["a", "b"], ["minimize", "minimize"], [0.1, 0.1])
    assert out is df
    assert out["nd"].to_dict() == {10: False, 20: True, 30: True}
    assert len(out) == 3


def test_label_eps_nd_rejects_existing_label_col():
    df = pd.DataFrame({"a": [1.0], "b": [1.0], "nd": [True]})
    with pytest.raises(ValueError, match="already exists"):
        label_eps_nd(df, "nd", ["a", "b"], ["minimize", "minimize"], [0.1, 0.1])


def test_label_eps_nd_rejects_length_mismatch():
    df = pd.DataFrame({"a": [1.0], "b": [1.0]})
    with pytest.raises(ValueError, match="Lengths"):
        label_eps_nd(df, "nd", ["a", "b"], ["minimize", "minimize"], [0.1])


def test_label_eps_nd_rejects_bad_direction():
    df = pd.DataFrame({"a": [1.0], "b": [1.0]})
    with pytest.raises(ValueError, match="minimize"):
        label_eps_nd(df, "nd", ["a", "b"], ["min", "minimize"], [0.1, 0.1])
