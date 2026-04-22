"""Top-level package exports for parasolpy.

Importing names here lets callers write:
	from parasolpy import has_superheader
instead of the longer:
	from parasolpy.file_processing import has_superheader

Both styles always work — the short form is just a convenience. The long
form (importing directly from the submodule) is never broken by anything here:
	from parasolpy.tradeoff import append_Kmeans   # always valid
	from parasolpy import append_Kmeans             # also valid
"""

__version__ = "0.0.1"

from parasolpy.dash_tools import (
	build_tradeoff_dash_app,
	load_dash_inputs,
)
from parasolpy.file_processing import (
	convert_solutions_csv_to_single_header,
	has_superheader,
	load_solutions_dataframe,
	split_solutions_csv,
	split_solutions_dataframe,
)
from parasolpy.interactive import (
	ExitInteractiveSession,
	load_experiment_epsilons,
	prompt_epsilons,
	prompt_experiment_name,
	prompt_starting_epsilons,
)
from parasolpy.ism import create_ism_traces
from parasolpy.nowak import (
	choose_analog_index,
	sim_multi_trace,
	sim_single_year,
)
from parasolpy.plotting import (
	plot_trace_exceedance,
	plot_trace_fan_chart,
	plot_trace_heatmap,
	plot_trace_monthly_seasonality,
	plot_trace_spaghetti,
)
from parasolpy.reservoir import sequent_peak
from parasolpy.tradeoff import (
	append_Kmeans,
	build_radar_figure,
	df_to_pt,
	label_eps_nd,
	load_objective_names,
	load_objectives_and_solutions,
	log_eps_experiment,
	normalize_for_radar,
	parallel_plot_hp,
	resolve_solutions_csv,
	run_eps_experiment,
)
from parasolpy.util import (
	convert_cfs_to_af,
	convert_cfs_to_cms,
	convert_cms_to_mcm,
	ensure_dir,
	pivot_timeseries_by_year,
	process_xml,
	read_xml,
	script_local_path,
)

# __all__ controls what is exported when someone does `from parasolpy import *`.
# It also signals to IDEs and documentation tools which names are part of the
# intentional public API (as opposed to internal helpers imported for convenience).
# Names starting with _ are intentionally excluded — they are private implementation details.
__all__ = [
	# dash_tools
	"build_tradeoff_dash_app",
	"load_dash_inputs",
	# file_processing
	"has_superheader",
	"load_solutions_dataframe",
	"convert_solutions_csv_to_single_header",
	"split_solutions_dataframe",
	"split_solutions_csv",
	# interactive
	"ExitInteractiveSession",
	"load_experiment_epsilons",
	"prompt_epsilons",
	"prompt_experiment_name",
	"prompt_starting_epsilons",
	# ism
	"create_ism_traces",
	# nowak
	"choose_analog_index",
	"sim_multi_trace",
	"sim_single_year",
	# plotting
	"plot_trace_exceedance",
	"plot_trace_fan_chart",
	"plot_trace_heatmap",
	"plot_trace_monthly_seasonality",
	"plot_trace_spaghetti",
	# reservoir
	"sequent_peak",
	# tradeoff
	"append_Kmeans",
	"build_radar_figure",
	"df_to_pt",
	"label_eps_nd",
	"load_objective_names",
	"load_objectives_and_solutions",
	"log_eps_experiment",
	"normalize_for_radar",
	"parallel_plot_hp",
	"resolve_solutions_csv",
	"run_eps_experiment",
	# util
	"convert_cfs_to_af",
	"convert_cfs_to_cms",
	"convert_cms_to_mcm",
	"ensure_dir",
	"pivot_timeseries_by_year",
	"process_xml",
	"read_xml",
	"script_local_path",
]
