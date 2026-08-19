#!/usr/bin/env bash
# v45 제출본 등가 검증 — 남은 구간만 (jung seed22~43, jh2 전체)
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_v45_verify2.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE TOPGUN_ABLATE 2>/dev/null || true
echo "########## v45제출 :: AIP_jung.dll ##########"
for k in $(seq 7 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jung.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
done
echo "########## v45제출 :: AIP_jh2.dll ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
done
echo "########## DONE ##########"
