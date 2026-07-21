import hiplot as hip
import pandas as pd
import pytest

from parasolpy.tradeoff import parallel_plot_hp


def _sample_df():
    return pd.DataFrame(
        {
            "obj": [1.0, 2.0, 3.0],
            "few_values": [0, 1, 0],
            "category_like": [10, 20, 10],
        }
    )


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
