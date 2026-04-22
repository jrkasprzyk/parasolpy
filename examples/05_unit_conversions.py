"""Unit conversions and annual pivoting utilities from parasolpy.util."""
import numpy as np
import pandas as pd

from parasolpy.util import (
    convert_cfs_to_af,
    convert_cfs_to_cms,
    convert_cms_to_mcm,
    pivot_timeseries_by_year,
)


def main():
    # Scalars: 1000 cfs for one month ≈ 59,502 acre-feet
    cfs = 1000
    print(f"{cfs} cfs = {convert_cfs_to_af(cfs):.1f} AF (monthly)")
    print(f"{cfs} cfs = {convert_cfs_to_cms(cfs):.2f} cms")
    print(f"100 cms  = {convert_cms_to_mcm(100):.2f} MCM (monthly)")

    # Vectorized: np.array in → np.array out
    arr = np.array([100, 500, 1000, 2500])
    print("cfs -> AF (array):", convert_cfs_to_af(arr))

    # Annual pivot of a daily series into a year x day-of-year matrix.
    rng = np.random.default_rng(3)
    dates = pd.date_range("2018-01-01", "2020-12-31", freq="D")
    flows = pd.Series(
        100 + 30 * np.sin(2 * np.pi * dates.dayofyear / 365) + rng.normal(0, 5, len(dates)),
        index=dates,
        name="flow",
    )
    pivoted = pivot_timeseries_by_year(flows)
    print("\nAnnual pivot (first 5 rows):")
    print(pivoted.head())
    print(f"Shape: {pivoted.shape}  (rows=day-of-year, cols=year)")


if __name__ == "__main__":
    main()
