import numpy as np


def sequent_peak(inflow, demand):
  # input: array of inflow
  # demand: constant demand

  # return: array of K values

  R = demand
  Q = np.copy(inflow)
  N = len(Q)
  K = np.zeros(N)

  # start the timeseries with no storage deficit
  K[0] = 0.0

  for i in range(1, N):
    if demand-Q[i]+K[i-1] > 0.0:
      K[i] = demand-Q[i]+K[i-1]
    else:
      K[i] = 0.0

  return K
