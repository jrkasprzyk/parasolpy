# Utilities

The `parasolpy.util` module contains path helpers, unit conversions, yearly time-series pivoting, and XML parsing utilities.

## Paths

```python
from parasolpy.util import ensure_dir, script_local_path
```

### `script_local_path`

`script_local_path(filename)` resolves a filename relative to the **directory of the calling script**, not the current working directory.  This is useful when a script needs to open data files that live next to it, regardless of where the script is launched from.

```python
# my_script.py  (lives in  /home/user/project/)
from parasolpy.util import script_local_path

# Resolves to /home/user/project/data/input.csv even when the script is
# run from a different working directory.
input_path = script_local_path("data/input.csv")

# Both forward slashes and backslashes are accepted, so Windows-style
# paths work on every platform.
input_path = script_local_path("data\\input.csv")

# Use must_exist=False to obtain a path for a file you are about to create.
output_path = script_local_path("results/output.csv", must_exist=False)
```

`script_local_path` raises `FileNotFoundError` by default when the target does not exist.  Pass `must_exist=False` to suppress this check.

### `ensure_dir`

`ensure_dir(path)` creates a directory (and any missing parents) and returns it as a `Path` object. Calling it on an already-existing directory is safe.

```python
from parasolpy.util import ensure_dir, script_local_path

# Create an output directory next to the script, then build a path inside it.
output_dir = ensure_dir(script_local_path("results", must_exist=False))
output_path = output_dir / "summary.csv"
```

## Unit Conversions

```python
from parasolpy.util import convert_cfs_to_af, convert_cfs_to_cms, convert_cms_to_mcm
```

These helpers accept numeric scalars, lists, tuples, NumPy arrays, and pandas Series.

```python
from parasolpy.util import convert_cfs_to_af

acre_feet_per_day = convert_cfs_to_af([100.0, 125.0, 90.0])
```

## Yearly Pivot

```python
from parasolpy.util import pivot_timeseries_by_year
```

`pivot_timeseries_by_year` turns a datetime-indexed Series or DataFrame into a day-of-year by year table.

## XML Parsing

```python
from parasolpy.util import process_xml, read_xml
```

`process_xml` extracts decision-variable names, objective names, and optionally objective directions from optimization configuration XML files.
