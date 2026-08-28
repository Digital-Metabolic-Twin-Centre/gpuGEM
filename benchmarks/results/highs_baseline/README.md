# HiGHS open-source CPU baseline

HiGHS 1.14.0 on all ten benchmark models, run 2026-08-26 as a licence-matched
comparison for gpuGEM: HiGHS and cuOpt are both free and open source, Gurobi is
commercial. The HiGHS-vs-cuOpt comparison is therefore the licence-matched one;
Gurobi is included as the commercial reference point.

## Result

All ten models reached `kOptimal`. HiGHS is correct at every scale but slow:
6-94x slower than cuOpt and a median 51x slower than Gurobi on models above
80k columns. Total solve time for the suite was 8.68 h versus 518 s for Gurobi
and 2637 s for cuOpt.

## Provenance

Every record in `highs_baseline.json` and each `logs/result_<model>.json`
sidecar carries `solve_s`, `wall_s`, `status`, `simplex_iterations`,
`objective`, `residual_inf`, `threads`, `time_limit_s`, `started_utc`, and the
1/5/15-minute machine load *before and after* the solve. The load fields are
recorded because the host is shared: any contention is visible in the record
rather than silently biasing a timing.

Loads during this run stayed between 1.0 and 1.8 on a 20-thread machine.

## Run conditions

Strictly serial, one solver at a time, 24 h cap per model, all threads
(`--threads 0`). An earlier sweep was discarded because it overlapped a Gurobi
calibration, a package build, and two GPU jobs on the same 20 logical cores;
see the archived audit. Harvey and Harvetta reproduced to 33.0 / 27.4 s across
both runs, and objectives reproduced to every printed digit, confirming that the
added instrumentation does not perturb the solve.

`gurobi_thread_parity.json` is the clean single- vs all-thread Gurobi
calibration that justifies the thread configuration reported in the manuscript
methods: Harvetta 9.232 s -> 3.368 s (2.7x), PMM1 465.927 s -> 40.004 s (11.6x).

## Reproducing

    python benchmarks/run_highs_baseline.py --repo . \
      --models e_coli_core iML1515 Harvey Harvetta S84 S23 S83 S85 S15 S9 \
      --time-limit 86400 --threads 0 \
      --out results/highs_baseline/highs_baseline.json \
      --log-dir results/highs_baseline/logs

Resume-safe: relaunching skips models already recorded in the output file.
`queue_after_highs.sh` chains the Gurobi calibration to start only after the
sweep exits, so the two never contend.

## Hardware

Intel Core i9-10900X @ 3.70 GHz (10C/20T), 125 GiB RAM, NVIDIA RTX A4500 20 GiB
(driver 560.35.05), Python 3.13.13. HiGHS 1.14.0, Gurobi 13.0.2, cuOpt 26.06.00.

