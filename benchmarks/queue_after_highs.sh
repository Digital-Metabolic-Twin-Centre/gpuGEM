#!/bin/bash
# Serial benchmark queue: wait for the HiGHS sweep to exit, THEN run the Gurobi
# thread-parity calibration. Never concurrently -- overlapping these two is the
# exact error this queue exists to prevent.
#
# Usage: queue_after_highs.sh <pid-of-highs-sweep>
set -u

PID="$1"
LOG=~/highs_bench/final/queue.log
PY=~/miniconda3/bin/python

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >> "$LOG"; }

log "queue started; waiting on HiGHS sweep pid $PID"

# Wait for the sweep to exit. kill -0 tests existence without signalling.
while kill -0 "$PID" 2>/dev/null; do
    sleep 60
done
log "HiGHS sweep pid $PID has exited"

# Guard: never start while another benchmark process is somehow alive.
if pgrep -f run_highs_baseline.py > /dev/null 2>&1; then
    log "ABORT: another run_highs_baseline.py is running; refusing to add load"
    exit 1
fi

# Let the machine settle so the calibration is not measured against a decaying
# load average from the job that just finished.
log "settling for 120 s before calibration"
sleep 120
log "load at calibration start: $(cat /proc/loadavg)"

cd ~/highs_bench || exit 1
log "running Gurobi thread-parity calibration"
$PY gurobi_threads.py >> ~/highs_bench/final/gurobi_threads_clean.log 2>&1
rc=$?
log "calibration finished rc=$rc"
log "load at calibration end: $(cat /proc/loadavg)"

# Preserve the calibration output under the final/ tree with the sweep results.
if [ -f ~/highs_bench/gurobi_threads.json ]; then
    cp ~/highs_bench/gurobi_threads.json ~/highs_bench/final/gurobi_threads_clean.json
    log "wrote final/gurobi_threads_clean.json"
fi

touch ~/highs_bench/final/QUEUE_COMPLETE
log "queue complete"

