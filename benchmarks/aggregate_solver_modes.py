"""Aggregate benchmarks/results/s85_solver_modes/*.json into a VariantComparison.

Standalone: reads only the committed per-variant JSON files, no solver import
required (mirrors benchmarks/aggregate_sweep.py's "regenerable from committed
results" property).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import solver_mode_variants as V

RESULTS = HERE / "results" / "s85_solver_modes"
SUMMARY_JSON = RESULTS / "summary.json"
SUMMARY_CSV = RESULTS / "summary.csv"

CSV_COLUMNS = ["variant_id", "is_baseline", "outcome", "outcome_reason",
               "solve_s", "status", "solved_by", "iters", "residual_inf", "verified_correct",
               "speedup_vs_baseline", "is_best_candidate"]


def load_results():
    """Read whichever of the 4 variant result files currently exist, in registry order."""
    results = []
    for variant in V.SOLVER_MODE_VARIANTS:
        p = RESULTS / (variant["id"] + ".json")
        if p.exists():
            results.append(json.loads(p.read_text()))
    return results


def summarize(results):
    """Compute the VariantComparison (data-model.md) from a list of VariantResult dicts."""
    baseline = next((r for r in results if r["variant"]["is_baseline"]), None)
    baseline_solve_s = baseline["solve_s"] if baseline and baseline["outcome"] == "Completed" else None

    candidates = []
    for r in results:
        if r["variant"]["is_baseline"]:
            continue
        completed = r["outcome"] == "Completed"
        speedup = None
        if completed and baseline_solve_s and r["solve_s"]:
            speedup = baseline_solve_s / r["solve_s"]
        candidates.append({
            "id": r["variant"]["id"],
            "solve_s": r["solve_s"] if completed else None,
            "verified_correct": bool(r.get("verified_correct")) and completed,
            "speedup": speedup,
        })

    eligible = [c for c in candidates
                if c["verified_correct"] and c["speedup"] is not None and c["speedup"] > 1]
    best = min(eligible, key=lambda c: c["solve_s"]) if eligible else None

    any_did_not_complete = any(r["outcome"] != "Completed" for r in results)

    return {
        "baseline_solve_s": baseline_solve_s,
        "candidates": candidates,
        "best_candidate_id": best["id"] if best else None,
        "best_candidate_speedup": best["speedup"] if best else None,
        "any_did_not_complete": any_did_not_complete,
    }


def write_summary(results, summary):
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))

    candidates_by_id = {c["id"]: c for c in summary["candidates"]}
    rows = []
    for r in results:
        vid = r["variant"]["id"]
        cand = candidates_by_id.get(vid)
        rows.append({
            "variant_id": vid,
            "is_baseline": r["variant"]["is_baseline"],
            "outcome": r["outcome"],
            "outcome_reason": r.get("outcome_reason") or "",
            "solve_s": round(r["solve_s"], 4) if r["solve_s"] is not None else "",
            "status": r.get("status") or "",
            "solved_by": r.get("solved_by") or "",
            "iters": r.get("iters") if r.get("iters") is not None else "",
            "residual_inf": r.get("residual_inf") if r.get("residual_inf") is not None else "",
            "verified_correct": bool(r.get("verified_correct")),
            "speedup_vs_baseline": (round(cand["speedup"], 4)
                                     if cand and cand["speedup"] is not None else ""),
            "is_best_candidate": bool(cand and vid == summary["best_candidate_id"]),
        })

    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main():
    results = load_results()
    summary = summarize(results)
    write_summary(results, summary)
    print("wrote %s and %s  (%d/%d variants present)" % (
        SUMMARY_JSON, SUMMARY_CSV, len(results), len(V.SOLVER_MODE_VARIANTS)))
    if summary["best_candidate_id"]:
        print("best candidate: %s  (%.2fx speedup vs baseline)" % (
            summary["best_candidate_id"], summary["best_candidate_speedup"]))
    else:
        print("no candidate beat the baseline while remaining verified-correct")
    if summary["any_did_not_complete"]:
        print("NOTE: at least one variant did not complete -- see summary.csv for details")


if __name__ == "__main__":
    main()
