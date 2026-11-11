# Borg Archive Lifespan Example

Script: `examples/07_borg_archive_lifespan.py`

This example parses the bundled Borg runtime file `parasolpy/data/RunTime_NorthSouth.txt`, finds the birth and death of every archived solution, and draws a survival chart.

```bash
python examples/07_borg_archive_lifespan.py
```

To also plot leaked model files, give the script a Borg-RiverWare `SolutionModels` folder:

```bash
python examples/07_borg_archive_lifespan.py path/to/SolutionModels
```

The script prints the snapshot count and NFE range, the number of solutions ever archived, the number still in the final archive, and the median and maximum lifespans.

Outputs:

- `examples/_output/archive_lifespan.png`

See [Borg Runtime Analysis](../user-guide/borg-runtime.md) for details on the functions.
