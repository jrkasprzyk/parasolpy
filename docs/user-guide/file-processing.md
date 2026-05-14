# File Processing

The `parasolpy.file_processing` module normalizes solution CSV files from RiverWare/Borg-style optimization workflows.

It handles single-header CSV files and two-row superheader files where top-level groups identify decision variables, objectives, or metrics.

## Loading and Normalization

```python
from parasolpy.file_processing import (
    convert_solutions_csv_to_single_header,
    has_superheader,
    load_solutions_dataframe,
)
```

```python
solutions, metadata = load_solutions_dataframe(
    "NondominatedSolutions.csv",
    superheader="auto",
    return_metadata=True,
)
```

Use `convert_solutions_csv_to_single_header` to write a normalized CSV that is easier to inspect or pass to downstream tools.

## Splitting Decisions and Objectives

```python
from parasolpy.file_processing import split_solutions_csv, split_solutions_dataframe
```

These helpers separate decision-variable columns from objective columns using metadata from the superheader when available, or explicit column lists when needed.
