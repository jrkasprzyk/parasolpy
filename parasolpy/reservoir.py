"""Reservoir sizing via the sequent peak algorithm."""

import numpy as np


def sequent_peak(inflow, demand):
    """Compute required reservoir storage using the sequent peak algorithm.

    Given a time series of inflows and a constant demand, returns the
    minimum storage required at each timestep to meet demand without deficit.

    Args:
        inflow: Array-like of inflow values, one per timestep (same units as demand).
        demand: Constant demand value per timestep.

    Returns:
        numpy.ndarray: Required storage (K) at each timestep. K[t] = 0 means
        no storage deficit; positive values indicate cumulative shortage.
    """
    R = demand
    Q = np.copy(inflow)
    N = len(Q)
    K = np.zeros(N)

    K[0] = 0.0

    for i in range(1, N):
        if demand - Q[i] + K[i - 1] > 0.0:
            K[i] = demand - Q[i] + K[i - 1]
        else:
            K[i] = 0.0

    return K
