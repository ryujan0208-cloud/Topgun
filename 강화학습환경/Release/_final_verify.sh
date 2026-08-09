#!/bin/bash
# ★ 제출본 검증: AIP_final_v40.dll(Rule_forTraining.xml을 읽음)이
#   개발본 AIP_v40.dll(Rule_v40.xml)과 **시드별로 동일**해야 한다.
#   제출 경로는 환경변수를 못 쓰므로 이 확인이 필수다.
#   전례: AIP_final.dll이 v27인 채로 방치돼 있었다(XML이 같아 안 보였음).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; cp -f Rule_forTraining_bak.xml Rule_forTraining.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT
cp -f Rule_forTraining.xml Rule_forTraining_bak.xml     # 원본 보존
cp -f Rule_v40.xml         Rule_forTraining.xml         # activate_rule_xml이 하는 일과 동일
cp -f Rule_mine_kwon.xml   Rule_mine.xml
unset TOPGUN_ABLATE TOPGUN_RULE

for OPP in AIP_jh2.dll AIP_kwon.dll; do
  for W in v40 final_v40; do
    cp -f "AIP_${W}.dll" AIP_DCS_ownship.dll
    echo "########## ${W} vs ${OPP} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
      | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" || echo "  !! 비정상"
    echo ""
  done
done
echo "=== 제출본 검증 완료 ==="
