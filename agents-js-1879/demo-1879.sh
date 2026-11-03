#!/bin/bash
cd /Users/himanshumehta/sai/oss/livekit-agents-js
show() { npm view "@livekit/agents@$1" dependencies --json 2>/dev/null | grep -E '"@opentelemetry/(api|core|resources|sdk-trace-base|sdk-trace-node|semantic-conventions)"' | sed 's/^ */  /'; }
echo "livekit/agents-js #1879: OpenTelemetry versions in @livekit/agents"
echo
echo "$ npm view @livekit/agents@1.5.5 dependencies   (last 1.5.x)"
show 1.5.5
echo
echo "$ npm view @livekit/agents@1.6.0 dependencies   (after #2105)"
show 1.6.0
echo
echo "$ git show @livekit/agents@1.6.0:agents/src/telemetry/traces.ts | grep registerSpanProcessor   (#2051)"
git show "@livekit/agents@1.6.0:agents/src/telemetry/traces.ts" | grep -n "registerSpanProcessor?:\|registerSpanProcessor(" | head -3 | sed 's/^ */  /'
