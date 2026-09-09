# Command-Line Tools

## Tradeoff Explorer

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

## Runtime Leaderboard

`parasolpy-runtime` watches a Borg MOEA runtime file while the run writes it and
renders the archive as a live leaderboard: new solutions appear green and
labelled `born`, removed solutions linger briefly as struck-through red `died`
rows, and survivors carry arrows showing places gained or lost.

```bash
parasolpy-runtime path/to/RunTime.txt
```

The equivalent module invocation is:

```bash
python -m parasolpy.runtime_dashboard path/to/RunTime.txt
```

Common options:

```bash
parasolpy-runtime path/to/RunTime.txt \
  --sort-column "Cora Avg Storage" \
  --descending \
  --interval 2 \
  --ghosts 2 \
  --port 8051
```

| Option | Purpose |
| --- | --- |
| `--sort-column NAME` | What to sort by: a data column name, or `id` / `age`. Default: `id`, which is oldest first. |
| `--descending` | Sort largest first instead of smallest first. |
| `--columns A,B,C` | Names for the data columns after the solution ID, for older runtime files that carry no header row. |
| `--ghosts N` | Snapshots a dead solution stays visible. `0` removes it immediately. |
| `--interval SECONDS` | Poll period. Also selectable in the page. |
| `--max-rows N` | Cap on rendered rows, from the top of the sort order. |
| `--replay` | Replay a finished file, one snapshot per refresh, instead of tailing a live one. |
| `--speed N` | Snapshots per refresh while replaying. |
| `--loop` | Restart a replay when it reaches the end. |
| `--demo` | Replay the bundled sample runtime file on a loop. |

The runtime file does not have to exist yet — the page shows
`waiting for first snapshot` until the run writes one, so the dashboard can be
opened before the optimization starts. If the file is truncated or rewritten,
the leaderboard resets and follows the new run.

Use `--debug` for local Dash debugging.

To see it move without a live run:

```bash
parasolpy-runtime --demo
```
