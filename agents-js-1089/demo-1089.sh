#!/bin/bash
cd /Users/himanshumehta/sai/oss/livekit-agents-js
T=agents/src/voice/zz_repro_1089.test.ts
cp /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/evidence/agents-js-1089/zz_repro_1089.test.ts $T
echo "livekit/agents-js #1089: greeting in onEnter, participant never subscribes to the agent track"
echo
echo "$ git rev-parse --short HEAD"
echo "  $(git rev-parse --short HEAD)"
echo "$ pnpm exec vitest run $T --reporter=verbose --silent=false"
pnpm exec vitest run $T --reporter=verbose --silent=false 2>&1 | grep -E "^session\.|✓|×|AssertionError|Tests " | sed -E 's#\|nodejs\| agents/src/voice/zz_repro_1089.test.ts > ##; s/^ */  /'
rm -f $T
