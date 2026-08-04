#!/bin/bash
# v32(상승 클램프 26.6->71.6deg) 검증. 판정기준은 실행 전에 고정했다:
#  (1) 위로잘림 50.8% 대폭 감소  (2) 수직오차 el 감소  (3) ACE 승수 >= v29(11승)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll; do
  echo "########## v32 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG)"
  echo ""
done
