# Nowak, K., J. Prairie, B. Rajagopalan, and U. Lall (2010),
# A nonparametric stochastic approach for multisite disaggregation of annual to daily streamflow,
# Water Resour. Res., 46, W08529.

import pandas as pd  # for dataframes and data processing
import numpy as np  # for numerical computation
import matplotlib.pyplot as plt  # for plotting
import sys  # system functions
from scipy import interpolate  # bring in only the interpolate function
import plotly.express as px  # plotly express for fast interactive plotting
from plotly.subplots import make_subplots
import plotly.graph_objects as go


def choose_analog_index(rng, Z, sim_Z):
    # inputs:
    # rng - random number generator instance
    # Z - input sequence of aggregated observed flows
    # sim_Z - simulated aggregated flow (scalar)

    # return: index of the chosen analog year from Z

    # Calculate the distance between the yearly flows and the
    # simulated value
    dist = np.absolute(Z - sim_Z)

    # inds will be the indices of the original sequence in ascending order
    inds = dist.argsort()

    # these are the yearly flows, sorted by their distance from the simulated flow
    sorted_Z = Z[inds]

    # the number of neighbors is a function of the
    # number of datapoints in the yearly sequence
    K = int(np.floor(np.sqrt(len(Z))))

    # the weight function gives the most weight
    # to the first neighbor (eq 1 in the paper)
    W = np.zeros(K)
    for i in range(K):
        W[i] = (1. / (i + 1.)) / sum(1. / k for k in range(1, K + 1))

    # here, we only keep the K nearest neighbors based on distance
    neighbors = sorted_Z[0:K]
    neighbors_inds = inds[0:K]

    # the index of the chosen year in the original Z sequence
    chosen_index = rng.choice(neighbors_inds, size=1, p=W)

    return int(chosen_index[0])


def sim_single_year(rng, Z, p, years, sim_Z, print_results=False):
    # inputs:
    # rng - random number generator instance
    # Z - input sequence of aggregated flows
    # p - input 2d array of proportion vectors (disagg timesteps in columns)
    # years - input sequence of years
    # sim_Z - simulated aggregated flow (scalar)
    # print_results - (optional) True for console output, False if not. Default False

    # return: sequence of simulated, disaggregated flow for one year

    chosen_index = choose_analog_index(rng, Z, sim_Z)

    # ...is used to find a proportion vector
    sim_p = p[chosen_index, :]

    # the simulated flow sequence is the proportion multiplied by simulated yearly flow
    sim_flow = sim_p * sim_Z

    if print_results is True:
        print(
            f"Sim annual {sim_Z: 0.1f}, "
            f"using analog year {years[chosen_index]}: "
            f"{np.array2string(sim_flow, precision=1, floatmode='fixed')}"
        )

    return sim_flow


def sim_multi_trace(rng, Z, p, years, sim_Z, repl=1, print_results=False):
    # inputs:
    # rng - random number generator instance
    # Z - input sequence of aggregated flows
    # p - input 2d array of proportion vectors (years in rows, periods in columns)
    # years - input sequence of years
    # mat_Z - simulated aggregated flow (sequences in rows, years in columns)
    # repl - (optional) number of replicates per simulated annual sequence. Default 1
    # print_results - (optional) True for console output, False if not. Default True

    # return: sequence of simulated, disaggregated flow for one year

    # what is the shape of the proportion matrix, p?
    num_input_years, num_periods = p.shape

    # what is the shape of the simulated annual data?
    num_seq, num_sim_years = sim_Z.shape

    # the output matrix will have the following shape:
    # rows: number of disaggregated periods * number of simulated years
    # columns: number of annual sequences * number of replicates
    #
    # example: seasonal data (4x per year), for sequences of 3 years: 12 rows
    # 5 annual sequences, each repeated twice: 10 columns
    mat_sim = np.zeros((num_periods * num_sim_years, num_seq * repl))

    j = 0  # column for the final output
    for r in range(repl):  # repeat for the number of replicates given by repl
        for s in range(num_seq):  # multiple sequences
            i = 0  # row for the final output
            for y in range(num_sim_years):  # multiple years
                sim_seas = sim_single_year(rng, Z, p, years, sim_Z[s, y])
                mat_sim[i:i + num_periods, j] = sim_seas
                i = i + num_periods
            j = j + 1

    return mat_sim
