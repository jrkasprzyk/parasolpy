import pandas as pd
import seaborn as sns
import plotly.express as px

from borgRWhelper.tradeoff import parallel_plot_hp, label_eps_nd
from borgRWhelper.util import script_local_path

# import archive (in 'readable' format)
all_solutions_df = pd.read_csv(script_local_path("AllPolicies.csv"), delimiter=",")

objective_names = ["Objectives.Powell_3490",
                   "Objectives.Powell_WY_Release",
                   "Objectives.Mead_1000",
                   "Objectives.LB_Shortage_Volume"]
num_objs = len(objective_names)

# directions for each objective (must be "minimize" or "maximize")
# TODO: we're not positive that these are correct for this example, since
# the data file that this refers to seems to be missing
objective_directions = ["maximize",
                        "maximize",
                        "maximize",
                        "minimize"]

metric_names = ["Objectives.LB_Shortage_Frequency",
                "Objectives.Mead_1020",
                "Objectives.Powell_3525",
                "Objectives.Powell_Release_LTEMP",
                "Objectives.Start_in_EQ",
                "Objectives.VariableHydrologicShortageIndicatorMetric",
                "Objectives.Avg_Powell_PE",
                "Objectives.Lee_Ferry_Deficit",
                "Objectives.Avg_Mead_PE",
                "Objectives.Max_Delta_Annual_Shortage",
                "Objectives.Avg_Annual_LB_Policy_Shortage"]

epsilons = [1,
            50000,
            1,
            50000]
            
all_solutions_df = label_eps_nd(all_solutions_df, "Eps Nd", objective_names, objective_directions, epsilons)

# save individual dataframes from each experiment
exp1_solutions_df = all_solutions_df.loc[all_solutions_df['Experiment'] == 1].copy(deep=True)
exp2_solutions_df = all_solutions_df.loc[all_solutions_df['Experiment'] == 2].copy(deep=True)
exp3_solutions_df = all_solutions_df.loc[all_solutions_df['Experiment'] == 3].copy(deep=True)
exp4_solutions_df = all_solutions_df.loc[all_solutions_df['Experiment'] == 4].copy(deep=True)

# create parallel plots and save into html
parallel_plot_hp(all_solutions_df[['Experiment',
                                   'Mead_Shortage_V_DV Row 0'] + metric_names + objective_names],
                 objective_names, objective_directions).to_html(script_local_path('all_solutions_with-metrics.html', must_exist=False))
parallel_plot_hp(exp1_solutions_df[[
                                       'Mead_Shortage_V_DV Row 0'] + metric_names + objective_names],
                 objective_names, objective_directions).to_html(script_local_path('exp1_solutions_with-metrics.html', must_exist=False))
parallel_plot_hp(exp2_solutions_df[[
                                       'Mead_Shortage_V_DV Row 0'] + metric_names + objective_names],
                 objective_names, objective_directions).to_html(script_local_path('exp2_solutions_with-metrics.html', must_exist=False))
parallel_plot_hp(exp3_solutions_df[[
                                       'Mead_Shortage_V_DV Row 0'] + metric_names + objective_names],
                 objective_names, objective_directions).to_html(script_local_path('exp3_solutions_with-metrics.html', must_exist=False))
parallel_plot_hp(exp4_solutions_df[[
                                       'Mead_Shortage_V_DV Row 0'] + metric_names + objective_names],
                 objective_names, objective_directions).to_html(script_local_path('exp4_solutions_with-metrics.html', must_exist=False))

# heatmap of correlation
sns_plot = sns.clustermap(exp2_solutions_df[metric_names + objective_names].corr(), cmap="rocket_r")

fig = px.scatter_matrix(exp2_solutions_df[objective_names])
fig.show()

fig = px.scatter_matrix(exp3_solutions_df[objective_names])
fig.show()
