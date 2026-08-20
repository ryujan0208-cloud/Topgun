#!/usr/bin/env bash
# 중단 구간 이어받기 — yuno divebait 전체 + fastthr 남은 8판, jung divebait 남은 1판
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_c_resume.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v48test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
export TOPGUN_ABLATE=fastthr
echo "########## fastthr :: AIP_yuno.dll ##########"
for k in $(seq 7 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_yuno.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error"
done
export TOPGUN_ABLATE=divebait
echo "########## divebait :: AIP_yuno.dll ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_yuno.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error"
done
echo "########## divebait :: AIP_jung.dll ##########"
for k in $(seq 14 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jung.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error"
done
echo "########## DONE ##########"
