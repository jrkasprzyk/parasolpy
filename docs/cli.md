# Tradeoff Explorer CLI

`parasolpy` installs the `parasolpy-tradeoff` command for launching an interactive Dash parallel-coordinates explorer against a results folder.

```bash
parasolpy-tradeoff path/to/output_folder
```

The equivalent module invocation is:

```bash
python -m parasolpy.dash_tools path/to/output_folder
```

Common options:

```bash
parasolpy-tradeoff path/to/output_folder \
  --config problem.xml \
  --solutions NondominatedSolutions.csv \
  --title "Tradeoff Explorer" \
  --colorscale viridis \
  --host 127.0.0.1 \
  --port 8050
```

Use `--debug` for local Dash debugging.

The output folder should contain a RiverWare/Borg-style XML configuration and solutions CSV, or you can pass explicit file names with `--config` and `--solutions`.
