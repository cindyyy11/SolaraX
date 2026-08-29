"""Score M3 against the injected ground truth. Produces the accuracy figure.

WHY THIS EXISTS. PRD section 11 makes "a stated accuracy figure from a real test"
the accountability for M3, and `hinfo/SUBMISSION-CHECKLIST.md`'s red-team item 2
asks for a number from a real test run rather than an estimate. This is that run.

fault_injection.py manufactures the answer key: real PVDAQ measurements with a
fault of known type, magnitude and date multiplied in, and a label file
recording exactly what was done. This marks the paper.

THE OBVIOUS ATTACK, AND THE ANSWER. "You found faults you invented." Two answers.

First, the severity ladder. The same detector is run against faults of
descending magnitude until it stops seeing them, and where that happens is
published. A recall curve that decays to zero at low severity is evidence of an
honest test; a flat 100 % would be evidence of a rigged one.

Second, the controls. Most sites in every run have NO fault injected, and they
are scored too. Recall without precision is free - a detector that flags
everything scores 100 % recall - so the false-positive count on the untouched
sites is reported next to it and carries equal weight.

WHY POOL SEEDS. One run can only inject four events: the protocol never touches
more than half a cohort and always leaves controls, which on an 11-site fleet
caps out at four. Four points do not make a recall curve. Each seed is an
independent draw of sites, fault types, start dates and ladder positions, so
pooling several gives a curve with something behind each point.

Run:
    python pipeline/score_detector.py                    # default 6 seeds
    python pipeline/score_detector.py --seeds 42 43 44
    python pipeline/score_detector.py --keep             # leave artifacts on disk

Writes: pipeline/output/detector_accuracy.json
        (and, transiently, the gitignored injected parquet files)
"""

import argparse
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_DIR = os.path.join(REPOSITORY_ROOT, "pipeline")
sys.path.insert(0, PIPELINE_DIR)

from baseline import (  # noqa: E402
    build_expected,
    load_actual_daily,
    load_fleet_sites,
    load_irradiance,
    load_model_params,
    plausibility_excluded_site_ids,
)
from peer_benchmark import run_detector  # noqa: E402

PROCESSED_DIR = os.path.join(REPOSITORY_ROOT, "data", "processed")
FLEET_INJECTED_PATH = os.path.join(PROCESSED_DIR, "fleet_daily_injected.parquet")
GROUND_TRUTH_PATH = os.path.join(REPOSITORY_ROOT, "pipeline", "output", "ground_truth.json")
ACCURACY_PATH = os.path.join(REPOSITORY_ROOT, "pipeline", "output", "detector_accuracy.json")

DEFAULT_SEEDS = (42, 43, 44, 45, 46, 47)

# Severity buckets for the recall curve. A soiling ramp has no single magnitude
# - its loss depends on how long it has been running - so it is reported on its
# own row rather than forced onto a scale it does not belong on.
SEVERITY_BUCKETS = (
    (">= 30 %", 0.30, 1.01),
    ("20 - 30 %", 0.20, 0.30),
    ("10 - 20 %", 0.10, 0.20),
    ("< 10 %", 0.0, 0.10),
)


def run_injection(seed):
    """Shell out to the harness. It owns the answer key; this only reads it."""
    result = subprocess.run(
        [sys.executable, os.path.join(PIPELINE_DIR, "fault_injection.py"),
         "--ladder", "--seed", str(seed)],
        capture_output=True, text=True, cwd=REPOSITORY_ROOT,
    )
    if result.returncode != 0:
        raise SystemExit("fault_injection.py failed for seed {}:\n{}".format(
            seed, result.stderr))

    with open(GROUND_TRUTH_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def load_injected_actual():
    frame = pd.read_parquet(FLEET_INJECTED_PATH)
    return frame[["site_id", "date", "kwh"]].rename(columns={"kwh": "actual_kwh"})


def event_severity(event):
    """One comparable magnitude per event, or None for a ramp."""
    if event["fault_type"] == "soiling_ramp":
        return None
    magnitude = event.get("magnitude_pct")
    return float(magnitude) if magnitude is not None else None


def score_one_run(sites, irradiance, injected_actual, params, excluded, events):
    """Run the detector on one injected fleet and mark it against the labels."""
    expected, baseline_diagnostics = build_expected(
        sites, irradiance, injected_actual, params, excluded_site_ids=excluded)
    results, _frame, _diagnostics = run_detector(
        sites, expected, params, excluded)

    truth_by_site = {event["site_id"]: event for event in events}
    rows = []

    for site_id, result in results.items():
        event = truth_by_site.get(site_id)
        flagged = result["flagged"]

        latency_days = None
        if event and flagged and result["divergence_start_date"]:
            injected_from = pd.Timestamp(event["injected_from"])
            detected_at = pd.Timestamp(result["divergence_start_date"])
            latency_days = int((detected_at - injected_from).days)

        rows.append({
            "site_id": site_id,
            "has_fault": event is not None,
            "fault_type": event["fault_type"] if event else "none",
            "severity": event_severity(event) if event else None,
            "flagged": flagged,
            "score": result["score"],
            "window_deviation": result["window_deviation"],
            "persistence": result["persistence"],
            "shape": result["shape"],
            "detected_start": result["divergence_start_date"],
            "injected_from": event["injected_from"] if event else None,
            "latency_days": latency_days,
        })

    return rows, baseline_diagnostics["derate"]


def apply_rule(rows, threshold, min_persistence, min_material_deviation):
    """Re-decide the flag under a candidate rule, without re-running the detector."""
    return [
        dict(row, flagged=(row["score"] <= threshold
                           and row["persistence"] >= min_persistence
                           and row["window_deviation"] <= -min_material_deviation))
        for row in rows
    ]


def sweep_thresholds(rows, min_persistence, min_material_deviation, candidates):
    """Precision, recall and F1 across candidate score thresholds.

    WHY THIS EXISTS. Iglewicz and Hoaglin's -3.5 is a generic cutoff for a
    generic outlier problem. It is not a claim about THIS fleet, whose healthy
    sites genuinely sit up to 9 % apart in peer-relative terms because they have
    different roof geometries and the fleet baseline assumes one. Taking the
    textbook constant on faith produced a detector that missed a 35 % step drop,
    which is not conservatism, it is a mis-specified test.

    So the operating point is measured instead of assumed. It is chosen on
    CALIBRATION seeds and reported on a DISJOINT set of TEST seeds - picking the
    threshold and quoting the accuracy on the same runs would be reporting how
    well the rule fits the data it was fitted to.
    """
    table = []
    for threshold in candidates:
        summary = confusion(apply_rule(
            rows, threshold, min_persistence, min_material_deviation))
        table.append({"threshold": threshold, **summary})
    return table


def confusion(rows):
    true_positive = sum(1 for row in rows if row["has_fault"] and row["flagged"])
    false_negative = sum(1 for row in rows if row["has_fault"] and not row["flagged"])
    false_positive = sum(1 for row in rows if not row["has_fault"] and row["flagged"])
    true_negative = sum(1 for row in rows if not row["has_fault"] and not row["flagged"])

    precision = (true_positive / (true_positive + false_positive)
                 if (true_positive + false_positive) else None)
    recall = (true_positive / (true_positive + false_negative)
              if (true_positive + false_negative) else None)
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else None)

    return {
        "true_positive": true_positive,
        "false_negative": false_negative,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "false_positive_rate": round(
            false_positive / (false_positive + true_negative), 4)
        if (false_positive + true_negative) else None,
    }


def recall_by_severity(rows):
    """The ladder. This is the curve that has to decay for the test to be honest."""
    curve = []
    for label, low, high in SEVERITY_BUCKETS:
        bucket = [row for row in rows
                  if row["has_fault"] and row["severity"] is not None
                  and low <= row["severity"] < high]
        if not bucket:
            continue
        detected = sum(1 for row in bucket if row["flagged"])
        curve.append({
            "severity": label,
            "events": len(bucket),
            "detected": detected,
            "recall": round(detected / len(bucket), 4),
        })

    ramps = [row for row in rows if row["fault_type"] == "soiling_ramp"]
    if ramps:
        detected = sum(1 for row in ramps if row["flagged"])
        curve.append({
            "severity": "soiling ramp (no fixed magnitude)",
            "events": len(ramps),
            "detected": detected,
            "recall": round(detected / len(ramps), 4),
        })
    return curve


def shape_confusion(rows):
    """Did the cause hypothesis get the shape right on the faults it caught?

    Reported separately from recall and never mixed into it: calling a step a
    ramp wastes a technician's first ten minutes, while missing the fault
    entirely wastes a month of generation. They are not the same error.
    """
    expected_shape = {
        "step_drop": "step",
        "string_loss": "step",
        "soiling_ramp": "progressive",
    }
    caught = [row for row in rows if row["has_fault"] and row["flagged"] and row["shape"]]
    if not caught:
        return {"scored": 0}

    correct = sum(1 for row in caught
                  if row["shape"] == expected_shape.get(row["fault_type"]))
    return {
        "scored": len(caught),
        "correct": correct,
        "accuracy": round(correct / len(caught), 4),
    }


def latency_summary(rows):
    values = [row["latency_days"] for row in rows if row["latency_days"] is not None]
    if not values:
        return {"detected_events": 0}
    return {
        "detected_events": len(values),
        "median_days_to_detect": float(np.median(values)),
        "mean_days_to_detect": round(float(np.mean(values)), 1),
        "min_days_to_detect": int(min(values)),
        "max_days_to_detect": int(max(values)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS),
                        help="seeds to pool (default: {})".format(
                            " ".join(str(seed) for seed in DEFAULT_SEEDS)))
    parser.add_argument("--keep", action="store_true",
                        help="leave the injected artifacts on disk afterwards")
    parser.add_argument("--calibrate", type=int, nargs="+", metavar="SEED",
                        help="calibration seeds: sweep the score threshold on "
                             "these and report the table, then evaluate the "
                             "configured threshold on --seeds as held-out data")
    arguments = parser.parse_args()

    irradiance = load_irradiance()
    if irradiance is None:
        raise SystemExit("no irradiance cache. Run: python pipeline/fetch_irradiance.py")

    params = load_model_params()
    sites = load_fleet_sites()

    # EXCLUSIONS COME FROM THE CLEAN FEED, ALWAYS. Same reasoning as
    # generate_dispatch: judged on injected data, a severe injection drops the
    # site below the plausibility floor and deletes the very test case it was
    # meant to create - silently, and with the label still pointing at it.
    excluded = plausibility_excluded_site_ids()
    clean_actual = load_actual_daily()
    if clean_actual is None:
        raise SystemExit("no fleet_daily.parquet. Run: python pipeline/fetch_pvdaq.py")

    _clean_expected, clean_diagnostics = build_expected(
        sites, irradiance, clean_actual, params, excluded_site_ids=excluded)
    clean_derate = clean_diagnostics["derate"]

    def score_seeds(seeds, label):
        rows = []
        derates = []
        print("{} over {} seeded runs".format(label, len(seeds)))
        for seed in seeds:
            events = run_injection(seed)["events"]
            injected_actual = load_injected_actual()
            seed_rows, derate = score_one_run(
                sites, irradiance, injected_actual, params, excluded, events)
            rows.extend(seed_rows)
            derates.append(derate)

            detected = sum(1 for row in seed_rows if row["has_fault"] and row["flagged"])
            false_positives = sum(
                1 for row in seed_rows if not row["has_fault"] and row["flagged"])
            print("  seed {:<4} {} events, {} detected, {} false positive(s), "
                  "derate {}".format(seed, len(events), detected, false_positives, derate))
        return rows, derates

    calibration = None
    if arguments.calibrate:
        overlap = set(arguments.calibrate) & set(arguments.seeds)
        if overlap:
            raise SystemExit(
                "calibration and test seeds overlap on {} - the whole point of "
                "splitting them is that they must not".format(sorted(overlap)))

        calibration_rows, _ = score_seeds(arguments.calibrate, "calibrating M3")
        # Swept past zero deliberately. If F1 kept climbing all the way to the
        # edge of the range, the score gate would be doing nothing and the rule
        # would really be persistence-plus-materiality wearing a z-score as
        # decoration - worth knowing rather than hiding behind a range that
        # stops just before it shows.
        candidates = [round(-4.0 + 0.25 * step, 2) for step in range(25)]
        table = sweep_thresholds(
            calibration_rows, params["detector"]["min_persistence"],
            params["detector"]["min_material_deviation"], candidates)

        print()
        print("threshold sweep on CALIBRATION seeds {} "
              "(persistence >= {:.0%} and materiality >= {:.0%} held fixed)".format(
                  arguments.calibrate, params["detector"]["min_persistence"],
                  params["detector"]["min_material_deviation"]))
        print("{:>10} {:>4} {:>4} {:>4} {:>4} {:>10} {:>8} {:>7}".format(
            "threshold", "TP", "FN", "FP", "TN", "precision", "recall", "F1"))
        for row in table:
            print("{:>10.2f} {:>4} {:>4} {:>4} {:>4} {:>10} {:>8} {:>7}".format(
                row["threshold"], row["true_positive"], row["false_negative"],
                row["false_positive"], row["true_negative"],
                "{:.1%}".format(row["precision"]) if row["precision"] is not None else "-",
                "{:.1%}".format(row["recall"]) if row["recall"] is not None else "-",
                "{:.3f}".format(row["f1"]) if row["f1"] is not None else "-"))

        # On a tie, take the STRICTER (more negative) threshold. Two operating
        # points with the same F1 are not equally good in the field: the
        # stricter one sends fewer technicians to healthy roofs, and a false
        # dispatch is the error this product exists to prevent.
        best = max((row for row in table if row["f1"] is not None),
                   key=lambda row: (row["f1"], -row["threshold"]), default=None)
        if best:
            print()
            print("best F1 on calibration: threshold {:.2f} (F1 {:.3f})".format(
                best["threshold"], best["f1"]))
            print("configured threshold   : {:.2f}".format(
                params["detector"]["modified_z_threshold"]))
        calibration = {"seeds": arguments.calibrate, "sweep": table,
                       "best_f1": best}
        print()

    all_rows, derates = score_seeds(
        arguments.seeds,
        "scoring M3 on HELD-OUT seeds" if arguments.calibrate else "scoring M3")

    summary = confusion(all_rows)
    curve = recall_by_severity(all_rows)
    shapes = shape_confusion(all_rows)
    latency = latency_summary(all_rows)

    print()
    print("M3 detector accuracy - pooled over {} runs".format(len(arguments.seeds)))
    print("=" * 68)
    print("site-runs scored      : {}".format(len(all_rows)))
    print("  with injected fault : {}".format(
        sum(1 for row in all_rows if row["has_fault"])))
    print("  controls (no fault) : {}".format(
        sum(1 for row in all_rows if not row["has_fault"])))
    print()
    print("  true positives      : {}".format(summary["true_positive"]))
    print("  false negatives     : {}".format(summary["false_negative"]))
    print("  false positives     : {}".format(summary["false_positive"]))
    print("  true negatives      : {}".format(summary["true_negative"]))
    print()
    print("  precision           : {}".format(
        "{:.1%}".format(summary["precision"]) if summary["precision"] is not None else "n/a"))
    print("  recall              : {}".format(
        "{:.1%}".format(summary["recall"]) if summary["recall"] is not None else "n/a"))
    print("  F1                  : {}".format(
        "{:.3f}".format(summary["f1"]) if summary["f1"] is not None else "n/a"))
    print("  false-positive rate : {}".format(
        "{:.1%}".format(summary["false_positive_rate"])
        if summary["false_positive_rate"] is not None else "n/a"))

    print()
    print("recall by severity - the ladder")
    print("-" * 68)
    for point in curve:
        print("  {:<34} {:>2}/{:<2} events   recall {:>6.1%}".format(
            point["severity"], point["detected"], point["events"], point["recall"]))

    if shapes.get("scored"):
        print()
        print("cause-shape agreement : {}/{} ({:.1%}) of detected faults".format(
            shapes["correct"], shapes["scored"], shapes["accuracy"]))

    if latency.get("detected_events"):
        print("days to detect        : median {:.0f}, mean {:.1f}, range {} to {}".format(
            latency["median_days_to_detect"], latency["mean_days_to_detect"],
            latency["min_days_to_detect"], latency["max_days_to_detect"]))

    print()
    print("derate stability      : clean fleet {}, injected runs {} to {}".format(
        clean_derate, min(derates), max(derates)))
    print("  (the fleet-median calibration is meant to be unmoved by a minority")
    print("   of degraded site-days; this is the check that it is)")

    payload = {
        "data_status": "SIMULATED",
        "note": ("Real PVDAQ measurements with synthetic faults of known type, "
                 "magnitude and date injected by pipeline/fault_injection.py. "
                 "Real method, synthetic labels - see CLAUDE.md on SIMULATED."),
        "seeds": arguments.seeds,
        "runs": len(arguments.seeds),
        "detector_method": ("Robust peer-deviation z-score (Iglewicz-Hoaglin "
                            "modified z-score, median/MAD)"),
        "threshold": params["detector"]["modified_z_threshold"],
        "min_persistence": params["detector"]["min_persistence"],
        "evaluation_window_days": params["detector"]["evaluation_window_days"],
        "confusion": summary,
        "recall_by_severity": curve,
        "cause_shape_agreement": shapes,
        "detection_latency_days": latency,
        "derate_clean": clean_derate,
        "derate_injected_range": [min(derates), max(derates)],
        "threshold_calibration": calibration,
        "held_out": bool(calibration),
    }
    os.makedirs(os.path.dirname(ACCURACY_PATH), exist_ok=True)
    with open(ACCURACY_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    print()
    print("wrote {}".format(os.path.relpath(ACCURACY_PATH, REPOSITORY_ROOT)))

    if not arguments.keep:
        subprocess.run(
            [sys.executable, os.path.join(PIPELINE_DIR, "fault_injection.py"), "--clean"],
            capture_output=True, text=True, cwd=REPOSITORY_ROOT)
        print("cleaned the injected artifacts (--keep to retain them)")


if __name__ == "__main__":
    main()
