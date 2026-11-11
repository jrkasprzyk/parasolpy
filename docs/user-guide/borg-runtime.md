# Borg Runtime Analysis

The `parasolpy.borg_runtime` module parses Borg MOEA runtime files and finds when each archived solution was born and when it was removed. Use it to see how long solutions survive in the archive, and to find saved solution-model files that Borg-RiverWare did not delete.

## Runtime File Format

A Borg runtime file contains periodic snapshots of the archive. Each snapshot has:

1. A header block: `Function evaluations N`, operator probabilities, `Improvements`, `Restarts`, `Population size`, and `Archive size`.
2. One whitespace-delimited row per archive member. The first field is the solution ID, which is the function evaluation (NFE) at which the solution was created.

## Functions

```python
from parasolpy.borg_runtime import (
    leaked_model_ids,
    parse_borg_runtime,
    parse_borg_runtime_metadata,
    solution_lifespans,
)
```

These four functions are also available from the package root (`from parasolpy import ...`).

| Function | Returns |
|---|---|
| `parse_borg_runtime(path)` | List of `(nfe, ids)` pairs, one per snapshot, in file order. `ids` is the set of solution IDs in the archive at that snapshot. |
| `parse_borg_runtime_metadata(path)` | DataFrame indexed by `nfe` with columns `improvements`, `restarts`, `population_size`, and `archive_size`. |
| `solution_lifespans(snapshots)` | DataFrame indexed by solution `id` with columns `birth`, `death`, and `in_final_archive`. |
| `leaked_model_ids(models_dir, spans)` | Sorted list of solution IDs that have a model file on disk but appear in no snapshot. |

## Lifespans

```python
snapshots = parse_borg_runtime("RunTime.txt")
spans = solution_lifespans(snapshots)

lifespan = spans["death"] - spans["birth"]
print(lifespan.median())
```

`birth` is always equal to the solution ID. Snapshots are periodic, so the real removal point is somewhere between the last snapshot that contains the solution and the next snapshot. By convention, `death` is the NFE of that next snapshot. For solutions still in the final archive, `death` is the final NFE.

## Leaked Model Files

Borg-RiverWare saves one model file per archived solution (for example `Solution123.mdl`) and deletes it when the solution leaves the archive. If a solution enters and leaves the archive between two snapshots, no snapshot records it. This often happens during a restart, when Borg writes no runtime output. Snapshot-based cleanup cannot see these solutions, so their files stay on disk.

```python
leaked = leaked_model_ids("path/to/SolutionModels", spans)
```

The default file pattern is `Solution*.mdl`. Use the `pattern` argument to change it. The function reads the first integer in each file name as the solution ID.

## Plotting

Use `parasolpy.plotting.plot_archive_lifespans` to plot the snapshots, with optional leaked IDs. See [Plotting](plotting.md#borg-archive-lifespans).

## Example Script

```bash
python examples/07_borg_archive_lifespan.py
python examples/07_borg_archive_lifespan.py path/to/SolutionModels
```

The script uses the bundled sample `parasolpy/data/RunTime_NorthSouth.txt`. It prints summary statistics and writes `examples/_output/archive_lifespan.png`. If you give it a `SolutionModels` folder, it also plots the leaked model IDs.
