#!/usr/bin/env bash
# v45 제출본 최종 검증 — 2026-08-16
#  기대: 새 제출본(AIP_final.dll, divefree 기본값)이
#        절제 실험의 divefree 결과와 **시드별 완전일치**해야 한다.
#        일치하지 않으면 '기본값 승격'이 절제 플래그와 다른 코드경로를 탄 것이다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_v45_verify.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE TOPGUN_ABLATE 2>/dev/null || true
for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
  echo "########## v45제출 :: ${OPP} ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
  done
done
echo "########## DONE ##########"
