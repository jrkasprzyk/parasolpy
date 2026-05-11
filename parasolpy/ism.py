"""Inflow Sequence Method (ISM) trace generation."""

import numpy as np


def create_ism_traces(inflow, k, trace_length):
    """Generate ISM synthetic traces from a historical inflow record.

    The Inflow Sequence Method creates an ensemble of synthetic traces by
    sliding a window of length ``trace_length`` over a doubled (wrap-around)
    copy of the historical record, stepping by ``k`` timesteps each time.

    Args:
        inflow: 1-D numpy array of historical inflow values.
        k: Step size between trace start points. Controls how many traces are
            generated: ``num_traces = floor(len(inflow) / k)``.
        trace_length: Number of timesteps in each output trace.

    Returns:
        tuple[numpy.ndarray, numpy.ndarray]:
            - traces: 2-D array of shape ``(trace_length, num_traces)`` where
              each column is one synthetic trace.
            - indices: 2-D array of the same shape with the original record
              indices used to construct each trace position.
    """
    # the number of traces is a known function of
    # the index k and the total length of the inflow record
    num_traces = int(np.floor(len(inflow) / k))

    # print("num_traces=%d"%num_traces)

    traces = np.zeros((trace_length, num_traces))

    indices = np.zeros((trace_length, num_traces))

    # because the traces 'wrap around', we need a doubled record
    inflow_doubled = np.concatenate((inflow, inflow), axis=None)

    j = 0  # the starting point of this trace
    for i in range(num_traces):
        traces[:, i] = inflow_doubled[j:j + trace_length]
        indices[:, i] = range(j, j + trace_length)
        j = j + k

    return traces, indices
