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

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
	__version__ = _pkg_version("parasolpy")
except PackageNotFoundError:  # running from a source checkout without an install
	__version__ = "0.0.0+unknown"

__help__ = f"""\
parasolpy {__version__} — Python tools for multi-objective decision analysis.

Modules and key public functions
---------------------------------
reservoir   : sequent_peak(inflow, demand)
ism         : create_ism_traces(inflow, k, trace_length)
nowak       : choose_analog_index, sim_single_year, sim_multi_trace
util        : convert_cfs_to_af/cms, convert_cms_to_mcm,
              pivot_timeseries_by_year, script_local_path, ensure_dir,
              read_xml, process_xml
file_processing : has_superheader, load_solutions_dataframe,
                  convert_solutions_csv_to_single_header,
                  split_solutions_dataframe, split_solutions_csv
tradeoff    : df_to_pt, label_eps_nd, append_Kmeans, parallel_plot_hp,
              load_objective_names, load_objectives_and_solutions,
              resolve_solutions_csv, normalize_for_radar,
              build_radar_figure, run_eps_experiment, log_eps_experiment
plotting    : plot_trace_heatmap, plot_trace_spaghetti, plot_trace_fan_chart,
              plot_trace_monthly_seasonality, plot_trace_exceedance
dash_tools  : build_tradeoff_dash_app, load_dash_inputs
interactive : prompt_experiment_name, prompt_epsilons,
              load_experiment_epsilons, prompt_starting_epsilons

Quick start
-----------
  import parasolpy
  parasolpy.help()                   # this message
  help(parasolpy.sequent_peak)       # built-in Python help for any function
  help(parasolpy.parallel_plot_hp)

CLI
---
  parasolpy-tradeoff OUTPUT_FOLDER [--debug]

Docs / source : https://github.com/jrkasprzyk/parasolpy
"""


def help():
	"""Print a summary of the parasolpy public API."""
	print(__help__)

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
	"__version__",
	"__help__",
	"help",
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
