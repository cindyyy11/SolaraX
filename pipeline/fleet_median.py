"""Recompute the observed PVDAQ fleet specific yield straight from the parquet.

WHY THIS EXISTS. The fleet median (kWh per kWp per day) is a number we want to
put in front of judges, and right now it is only visible inside a generated
dispatch.json whose neighbouring values are PLACEHOLDER. A reader cannot tell
which is which.

Worse, config/assumptions.json carries assumed_yield_kwh_per_kwp_day = 3.8 and
the observed median lands near it. That looks like circular reasoning even
though the two come from completely separate code paths: the assumption feeds
placeholder_performance_index() and nothing else, while the observed median is
computed by mean_performance_index() over the real parquet series.

This script exists so nobody has to take that on trust. It reads only the
measured data and prints the arithmetic.

Run:
    python pipeline/fleet_median.py
    python pipeline/fleet_median.py --json    # machine-readable

Reads:  data/processed/fleet_daily.parquet
Writes: nothing.
"""

import argparse
import json
import os

import pandas as pd

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLEET_DAILY_PATH = os.path.join(REPOSITORY_ROOT, "data", "processed", "fleet_daily.parquet")
ASSUMPTIONS_PATH = os.path.join(REPOSITORY_ROOT, "config", "assumptions.json")


def compute(frame, floor):
    """Per-site mean specific yield, then the fleet median over plausible sites.

    Mirrors build_exclusions() in generate_dispatch.py deliberately: sites below
    the plausibility floor are excluded from the fleet median, because a site
    reporting a fraction of its real output would otherwise drag the reference
    down and make genuinely healthy peers look better than they are.
    """
    per_site = (
        frame.groupby("site_id")
        .agg(
            mean_specific_yield=("performance_index", "mean"),
            days=("performance_index", "size"),
            capacity_kwp=("capacity_kwp", "first"),
        )
        .sort_values("mean_specific_yield")
    )

    per_site["included"] = per_site["mean_specific_yield"] >= floor
    included = per_site[per_site["included"]]

    return per_site, {
        "fleet_median_kwh_per_kwp_day": round(float(included["mean_specific_yield"].median()), 4),
        "fleet_mean_kwh_per_kwp_day": round(float(included["mean_specific_yield"].mean()), 4),
        "sites_total": int(len(per_site)),
        "sites_included": int(len(included)),
        "sites_excluded": int((~per_site["included"]).sum()),
        "plausibility_floor_kwh_per_kwp_day": floor,
        "site_days": int(per_site["days"].sum()),
        "date_min": str(frame["date"].min()),
        "date_max": str(frame["date"].max()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    args = parser.parse_args()

    with open(ASSUMPTIONS_PATH) as handle:
        assumptions = json.load(handle)
    floor = assumptions["min_plausible_performance_index"]

    frame = pd.read_parquet(FLEET_DAILY_PATH)
    per_site, result = compute(frame, floor)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("Observed specific yield — real NREL PVDAQ measurements only")
    print("source: {}".format(os.path.relpath(FLEET_DAILY_PATH, REPOSITORY_ROOT)))
    print("window: {} to {}  ({} site-days)".format(
        result["date_min"], result["date_max"], result["site_days"]))
    print("-" * 66)
    print("{:<10} {:>10} {:>8} {:>8}   {}".format(
        "site_id", "kWh/kWp/d", "kWp", "days", "in median"))
    for site_id, row in per_site.iterrows():
        print("{:<10} {:>10.3f} {:>8.1f} {:>8d}   {}".format(
            site_id,
            row["mean_specific_yield"],
            row["capacity_kwp"],
            int(row["days"]),
            "yes" if row["included"] else "NO — below floor",
        ))
    print("-" * 66)
    print("plausibility floor      {:.2f} kWh/kWp/day  (assumptions.min_plausible_performance_index)".format(floor))
    print("sites in median         {} of {}".format(result["sites_included"], result["sites_total"]))
    print("FLEET MEDIAN            {:.4f} kWh/kWp/day".format(result["fleet_median_kwh_per_kwp_day"]))
    print("fleet mean              {:.4f} kWh/kWp/day".format(result["fleet_mean_kwh_per_kwp_day"]))
    print()
    print("This number is measured. assumptions.assumed_yield_kwh_per_kwp_day")
    print("({}) is not an input to it — see the module docstring.".format(
        assumptions["assumed_yield_kwh_per_kwp_day"]))


if __name__ == "__main__":
    main()
