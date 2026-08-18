"""Pull PVGIS reference cases for the four Malaysian sites named in the PRD.

WHY THIS EXISTS. Every generation number in SolaraX comes from American
inverters, because no openly reusable per-site Malaysian inverter time series
exists (docs/RESEARCH.md section 5, verified three ways). That is a fact about
the world, not a gap we can close by looking harder.

What we CAN compute honestly is the other half: what a system at real Malaysian
coordinates SHOULD produce, from a real meteorological reanalysis (ERA5) through
a real physical model. That is a reference case, not a measurement, and this script is careful
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
ASSUMPTIONS_PATH = os.path.join(REPOSITORY_ROOT, "config", "assumptions.json")

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
    # Radiation database, set EXPLICITLY. PVGIS defaults this when omitted, and a
    # default that changes underneath us would silently re-model everything.
    #
    # ERA5 is not a preference, it is the only option here: PVGIS-SARAH2 rejects
    # Malaysian coordinates outright ("Location out of the spatial coverage of
    # the radiation database selected"), because Meteosat's field of view does
    # not reach 101-104 deg E. Verified 18 Aug 2026.
    "raddatabase": "PVGIS-ERA5",

    # Terrain shadowing from the digital elevation model. Explicit because the
    # default has flipped between PVGIS versions.
    "usehorizon": 1,

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

# PVGIS-ERA5 covers 2005-2020. The period is not passed as a parameter — PVGIS
# uses the database's full range for PVcalc — but it is recorded in the artifact
# because a yield figure means nothing without the years it averages.
#
# NOTE ON PROVENANCE: ERA5 is ECMWF's meteorological REANALYSIS. It assimilates
# satellite and ground observations but is not a satellite product. Describe it
# as "ERA5 reanalysis", never as "satellite weather" — the distinction matters
# because sensor independence is the core technical claim and it has to be
# stated precisely. NASA POWER, used for the US pipeline, does derive its solar
# fields from satellite observation (CERES); the two are not the same thing.
RADIATION_PERIOD = {"database": "PVGIS-ERA5", "kind": "meteorological reanalysis (ECMWF ERA5)", "year_min": 2005, "year_max": 2020}


def fetch_site(site):
    """One PVcalc call. Returns the raw PVGIS response."""
    params = dict(MODEL, lat=site["lat"], lon=site["lon"])
    url = PVGIS_ENDPOINT + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


class ParameterMismatch(RuntimeError):
    """PVGIS modelled something other than what we asked for."""


def verify_response(site, inputs):
    """Fail loudly if PVGIS did not model what we requested.

    Recording the returned parameters is not enough. PVGIS substitutes defaults
    for parameters it rejects and still answers HTTP 200, so a request quietly
    downgraded to free-standing produces a perfectly valid-looking artifact with
    different physics behind it. That is the exact failure this script exists to
    prevent, so the check has to reject, not just report.
    """
    mounting = inputs["mounting_system"]["fixed"]
    module = inputs["pv_module"]
    meteo = inputs["meteo_data"]

    expected = [
        ("mounting type", mounting["type"], "building-integrated"),
        ("slope", mounting["slope"]["value"], MODEL["angle"]),
        ("azimuth", mounting["azimuth"]["value"], MODEL["aspect"]),
        ("technology", module["technology"], "c-Si"),
        ("peak power", module["peak_power"], float(MODEL["peakpower"])),
        ("system loss", module["system_loss"], float(MODEL["loss"])),
        ("radiation database", meteo["radiation_db"], MODEL["raddatabase"]),
    ]

    mismatches = [
        "{}: asked {!r}, got {!r}".format(label, want, got)
        for label, got, want in expected
        if got != want
    ]
    if mismatches:
        raise ParameterMismatch(
            "PVGIS modelled {} with parameters we did not request:\n  {}\n"
            "Refusing to write an artifact whose stated parameters are not the "
            "ones behind the numbers.".format(site["name"], "\n  ".join(mismatches))
        )

    # Not asserted, only recorded: PVGIS chooses the period from the database
    # rather than from our request, so pinning it would break on their next
    # update. It still belongs in the artifact — a yield figure is meaningless
    # without the years it averages.
    return {"year_min": meteo["year_min"], "year_max": meteo["year_max"]}


def build_case(site):
    """Fetch one site and reduce it to the fields we are willing to stand behind."""
    raw = fetch_site(site)
    inputs = raw["inputs"]
    period = verify_response(site, inputs)

    totals = raw["outputs"]["totals"]["fixed"]
    annual_kwh = totals["E_y"]
    specific_yield = annual_kwh / MODEL["peakpower"] / 365.0

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
            "year_min": period["year_min"],
            "year_max": period["year_max"],
        },
    }


def check_assumptions_in_sync(artifact):
    """Warn if config/assumptions.json has drifted from this artifact.

    The mean and range are copied into assumptions.json by hand, because that
    file is the single place commercial constants live and the pipeline copies
    it verbatim into dispatch.json. A legitimate PVGIS re-run would otherwise
    leave Screen 4 showing a number this artifact no longer supports.

    Returns a list of drift descriptions, empty when in sync.
    """
    with open(ASSUMPTIONS_PATH) as handle:
        assumptions = json.load(handle)

    summary = artifact["summary"]
    pairs = [
        ("malaysia_reference_yield_kwh_per_kwp_day",
         assumptions.get("malaysia_reference_yield_kwh_per_kwp_day"),
         summary["specific_yield_mean_kwh_per_kwp_day"]),
        ("malaysia_reference_yield_kwh_per_kwp_day_range.low",
         (assumptions.get("malaysia_reference_yield_kwh_per_kwp_day_range") or {}).get("low"),
         summary["specific_yield_min_kwh_per_kwp_day"]),
        ("malaysia_reference_yield_kwh_per_kwp_day_range.high",
         (assumptions.get("malaysia_reference_yield_kwh_per_kwp_day_range") or {}).get("high"),
         summary["specific_yield_max_kwh_per_kwp_day"]),
    ]

    return [
        "{}: assumptions.json has {!r}, this run produced {!r}".format(key, held, fresh)
        for key, held, fresh in pairs
        if held != fresh
    ]


def build_artifact(cases):
    yields = [case["specific_yield_kwh_per_kwp_day"] for case in cases]

    return {
        "data_status": "BUILT",
        "artifact": "Malaysian reference cases — modelled expected output",
        "what_this_is": (
            "Expected output for a reference C&I rooftop system at four real "
            "Malaysian coordinates, from the PVGIS-ERA5 meteorological "
            "reanalysis through PVGIS's physical PV model. ERA5 is a "
            "reanalysis product that assimilates satellite and ground "
            "observations - it is not itself a satellite dataset, and saying "
            "so would misdescribe the provenance."
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

    drift = check_assumptions_in_sync(artifact)
    if drift:
        print("\n!! config/assumptions.json is OUT OF SYNC with this run:")
        for line in drift:
            print("   " + line)
        print("   Update assumptions.json and its notes, then regenerate")
        print("   dispatch.json — Screen 4 reads those values, not this file.")
    else:
        print("config/assumptions.json is in sync")

    if args.dry_run:
        print("\n--dry-run: nothing written")
        return 1 if drift else 0

    with open(OUTPUT_PATH, "w") as handle:
        json.dump(artifact, handle, indent=2)
        handle.write("\n")
    print("\nwrote {}".format(os.path.relpath(OUTPUT_PATH, REPOSITORY_ROOT)))
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
