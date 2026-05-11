import numpy as np
import pandas as pd

from borgRWhelper.nowak import sim_multi_trace
from borgRWhelper.util import script_local_path


def main():
    input_path = script_local_path('oak_creek_monthly_af.xlsx')
    output_path = script_local_path('oak_sim_monthly.xlsx', must_exist=False)

    oak_obs_monthly_df = pd.read_excel(input_path,
                                       sheet_name='Monthly Data',
                                       index_col=0)

    oak_sim_ann_df = pd.read_excel(input_path,
                                   sheet_name='Simulated Annual',
                                   index_col=0)

    # convert to np array with shape as below
    # shape: sequences in rows; years in columns
    oak_sim_ann_flow = oak_sim_ann_df.to_numpy(copy=True)

    oak_obs_years = oak_obs_monthly_df.Year.unique()
    month_labels = oak_obs_monthly_df.loc[oak_obs_monthly_df['Year'] == oak_obs_years[0], 'Month'].to_numpy()

    oak_obs_monthly = oak_obs_monthly_df['Volume (af)'].to_numpy()

    # shape: years in rows, monthly values in columns
    oak_obs_monthly_mat = oak_obs_monthly.reshape((len(oak_obs_years), 12))

    oak_obs_ann_flow = np.sum(oak_obs_monthly_mat, axis=1)

    # Convert annual totals to a column vector with shape (num_years, 1) so each
    # row of monthly values is divided by that same year's annual total.
    oak_obs_ann_flow_col = oak_obs_ann_flow.reshape(-1, 1)

    # shape: years in rows, monthly proportions in columns
    oak_obs_p = oak_obs_monthly_mat / oak_obs_ann_flow_col

    # reset the random number generator to produce consistent results for this example
    oak_rng = np.random.default_rng(seed=42)

    # sim_multi_trace returns one column per simulated trace/replicate and stacks
    # all within-year monthly values down the rows.
    oak_sim_monthly = sim_multi_trace(oak_rng, oak_obs_ann_flow,
                                      oak_obs_p, oak_obs_years,
                                      oak_sim_ann_flow,
                                      repl=10, print_results=False)

    # The simulated annual input has 5 years, so the output rows are grouped into
    # 5 simulated years x 12 months. Build a MultiIndex so those stacked rows are
    # labeled as (SimYear, Month) instead of plain integer row numbers.
    sim_year_labels = [f"SimYear_{i}" for i in range(1, oak_sim_ann_flow.shape[1] + 1)]
    row_index = pd.MultiIndex.from_product([sim_year_labels, month_labels], names=['SimYear', 'Month'])

    # With repl=10 and 5 input annual sequences, sim_multi_trace generates 50 output
    # traces total. Name the columns explicitly so the Excel output is easier to inspect.
    column_labels = [f"Trace_{i:02d}" for i in range(1, oak_sim_monthly.shape[1] + 1)]

    oak_sim_monthly_df = pd.DataFrame(oak_sim_monthly, index=row_index, columns=column_labels)
    print(oak_sim_monthly_df.head(12).round(2))

    oak_sim_monthly_df.to_excel(output_path)
    return oak_sim_monthly_df


if __name__ == "__main__":
    main()
