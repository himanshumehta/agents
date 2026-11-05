#!/bin/bash
S=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad
cd $S/lk-main
PY=$S/lk-main/.venv/bin/python
echo "livekit/agents #7006: what a finished job process leaves in PROMETHEUS_MULTIPROC_DIR"
echo "main $(git rev-parse --short=9 HEAD) (includes livekit-agents@1.8.10; supervised_proc.py same as origin/main)"
echo "real ProcJobExecutor child (spawn); its initialize fn records a Counter, a Histogram,"
echo "a Gauge (default 'all') and a Gauge(multiprocess_mode='livesum'); then aclose()"
echo
show() { (cd $S/cmp-7006 && PYTHONPATH=$S/cmp-7006 perl -e 'alarm 120; exec @ARGV' $PY run_7006.py "$1" 2>/dev/null | tail -1) | $PY -c "
import json,sys
d=json.load(sys.stdin)
print(f\"{d['label']:<7} child while running: {' '.join(d['child_files_while_running'])}\")
print(f\"{'':<7} child after aclose(): {' '.join(d['child_files_after_aclose']) or '(none)'}\")
print(f\"{'':<7} parent (worker) pid:  {' '.join(d['parent_files'])}\")"; }
show main
echo
git apply --exclude='tests/*' $S/cmp-7006/pr-7017.diff
show "#7017"
git checkout -q -- .
echo
echo "prometheus_client.multiprocess.mark_process_dead removes only gauge_live*_<pid>.db"
