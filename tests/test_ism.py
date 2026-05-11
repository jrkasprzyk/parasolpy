import numpy as np
import pytest

from parasolpy.ism import create_ism_traces


def test_output_shapes():
    inflow = np.arange(1, 21, dtype=float)  # 20 timesteps
    k = 4
    trace_length = 10
    traces, indices = create_ism_traces(inflow, k, trace_length)
    expected_num_traces = int(np.floor(len(inflow) / k))  # 5
    assert traces.shape == (trace_length, expected_num_traces)
    assert indices.shape == (trace_length, expected_num_traces)


def test_returns_two_arrays():
    inflow = np.ones(12)
    result = create_ism_traces(inflow, k=3, trace_length=6)
    assert len(result) == 2
    traces, indices = result
    assert isinstance(traces, np.ndarray)
    assert isinstance(indices, np.ndarray)


def test_wrap_around_uses_doubled_record():
    # With k=5 and len=10, num_traces=2. Trace 1 starts at j=5, trace_length=8
    # → indices [5,6,7,8,9,10,11,12] (into the doubled record)
    inflow = np.arange(1, 11, dtype=float)  # [1..10]
    k = 5
    trace_length = 8
    traces, indices = create_ism_traces(inflow, k, trace_length)
    assert traces.shape[1] == 2
    expected_indices = np.array([5, 6, 7, 8, 9, 10, 11, 12], dtype=float)
    np.testing.assert_array_equal(indices[:, 1], expected_indices)


def test_num_traces_formula():
    for length, k in [(30, 5), (100, 7), (50, 3)]:
        inflow = np.ones(length)
        traces, _ = create_ism_traces(inflow, k, trace_length=10)
        assert traces.shape[1] == int(np.floor(length / k))
