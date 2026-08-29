"""Score the M3 detector against injected ground truth.

    .venv/bin/python pipeline/evaluate.py                 # 20 seeds
    .venv/bin/python pipeline/evaluate.py --seeds 1-50
    .venv/bin/python pipeline/evaluate.py --json out.json

THIS IS THE MARKING, NOT THE EXAM. It builds nothing and tunes nothing. It
injects faults of known type, size and start date into the REAL PVDAQ series,
runs the detector over the result, and compares what came back against the
label file. docs/ARCHITECTURE.md section 5 names the four figures it must
report: precision, recall, median days-to-detect, and the false-positive rate
on un-injected sites.

WHY MANY SEEDS. One run cannot inject more than half a cohort
(fault_injection.choose_events), which on this fleet caps at four sites. Four
points is not a recall curve, so every seed is run in memory and the results
are pooled. Nothing is written to data/processed — load_frames() returns fresh
frames each time and the injection happens on the copy, so the working tree is
never touched and no run can contaminate the next.

THE FIGURE THAT MATTERS MOST IS THE ONE THAT DECAYS. A recall curve that falls
to zero at low severity is evidence of an honest test; a flat 100% is evidence
of a rigged one. The per-rung table below is the point of this file, not the
headline percentage.

WHAT IS SUBTRACTED, AND WHY. One site in this fleet carries a genuine sustained
divergence in the real 2019 data, before anything is injected. Counting it as a
false positive would understate precision — the detector is right about it —
but silently excusing every unexpected flag would let real false positives hide
behind the excuse. So the baseline is measured once on the CLEAN series and
both numbers are reported: raw, and adjusted for sites already diverging.
"""

import argparse
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detect_cohort
import fault_injection
import generate_dispatch


REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The ladder fault_injection walks down, loss fraction per rung. Recall is
# reported against these so the detection floor is visible rather than averaged
# away. Mirrors SEVERITY_LADDER in fault_injection.py.
SEVERITY_RUNGS = [0.35, 0.25, 0.18, 0.12, 0.08, 0.05]


def frame_to_series(fleet_frame):
    """Fleet DataFrame -> the {site_id: [rows]} shape the detector consumes.

    Dates are remapped exactly as generate_dispatch does, so an evaluation run
    and a production run see the same calendar. Ground-truth dates are SOURCE
    dates and get the same treatment before any comparison.
    """
    series = {}
    ordered = fleet_frame.sort_values(["site_id", "date"])
    for record in ordered.to_dict("records"):
        series.setdefault(str(record["site_id"]), []).append({
            "date": generate_dispatch.remap_date(str(record["date"])),
            "actual_kwh": float(record["kwh"]),
            "performance_index": float(record["performance_index"]),
        })
    return series


def severity_rung(event):
    """Which rung of the ladder this event sits on.

    `severity_scale` is the rung normalised to the TOP rung, so the rung is
    recovered exactly as `SEVERITY_RUNGS[0] * severity_scale` for every fault
    type. Reading `magnitude_pct` instead would work for step_drop and
    string_loss but not for soiling_ramp, which records magnitude as null and
    carries its severity in `rate_per_day`. Matching soiling on its raw
    severity_scale filed a 0.51-scaled ramp under the 35% rung and made the
    strongest rung look like it had twice as many samples as it did.
    """
    scale = event.get("severity_scale")
    if scale is None:
        return None
    implied = SEVERITY_RUNGS[0] * scale
    return min(SEVERITY_RUNGS, key=lambda rung: abs(rung - implied))


def baseline_flagged(assumptions):
    """Sites the detector flags on the CLEAN series, before any injection.

    These are real divergences in the real data. They are reported separately
    so that neither mistake is made: counting them as false positives would
    punish the detector for being right, and excusing every surprise flag would
    let genuine false positives hide.
    """
    sites = generate_dispatch.load_fleet_sites()
    clean = generate_dispatch.load_real_daily_series()
    exclusions = generate_dispatch.build_exclusions(sites, clean, assumptions)
    members = generate_dispatch.build_cohort_membership(sites)
    results, _ = detect_cohort.detect_fleet(clean, members, assumptions, exclusions)
    return {site_id for site_id, result in results.items()
            if result["tier"] != detect_cohort.TIER_HEALTHY}, exclusions, members


def evaluate_seed(seed, count, assumptions, exclusions, members, baseline):
    """Inject one seeded ladder in memory, detect, and score against the labels."""
    frames = fault_injection.load_frames()
    frames["fleet"]["injected"] = False
    frames["inverter"]["injected"] = False

    events = fault_injection.choose_events(frames, assumptions, seed, count)
    for event in events:
        fault_injection.apply_event(frames, event)

    injected = frame_to_series(frames["fleet"])
    results, _ = detect_cohort.detect_fleet(injected, members, assumptions, exclusions)

    truth = {event["site_id"]: event for event in events}
    rows = []
    for site_id, result in sorted(results.items()):
        event = truth.get(site_id)
        flagged = result["tier"] != detect_cohort.TIER_HEALTHY

        days_to_detect = None
        detecting_before_injection = False
        if event and flagged:
            # Measured at the WATCH threshold, not the dispatch one: the
            # question is when the operator would first have seen this site at
            # all. Using persist_days would report no figure whatsoever for
            # every site that reached monitor but never dispatch, which is most
            # of the weaker half of the ladder.
            # Re-score this one site to find when the rule would FIRST have
            # fired, rather than whether it is firing now.
            cohort_id = next(cid for cid, group in members.items()
                             if any(m["site_id"] == site_id for m in group))
            analysed = [m["site_id"] for m in members[cohort_id]
                        if m["site_id"] not in exclusions]
            # LEAVE-ONE-OUT, matching the detector exactly. This previously
            # used the whole-cohort reference, which INCLUDES the subject — a
            # systematically weaker statistic than the one that produced the
            # `flagged` verdict being measured. It inflated days-to-detect and
            # dropped 8 of 17 true positives out of the figure entirely,
            # because they never trip under a reference they are inside of.
            reference = detect_cohort.peer_reference_by_date(
                injected, analysed, site_id, assumptions["min_cohort_size"])
            scored = detect_cohort.score_site(injected.get(site_id), reference)
            started = generate_dispatch.remap_date(event["injected_from"])

            # WAS IT ALREADY TRIPPING WHEN THE FAULT ARRIVED?
            #
            # Measured on the window immediately BEFORE the injection, not on
            # the whole history. A site that tripped once in February and
            # recovered was not tripping in May, and counting it as such would
            # discard real detections. What disqualifies a true positive is the
            # rule firing on the day the fault started — then the flag was
            # already up and the injection cannot be what raised it.
            before = [row for row in scored if row["date"] < started]
            detecting_before_injection = False
            if before:
                breaches_at_injection = detect_cohort.breaches_in_window(
                    before, detect_cohort.parse_date(before[-1]["date"]),
                    assumptions["persist_window_days"],
                    assumptions["z_score_threshold"])
                detecting_before_injection = (
                    len(breaches_at_injection) >= assumptions["watch_days"])

            # Days-to-detect is measured from the injection forward only.
            after = [row for row in scored if row["date"] >= started]
            first = detect_cohort.first_detection_date(
                after, assumptions["z_score_threshold"],
                assumptions["watch_days"], assumptions["persist_window_days"])
            if first and not detecting_before_injection:
                days_to_detect = (detect_cohort.parse_date(first)
                                  - detect_cohort.parse_date(started)).days

        rows.append({
            "seed": seed,
            "site_id": site_id,
            "injected": event is not None,
            "fault_type": event["fault_type"] if event else None,
            "rung": severity_rung(event) if event else None,
            "flagged": flagged,
            "tier": result["tier"],
            "score": result["score"],
            "days_to_detect": days_to_detect,
            "detecting_before_injection": detecting_before_injection,
            "pre_existing": site_id in baseline,
        })
    return rows


def summarise(rows):
    """Pool every seed into the four reported figures, plus the rung table."""
    true_positive = [r for r in rows if r["injected"] and r["flagged"]]
    false_negative = [r for r in rows if r["injected"] and not r["flagged"]]
    false_positive = [r for r in rows if not r["injected"] and r["flagged"]]
    true_negative = [r for r in rows if not r["injected"] and not r["flagged"]]

    # Un-injected sites that were ALREADY diverging in the clean series are
    # real detections, not errors. Reported both ways, never silently dropped.
    adjusted_fp = [r for r in false_positive if not r["pre_existing"]]

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None

    detected_days = [r["days_to_detect"] for r in true_positive
                     if r["days_to_detect"] is not None]

    # True positives that were ALREADY tripping before their injection started.
    # Credited to the detector by a naive recall count, but they are not
    # evidence it found the injected fault.
    already_tripping = [r for r in true_positive if r["detecting_before_injection"]]
    attributable = len(true_positive) - len(already_tripping)

    by_rung = {}
    for rung in SEVERITY_RUNGS:
        at_rung = [r for r in rows if r["injected"] and r["rung"] == rung]
        if not at_rung:
            continue
        caught = [r for r in at_rung if r["flagged"]]
        dispatched = [r for r in at_rung if r["tier"] == detect_cohort.TIER_DISPATCH]
        by_rung[rung] = {
            "injected": len(at_rung),
            "detected": len(caught),
            "dispatched": len(dispatched),
            "recall": ratio(len(caught), len(at_rung)),
        }

    return {
        "injections": len(true_positive) + len(false_negative),
        "un_injected_site_runs": len(false_positive) + len(true_negative),
        "true_positive": len(true_positive),
        "false_negative": len(false_negative),
        "false_positive_raw": len(false_positive),
        "false_positive_adjusted": len(adjusted_fp),
        "precision_raw": ratio(len(true_positive), len(true_positive) + len(false_positive)),
        "precision_adjusted": ratio(len(true_positive), len(true_positive) + len(adjusted_fp)),
        "recall": ratio(len(true_positive), len(true_positive) + len(false_negative)),
        "false_positive_rate_raw": ratio(
            len(false_positive), len(false_positive) + len(true_negative)),
        "false_positive_rate_adjusted": ratio(
            len(adjusted_fp), len(adjusted_fp) + len(true_negative)),
        "median_days_to_detect": statistics.median(detected_days) if detected_days else None,
        "days_to_detect_n": len(detected_days),
        "already_tripping_before_injection": len(already_tripping),
        "attributable_true_positive": attributable,
        "recall_attributable": ratio(attributable, len(true_positive) + len(false_negative)),
        "by_rung": by_rung,
    }


def parse_seeds(text):
    if "-" in text:
        first, last = text.split("-", 1)
        return list(range(int(first), int(last) + 1))
    return [int(part) for part in text.split(",") if part.strip()]


def percent(value):
    return "n/a" if value is None else "{:.0%}".format(value)


def report(summary, seeds, assumptions):
    print("M3 detector accuracy — {} seeded runs".format(len(seeds)))
    print("=" * 62)
    print("rule: z < {} on >= {} of the trailing {} days, cohort minimum {}".format(
        assumptions["z_score_threshold"], assumptions["persist_days"],
        assumptions["persist_window_days"], assumptions["min_cohort_size"]))
    print()
    print("  injections evaluated       {}".format(summary["injections"]))
    print("  un-injected site-runs      {}".format(summary["un_injected_site_runs"]))
    print()
    print("  recall                     {}  ({}/{})".format(
        percent(summary["recall"]), summary["true_positive"], summary["injections"]))
    print("  recall, attributable       {}  ({}/{})  <- excludes sites already tripping".format(
        percent(summary["recall_attributable"]),
        summary["attributable_true_positive"], summary["injections"]))
    print("  precision                  {}  raw   ·  {}  adjusted".format(
        percent(summary["precision_raw"]), percent(summary["precision_adjusted"])))
    print("  false-positive rate        {}  raw   ·  {}  adjusted".format(
        percent(summary["false_positive_rate_raw"]),
        percent(summary["false_positive_rate_adjusted"])))
    print("  median days to detect      {}  (n={}, at the watch threshold)".format(
        summary["median_days_to_detect"], summary["days_to_detect_n"]))
    print()
    print("  'adjusted' removes un-injected sites that were already diverging in the")
    print("  clean series. Those are real faults the detector found, not errors.")
    print()
    print("  {} of {} true positives were ALREADY tripping before their injection".format(
        summary["already_tripping_before_injection"], summary["true_positive"]))
    print("  began. A naive recall count credits those to the detector; the")
    print("  attributable figure above does not. Use the attributable one.")
    print()
    print("RECALL BY SEVERITY — the detection floor, which is the honest part")
    print("-" * 62)
    print("  {:>8}  {:>9}  {:>9}  {:>11}  {}".format(
        "severity", "injected", "detected", "dispatched", "recall"))
    for rung in SEVERITY_RUNGS:
        stats = summary["by_rung"].get(rung)
        if not stats:
            print("  {:>7.0%}  {:>9}  {:>9}  {:>11}  {}".format(rung, 0, "-", "-", "not sampled"))
            continue
        print("  {:>7.0%}  {:>9}  {:>9}  {:>11}  {}".format(
            rung, stats["injected"], stats["detected"], stats["dispatched"],
            percent(stats["recall"])))
    print()
    print("  'detected' is dispatch or monitor. 'dispatched' cleared persistence AND")
    print("  the money threshold. A curve that decays at the bottom is the point.")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", default="1-20",
                        help="seed range '1-20' or list '1,7,42' (default 1-20)")
    parser.add_argument("--count", type=int, default=4,
                        help="injection sites requested per seed (default 4)")
    parser.add_argument("--json", dest="json_path",
                        help="also write the full result to this path")
    args = parser.parse_args()

    seeds = parse_seeds(args.seeds)
    assumptions = generate_dispatch.load_assumptions()
    baseline, exclusions, members = baseline_flagged(assumptions)

    if baseline:
        print("baseline: {} site(s) already diverging in the clean series: {}".format(
            len(baseline), ", ".join(sorted(baseline))))
        print()

    rows = []
    for seed in seeds:
        rows.extend(evaluate_seed(seed, args.count, assumptions,
                                  exclusions, members, baseline))

    summary = summarise(rows)
    report(summary, seeds, assumptions)

    if args.json_path:
        with open(args.json_path, "w") as handle:
            json.dump({
                "data_status": "SIMULATED",
                "note": ("Real PVDAQ series with synthetic faults injected. The method "
                         "is real; the faults are not."),
                "seeds": seeds,
                "assumptions": {key: assumptions[key] for key in (
                    "z_score_threshold", "persist_days", "persist_window_days",
                    "watch_days", "min_cohort_size")},
                "baseline_flagged": sorted(baseline),
                "summary": summary,
                "rows": rows,
            }, handle, indent=2)
        print()
        print("wrote {}".format(os.path.relpath(args.json_path, REPOSITORY_ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
