#!/usr/bin/env bash
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_bC.sh.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v47test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for MODE in base aim45 aim50 mergeslow; do
  if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
  echo "########## ${MODE} :: AIP_yuno.dll ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "AIP_yuno.dll" 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
  done
done
echo "########## DONE ##########"
