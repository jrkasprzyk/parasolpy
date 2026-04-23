"""Nonparametric stochastic disaggregation after Nowak et al. (2010).

Reference:
    Nowak, K., J. Prairie, B. Rajagopalan, and U. Lall (2010),
    A nonparametric stochastic approach for multisite disaggregation of
    annual to daily streamflow, Water Resour. Res., 46, W08529.
"""

import numpy as np


def choose_analog_index(rng, Z, sim_Z):
    """Select an analog year index using K-nearest-neighbor weighting.

    Finds the K nearest neighbors in ``Z`` to the simulated annual flow
    ``sim_Z`` (where ``K = floor(sqrt(len(Z)))``), then draws one index
    with probability inversely proportional to rank distance (eq. 1 in the
    paper).

    Args:
        rng: numpy random Generator instance (e.g. ``numpy.random.default_rng()``).
        Z: 1-D numpy array of observed aggregated (annual) flows.
        sim_Z: Scalar simulated aggregated flow for the current year.

    Returns:
        int: Index into ``Z`` of the chosen analog year.
    """
    # Calculate the distance between the yearly flows and the simulated value
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
    """Disaggregate one simulated annual flow into sub-annual periods.

    Selects an analog year via :func:`choose_analog_index`, then scales its
    proportion vector by ``sim_Z`` to produce a disaggregated flow sequence.

    Args:
        rng: numpy random Generator instance.
        Z: 1-D array of observed annual flows (length = number of historical years).
        p: 2-D array of shape ``(num_years, num_periods)`` where each row is the
            fraction of annual flow in each sub-annual period.
        years: 1-D array of calendar years corresponding to rows of ``p``.
        sim_Z: Scalar simulated annual flow for the year being disaggregated.
        print_results: If True, print a one-line summary to stdout.

    Returns:
        numpy.ndarray: 1-D array of length ``num_periods`` with the disaggregated
        flow for each sub-annual period.
    """

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
    """Disaggregate multiple simulated annual sequences into sub-annual traces.

    Calls :func:`sim_single_year` for every combination of sequence, replicate,
    and year in ``sim_Z``, assembling results into a single output matrix.

    Args:
        rng: numpy random Generator instance.
        Z: 1-D array of observed annual flows.
        p: 2-D array of shape ``(num_years, num_periods)`` with proportion vectors.
        years: 1-D array of calendar years corresponding to rows of ``p``.
        sim_Z: 2-D array of shape ``(num_sequences, num_sim_years)`` with simulated
            annual flows; rows are independent sequences, columns are years.
        repl: Number of replicates generated for each row of ``sim_Z``. Defaults to 1.
        print_results: If True, print per-year summary lines to stdout.

    Returns:
        numpy.ndarray: 2-D array of shape
        ``(num_periods * num_sim_years, num_sequences * repl)`` containing the
        disaggregated flows. Each column is one complete trace.
    """

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
