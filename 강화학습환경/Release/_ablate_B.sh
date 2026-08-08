#!/bin/bash
# 절제 배치 B — Rule_mine.xml을 **읽지 않는** 상대만. 배치 A와 동시에 돌려도 안전하다.
#
# ★ ownship DLL은 여기서도 바꾸지 않는다(배치 A 주석 참고).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

run_one () {   # $1=절제태그  $2=상대
  local TAG="$1"; local OPP="$2"
  echo "########## ablate=${TAG} vs ${OPP} ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

for TAG in v31 v21 v17 v27 v32clamp v18dive v23corner; do
  run_one "$TAG" AIP_v7.dll
  run_one "$TAG" SEARCH
  run_one "$TAG" STRAIGHT
done

echo "=== 배치 B 완료 ==="
