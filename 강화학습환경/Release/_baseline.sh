#!/bin/bash
# v32 전체 유형 기준선. 신규 3종(junghwan/SEARCH/STRAIGHT)은 기준선이 없어 판정 불가였다.
# 앞으로 모든 변경은 이 표와 대조한다. 유형별 커버리지로 판정하기 위함.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll' EXIT
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for OPP in AIP_junghwan.dll SEARCH STRAIGHT; do
  echo "########## v32 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
