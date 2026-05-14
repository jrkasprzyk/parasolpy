# Utilities

The `parasolpy.util` module contains path helpers, unit conversions, yearly time-series pivoting, and XML parsing utilities.

## Paths

```python
from parasolpy.util import ensure_dir, script_local_path
```

`ensure_dir(path)` creates a directory and parents when missing. `script_local_path(filename)` resolves a path relative to the calling script.

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
