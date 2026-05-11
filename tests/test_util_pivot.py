import numpy as np
import pandas as pd
import pytest

from parasolpy.util import pivot_timeseries_by_year


def _daily_series(start="2000-01-01", periods=365 * 3, fill=1.0):
    idx = pd.date_range(start=start, periods=periods, freq="D")
    return pd.Series(fill, index=idx)


def test_returns_dataframe():
    s = _daily_series()
    result = pivot_timeseries_by_year(s)
    assert isinstance(result, pd.DataFrame)


def test_columns_are_years():
    s = _daily_series(start="2000-01-01", periods=365 * 2)
    result = pivot_timeseries_by_year(s)
    assert 2000 in result.columns
    assert 2001 in result.columns


def test_index_is_day_of_year():
    s = _daily_series()
    result = pivot_timeseries_by_year(s)
    assert result.index.min() == 1
    assert result.index.max() <= 366


def test_constant_series_mean_equals_constant():
    s = _daily_series(fill=5.0)
    result = pivot_timeseries_by_year(s, aggfunc="mean")
    assert (result.dropna() == 5.0).all().all()


def test_dataframe_single_column_auto_detected():
    idx = pd.date_range("2000-01-01", periods=365, freq="D")
    df = pd.DataFrame({"flow": np.ones(365)}, index=idx)
    result = pivot_timeseries_by_year(df)
    assert isinstance(result, pd.DataFrame)


def test_dataframe_explicit_value_column():
    idx = pd.date_range("2000-01-01", periods=365, freq="D")
    df = pd.DataFrame({"flow": np.ones(365), "temp": np.zeros(365)}, index=idx)
    result = pivot_timeseries_by_year(df, value_column="flow")
    assert isinstance(result, pd.DataFrame)


def test_rejects_non_datetime_index():
    s = pd.Series([1.0, 2.0], index=[0, 1])
    with pytest.raises(TypeError):
        pivot_timeseries_by_year(s)


def test_rejects_non_series_dataframe():
    with pytest.raises(TypeError):
        pivot_timeseries_by_year([1, 2, 3])


def test_rejects_value_column_on_series():
    s = _daily_series()
    with pytest.raises(ValueError):
        pivot_timeseries_by_year(s, value_column="flow")
