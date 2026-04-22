"""Interactive CLI helpers for epsilon experiment workflows.

These functions handle user prompting and input validation; they contain no
analysis logic. Import them in scripts that need a terminal-based interface
for iterating on epsilon non-dominance parameters.
"""

import json
from pathlib import Path


class ExitInteractiveSession(Exception):
    """Raised when the user requests to exit an interactive CLI workflow."""


def _raise_if_exit_requested(value):
    """Exit the interactive workflow when the user types a quit command."""
    if value.lower() in {"q", "quit", "exit"}:
        raise ExitInteractiveSession()


def prompt_experiment_name(prompt_text="\nExperiment name: "):
    """Prompt the user for a filesystem-safe experiment name.

    Returns:
        str: A sanitized, non-empty experiment name suitable for use in filenames.
    """
    while True:
        name = input(prompt_text).strip()
        _raise_if_exit_requested(name)
        if not name:
            print("  Name cannot be empty.")
            continue
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
        if safe != name:
            print(f"  Sanitized to: {safe}")
        return safe


def prompt_epsilons(objective_names, current_epsilons):
    """Prompt for an epsilon value per objective, carrying forward the current value as default.

    Args:
        objective_names: List of objective name strings shown as labels.
        current_epsilons: List of current epsilon floats used as defaults.

    Returns:
        list of float: New epsilon values, one per objective.
    """
    if len(objective_names) != len(current_epsilons):
        raise ValueError(
            "objective_names and current_epsilons must have the same length."
        )
    print("Enter epsilon for each objective (press Enter to keep current value, or 'q' to quit):")
    new_epsilons = []
    for name, current in zip(objective_names, current_epsilons):
        while True:
            raw = input(f"  {name} [{current}]: ").strip()
            _raise_if_exit_requested(raw)
            if raw == "":
                new_epsilons.append(current)
                break
            try:
                val = float(raw)
                if val <= 0:
                    print("  Epsilon must be positive.")
                    continue
                new_epsilons.append(val)
                break
            except ValueError:
                print("  Invalid number, try again.")
    return new_epsilons


def load_experiment_epsilons(output_folder, experiment_name, objective_names):
    """Load epsilon defaults from a saved experiment JSON file.

    Args:
        output_folder: Folder containing per-experiment JSON files.
        experiment_name: Experiment suffix used in eps_experiment_<name>.json.
        objective_names: Ordered list of objectives to align the returned epsilons.

    Returns:
        list of float: Epsilons ordered to match objective_names.
    """
    log_path = Path(output_folder) / f"eps_experiment_{experiment_name}.json"
    if not log_path.exists():
        raise FileNotFoundError(f"Experiment file not found: {log_path}")

    with open(log_path, "r", encoding="utf-8") as f:
        record = json.load(f)

    if not isinstance(record, dict) or "epsilons" not in record:
        raise ValueError(f"Experiment file is missing an 'epsilons' object: {log_path}")

    epsilon_map = record["epsilons"]
    missing = [name for name in objective_names if name not in epsilon_map]
    if missing:
        raise ValueError(
            f"Experiment file {log_path.name} is missing epsilon values for: {missing}"
        )

    return [float(epsilon_map[name]) for name in objective_names]


def prompt_starting_epsilons(output_folder, objective_names, default_epsilons):
    """Optionally seed starting epsilons from a previously saved experiment.

    If no prior experiment is chosen, returns default_epsilons unchanged along
    with None for the experiment name.
    """
    folder = Path(output_folder)
    available = sorted(
        path.stem.removeprefix("eps_experiment_")
        for path in folder.glob("eps_experiment_*.json")
    )
    if not available:
        return default_epsilons, None

    print("Saved epsilon experiments:")
    print(f"  {', '.join(available)}")
    if len(available) == 1:
        prompt = (
            "Load saved experiment by name"
            f" (or 'y' to use '{available[0]}')? [Enter to skip]: "
        )
    else:
        prompt = "Load saved experiment by name? [Enter to skip, q to quit]: "

    choice = input(prompt).strip()
    _raise_if_exit_requested(choice)
    if not choice:
        return default_epsilons, None

    if len(available) == 1 and choice.lower() in {"y", "yes"}:
        choice = available[0]

    return load_experiment_epsilons(folder, choice, objective_names), choice
