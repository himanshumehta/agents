#!/bin/bash
cd /Users/himanshumehta/sai/oss/livekit-agents-js
echo "livekit/agents-js #1080: doInference with a closed IPC channel, real job process (agents/dist) on main $(git rev-parse --short HEAD)"
for m in await floating disconnect; do
  echo
  echo "$ node zz_repro_1080_run.mjs $m"
  node zz_repro_1080_run.mjs $m
done
