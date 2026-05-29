"""RiverWare RDF file parser and CSV converter.

This module provides both a library API and a command-line interface for
reading RiverWare RDF files and converting slot data to CSV.

Library
-------
    from parasolpy.rdf import parse_rdf, list_slots
    rdf = parse_rdf("model.rdf")
    for slot in list_slots(rdf):
        print(slot["key"])

CLI
---
    python -m parasolpy.rdf info <file.rdf>
    python -m parasolpy.rdf slots <file.rdf> [--series-only]
    python -m parasolpy.rdf convert <file.rdf> --slot "ObjectName.SlotName" --output out.csv
    python -m parasolpy.rdf convert <file.rdf> --slot "ObjectName.SlotName" --output out.csv --format wide
    python -m parasolpy.rdf convert <file.rdf> --slot "ObjectName.SlotName" --output out.csv --format stacked
    python -m parasolpy.rdf convert <file.rdf> --slot "ObjectName.SlotName" --output out.csv --format long
    python -m parasolpy.rdf convert <file.rdf> --slot "ObjectName.SlotName" --output out.csv --format enriched

RDF format (text, one token per line):
  Package preamble  key:value ... END_PACKAGE_PREAMBLE
  Per run:
    Run preamble    key:value ... END_RUN_PREAMBLE
    Timestep list   YYYY-M-D 24:00  (time_steps lines)
    Per slot:
      Slot preamble key:value ... END_SLOT_PREAMBLE
      units line
      scale line
      values        (time_steps lines for series; 1 line for scalar)
      END_COLUMN
      END_SLOT
    END_RUN
"""

from __future__ import annotations

import argparse
import csv
import sys
import warnings
from datetime import datetime
from pathlib import Path


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def _normalize_ts(raw: str) -> str:
    """Convert 'YYYY-M-D 24:00' → ISO date 'YYYY-MM-DD'."""
    date_part = raw.split()[0]
    dt = datetime.strptime(date_part, "%Y-%m-%d")
    # RiverWare 24:00 = end of that calendar day — keep as-is
    return dt.strftime("%Y-%m-%d")


def _parse_preamble(lines: list[str], pos: int, end_marker: str) -> tuple[dict, int]:
    """
    Read key:value lines from pos until end_marker (exclusive).
    Returns (dict, new_pos).  end_marker line is consumed.
    If end_marker == 1 (int), reads exactly one line.
    """
    result: dict = {}
    while pos < len(lines):
        line = lines[pos]
        pos += 1
        if line == end_marker:
            break
        parts = line.split(":", 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else None
        result[key] = value
        if end_marker == 1:  # sentinel: read exactly one line
            break
    return result, pos


def _parse_slot(lines: list[str], pos: int, nts: int) -> tuple[dict, int]:
    """Parse one slot block starting at pos (first line = object_type or similar)."""
    slot, pos = _parse_preamble(lines, pos, "END_SLOT_PREAMBLE")

    # units and scale are bare single-value lines (no key prefix)
    units_line = lines[pos]; pos += 1
    scale_line = lines[pos]; pos += 1

    # Parse bare "key: value" or just "value"
    def _bare_value(line: str) -> str:
        return line.split(":", 1)[-1].strip() if ":" in line else line.strip()

    slot["units"] = _bare_value(units_line)
    slot["scale"] = _bare_value(scale_line)

    # Find next END_COLUMN to determine scalar vs series
    ec_idx = next(
        (i for i in range(pos, len(lines)) if lines[i] == "END_COLUMN"),
        None,
    )
    if ec_idx is None:
        raise ValueError(f"END_COLUMN not found after position {pos}")

    n_values = ec_idx - pos
    slot_type = (slot.get("slot_type") or "").strip().lower()
    is_series_slot = "series" in slot_type
    is_scalar_slot = "scalar" in slot_type

    if is_series_slot:
        slot["scalar"] = False
    elif is_scalar_slot:
        slot["scalar"] = True
    elif n_values == nts:
        slot["scalar"] = False
    elif n_values == 1:
        slot["scalar"] = True
    else:
        warnings.warn(
            f"Slot '{slot.get('object_name')}.{slot.get('slot_name')}': "
            f"expected {nts} or 1 values, found {n_values}. Skipping."
        )
        slot["values"] = []
        slot["scalar"] = None
        pos = ec_idx + 1  # skip to after END_COLUMN
        if pos < len(lines) and lines[pos] == "END_SLOT":
            pos += 1
        return slot, pos

    raw_values = lines[pos : pos + n_values]
    try:
        slot["values"] = [float(v) for v in raw_values]
    except ValueError:
        slot["values"] = raw_values  # keep as strings if not numeric

    pos = ec_idx + 1  # advance past END_COLUMN
    if pos < len(lines) and lines[pos] == "END_SLOT":
        pos += 1

    return slot, pos


def _parse_run(lines: list[str], pos: int) -> tuple[dict, int]:
    """Parse one run block.  pos points to first line after END_PACKAGE_PREAMBLE
    (or after previous END_RUN)."""
    run: dict = {}

    preamble, pos = _parse_preamble(lines, pos, "END_RUN_PREAMBLE")
    run["preamble"] = preamble

    nts = int(preamble.get("time_steps") or preamble.get("timesteps") or 0)

    # Read timestep list
    raw_times = lines[pos : pos + nts]
    run["times"] = [_normalize_ts(t) for t in raw_times]
    pos += nts

    # Read slots until END_RUN
    run["slots"] = {}
    while pos < len(lines):
        if lines[pos] == "END_RUN":
            pos += 1
            break

        slot, pos = _parse_slot(lines, pos, nts)
        key = f"{slot.get('object_name', '')}.{slot.get('slot_name', '')}"
        run["slots"][key] = slot

    return run, pos


def parse_rdf(path: str | Path) -> dict:
    """
    Parse a RiverWare RDF file.

    Returns:
        {
            "meta": {key: value, ...},
            "runs": [
                {
                    "preamble": {key: value, ...},
                    "times": ["YYYY-MM-DD", ...],
                    "slots": {
                        "ObjectName.SlotName": {
                            "object_type": ..., "object_name": ...,
                            "slot_type": ..., "slot_name": ...,
                            "units": ..., "scale": ...,
                            "scalar": bool,
                            "values": [float, ...]
                        },
                        ...
                    }
                },
                ...
            ]
        }
    """
    path = Path(path)
    if path.suffix.lower() != ".rdf":
        raise ValueError(f"{path} does not appear to be an rdf file.")
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist.")

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    # Strip carriage returns from Windows line endings
    lines = [ln.rstrip("\r") for ln in lines]

    pos = 0
    meta, pos = _parse_preamble(lines, pos, "END_PACKAGE_PREAMBLE")

    expected_runs = int(meta.get("number_of_runs") or 0)
    runs: list[dict] = []

    while len(runs) < expected_runs and pos < len(lines):
        run, pos = _parse_run(lines, pos)
        runs.append(run)

    return {"meta": meta, "runs": runs}


def list_slots(rdf: dict) -> list[dict]:
    """Return slot metadata list from first run (all runs share the same slots)."""
    if not rdf["runs"]:
        return []
    return [
        {
            "key": key,
            "object_name": s.get("object_name", ""),
            "slot_name": s.get("slot_name", ""),
            "object_type": s.get("object_type", ""),
            "slot_type": s.get("slot_type", ""),
            "units": s.get("units", ""),
            "scale": s.get("scale", ""),
            "scalar": s.get("scalar"),
        }
        for key, s in rdf["runs"][0]["slots"].items()
    ]


# --------------------------------------------------------------------------- #
# CSV writers
# --------------------------------------------------------------------------- #
def _scalar_keys(runs: list[dict]) -> list[str]:
    first_slots = runs[0]["slots"]
    return [k for k, v in first_slots.items() if v.get("scalar")]


def _stacked_date_col_name(ref_times: list[str]) -> str:
    # Annual data in sample files is represented by Jan 1 timestamps.
    if ref_times and all(t.endswith("-01-01") for t in ref_times):
        return "year"
    return "date"


def _trace_id(run: dict) -> str:
    return f"trace_{run['preamble'].get('trace', '?')}"


def _write_wide(
    runs: list[dict], slot_key: str, ref_times: list[str], out_path: Path
) -> None:
    headers = ["date"] + [_trace_id(r) for r in runs]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        # Determine row count from first run's slot
        first_values = runs[0]["slots"][slot_key]["values"]
        n_rows = len(first_values)

        for row_i in range(n_rows):
            date = ref_times[row_i] if row_i < len(ref_times) else ""
            row = [date]
            for run in runs:
                vals = run["slots"][slot_key]["values"]
                row.append(vals[row_i] if row_i < len(vals) else "")
            writer.writerow(row)


def _write_long(
    runs: list[dict], slot_key: str, ref_times: list[str], out_path: Path
) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "trace", "value"])
        for run in runs:
            trace = _trace_id(run)
            vals = run["slots"][slot_key]["values"]
            for i, val in enumerate(vals):
                date = ref_times[i] if i < len(ref_times) else ""
                writer.writerow([date, trace, val])


def _write_stacked_header(
    runs: list[dict],
    slot_key: str,
    ref_times: list[str],
    out_path: Path,
    scalar_keys: list[str],
) -> None:
    trace_ids = [_trace_id(r) for r in runs]
    date_col = _stacked_date_col_name(ref_times)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        for sk in scalar_keys:
            label_name = sk.split(".", 1)[1] if "." in sk else sk
            label_vals = []
            for run in runs:
                vals = run["slots"][sk]["values"]
                label_vals.append(vals[0] if vals else "")
            writer.writerow([label_name] + label_vals)

        writer.writerow([date_col] + trace_ids)

        first_values = runs[0]["slots"][slot_key]["values"]
        n_rows = len(first_values)
        for row_i in range(n_rows):
            date = ref_times[row_i] if row_i < len(ref_times) else ""
            row = [date]
            for run in runs:
                vals = run["slots"][slot_key]["values"]
                row.append(vals[row_i] if row_i < len(vals) else "")
            writer.writerow(row)


def _write_enriched(
    runs: list[dict], slot_key: str, ref_times: list[str], out_path: Path
) -> None:
    """Stacked format with scalar slot values appended as label columns."""
    scalar_keys = _scalar_keys(runs)
    category_names = [k.split(".", 1)[1] if "." in k else k for k in scalar_keys]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "trace", "value"] + category_names)
        for run in runs:
            trace = _trace_id(run)
            vals = run["slots"][slot_key]["values"]
            scalar_vals = [run["slots"][sk]["values"][0] if run["slots"][sk]["values"] else ""
                           for sk in scalar_keys]
            for i, val in enumerate(vals):
                date = ref_times[i] if i < len(ref_times) else ""
                writer.writerow([date, trace, val] + scalar_vals)


def _write_sidecar(runs: list[dict], out_path: Path) -> Path | None:
    """Write <stem>_labels.csv with one row per trace and one column per scalar slot.

    Returns the sidecar path, or None if no scalar slots exist.
    """
    scalar_keys = _scalar_keys(runs)
    if not scalar_keys:
        return None

    sidecar_path = out_path.with_name(out_path.stem + "_labels.csv")
    # Use just the slot_name portion (after the dot) as the category header.
    category_names = [k.split(".", 1)[1] if "." in k else k for k in scalar_keys]

    with sidecar_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["column"] + category_names)
        for run in runs:
            row = [_trace_id(run)]
            for sk in scalar_keys:
                vals = run["slots"][sk]["values"]
                row.append(vals[0] if vals else "")
            writer.writerow(row)

    return sidecar_path


# --------------------------------------------------------------------------- #
# CLI commands
# --------------------------------------------------------------------------- #
def cmd_info(args: argparse.Namespace) -> None:
    rdf = parse_rdf(args.file)
    meta = rdf["meta"]
    runs = rdf["runs"]

    print("=== Package metadata ===")
    for k, v in meta.items():
        print(f"  {k}: {v}")

    if runs:
        first = runs[0]["preamble"]
        last = runs[-1]["preamble"]
        print(f"\n=== Runs ===")
        print(f"  count         : {len(runs)}")
        print(f"  time_step_unit: {first.get('time_step_unit', 'unknown')}")
        print(f"  first run     : trace={first.get('trace')}  "
              f"start={first.get('start')}  end={first.get('end')}  "
              f"time_steps={first.get('time_steps')}")
        print(f"  last run      : trace={last.get('trace')}  "
              f"start={last.get('start')}  end={last.get('end')}")

    slots = list_slots(rdf)
    if slots:
        print(f"\n=== Slots ({len(slots)}) ===")
        col_w = max(len(s["key"]) for s in slots) + 2
        header = f"  {'slot':<{col_w}}  {'type':<18}  {'units':<12}  scalar"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for s in slots:
            print(
                f"  {s['key']:<{col_w}}  {s['slot_type']:<18}  "
                f"{s['units']:<12}  {s['scalar']}"
            )
    else:
        print("No slots found.")


def cmd_convert(args: argparse.Namespace) -> None:
    rdf = parse_rdf(args.file)
    runs = rdf["runs"]

    if not runs:
        print("No runs found in file.", file=sys.stderr)
        sys.exit(1)

    slot_key = args.slot

    # Validate slot exists
    available = list(runs[0]["slots"].keys())
    if slot_key not in available:
        print(f"Slot '{slot_key}' not found.", file=sys.stderr)
        print("Available slots:", file=sys.stderr)
        for k in available:
            print(f"  {k}", file=sys.stderr)
        sys.exit(1)

    # Warn if timesteps differ across runs
    ref_times = runs[0]["times"]
    for i, run in enumerate(runs[1:], start=2):
        if run["times"] != ref_times:
            warnings.warn(
                f"Run {i} (trace={run['preamble'].get('trace')}) has different "
                f"timesteps from run 1. Using run 1 timesteps for date column."
            )

    slot_info = runs[0]["slots"][slot_key]
    if slot_info.get("scalar"):
        print(
            f"Warning: '{slot_key}' is a scalar slot (1 value per run, not per timestep). "
            "Output will have 1 data row.",
            file=sys.stderr,
        )

    out_path = Path(args.output)

    fmt = args.format if args.format is not None else "wide"
    scalar_keys = _scalar_keys(runs)

    if fmt == "wide":
        _write_wide(runs, slot_key, ref_times, out_path)
        sidecar_path = _write_sidecar(runs, out_path)
        print(f"Wrote {out_path}")
        if sidecar_path:
            print(f"Wrote {sidecar_path}")
    elif fmt == "stacked":
        if not scalar_keys:
            print(
                "Format 'stacked' requires scalar slots for label header rows. "
                "No scalar slots were found.",
                file=sys.stderr,
            )
            sys.exit(1)
        _write_stacked_header(runs, slot_key, ref_times, out_path, scalar_keys)
        print(f"Wrote {out_path}")
    elif fmt == "long":
        _write_long(runs, slot_key, ref_times, out_path)
        print(f"Wrote {out_path}")
    else:  # enriched
        _write_enriched(runs, slot_key, ref_times, out_path)
        print(f"Wrote {out_path}")


def cmd_slots(args: argparse.Namespace) -> None:
    """Print one slot key per line — useful for scripting."""
    rdf = parse_rdf(args.file)
    for s in list_slots(rdf):
        if args.series_only and s["scalar"]:
            continue
        print(s["key"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="parasolpy-rdf",
        description="Read and convert RiverWare RDF files.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # info
    p_info = sub.add_parser("info", help="Print metadata and slot list.")
    p_info.add_argument("file", help="Path to .rdf file.")

    # slots
    p_slots = sub.add_parser("slots", help="Print slot names one per line (for scripting).")
    p_slots.add_argument("file", help="Path to .rdf file.")
    p_slots.add_argument("--series-only", action="store_true",
                         help="Exclude scalar slots; print series slots only.")

    # convert
    p_conv = sub.add_parser("convert", help="Export a slot to CSV.")
    p_conv.add_argument("file", help="Path to .rdf file.")
    p_conv.add_argument(
        "--slot",
        required=True,
        metavar="OBJECT.SLOT",
        help='Slot to export, e.g. "Example Reservoir.Pool Elevation".',
    )
    p_conv.add_argument("--output", required=True, metavar="PATH", help="Output CSV path.")
    p_conv.add_argument(
        "--format",
        choices=["wide", "stacked", "long", "enriched"],
        default=None,
        help=(
            "Output format. Default: wide. "
            "Options: wide (wide + optional sidecar), stacked (wide with scalar "
            "label header rows), long (date/trace/value), enriched (long + labels)."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "info":
        cmd_info(args)
    elif args.command == "slots":
        cmd_slots(args)
    elif args.command == "convert":
        cmd_convert(args)


if __name__ == "__main__":
    main()
