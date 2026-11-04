#!/bin/bash
cd /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/wt-2040
T=agents/src/voice/agent_activity_reply_instructions.test.ts
F=agents/src/voice/agent_activity.ts
run() { pnpm exec vitest run $T --reporter=verbose 2>&1 | grep -E "✓|×|→|Tests " | sed -E 's#\|nodejs\| agents/src/voice/agent_activity_reply_instructions.test.ts > per-reply instructions > ##; s/^ */  /'; }
echo "livekit/agents-js #2778: where per-reply instructions land in the LLM request"
echo
echo "$ git show origin/main:$F > $F   (main 39b2e651: concatenated onto the agent's instructions)"
git show origin/main:$F > $F
echo "$ pnpm exec vitest run $T"
run
echo
echo "$ git checkout ef87ab20 -- $F   (this branch: their own system message)"
git checkout -q ef87ab20 -- $F
echo "$ pnpm exec vitest run $T"
run
