"""Aggregate benchmarks/results/s85_objectives/*.json into a SweepSummary.

Standalone: reads only the committed per-objective JSON files, no solver
import required (mirrors benchmarks/make_figure.py's "regenerable from
committed results" property).
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from benchmarks import s85_objectives as O

RESULTS = O.RESULTS_DIR
SUMMARY_JSON = RESULTS / "summary.json"
SUMMARY_CSV = RESULTS / "summary.csv"

_SKIP_NAMES = {"objectives.json", "summary.json"}

CSV_COLUMNS = ["objective_id", "reaction", "category", "is_baseline",
               "gurobi_solve_s", "gurobi_status", "gurobi_residual_inf",
               "cuopt_solve_s", "cuopt_status", "cuopt_residual_inf",
               "obj_rel_diff", "both_feasible",
               "runtime_ratio", "is_outlier", "outlier_direction"]


def load_results():
    results = []
    for p in sorted(RESULTS.glob("*.json")):
        if p.name in _SKIP_NAMES:
            continue
        results.append(json.loads(p.read_text()))
    return results


def summarize(results):
    """Compute the SweepSummary (data-model.md) from a list of per-objective
    result dicts (as produced by run_objective_sweep.solve_objective)."""
    gated = [r for r in results if r.get("both_feasible")]

    gurobi_times = [r["gurobi"]["solve_s_median"] for r in gated]
    cuopt_times = [r["cuopt"]["solve_s_median"] for r in gated]
    ratios = {r["objective"]["id"]: r["cuopt"]["solve_s_median"] / r["gurobi"]["solve_s_median"]
              for r in gated}

    def stats(xs):
        if not xs:
            return None, None, None, None
        return statistics.mean(xs), statistics.median(xs), min(xs), max(xs)

    g_mean, g_median, g_min, g_max = stats(gurobi_times)
    c_mean, c_median, c_min, c_max = stats(cuopt_times)

    ratio_median = statistics.median(ratios.values()) if ratios else None
    baseline = next((r for r in gated if r["objective"].get("is_baseline")), None)
    baseline_ratio = ratios.get(baseline["objective"]["id"]) if baseline else None

    outliers = []
    if ratio_median:
        for oid, ratio in ratios.items():
            if ratio < ratio_median / 2 or ratio > ratio_median * 2:
                outliers.append({
                    "id": oid, "ratio": ratio,
                    "direction": "faster" if ratio < ratio_median else "slower",
                })

    return {
        "n_objectives_total": len(results),
        "n_objectives_gated": len(gated),
        "gurobi_solve_s_mean": g_mean, "gurobi_solve_s_median": g_median,
        "gurobi_solve_s_min": g_min, "gurobi_solve_s_max": g_max,
        "cuopt_solve_s_mean": c_mean, "cuopt_solve_s_median": c_median,
        "cuopt_solve_s_min": c_min, "cuopt_solve_s_max": c_max,
        "runtime_ratio_median": ratio_median,
        "baseline_ratio": baseline_ratio,
        "outliers": sorted(outliers, key=lambda o: o["id"]),
    }


def write_summary(results, summary):
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2))

    outlier_by_id = {o["id"]: o for o in summary["outliers"]}
    rows = []
    for r in results:
        oid = r["objective"]["id"]
        gated = r.get("both_feasible")
        g_s = r["gurobi"]["solve_s_median"]
        c_s = r["cuopt"]["solve_s_median"]
        ratio = (c_s / g_s) if gated else None
        out = outlier_by_id.get(oid)
        rows.append({
            "objective_id": oid,
            "reaction": r["objective"]["reaction"],
            "category": r["objective"]["category"],
            "is_baseline": r["objective"]["is_baseline"],
            "gurobi_solve_s": round(g_s, 4),
            "gurobi_status": r["gurobi"]["repeats"][0]["status"],
            "gurobi_residual_inf": max(x["residual_inf"] for x in r["gurobi"]["repeats"]),
            "cuopt_solve_s": round(c_s, 4),
            "cuopt_status": r["cuopt"]["repeats"][0]["status"],
            "cuopt_residual_inf": max(x["residual_inf"] for x in r["cuopt"]["repeats"]),
            "obj_rel_diff": r["obj_rel_diff"],
            "both_feasible": gated,
            "runtime_ratio": round(ratio, 4) if ratio is not None else "",
            "is_outlier": out is not None,
            "outlier_direction": out["direction"] if out else "",
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
    print("wrote %s and %s  (%d/%d objectives gated)" % (
        SUMMARY_JSON, SUMMARY_CSV, summary["n_objectives_gated"], summary["n_objectives_total"]))
    if summary["baseline_ratio"] is not None and summary["runtime_ratio_median"] is not None:
        print("baseline ratio=%.2f  median ratio=%.2f  outliers=%s" % (
            summary["baseline_ratio"], summary["runtime_ratio_median"],
            [o["id"] for o in summary["outliers"]]))


if __name__ == "__main__":
    main()
