#!/bin/bash
cd /Users/himanshumehta/sai/oss/livekit-agents-js
T=plugins/inworld/src/stt_recovery.test.ts
F=plugins/inworld/src/stt.ts
run() { pnpm exec vitest run $T -t "delivers every new frame" --reporter=verbose 2>&1 | grep -E "✓|×|→|Tests " | grep -v "↓" | sed -E 's#\|nodejs\| plugins/inworld/src/stt_recovery.test.ts > ##; s/^ */  /'; }
echo "livekit/agents-js #2608: Inworld STT, reconnect then push frames 1..6"
echo
echo "$ git show d7bb08a758^:$F > $F   (stt.ts before #2619)"
git show d7bb08a758^:$F > $F
echo "$ pnpm exec vitest run $T -t 'delivers every new frame'"
run
git checkout -q -- $F
echo
echo "$ git checkout origin/main -- $F   (after #2619, shipped in agents-plugin-inworld@1.9.2)"
echo "$ pnpm exec vitest run $T -t 'delivers every new frame'"
run
