#!/bin/bash
S=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad
cd $S/lk-main
PY=.venv/bin/python
P=livekit-agents/livekit/agents/observability.py
echo "livekit/agents #7486: Tagger outcome invariant, main $(git rev-parse --short=9 HEAD) vs #7490 vs #7491"
echo "cells: outcome/outcome_reason tags"
echo
$PY $S/cmp-7486/compare_7486.py $P main > /tmp/t-main.json
for n in 7490 7491; do git show pr/$n:$P > /tmp/obs-$n.py; $PY $S/cmp-7486/compare_7486.py /tmp/obs-$n.py "#$n" > /tmp/t-$n.json; done
$PY $S/cmp-7486/table.py /tmp/t-main.json /tmp/t-7490.json /tmp/t-7491.json
echo
for n in 7490 7491; do
  t=$(git ls-tree -r --name-only pr/$n tests | grep -E 'test_tagger|test_observability' | head -1)
  git show pr/$n:$t > $t
  echo "\$ pytest $t   (#$n tests, main code)   $($PY -m pytest $t -q -p no:cacheprovider 2>&1 | tail -1)"
  git show pr/$n:$P > $P
  echo "\$ pytest $t   (#$n tests, #$n code)    $($PY -m pytest $t -q -p no:cacheprovider 2>&1 | tail -1)"
  git checkout -q -- $P; git checkout -q -- $t 2>/dev/null || rm -f $t
done
