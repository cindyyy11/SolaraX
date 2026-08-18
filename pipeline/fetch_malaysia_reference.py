"""Pull PVGIS reference cases for the four Malaysian sites named in the PRD.

WHY THIS EXISTS. Every generation number in SolaraX comes from American
inverters, because no openly reusable per-site Malaysian inverter time series
exists (docs/RESEARCH.md section 5, verified three ways). That is a fact about
the world, not a gap we can close by looking harder.

What we CAN compute honestly is the other half: what a system at real Malaysian
coordinates SHOULD produce, from real satellite weather through a real physical
model. That is a reference case, not a measurement, and this script is careful
about the difference.

WHAT THIS IS NOT. It does not produce measured Malaysian output and must never
be presented as such. It cannot be used as ground truth for detection, because
a detector evaluated against a model it was derived from proves nothing.

Run:
    python pipeline/fetch_malaysia_reference.py            # writes the artifact
    python pipeline/fetch_malaysia_reference.py --dry-run  # print, write nothing

Output: data/malaysia_reference_cases.json
Method note: docs/MALAYSIA-REFERENCE.md
"""

import argparse
import json
import os
import urllib.parse
import urllib.request

# --- Paths ------------------------------------------------------------------

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(REPOSITORY_ROOT, "data", "malaysia_reference_cases.json")

# --- The four sites ---------------------------------------------------------
# Named in docs/ARCHITECTURE-PLAN.md section 3.7 as the Malaysian baseline panel.
# Coordinates are the industrial/commercial areas those names refer to, chosen
# because the buyer is a C&I rooftop owner — not town centres.

SITES = [
    {"name": "Bukit Raja, Klang",  "state": "Selangor",        "lat": 3.0800, "lon": 101.4400},
    {"name": "Senai",              "state": "Johor",           "lat": 1.6018, "lon": 103.6689},
    {"name": "Nilai",              "state": "Negeri Sembilan", "lat": 2.8148, "lon": 101.7990},
    {"name": "Ipoh",               "state": "Perak",           "lat": 4.5975, "lon": 101.0901},
]

# --- Model parameters -------------------------------------------------------
# EVERY ONE OF THESE CHANGES THE ANSWER. They are set here, deliberately, and
# copied into the artifact so any figure can be traced back to what produced it.
# PVGIS defaults are NOT used silently anywhere.

PVGIS_ENDPOINT = "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc"

MODEL = {
    # Reference system size. Arbitrary but fixed: every output is normalised to
    # kWh/kWp/day, so the absolute size only sets the scale of the raw kWh.
    "peakpower": 100,

    # Roof-mounted, NOT free-standing. This is the parameter most likely to be
    # left at its default and it matters: a roof-mounted module sits against a
    # warm surface with restricted airflow, runs hotter, and therefore yields
    # less than the same module free-standing. Our buyer owns rooftops.
    "mountingplace": "building",

    # Tilt. Malaysian rooftop practice is a shallow tilt — enough for rain to
    # drain and self-clean, not so much that it catches wind load. At 1-5 deg N
    # a horizontal panel is already near the irradiance optimum, so 10 deg costs
    # almost nothing in yield and reflects what is actually installed.
    "angle": 10,

    # Azimuth, PVGIS convention: 0 = due south. Malaysia straddles just north of
    # the equator, so south-facing is correct for these latitudes.
    "aspect": 0,

    # Crystalline silicon — the dominant C&I rooftop technology.
    "pvtechchoice": "crystSi",

    # System loss (%). PVGIS's own default, covering cabling, inverter, soiling
    # and mismatch. NOTE: Malaysian soiling is measurably worse than the
    # temperate assumption behind this figure (docs/RESEARCH.md section 3
    # reports reductions up to 58.67% in extreme cases), so 14% is optimistic
    # for Malaysia. Left at the default deliberately, and flagged here, so the
    # number is comparable to other published PVGIS figures rather than being
    # quietly tuned by us.
    "loss": 14,

    "outputformat": "json",
}

# PVGIS-ERA5 covers 2005-2020. Not passed as a parameter — PVGIS uses its full
# available range for PVcalc — but recorded in the artifact because a yield
# figure means nothing without the period it averages.
RADIATION_PERIOD = {"database": "PVGIS-ERA5", "year_min": 2005, "year_max": 2020}


def fetch_site(site):
    """One PVcalc call. Returns the raw PVGIS response."""
    params = dict(MODEL, lat=site["lat"], lon=site["lon"])
    url = PVGIS_ENDPOINT + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def build_case(site):
    """Fetch one site and reduce it to the fields we are willing to stand behind."""
    raw = fetch_site(site)
    totals = raw["outputs"]["totals"]["fixed"]
    inputs = raw["inputs"]

    annual_kwh = totals["E_y"]
    specific_yield = annual_kwh / MODEL["peakpower"] / 365.0

    # Read the mounting back out of the RESPONSE rather than trusting what we
    # sent. PVGIS silently substitutes defaults for parameters it rejects, and a
    # request that was quietly downgraded to free-standing would otherwise look
    # identical to one that worked.
    mounting = inputs["mounting_system"]["fixed"]

    return {
        "name": site["name"],
        "state": site["state"],
        "latitude": inputs["location"]["latitude"],
        "longitude": inputs["location"]["longitude"],
        "elevation_m": inputs["location"]["elevation"],
        "annual_kwh": round(annual_kwh, 1),
        "annual_irradiation_kwh_per_m2": round(totals["H(i)_y"], 1),
        "specific_yield_kwh_per_kwp_day": round(specific_yield, 3),
        "confirmed_by_pvgis": {
            "mounting_type": mounting["type"],
            "slope_deg": mounting["slope"]["value"],
            "azimuth_deg": mounting["azimuth"]["value"],
            "technology": inputs["pv_module"]["technology"],
            "peak_power_kwp": inputs["pv_module"]["peak_power"],
            "system_loss_pct": inputs["pv_module"]["system_loss"],
            "radiation_database": inputs["meteo_data"]["radiation_db"],
            "year_min": inputs["meteo_data"]["year_min"],
            "year_max": inputs["meteo_data"]["year_max"],
        },
    }


def build_artifact(cases):
    yields = [case["specific_yield_kwh_per_kwp_day"] for case in cases]

    return {
        "data_status": "BUILT",
        "artifact": "Malaysian reference cases — modelled expected output",
        "what_this_is": (
            "Expected output for a reference C&I rooftop system at four real "
            "Malaysian coordinates, from real satellite weather (PVGIS-ERA5) "
            "through PVGIS's physical PV model."
        ),
        "what_this_is_not": (
            "NOT measured generation. No Malaysian site produced these numbers. "
            "No openly reusable per-site Malaysian inverter time series exists "
            "(docs/RESEARCH.md section 5). These figures must never be presented "
            "as measurements, and must never be used as ground truth for "
            "detection accuracy."
        ),
        "source": PVGIS_ENDPOINT,
        "radiation_period": RADIATION_PERIOD,
        "model_parameters_requested": MODEL,
        "summary": {
            "site_count": len(cases),
            "specific_yield_min_kwh_per_kwp_day": round(min(yields), 3),
            "specific_yield_max_kwh_per_kwp_day": round(max(yields), 3),
            "specific_yield_mean_kwh_per_kwp_day": round(sum(yields) / len(yields), 3),
        },
        "sites": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and print, but write nothing")
    args = parser.parse_args()

    cases = []
    for site in SITES:
        case = build_case(site)
        cases.append(case)
        print("{:<20} {:>8.1f} kWh/y   {:>5.2f} kWh/kWp/day   {} @ {} deg".format(
            case["name"],
            case["annual_kwh"],
            case["specific_yield_kwh_per_kwp_day"],
            case["confirmed_by_pvgis"]["mounting_type"],
            case["confirmed_by_pvgis"]["slope_deg"],
        ))

    artifact = build_artifact(cases)
    summary = artifact["summary"]
    print("\nrange {}-{} kWh/kWp/day, mean {}".format(
        summary["specific_yield_min_kwh_per_kwp_day"],
        summary["specific_yield_max_kwh_per_kwp_day"],
        summary["specific_yield_mean_kwh_per_kwp_day"],
    ))

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return

    with open(OUTPUT_PATH, "w") as handle:
        json.dump(artifact, handle, indent=2)
        handle.write("\n")
    print("\nwrote {}".format(os.path.relpath(OUTPUT_PATH, REPOSITORY_ROOT)))


if __name__ == "__main__":
    main()
