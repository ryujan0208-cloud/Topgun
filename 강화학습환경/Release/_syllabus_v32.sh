#!/bin/bash
# 빠뜨린 검증: BFM Syllabus. 우리 규칙은 "Syllabus + 15시드 실전 둘 다"인데
# v32는 배치만 돌렸다(v25가 Syllabus만 통과해 기각된 전례의 반대 실수).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
for V in v29 v32; do
  cp -f "AIP_${V}.dll" AIP_DCS_ownship.dll
  echo "########## ${V} Syllabus ##########"
  "$PY" bfm_syllabus.py --opponents AIP_v7.dll,AIP_kwon.dll --repeats 2 --time 100 2>&1 \
    | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)"
  echo ""
done
