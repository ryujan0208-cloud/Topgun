#!/usr/bin/env bash
# divefree 재시험 — 크래시로 중단된 나머지 구간만 (2026-08-16)
#  이미 완료: base 전체 45판, divefree yuno 15판 + jung 5판(seed 1~13)
#  남은 것  : divefree jung seed16~43(10판), divefree jh2 15판
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_divefree2.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll" TOPGUN_ABLATE="divefree"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE 2>/dev/null || true

echo "########## divefree :: AIP_jung.dll ##########"
for k in $(seq 5 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jung.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
done
echo "########## divefree :: AIP_jh2.dll ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
done
echo "########## DONE ##########"
