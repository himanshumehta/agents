#!/bin/bash
cd /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/lk-main
P=../evidence/agents-7900/halfopen_probe_20s.py
echo "livekit/agents #7900: reporter's half-open probe (WATCH lowered from 75s to 20s)"
echo
echo "$ git checkout -q --detach ae5e989f8^   (before #8123)"
git checkout -q --detach ae5e989f8^
echo "$ python -I halfopen_probe_20s.py openai elevenlabs inworld deepgram"
.venv/bin/python -I $P openai elevenlabs inworld deepgram 2>/dev/null | sed 's/^/  /'
echo
echo "$ git checkout -q --detach c2b2f5cbd   (origin/main, includes #8123, released in livekit-agents@1.8.10)"
git checkout -q --detach c2b2f5cbd
echo "$ python -I halfopen_probe_20s.py openai elevenlabs inworld deepgram"
.venv/bin/python -I $P openai elevenlabs inworld deepgram 2>/dev/null | sed 's/^/  /'
