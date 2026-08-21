"""Aggregate benchmarks/results/cuopt_tuning/*.json into the single ranked
TuningComparison (spec FR-010/SC-004).

Standalone: reads only the committed per-candidate JSON files plus S85's
already-published Gurobi result, no solver import required (mirrors
benchmarks/aggregate_solver_modes.py's "regenerable from committed results"
property).

Reports speedup_vs_gurobi as a first-class number, not just speedup_vs_baseline
-- the project's real preferred goal is beating Gurobi outright on whole-body/
microbiome models, not merely improving on cuOpt's own prior baseline.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import cuopt_tuning_candidates as C

RESULTS = HERE / "results" / "cuopt_tuning"
SUMMARY_JSON = RESULTS / "summary.json"
SUMMARY_CSV = RESULTS / "summary.csv"
S85_RESULT = HERE / "results" / "S85.json"

CSV_COLUMNS = ["candidate_id", "user_story", "cuopt_version", "solve_s",
               "speedup_vs_baseline", "speedup_vs_gurobi", "status", "residual_inf",
               "objective_agrees_with_gurobi", "verified_correct", "source_note"]


def _gurobi_solve_s():
    d = json.loads(S85_RESULT.read_text())
    return d["gurobi"]["solve_s_median"]


def load_results():
    """Read whichever results/cuopt_tuning/*.json files exist, in CANDIDATES
    registry order (US1, then US2 upgrade re-runs), then PREPROCESSING_CANDIDATES
    (US3), plus any LINKED_RESULTS entries -- never alphabetical by filename.
    Covers all three user stories (spec FR-010) -- a candidate missing here
    would be silently dropped from the one comparison meant to include
    everything attempted."""
    results = []
    seen_ids = set()

    for candidate in C.CANDIDATES:
        p = RESULTS / (candidate["id"] + ".json")
        if p.exists():
            results.append(json.loads(p.read_text()))
            seen_ids.add(candidate["id"])
        # version-upgrade re-runs: <id>_<version>.json, any version suffix present
        for sibling in sorted(RESULTS.glob(candidate["id"] + "_*.json")):
            results.append(json.loads(sibling.read_text()))

    for candidate in C.PREPROCESSING_CANDIDATES:
        p = RESULTS / (candidate["id"] + ".json")
        if p.exists():
            results.append(json.loads(p.read_text()))
            seen_ids.add(candidate["id"])

    gurobi_ref = json.loads(S85_RESULT.read_text()) if S85_RESULT.exists() else None
    for linked in C.LINKED_RESULTS:
        if not linked["result_path"].exists():
            continue
        d = json.loads(linked["result_path"].read_text())
        cfg = d.get(linked["result_key"])
        if cfg is None:
            continue
        obj_agrees = False
        verified_correct = False
        if gurobi_ref is not None:
            res_tol = gurobi_ref["res_tol"]
            gurobi_obj = gurobi_ref["gurobi"]["objective"]
            obj = cfg.get("objective")
            if obj is not None:
                denom = max(1.0, abs(obj), abs(gurobi_obj))
                obj_agrees = abs(obj - gurobi_obj) / denom <= gurobi_ref["obj_tol"]
            resid = cfg.get("residual_inf")
            verified_correct = bool(
                cfg.get("status") == "Optimal" and resid is not None
                and resid <= res_tol and obj_agrees)
        results.append({
            "id": linked["id"],
            "user_story": linked["user_story"],
            "cuopt_version": d.get("versions", {}).get("cuopt_version", "unknown"),
            "cuopt_kwargs": {"per_constraint_residual": 0},
            "phases": [],
            "status": cfg.get("status"),
            "solve_s": cfg.get("solve_s"),
            "iterations": cfg.get("iterations"),
            "objective": cfg.get("objective"),
            "residual_inf": cfg.get("residual_inf"),
            "objective_agrees_with_gurobi": obj_agrees,
            "verified_correct": verified_correct,
            "source_note": linked["source_note"],
            "error": None,
        })

    return results


def summarize(results, gurobi_solve_s):
    baseline = next((r for r in results if r["id"] == "baseline"), None)
    baseline_solve_s = (baseline["solve_s"]
                         if baseline and baseline.get("verified_correct") else None)

    rows = []
    for r in results:
        solve_s = r.get("solve_s")
        speedup_vs_baseline = (baseline_solve_s / solve_s
                                if baseline_solve_s and solve_s else None)
        speedup_vs_gurobi = (gurobi_solve_s / solve_s
                              if gurobi_solve_s and solve_s else None)
        rows.append({
            "candidate_id": r["id"],
            "user_story": r["user_story"],
            "cuopt_version": r.get("cuopt_version", "unknown"),
            "solve_s": solve_s,
            "speedup_vs_baseline": speedup_vs_baseline,
            "speedup_vs_gurobi": speedup_vs_gurobi,
            "status": r.get("status"),
            "residual_inf": r.get("residual_inf"),
            "objective_agrees_with_gurobi": bool(r.get("objective_agrees_with_gurobi")),
            "verified_correct": bool(r.get("verified_correct")),
            "source_note": r.get("source_note", ""),
        })

    # verified_correct first, then by speedup_vs_gurobi descending -- the ranking
    # itself must reflect the real goal (beat Gurobi), not just beat baseline.
    rows.sort(key=lambda row: (
        not row["verified_correct"],
        -(row["speedup_vs_gurobi"] or 0.0),
    ))

    eligible_vs_baseline = [row for row in rows
                             if row["verified_correct"] and row["candidate_id"] != "baseline"
                             and row["speedup_vs_baseline"] and row["speedup_vs_baseline"] > 1]
    best_vs_baseline = max(eligible_vs_baseline,
                            key=lambda row: row["speedup_vs_baseline"], default=None)

    beat_gurobi = [row for row in rows
                   if row["verified_correct"]
                   and row["speedup_vs_gurobi"] and row["speedup_vs_gurobi"] > 1]

    closest_to_gurobi = max(
        (row for row in rows if row["verified_correct"] and row["speedup_vs_gurobi"]),
        key=lambda row: row["speedup_vs_gurobi"], default=None)

    return {
        "rows": rows,
        "gurobi_solve_s": gurobi_solve_s,
        "baseline_solve_s": baseline_solve_s,
        "best_candidate_id": best_vs_baseline["candidate_id"] if best_vs_baseline else None,
        "best_candidate_speedup_vs_baseline": (
            best_vs_baseline["speedup_vs_baseline"] if best_vs_baseline else None),
        "candidates_beating_gurobi": [row["candidate_id"] for row in beat_gurobi],
        "closest_to_gurobi_id": closest_to_gurobi["candidate_id"] if closest_to_gurobi else None,
        "closest_to_gurobi_speedup": (
            closest_to_gurobi["speedup_vs_gurobi"] if closest_to_gurobi else None),
    }


def write_summary(summary):
    RESULTS.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in summary["rows"]:
            w.writerow(row)


def main():
    if not S85_RESULT.exists():
        print("no %s -- nothing to compare against" % S85_RESULT)
        return
    gurobi_solve_s = _gurobi_solve_s()
    results = load_results()
    summary = summarize(results, gurobi_solve_s)
    write_summary(summary)
    print("wrote %s and %s (%d candidate results)" % (SUMMARY_JSON, SUMMARY_CSV, len(results)))

    if summary["best_candidate_id"]:
        print("best vs. baseline: %s (%.2fx speedup vs. cuOpt's own prior default)" % (
            summary["best_candidate_id"], summary["best_candidate_speedup_vs_baseline"]))
    else:
        print("no candidate beat cuOpt's own baseline while remaining verified-correct")

    if summary["candidates_beating_gurobi"]:
        beaters = ", ".join(summary["candidates_beating_gurobi"])
        print("*** %d candidate(s) BEAT GUROBI: %s ***" % (
            len(summary["candidates_beating_gurobi"]), beaters))
    elif summary["closest_to_gurobi_id"]:
        print("no candidate beat Gurobi; closest was %s at %.3fx Gurobi's speed "
              "(i.e. %.1fx slower)" % (
                  summary["closest_to_gurobi_id"], summary["closest_to_gurobi_speedup"],
                  1.0 / summary["closest_to_gurobi_speedup"]))
    else:
        print("no verified-correct candidate to compare against Gurobi yet")


if __name__ == "__main__":
    main()
