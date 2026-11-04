#!/bin/bash
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python}
F=livekit-plugins/livekit-plugins-google/livekit/plugins/google/realtime/realtime_api.py
T=tests/test_plugin_google_realtime.py
trap 'git checkout -q -- "$F"' EXIT
echo "PoC: the real RealtimeSession._recv_task fed a fake Gemini stream: one audio chunk, then ONE message carrying turn_complete + tool_call(end_call)"
git show c2b2f5cbd6:$F > $F
$PY "$HERE/poc_combined_message.py" "main c2b2f5cbd" 2>/dev/null
git checkout -q -- $F
$PY "$HERE/poc_combined_message.py" "this PR" 2>/dev/null
echo
echo "$ pytest $T"
$PY -m pytest -q -p no:cacheprovider $T 2>&1 | tail -1 | sed 's/^/   /'
echo "$ mutation A: loop finalizes only on turn_complete (a lone tool_call never ends the turn)"
sed -i.bak 's/if ((sc := response.server_content) and sc.turn_complete) or response.tool_call:/if (sc := response.server_content) and sc.turn_complete:/' $F && rm -f $F.bak
$PY -m pytest -q -p no:cacheprovider $T -k lone_tool_call 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/^/   /'
git checkout -q -- $F
echo "$ mutation B: _handle_server_content finalizes on turn_complete again (as on main)"
$PY - <<'PY'
p="livekit-plugins/livekit-plugins-google/livekit/plugins/google/realtime/realtime_api.py"; s=open(p).read()
i=s.index("    def _handle_server_content("); j=s.index("\n    def ", i+10)
open(p,"w").write(s[:j]+"\n        if server_content.turn_complete:\n            self._mark_current_generation_done()\n"+s[j:])
PY
$PY -m pytest -q -p no:cacheprovider $T -k combined_turn_complete 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/^/   /'
