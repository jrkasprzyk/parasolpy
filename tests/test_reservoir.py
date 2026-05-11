import numpy as np
import pytest

from parasolpy.reservoir import sequent_peak


def test_no_deficit_when_inflow_exceeds_demand():
    inflow = np.array([10.0, 10.0, 10.0])
    K = sequent_peak(inflow, demand=5.0)
    np.testing.assert_array_equal(K, np.zeros(3))


def test_deficit_accumulates():
    # Demand 10, inflow 0 every step → storage grows each period
    inflow = np.zeros(4)
    K = sequent_peak(inflow, demand=10.0)
    assert K[0] == 0.0
    assert K[1] == pytest.approx(10.0)
    assert K[2] == pytest.approx(20.0)
    assert K[3] == pytest.approx(30.0)


def test_deficit_resets_to_zero():
    # Large inflow in period 3 should flush deficit back to 0
    inflow = np.array([0.0, 0.0, 100.0])
    K = sequent_peak(inflow, demand=5.0)
    assert K[2] == 0.0


def test_returns_numpy_array():
    inflow = np.array([5.0, 5.0])
    result = sequent_peak(inflow, demand=3.0)
    assert isinstance(result, np.ndarray)
    assert len(result) == 2


def test_length_matches_inflow():
    inflow = np.ones(100) * 2.0
    K = sequent_peak(inflow, demand=1.0)
    assert len(K) == 100
