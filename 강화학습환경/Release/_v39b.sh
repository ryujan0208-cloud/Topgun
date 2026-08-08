#!/bin/bash
# v39 중단분 재개(ACE까지 완료됨). 나머지 8상대.
# ※ 조각(직진 dealt 1.0073->0.0000, ACE taken 0.0165->0.1034)만으로 기각하지 않는다.
#    유형별 커버리지로 판정하려면 전 상대가 필요하다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32 복구"' EXIT
cp -f AIP_v39.dll AIP_DCS_ownship.dll
for OPP in AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll AIP_junghwan.dll SEARCH STRAIGHT; do
  echo "########## v39 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
