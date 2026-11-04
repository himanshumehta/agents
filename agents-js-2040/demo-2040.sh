#!/bin/bash
E=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/evidence/agents-js-2040
T=agents/src/voice/avatar/zz_repro_2040.test.ts
run() { pnpm exec vitest run $T --silent=false --reporter=verbose --testTimeout=15000 2>&1 | grep -E "avatar left|✓|×|→|Tests " | sed -E 's#\|nodejs\| agents/src/voice/avatar/zz_repro_2040.test.ts > ##; s/^ */  /'; }
echo "livekit/agents-js #2040: avatar sink, avatar leaves, session.output.audio = new output, then say()"
echo
cd /Users/himanshumehta/sai/oss/livekit-agents-js
echo "$ git rev-parse --short HEAD   (main)"
echo "  $(git rev-parse --short HEAD)"
echo "$ cp zz_repro_2040.test.ts $T && pnpm exec vitest run $T"
cp $E/zz_repro_2040.test.ts $T
run
rm -f $T
echo
cd /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/wt-2040
echo "$ git apply datastream-finish-on-leave.patch   (DataStreamAudioOutput finishes pending playout when the avatar leaves)"
git apply $E/datastream-finish-on-leave.patch
echo "$ cp zz_repro_2040.test.ts $T && pnpm exec vitest run $T"
cp $E/zz_repro_2040.test.ts $T
run
rm -f $T
