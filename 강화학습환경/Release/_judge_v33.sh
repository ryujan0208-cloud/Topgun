#!/bin/bash
# v33(lag pursuit 전환) 검증. 기준은 실행 전에 고정:
#  (1) 근거리 체류/사격조건 틱 증가  (2) Syllabus S2 개선  (3) ACE 승수 >= v32(13승)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v33.dll AIP_DCS_ownship.dll
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll; do
  echo "########## v33 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -E "^\[seed|^SUMMARY"
  echo ""
done
