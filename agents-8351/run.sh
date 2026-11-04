#!/bin/bash
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
cd "$(git rev-parse --show-toplevel)"
PY=${PYTHON:-python}
F=livekit-agents/livekit/agents/voice/audio_recognition.py
cp "$SRC/test_zz_noise_segment.py" tests/test_zz_noise_segment.py
trap 'git checkout -q -- "$F"; rm -f tests/test_zz_noise_segment.py' EXIT
run(){ $PY -m pytest -q -s tests/test_zz_noise_segment.py -p no:cacheprovider 2>&1 | grep RESULT | sed 's/^/   /'; }
echo "scenario A: noise VAD segment (no final) + 'hello' segment (1 final), commit 0.6 s later"
echo "scenario B: 2 VAD segments, final 'hello' in hand, final 'again' lands 0.3 s after commit"
echo; echo "$ main 8f62cabfa"; git show 8f62cabfa:$F > $F; run; git checkout -q -- $F
echo; echo "$ PR #8351 185325e5d"; run
echo; echo "$ PR #8351 with the finals>=segments check removed"
$PY -c "
p='$F';s=open(p).read();o='                and not self._speaking\n                and self._finals_in_turn >= self._vad_segments_ended_in_turn\n';assert o in s;open(p,'w').write(s.replace(o,'                and not self._speaking\n'))"
run
