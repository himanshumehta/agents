#!/bin/bash
S=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad
cd $S/lk-main
PY=.venv/bin/python
F=livekit-agents/livekit/agents/telemetry/loop_monitor.py
T=tests/test_loop_monitor.py
echo "livekit/agents #7599: EventLoopMonitor loses the stack sample when a tick races the watchdog"
echo "main $(git rev-parse --short=9 HEAD) (includes livekit-agents@1.8.10; loop_monitor.py same as origin/main)"
echo "repro = the issue's script; repro_fair = same, but a watchdog blocked on the monitor's lock may wait"
echo
printf "%-7s %-12s %-12s %-12s %s\n" code "repro A/B" "fair A/B" "lock held" "PR's own tests: main code -> PR code"
res() { local o; o=$(perl -e 'alarm 30; exec @ARGV' $PY -u $S/cmp-7599/$1 2>/dev/null | grep -oE '^case [AB]: (PASS|FAIL)' | awk '{print $3}' | paste -sd/ -); case "$o" in */*) echo "$o";; "") echo "hang";; *) echo "$o/hang";; esac; }
for n in main 7606 7618 8199; do
  if [ "$n" = main ]; then a=$(res repro.py); b=$(res repro_fair.py); printf "%-7s %-12s %-12s %-12s %s\n" main "$a" "$b" "-" "-"; continue; fi
  git show pr/$n:$T > $T
  tm=$($PY -m pytest $T -q -p no:cacheprovider 2>&1 | grep -oE '[0-9]+ failed|[0-9]+ passed' | paste -sd' ' -)
  git checkout -q -- $T
  git apply --exclude='tests/*' $S/cmp-7599/pr-$n.diff
  a=$(res repro.py); b=$(res repro_fair.py)
  lock=$(awk '/def _watchdog_check/,/def _sample_loop_thread/' $F | grep -B30 '_sample_loop_thread(lag)' | grep -q 'samples_in_flight' && echo "no" || echo "yes")
  git show pr/$n:$T > $T
  tp=$($PY -m pytest $T -q -p no:cacheprovider 2>&1 | grep -oE '[0-9]+ failed|[0-9]+ passed' | paste -sd' ' -)
  git checkout -q -- .
  printf "%-7s %-12s %-12s %-12s %s\n" "#$n" "$a" "$b" "$lock" "$tm -> $tp"
done
echo
echo "lock held = the watchdog keeps _lock while it walks the loop thread's stack"
echo "hang = the script waited on the paused tick, which holds the lock (stopped after 30 s)"
