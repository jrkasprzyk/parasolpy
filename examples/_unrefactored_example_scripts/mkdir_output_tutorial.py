import pandas as pd

from borgRWhelper.util import script_local_path, ensure_dir


def main():
    # Resolve an output folder path relative to this script. It may not exist yet.
    output_dir = script_local_path("generated_outputs", must_exist=False)

    # Create the folder tree if needed.
    ensure_dir(output_dir)

    # Build an output file path and write a sample table.
    output_csv = output_dir / "sample_results.csv"
    demo_df = pd.DataFrame(
        {
            "Scenario": ["A", "B", "C"],
            "Score": [0.91, 0.87, 0.95],
        }
    )
    demo_df.to_csv(output_csv, index=False)

    print(f"Wrote: {output_csv}")


if __name__ == "__main__":
    main()
