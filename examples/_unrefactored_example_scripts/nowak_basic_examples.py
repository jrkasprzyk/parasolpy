import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from borgRWhelper.nowak import choose_analog_index, sim_multi_trace, sim_single_year


def run_single_year_example():
    print("Example 1: Ten repetitions of one simulated Z value (from paper)")

    obs_years = np.array([1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975])
    obs_ann_flow = np.array([35.0, 40.0, 33.0, 52.0, 43.0, 56.0, 38.0, 49.0, 32.0])
    obs_p = np.array(
        [[0.1, 0.3, 0.4, 0.2],
         [0.15, 0.25, 0.35, 0.25],
         [0.1, 0.2, 0.5, 0.2],
         [0.5, 0.15, 0.65, 0.15],
         [0.2, 0.2, 0.4, 0.2],
         [0.1, 0.2, 0.4, 0.3],
         [0.15, 0.2, 0.4, 0.25],
         [0.05, 0.1, 0.8, 0.05],
         [0.2, 0.2, 0.5, 0.1]]
    )
    sim_ann_flow = 70.0

    analog_rng = np.random.default_rng(seed=42)
    chosen_index = choose_analog_index(analog_rng, obs_ann_flow, sim_ann_flow)
    print(f"One sampled analog year from helper: {obs_years[chosen_index]}")

    sim_rng = np.random.default_rng(seed=42)
    for _ in range(10):
        sim_single_year(sim_rng, obs_ann_flow, obs_p, obs_years, sim_ann_flow, print_results=True)


def run_multi_trace_example(make_plot=True):
    print("Example 2: A longer example with multiple simulated years")

    obs_years = np.array([2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007])
    obs_seas_flow = np.array([50.0, 52.0, 80.0, 105.0, 60.0, 70.0, 90.0, 110.0,
                              60.0, 24.0, 40.0, 80.0, 40.0, 30.0, 80.0, 92.0,
                              81.0, 55.0, 81.0, 92.0, 50.0, 60.0, 100.0, 150.0,
                              20.0, 10.0, 80.0, 100.0, 50.0, 20.0, 30.0, 120.0])
    sim_ann_flow = np.array([[275.0, 300.0, 305.0],
                             [200.0, 220.0, 400.0],
                             [300.0, 310.0, 289.0],
                             [260.0, 311.0, 400.0],
                             [200.0, 250.0, 260.0]])

    obs_seas_flow_mat = obs_seas_flow.reshape((len(obs_years), 4))
    obs_ann_flow = obs_seas_flow_mat.sum(axis=1)
    obs_p = obs_seas_flow_mat / obs_ann_flow[:, np.newaxis]

    sim_rng = np.random.default_rng(seed=42)
    sim_seas_flow = sim_multi_trace(sim_rng, obs_ann_flow, obs_p, obs_years, sim_ann_flow, repl=2)

    sim_year_labels = [f"SimYear_{i}" for i in range(1, sim_ann_flow.shape[1] + 1)]
    period_labels = [f"Period_{i}" for i in range(1, obs_p.shape[1] + 1)]
    row_index = pd.MultiIndex.from_product([sim_year_labels, period_labels], names=["SimYear", "Period"])
    column_labels = [f"Trace_{i:02d}" for i in range(1, sim_seas_flow.shape[1] + 1)]

    sim_df = pd.DataFrame(sim_seas_flow, index=row_index, columns=column_labels)
    print(sim_df.head(8).round(1))

    if make_plot:
        ax = sim_df.plot(figsize=(10, 5), legend=False, title="Nowak Multi-Trace Example")
        ax.set_ylabel("Disaggregated Flow")
        ax.figure.tight_layout()

    return sim_df


def main(show_plot=True):
    run_single_year_example()
    run_multi_trace_example(make_plot=show_plot)
    if show_plot:
        plt.show()


if __name__ == "__main__":
    main()