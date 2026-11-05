#!/bin/bash
S=/private/tmp/claude-502/-Users-himanshumehta-sai/d3afa51d-b147-43b4-babf-30e20009f776/scratchpad
cd $S/lk-main
export SILERO_ONNX=$S/evidence/silero_vad.onnx
PY=.venv/bin/python
echo "livekit/agents #7597: silero VAD deactivation_threshold after update_options"
echo "main = $(git rev-parse --short=9 HEAD) (silero/vad.py identical to origin/main $(git rev-parse --short=9 origin/main))"
echo
$PY $S/cmp-7597/compare_7597.py main > /tmp/cmp-main.json
for n in 7607 7611 7735 8155 8161; do
  while read -r f; do git show "pr/$n:$f" > "$f"; done < $S/cmp-7597/files-$n.txt
  $PY $S/cmp-7597/compare_7597.py "#$n" > /tmp/cmp-$n.json
  git checkout -q -- .
done
$PY $S/cmp-7597/table.py /tmp/cmp-main.json /tmp/cmp-7607.json /tmp/cmp-7611.json /tmp/cmp-7735.json /tmp/cmp-8155.json /tmp/cmp-8161.json
echo
echo "values: deactivation_threshold on the VAD (/ on the already-open stream)"
