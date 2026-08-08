#!/bin/bash
# dt 수정 배치 E — Rule_mine.xml을 **읽지 않는** 상대만. 배치 D와 동시 실행 안전.
# ★ ownship DLL은 바꾸지 않는다(배치 D 주석 참고). [DUTY]/[ACTIVE]도 버리지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

run_one () {   # $1=변형 $2=상대
  local TAG="$1"; local OPP="$2"
  echo "########## ${TAG} vs ${OPP} ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

for TAG in dtfix_orbit dtfix_full; do
  run_one "$TAG" AIP_v7.dll
  run_one "$TAG" AIP_sync.dll
  run_one "$TAG" SEARCH
  run_one "$TAG" STRAIGHT
done

echo "=== 배치 E 완료 ==="
