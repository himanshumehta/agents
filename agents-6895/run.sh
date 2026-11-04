#!/bin/bash
set -e
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python}
F=livekit-agents/livekit/agents/voice/amd/detector.py
T=tests/test_amd_classifier.py
trap 'git checkout -q -- "$F"' EXIT
run(){ $PY -m pytest -q -p no:cacheprovider "$T" -k WaitUntilAnswered 2>&1 | grep -E "^FAILED|TypeError: AMD|passed|failed" | sort -u | sed 's/^/   /'; }
echo "$ main c2b2f5cbd detector.py + this PR's tests"; git show c2b2f5cbd6:$F > $F; run; git checkout -q -- $F
echo; echo "$ this PR"; run
echo; echo "$ this PR with 'and self._wait_until_answered' removed"
$PY - <<'PY'
import re
p="livekit-agents/livekit/agents/voice/amd/detector.py"; s=open(p).read()
m=re.search(r"\n(\s*)and self\._wait_until_answered\n", s); assert m
open(p,"w").write(s.replace(m.group(0), "\n", 1))
PY
run
