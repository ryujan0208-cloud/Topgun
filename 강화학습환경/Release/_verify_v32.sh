#!/bin/bash
# v32 과적합 점검: 미검증 상대 6종 x 15시드.
# 한 상대가 크래시(JSBSim access violation 전례)해도 나머지는 계속 돌린다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for OPP in AIP_sync.dll AIP_synccircle.dll AIP_shrink.dll AIP_jink.dll AIP_trinity.dll AIP_v7.dll; do
  echo "########## v32 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)" || echo "  !! 이 상대에서 비정상 종료"
  echo ""
done
echo "=== 전체 완료 ==="
