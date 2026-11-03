#!/bin/bash
cd /Users/himanshumehta/sai/oss/livekit-agents-js
T=plugins/deepgram/src/deepgram_silence_frames.test.ts
F=plugins/deepgram/src/stt.ts
cp /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/evidence/deepgram_silence_frames.test.ts $T
run() { pnpm exec vitest run $T --reporter=verbose --silent=false 2>&1 | grep -E "pushed|✓|×|AssertionError|Tests " | sed -E 's#\|nodejs\| plugins/deepgram/src/deepgram_silence_frames.test.ts > ##; s/^ */  /'; }
echo "livekit/agents-js #2242: Deepgram STT, 1 s speech then 3 s silence into a local socket"
echo
echo "$ git show 5ebb38e8de^:$F > $F   (stt.ts before #2586)"
git show 5ebb38e8de^:$F > $F
echo "$ git grep -c AudioEnergyFilter -- $F"
echo "  $(grep -c AudioEnergyFilter $F)"
echo "$ pnpm exec vitest run $T"
run
git checkout -q -- $F
echo
echo "$ git checkout origin/main -- $F   (after #2586, shipped in agents-plugin-deepgram@1.9.1)"
echo "$ git grep -c AudioEnergyFilter -- $F"
echo "  $(grep -c AudioEnergyFilter $F)"
echo "$ pnpm exec vitest run $T"
run
rm -f $T
