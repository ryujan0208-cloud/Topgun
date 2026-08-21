#!/usr/bin/env bash
# v46 제출본 등가 검증 — 기본값 승격본(AIP_final.dll)이 절제 플래그(fastthr)와 시드일치해야 한다
# ★ CLAUDE.md: v40 때 이걸 안 해서 이틀간 제출 조합이 사실상 v32였다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_v46_verify.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE TOPGUN_ABLATE 2>/dev/null || true
for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
  echo "########## v46제출 :: ${OPP} ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|Error"
  done
done
echo "########## DONE ##########"
