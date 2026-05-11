# Example Scripts and Notebooks

These examples assume `borgRWhelper` is importable from any folder.

## One-time setup (per virtual environment)

From the repository root, run:

```powershell
c:/GitHub/BorgRWProblems/borgRWhelper/.venv/Scripts/python.exe -m pip install -e .
```

This installs the repo in editable mode so imports like:

```python
from borgRWhelper.nowak import sim_single_year, sim_multi_trace
```

work from `example_scripts/` and other deep subfolders without modifying `sys.path`.

## Script versions

These original scripts remain at the top level of `example_scripts/`:
- `nowak_basic_examples.py`
- `nowak_oakcreek_example.py`
- `sort_and_plot_tradeoffs.py`
- `minimal_dash_app.py`
- `mkdir_output_tutorial.py`

## Notebook versions

Each converted notebook now lives in its own subfolder with local inputs and outputs:
- `nowak_basic_examples/`
- `nowak_oakcreek_example/`
- `sort_and_plot_tradeoffs/`
- `minimal_dash_app/`
- `mkdir_output_tutorial/`

Each notebook folder follows this structure:
- `data/` for local input/context files
- `output/` for generated outputs
- `<example_name>.ipynb` and a local `README.md`

## Existing notebook demo

The original file-processing notebook remains in:
- `file_processing_demo/`
