#!/bin/bash
set -e
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python}
REMOTE=${REMOTE:-origin}
T=tests/test_duplex_adapter.py
S=livekit-agents/livekit/agents/llm/duplex_adapter.py
git fetch -q "$REMOTE" pull/7862/head:refs/remotes/pr/7862
MB=$(git merge-base refs/remotes/pr/7862 HEAD)
trap 'git checkout -q HEAD -- "$T" "$S"' EXIT
echo "main: $(git log --oneline -1 HEAD | cut -c1-72)"
echo "#8301 (merged Nov 3) in this main: $(git merge-base --is-ancestor 8f62cabfa HEAD && echo yes || echo no)"
git diff "$MB" refs/remotes/pr/7862 -- "$T" | git apply
echo; echo "$ main + only the 3 new tests from #7862"
$PY -m pytest -q "$T" -p no:cacheprovider 2>&1 | grep -E "^FAILED|^E +AssertionError: assert not deque|passed|failed" | sort -u | sed 's/^/   /'
git diff "$MB" refs/remotes/pr/7862 -- "$S" | git apply -3 >/dev/null 2>&1
echo; echo "$ main + #7862's tests and fix (3-way merged, no conflicts)"
$PY -m pytest -q "$T" -p no:cacheprovider 2>&1 | tail -1 | sed 's/^/   /'
