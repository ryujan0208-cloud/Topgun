#!/bin/bash
# v29 vs v31, ACE 상대 15시드 시드별 승패 비교.
# 판정 1순위는 준 데미지가 아니라 "승리 수"(규정 제6조: 타임아웃 시 HP 비교).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"   # 이 프로젝트 전용 conda env (pymap3d 등)
for V in v29 v31; do
  cp -f "AIP_${V}.dll" AIP_DCS_ownship.dll
  echo "########## ${V} vs ACE ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 ACE 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG)"
  echo ""
done
