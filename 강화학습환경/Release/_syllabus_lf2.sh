#!/bin/bash
# lowfloor2 Syllabus 검증. 규칙: 채택은 Syllabus + 15시드 실전 둘 다.
# v32 기준: PASS 0 / WEAK 7 / FAIL 5 (총 12)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT
cp -f Rule_mine_kwon.xml Rule_mine.xml       # Syllabus 상대에 kwon이 있다
cp -f AIP_lf2.dll AIP_DCS_ownship.dll
export TOPGUN_ABLATE=lowfloor2
export TOPGUN_RULE=./Rule_lowfloor.xml
echo "########## lowfloor2 Syllabus ##########"
"$PY" bfm_syllabus.py --opponents AIP_v7.dll,AIP_kwon.dll --repeats 2 --time 100 2>&1 \
  | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)"
echo "=== syllabus 완료 ==="
