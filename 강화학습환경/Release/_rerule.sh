#!/bin/bash
# 대회 공식 규칙(3단계 phase) 적용 후 전 상대 재측정.
# 지금까지의 모든 판정이 Phase 1 고정 기준이었으므로 무엇이 유지되고 무엇이 뒤집히는지 확인.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v32 vs ${OPP} (대회규칙) ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|CLAMP_DIAG|ONECIRCLE)" || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
