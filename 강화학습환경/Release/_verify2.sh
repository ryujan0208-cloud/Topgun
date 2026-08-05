#!/bin/bash
# v32 과적합 점검 (재개). 상대별로 v29 -> v32 를 짝지어 돌린다.
# 짝으로 묶는 이유: 중간에 끊겨도 이미 끝난 상대는 비교 가능한 쌍이 남는다.
# 취약 영역(원선회)부터 = shrink, synccircle 먼저.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
for OPP in AIP_shrink.dll AIP_synccircle.dll AIP_trinity.dll AIP_jink.dll AIP_v7.dll AIP_sync.dll; do
  for V in v29 v32; do
    cp -f "AIP_${V}.dll" AIP_DCS_ownship.dll
    echo "########## ${V} vs ${OPP} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)" || echo "  !! 비정상 종료"
    echo ""
  done
done
echo "=== 전체 완료 ==="
