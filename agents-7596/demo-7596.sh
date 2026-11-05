#!/bin/bash
S=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad
cd $S/lk-main
PY=$S/lk-main/.venv/bin/python
echo "livekit/agents #7596: AgentServer.run startup cleanup of PROMETHEUS_MULTIPROC_DIR"
echo "main $(git rev-parse --short=9 HEAD) (includes livekit-agents@1.8.10; worker.py same as origin/main)"
echo "dir before run(): this process's gauge file + a dead child's files + a live sibling's files"
echo
printf "%-7s %-6s %-44s %s\n" "code" "issue" "files left after run()" "/metrics (app, sibling, worker load)"
for n in main 7609 7615 8159; do
  [ "$n" != main ] && git apply --exclude='tests/*' $S/cmp-7596/pr-$n.diff
  r=$(cd $S/cmp-7596 && $PY repro.py 2>/dev/null | grep -oE '^(PASS|FAIL)')
  j=$(cd $S/cmp-7596 && $PY repro_mixed.py "$n" 2>/dev/null | tail -1)
  $PY - "$n" "$r" "$j" <<'PY'
import json, sys
n, r, j = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
own = sorted(a.replace("gauge_all", "g_all").replace("gauge_max", "g_max").replace("counter", "ctr") for a in j["after"])
s = j["series"]
yn = lambda x: "yes" if x else "no"
print(f"{('#'+n) if n!='main' else n:<7} {r:<6} {' '.join(own):<44} app={yn('app_warmup_done' in s)} sibling={yn('live_sibling_gauge' in s)} load={yn('lk_agents_worker_load' in s)}")
PY
  git checkout -q -- .
done
echo
echo "issue = the reporter's repro.py from #7596, unchanged"
