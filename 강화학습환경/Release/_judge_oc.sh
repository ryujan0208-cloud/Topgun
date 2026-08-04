#!/bin/bash
# v31의 간판 주장(onecircle 5.6배)이 ACE처럼 단일 시드 아웃라이어인지 확인.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
for V in v29 v31; do
  cp -f "AIP_${V}.dll" AIP_DCS_ownship.dll
  echo "########## ${V} vs onecircle ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_onecircle.dll 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG)"
  echo ""
done
