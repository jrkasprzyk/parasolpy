"""Multi-objective tradeoff analysis: epsilon non-dominance, parallel plots, clustering."""

import json
import hiplot as hip
import pandas as pd
import platypus as pt
import plotly.graph_objects as go
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

from parasolpy.util import process_xml


def df_to_pt(df, obj_names, obj_directions, num_vars=0, num_constrs=0):
  """
  Converts a pandas DataFrame of solutions into a list of Platypus Solution objects.

  This function takes a DataFrame where each row represents a solution and columns
  represent objectives (and potentially decision variables or constraints).
  It creates Platypus Problem and Solution objects, mapping DataFrame rows
  to solutions and objective columns to Platypus objectives, handling minimization
  and maximization as specified.

  Args:
    df (pd.DataFrame): The input DataFrame where each row is a solution.
    obj_names (list of str): A list of column names in `df` that represent
                                   the objective functions.
    obj_directions (list of str): A list of strings ('minimize' or 'maximize')
                                        indicating the optimization direction for
                                        each objective. Must match the order of
                                        `obj_names_param`.
    num_vars (int, optional): The number of decision variables in the problem.
                           Defaults to 0.
    num_constrs (int, optional): The number of constraints in the problem.
                              Defaults to 0.

  Returns:
    list: A list of Platypus Solution objects, each representing a row from
          the input DataFrame.

  Raises:
    TypeError: If `df` is not a pandas DataFrame, or if `obj_names`,
               `obj_directions` are not lists of strings.
    ValueError: If `obj_names` is empty, objective directions are invalid,
                lengths of `obj_names` and `obj_directions` do not match,
                or `num_vars`/`num_constrs` are not non-negative integers.
  """
  # Validate input parameters
  if not isinstance(df, pd.DataFrame):
    raise TypeError("Input 'df' must be a pandas DataFrame.")
  if not isinstance(obj_names, list) or not all(isinstance(name, str) for name in obj_names):
    raise TypeError("Input 'obj_names' must be a list of strings.")
  if not obj_names:
    raise ValueError("Input 'obj_names' cannot be empty.")
  if not isinstance(obj_directions, list) or not all(isinstance(direction, str) for direction in obj_directions):
    raise TypeError("Input 'obj_directions' must be a list of strings.")
  if not all(d in ['minimize', 'maximize'] for d in obj_directions):
    raise ValueError("Objective directions must be 'minimize' or 'maximize'.")
  if len(obj_names) != len(obj_directions):
    raise ValueError("Length of 'obj_names' must match 'obj_directions'.")
  if not isinstance(num_vars, int) or num_vars < 0:
    raise ValueError("Input 'nvars' must be a non-negative integer.")
  if not isinstance(num_constrs, int) or num_constrs < 0:
    raise ValueError("Input 'nconstrs' must be a non-negative integer.")

  num_objs = len(obj_names)
  problem = pt.Problem(nvars=num_vars, nobjs=num_objs, nconstrs=num_constrs)
  pt_solutions = []
  for index, row in df.iterrows():
    # create solution object
    solution = pt.Solution(problem)

    # save an id for which row of the original
    # dataframe this solution came from. really important
    # for cross-referencing things later!
    solution.id = index

    # populate the objective values into platypus, correcting
    # the maximized objectives by multiplying by -1
    for j in range(num_objs):
      if obj_directions[j] == 'minimize':
        solution.objectives[j] = row[obj_names[j]]
      elif obj_directions[j] == 'maximize':
        solution.objectives[j] = -1.0*row[obj_names[j]]

    # add the solution to the list
    pt_solutions.append(solution)
  return pt_solutions


def parallel_plot_hp(df,
                     obj_names=None,
                     obj_directions=None,
                     plot_direction='bottom',
                     color_column=None,
                     hide_columns=None,
                     forced_ranges_columns=None,
                     force_min=None,
                     force_max=None,
                     colormap='interpolateViridis',
                     invert_columns=None
                     ):
    """
    Generates an interactive parallel plot using HiPlot for visualizing solution tradeoffs.

    This function takes a DataFrame of solutions and generates a parallel coordinates plot
    to visualize the relationships between different objective functions and other metrics.
    It supports customizing the plot's direction (for highlighting 'good' solutions),
    coloring by a specific column, and hiding unnecessary columns.

    Args:
        df (pd.DataFrame): The input DataFrame where each row represents a solution
                           and columns represent objectives or other attributes.
        obj_names (list of str): Names of the objective columns in `df`.
        obj_directions (list of str): Optimization direction ('minimize' or 'maximize') for each objective.
        plot_direction (str, optional): Defines the direction for inverting objective axes
                                        to highlight optimal regions. Must be 'bottom'
                                        (good solutions at the bottom of the plot) or
                                        'top' (good solutions at the top). Defaults to 'bottom'.
        color_column (str, optional): The name of the column in `df` to use for coloring
                                      the lines in the parallel plot. If None, no column
                                      will be used for coloring. Defaults to None.
        hide_columns (list of str, optional): A list of column names in `df` to hide from
                                          the parallel plot. Defaults to None (no columns hidden).
        forced_ranges_columns (list of str, optional): Columns for which a forced axis
                                          range should be applied in the parallel plot.
        force_min (list of number, optional): Minimum values for each forced-range column.
        force_max (list of number, optional): Maximum values for each forced-range column.
        colormap (str, optional): D3 colormap name used when `color_column` is provided.
        invert_columns (list of str, optional): Explicit columns to invert. If provided,
                                          this takes precedence over obj_names/obj_directions.

    Returns:
        hiplot.Experiment: An HiPlot experiment object configured with the parallel plot.

    Raises:
        TypeError: If any input is malformed (wrong types for list/string arguments).
        ValueError: If `plot_direction` is not 'bottom' or 'top', `color_column` is not
            present in `df` (when provided), any specified column is missing,
            or forced-range list lengths do not match.
    """

    # Input Validation
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input 'df' must be a pandas DataFrame.")

    if not isinstance(plot_direction, str) or plot_direction not in ['bottom', 'top']:
        raise ValueError(
            "Input 'plot_direction' must be either 'bottom' or 'top'.")

    if color_column is not None:
        if not isinstance(color_column, str):
            raise TypeError("Input 'color_column' must be a string or None.")
        if color_column not in df.columns:
            raise ValueError(
                f"'color_column' '{color_column}' not found in DataFrame columns.")

    if not isinstance(colormap, str) or not colormap:
      raise TypeError("Input 'colormap' must be a non-empty string.")

    if hide_columns is not None:
        if not isinstance(hide_columns, list) or not all(isinstance(col, str) for col in hide_columns):
            raise TypeError("Input 'hide_columns' must be a list of strings.")
        invalid_hide_columns = [
            col for col in hide_columns if col not in df.columns]
        if invalid_hide_columns:
            raise ValueError(
                f"Columns to hide {invalid_hide_columns} not found in DataFrame.")

    if invert_columns is not None:
      if not isinstance(invert_columns, list) or not all(isinstance(col, str) for col in invert_columns):
        raise TypeError("Input 'invert_columns' must be a list of strings.")
      invalid_invert_columns = [col for col in invert_columns if col not in df.columns]
      if invalid_invert_columns:
        raise ValueError(
          f"Columns to invert {invalid_invert_columns} not found in DataFrame.")

    if obj_names is not None:
      if not isinstance(obj_names, list) or not all(isinstance(col, str) for col in obj_names):
        raise TypeError("Input 'obj_names' must be a list of strings or None.")
      invalid_obj_names = [col for col in obj_names if col not in df.columns]
      if invalid_obj_names:
        raise ValueError(
          f"Objective columns {invalid_obj_names} not found in DataFrame.")

    if obj_directions is not None:
      if not isinstance(obj_directions, list) or not all(isinstance(direction, str) for direction in obj_directions):
        raise TypeError("Input 'obj_directions' must be a list of strings or None.")
      invalid_dirs = [d for d in obj_directions if d not in ['minimize', 'maximize']]
      if invalid_dirs:
        raise ValueError("Objective directions must be 'minimize' or 'maximize'.")

    if (obj_names is None) != (obj_directions is None):
      raise ValueError("Inputs 'obj_names' and 'obj_directions' must both be provided or both be None.")

    if obj_names is not None and len(obj_names) != len(obj_directions):
      raise ValueError("Lengths of 'obj_names' and 'obj_directions' must match.")

    if forced_ranges_columns is not None:
      if not isinstance(forced_ranges_columns, list) or not all(isinstance(col, str) for col in forced_ranges_columns):
        raise TypeError("Input 'forced_ranges_columns' must be a list of strings.")
      invalid_forced_cols = [col for col in forced_ranges_columns if col not in df.columns]
      if invalid_forced_cols:
        raise ValueError(
          f"Forced-range columns {invalid_forced_cols} not found in DataFrame.")

    if force_min is not None:
      if not isinstance(force_min, list) or not all(isinstance(v, (int, float)) for v in force_min):
        raise TypeError("Input 'force_min' must be a list of numbers.")

    if force_max is not None:
      if not isinstance(force_max, list) or not all(isinstance(v, (int, float)) for v in force_max):
        raise TypeError("Input 'force_max' must be a list of numbers.")

    if forced_ranges_columns is not None or force_min is not None or force_max is not None:
      if forced_ranges_columns is None or force_min is None or force_max is None:
        raise ValueError(
          "Inputs 'forced_ranges_columns', 'force_min', and 'force_max' must all be provided together.")
      if not (len(forced_ranges_columns) == len(force_min) == len(force_max)):
        raise ValueError(
          "Lengths of 'forced_ranges_columns', 'force_min', and 'force_max' must match.")

    # Convert the default 'None' to list types
    if hide_columns is None:
        hide_columns = []

    # Use the plot_direction parameter to automatically
    # invert or retain the direction of each column
    pp_invert = []
    if invert_columns is not None:
        pp_invert = invert_columns
    elif obj_names is not None and obj_directions is not None:
        if plot_direction == 'bottom':
            for j in range(len(obj_names)):
                if obj_directions[j] == 'maximize':
                    pp_invert.append(obj_names[j])
        elif plot_direction == 'top':
            for j in range(len(obj_names)):
                if obj_directions[j] == 'minimize':
                    pp_invert.append(obj_names[j])

    # In order to always hide uid and from_uid from the parallel plot,
    # we append these columns to the user-identified set of columns
    pp_hide = hide_columns + ['uid', 'from_uid']

    # Create plot
    exp = hip.Experiment.from_dataframe(df)

    # Set color column and colormap
    if color_column is not None:
        exp.colorby = color_column
        exp.parameters_definition[color_column].colormap = colormap

    # Apply forced ranges when requested
    if forced_ranges_columns is not None:
        for i, col in enumerate(forced_ranges_columns):
            exp.parameters_definition[col].force_range(force_min[i], force_max[i])

    # Now we update the experiment object to implement the hidden and
    # inverted columns
    exp.display_data(hip.Displays.PARALLEL_PLOT).update(
        {
            'hide': pp_hide,
            'invert': pp_invert
        }
    )

    # And similarly, update the data table that is rendered below the plot
    exp.display_data(hip.Displays.TABLE).update(
        {
            'hide': ['uid', 'from_uid']
        }
    )

    # The experiment object is returned so that it can be used later
    return exp

# Modified this function based on development in the CVEN5393 repository


def label_eps_nd(df, label_col, obj_names, obj_directions, epsilons, num_vars=0, num_constrs=0):
  """
  label_eps_nd: label epsilon non-dominated solutions

  This function takes a DataFrame of solutions and identifies which ones are epsilon non-dominated based on a given set of objectives, directions, and epsilon values. It adds a new boolean column to the DataFrame, marking `True` for epsilon non-dominated solutions and `False` otherwise.

  ### Positional Arguments:
  *   `df` (pd.DataFrame): The input DataFrame containing solution data.
  *   `label_col` (str): The name of the new column to be added to `df` to store the boolean labels.
  *   `obj_names` (list of str): Names of the objective columns in `df`.
  *   `obj_directions` (list of str): Optimization direction ('minimize' or 'maximize') for each objective.
  *   `epsilons` (list of numbers): Epsilon values for each objective, defining the desired precision for performing the epsilon non-dominance calculation.

  ### Optional Keyword Arguments:
  *   `num_vars` (int, optional): Number of decision variables. Defaults to 0.
  *   `num_constrs` (int, optional): Number of constraints. Defaults to 0.

  ### How it works:
  1.  **Input Validation:** Checks if all input parameters are of the correct type and format.
  2.  **Initialize Label Column:** Creates a new column in the DataFrame (`label_col`) and sets all values to `False`.
  3.  **Convert to Platypus Format:** Uses the `df_to_pt` function to convert the DataFrame into a list of Platypus `Solution` objects.
  4.  **Epsilon Non-dominated Sorting:** Employs the `EpsilonBoxArchive` from Platypus to perform the epsilon non-dominated sort.
  5.  **Label Solutions:** Identifies the `id` (original DataFrame index) of the epsilon non-dominated solutions and updates the `label_col` in the input DataFrame to `True` for these solutions.
  6.  **Return DataFrame:** Returns the DataFrame with the new `label_col` populated.
  """
  # Validate input parameters
  if not isinstance(df, pd.DataFrame):
    raise TypeError("Input 'df' must be a pandas DataFrame.")
  if not isinstance(label_col, str) or not label_col:
    raise ValueError("Input 'label_col' must be a non-empty string.")
  if label_col in df.columns:
      raise ValueError(
          f"label_col '{label_col}' already exists in DataFrame. Please choose a different name.")
  if not isinstance(obj_names, list) or not all(isinstance(name, str) for name in obj_names):
    raise TypeError("Input 'objective_names' must be a list of strings.")
  if not obj_names:
    raise ValueError("Input 'objective_names' cannot be empty.")
  if not isinstance(obj_directions, list) or not all(isinstance(direction, str) for direction in obj_directions):
    raise TypeError("Input 'objective_directions' must be a list of strings.")
  if not all(d in ['minimize', 'maximize'] for d in obj_directions):
    raise ValueError("Objective directions must be 'minimize' or 'maximize'.")
  if not isinstance(epsilons, list) or not all(isinstance(e, (int, float)) for e in epsilons):
    raise TypeError("Input 'epsilons' must be a list of numbers.")

  if not (len(obj_names) == len(obj_directions) == len(epsilons)):
    raise ValueError(
        "Lengths of 'objective_names', 'objective_directions', and 'epsilons' must all match.")
  if not isinstance(num_vars, int) or num_vars < 0:
    raise ValueError("Input 'nvars' must be a non-negative integer.")
  if not isinstance(num_constrs, int) or num_constrs < 0:
    raise ValueError("Input 'nconstrs' must be a non-negative integer.")

  # reset the label column
  df[label_col] = False

  # convert to platypus format
  pt_solutions = df_to_pt(df, obj_names, obj_directions, num_vars, num_constrs)

  # save the epsilon non-dominated solutions to a new list of platypus solutions
  eps_pt = pt.EpsilonBoxArchive(epsilons)
  for solution in pt_solutions:
    eps_pt.add(solution)

  # save which ids ended up being epsilon non-dominated
  eps_ids = [sol.id for sol in eps_pt]

  # add labels to the epsilon non-dominated solutions
  for id in eps_ids:
    df.at[id, label_col] = True

  return df


def append_Kmeans(df, num_clusters=3, cluster_columns=None):
    """Cluster solutions with K-Means and append a 'Cluster' column in place.

    Args:
        df: DataFrame of solutions. Modified in place — a ``"Cluster"`` column
            containing integer cluster labels (0-indexed) is added.
        num_clusters: Number of K-Means clusters. Defaults to 3.
        cluster_columns: List of column names to use as features. When None,
            all columns in ``df`` are used.

    Returns:
        tuple[pd.DataFrame, sklearn.cluster.KMeans]:
            - The input ``df`` with the new ``"Cluster"`` column added.
            - The fitted KMeans object (useful for inspecting centroids).
    """
    kmeans = KMeans(n_clusters=num_clusters)
    if cluster_columns:
        kmeans.fit(df[cluster_columns])
    else:
        kmeans.fit(df)

    df["Cluster"] = kmeans.labels_

    return df, kmeans


def _resolve_config_path(output_folder, config_filename=None):
  """Resolve a configuration XML path for legacy and newer output folder layouts."""
  folder = Path(output_folder)

  # If the caller provided an explicit config file path, treat that as authoritative.
  # We fail fast here instead of silently falling back so path mistakes are visible.
  if config_filename is not None:
    candidate = folder / config_filename
    if candidate.exists():
      return candidate
    raise FileNotFoundError(
      f"Configuration XML not found: {candidate}. "
      f"Pass a valid config filename or set config_filename=None for auto-discovery."
    )

  # Ordered fallback list:
  # 1) historical CopyOfConfiguration.xml locations
  # 2) any XML file in common copy folders (for newer naming conventions)
  candidates = [
    folder / "CopyOfConfiguration.xml",
    folder / "InputFilesCopy" / "CopyOfConfiguration.xml",
    folder / "Input Files Copy" / "CopyOfConfiguration.xml",
  ]

  # Extend the candidate set with all XML files in likely locations.
  # This makes the helper robust when API versions preserve the original
  # configuration filename instead of copying to CopyOfConfiguration.xml.
  for subfolder in ["InputFilesCopy", "Input Files Copy", ""]:
    search_dir = folder / subfolder if subfolder else folder
    if search_dir.exists():
      candidates.extend(sorted(search_dir.glob("*.xml")))

  # Keep first-match behavior while avoiding duplicate path checks.
  # First match is intentional because candidate ordering encodes priority.
  seen = set()
  for candidate in candidates:
    candidate_str = str(candidate)
    if candidate_str in seen:
      continue
    seen.add(candidate_str)
    if candidate.exists() and candidate.is_file():
      return candidate

  raise FileNotFoundError(
    f"No configuration XML found in {folder}. "
    f"Expected CopyOfConfiguration.xml or an XML file under InputFilesCopy/Input Files Copy."
  )


def load_objective_names(output_folder, config_filename=None, return_config_path=False, include_directions=False):
  """Load objective names from an output folder configuration XML.

  Args:
    output_folder: Search output folder containing copied input files.
    config_filename: Optional relative path to a specific XML file. If None,
      auto-discovers legacy CopyOfConfiguration.xml or newer XML names.
    return_config_path: If True, also return the resolved config XML path.
    include_directions: If True, also return the list of objective directions.
  """
  if not isinstance(return_config_path, bool):
    raise TypeError("Input 'return_config_path' must be a boolean.")
  if not isinstance(include_directions, bool):
    raise TypeError("Input 'include_directions' must be a boolean.")

  config_path = _resolve_config_path(output_folder, config_filename=config_filename)
  _decision_variable_names, objective_names, objective_directions = process_xml(
    config_path,
    include_objective_directions=True,
    default_objective_direction="minimize"
  )

  if include_directions and return_config_path:
    return objective_names, objective_directions, config_path
  if include_directions:
    return objective_names, objective_directions
  if return_config_path:
    return objective_names, config_path
  return objective_names


def resolve_solutions_csv(output_folder, solutions_filename=None):
  """Resolve a solutions CSV path across canonical and user-renamed naming patterns."""
  folder = Path(output_folder)

  if solutions_filename is not None:
    candidate = folder / solutions_filename
    if candidate.exists():
      return candidate
    raise FileNotFoundError(f"Solutions CSV not found: {candidate}")

  # Preferred canonical outputs first (stable default behavior).
  candidates = [
    folder / "Plot.csv",
    folder / "Plot_with_clusters.csv",
    folder / "NondominatedSolutions.ToHiPlot.csv",
    folder / "NondominatedSolutions.csv",
  ]

  # Include contextual variants generated by iterative workflows.
  candidates.extend(sorted(folder.glob("Plot*.csv")))
  candidates.extend(sorted(folder.glob("NondominatedSolutions*.csv")))

  # Preserve first-match priority while removing duplicate paths.
  seen = set()
  deduped_candidates = []
  for candidate in candidates:
    candidate_str = str(candidate)
    if candidate_str in seen:
      continue
    seen.add(candidate_str)
    deduped_candidates.append(candidate)

  for candidate in deduped_candidates:
    if candidate.exists() and candidate.is_file():
      return candidate

  raise FileNotFoundError(
    f"No solutions CSV found in {folder}. Tried: {[c.name for c in deduped_candidates]}"
  )


def load_objectives_and_solutions(output_folder,
                                 config_filename=None,
                                 solutions_filename=None,
                                 return_paths=False,
                                 include_directions=False):
  """Load objective names and solutions DataFrame from an output folder.

  Args:
    output_folder: Search output folder containing copied input files and result CSVs.
    config_filename: Optional relative config XML path; auto-discovered when None.
    solutions_filename: Optional relative solutions CSV path; auto-discovered when None.
    return_paths: If True, also return resolved config and CSV paths.
    include_directions: If True, also return the list of objective directions.
  """
  if not isinstance(return_paths, bool):
    raise TypeError("Input 'return_paths' must be a boolean.")
  if not isinstance(include_directions, bool):
    raise TypeError("Input 'include_directions' must be a boolean.")

  if include_directions:
    objective_names, objective_directions, config_path = load_objective_names(
      output_folder,
      config_filename=config_filename,
      return_config_path=True,
      include_directions=True,
    )
  else:
    objective_names, config_path = load_objective_names(
      output_folder,
      config_filename=config_filename,
      return_config_path=True,
    )
  solutions_path = resolve_solutions_csv(output_folder, solutions_filename=solutions_filename)
  solutions = pd.read_csv(solutions_path)
  if solutions.empty:
    raise ValueError(f"Solutions file is empty: {solutions_path}")

  result = (objective_names, solutions)
  if include_directions:
    result += (objective_directions,)
  if return_paths:
    result += (config_path, solutions_path)
  return result


def normalize_for_radar(solutions, objective_names):
  """Return normalized radar values and objective labels with closure for polygon plotting."""
  if not isinstance(solutions, pd.DataFrame):
    raise TypeError("Input 'solutions' must be a pandas DataFrame.")
  if not isinstance(objective_names, list) or not objective_names or not all(isinstance(n, str) for n in objective_names):
    raise TypeError("Input 'objective_names' must be a non-empty list of strings.")

  objectives_with_closure = objective_names + [objective_names[0]]
  missing = [c for c in objectives_with_closure if c not in solutions.columns]
  if missing:
    raise ValueError(f"Objective columns missing from DataFrame: {missing}")

  normalized = solutions.copy(deep=True)
  scaler = MinMaxScaler()
  normalized[objectives_with_closure] = scaler.fit_transform(-1.0 * normalized[objectives_with_closure])
  return normalized, objectives_with_closure


def build_radar_figure(normalized_solutions, objectives_with_closure, showlegend=False):
  """Create a Plotly radar figure from normalized solution values."""
  if not isinstance(normalized_solutions, pd.DataFrame):
    raise TypeError("Input 'normalized_solutions' must be a pandas DataFrame.")
  if not isinstance(objectives_with_closure, list) or not all(isinstance(n, str) for n in objectives_with_closure):
    raise TypeError("Input 'objectives_with_closure' must be a list of strings.")
  if not isinstance(showlegend, bool):
    raise TypeError("Input 'showlegend' must be a boolean.")

  fig = go.Figure()
  for i in range(len(normalized_solutions)):
    fig.add_trace(go.Scatterpolar(
      r=normalized_solutions.iloc[i][objectives_with_closure].to_numpy(),
      theta=objectives_with_closure,
      fill='none',
      name=f"Solution {i}",
      opacity=0.5,
    ))

  fig.update_layout(
    polar=dict(radialaxis=dict(visible=True)),
    showlegend=showlegend
  )
  return fig


def run_eps_experiment(output_folder, objective_names, objective_directions,
                       solutions_base, experiment_name, epsilons):
  """Apply epsilon non-dominance labeling and write named output files.

  This is the core computation step for one epsilon experiment: it labels
  solutions, writes two CSVs and one HTML parallel-plot file, and returns
  a summary dict so callers can report results without coupling to the I/O.

  Args:
    output_folder: Directory where output files are written.
    objective_names: List of objective column names.
    objective_directions: List of 'minimize'/'maximize' strings matching objective_names.
    solutions_base: DataFrame of candidate solutions (not mutated; a copy is made).
    experiment_name: Filesystem-safe string used as a suffix in all output filenames.
    epsilons: List of epsilon values, one per objective.

  Returns:
    dict with keys:
      'n_total'    — total number of input solutions
      'n_retained' — number of epsilon non-dominated solutions
      'labeled_path'  — Path written for all solutions with eps_nd label
      'eps_only_path' — Path written for epsilon non-dominated solutions only
      'html_path'     — Path written for HiPlot parallel-plot HTML
  """
  if not isinstance(solutions_base, pd.DataFrame):
    raise TypeError("Input 'solutions_base' must be a pandas DataFrame.")
  if not isinstance(experiment_name, str) or not experiment_name:
    raise ValueError("Input 'experiment_name' must be a non-empty string.")

  folder = Path(output_folder)
  solutions = solutions_base.copy()
  solutions = label_eps_nd(
    solutions,
    label_col="eps_nd",
    obj_names=objective_names,
    obj_directions=objective_directions,
    epsilons=epsilons,
  )
  eps_solutions = solutions[solutions["eps_nd"]].copy()

  labeled_path = folder / f"Plot_with_eps_labels_{experiment_name}.csv"
  eps_only_path = folder / f"Plot_with_only_eps_{experiment_name}.csv"
  html_path = folder / f"Plot_with_only_eps_{experiment_name}.html"

  solutions.to_csv(labeled_path)
  eps_solutions.to_csv(eps_only_path)
  parallel_plot_hp(
    eps_solutions,
    obj_names=objective_names,
    obj_directions=objective_directions,
    hide_columns=["Solution"],
  ).to_html(html_path)

  return {
    "n_total": len(solutions),
    "n_retained": len(eps_solutions),
    "labeled_path": labeled_path,
    "eps_only_path": eps_only_path,
    "html_path": html_path,
  }


def log_eps_experiment(log_path, entry):
  """Write a single experiment record to a JSON file.

  One file is written per experiment. If the file already exists it is
  overwritten (e.g. when re-running an experiment with the same name).
  Path objects in the entry are automatically serialized to strings.

  Args:
    log_path: Path-like destination for the JSON file.
    entry: dict describing the experiment. All values must be JSON-serializable
      or Path objects (which are converted to strings automatically).
  """
  if not isinstance(entry, dict):
    raise TypeError("Input 'entry' must be a dict.")

  log_path = Path(log_path)

  def _serialize(obj):
    if isinstance(obj, Path):
      return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

  with open(log_path, "w", encoding="utf-8") as f:
    json.dump(entry, f, indent=2, default=_serialize)
    f.write("\n")
