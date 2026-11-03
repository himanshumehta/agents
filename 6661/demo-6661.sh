#!/bin/bash
cd /private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/wt-6781
PY=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad/lk-main/.venv/bin/python
P=livekit-agents/livekit/agents/voice/remote_session.py
K="aclose_flushes or raises_instead_of_dropping"
run() { PYTHONPATH=$PWD/livekit-agents $PY -m pytest tests/test_remote_session.py -p no:cacheprovider -k "$K" -rA 2>&1 | grep -E "^(PASSED|FAILED)|^E +(TimeoutError|Failed)|passed|failed" | grep -v "^E .*CancelledError" | sed 's/^/  /'; }
echo "livekit/agents #6661: session host responses, tests from #6781"
echo
echo "$ git show 3568970323^:$P > $P   (remote_session.py before #6781)"
git show 3568970323^:$P > $P
echo "$ pytest tests/test_remote_session.py -k '$K'"
run
git checkout -q -- $P
echo
echo "$ git checkout 3568970323 -- $P   (after #6781, shipped in livekit-agents@1.6.10)"
echo "$ pytest tests/test_remote_session.py -k '$K'"
run
