import numpy as np


def create_ism_traces(inflow, k, trace_length):
    # inputs
    # inflow: a numpy array
    # k: the value k indicates the number of timesteps to skip when creating new traces
    # trace_length: the desired length of the traces created

    # return: a 2d numpy array with columns as traces and rows as timesteps

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
