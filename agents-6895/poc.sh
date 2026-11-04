#!/bin/bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python}
OUT=${OUT:-$HERE/poc-out}
mkdir -p "$OUT"
F=livekit-agents/livekit/agents/voice/amd/detector.py
trap 'git checkout -q -- "$F"' EXIT
echo "simulated SIP call: voicemail greeting as early media 0.5-6.4 s, beep 6.9 s, 200 OK (callStatus active) at 12.0 s"
echo
git show c2b2f5cbd6:$F > $F
$PY "$HERE/poc_early_media.py" default --label "main c2b2f5cbd (no option)" --out "$OUT/main.json" 2>/dev/null
git checkout -q -- $F
$PY "$HERE/poc_early_media.py" default --label "this PR, default (wait_until_answered=True)" --out "$OUT/pr-default.json" 2>/dev/null
$PY "$HERE/poc_early_media.py" opt-in --label "this PR, wait_until_answered=False" --out "$OUT/pr-optin.json" 2>/dev/null
