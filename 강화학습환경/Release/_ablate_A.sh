#!/bin/bash
# 절제 배치 A — Rule_mine.xml을 쓰는 상대(kwon/junghwan)를 **이 배치에만** 모았다.
#   배치 B는 Rule_mine.xml을 건드리지 않으므로 둘을 동시에 돌려도 충돌하지 않는다.
#
# ★ ownship DLL은 여기서 바꾸지 않는다. 실행 전에 한 번만 넣어두고,
#   두 배치가 모두 끝난 뒤 사람이 v32로 되돌린다.
#   (양쪽 스크립트에 trap을 걸면 먼저 끝난 쪽이 상대 배치를 망가뜨린다)
#     cp -f AIP_ablate.dll AIP_DCS_ownship.dll     <- 실행 전 1회
#     cp -f AIP_v32.dll    AIP_DCS_ownship.dll     <- 둘 다 끝난 뒤
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

run_one () {   # $1=절제태그  $2=상대  $3=Rule_mine에 넣을 파일
  local TAG="$1"; local OPP="$2"; local MINE="$3"
  [ -n "$MINE" ] && cp -f "$MINE" Rule_mine.xml
  echo "########## ablate=${TAG} vs ${OPP} ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

for TAG in v31 v21 v17 v27 v32clamp v18dive v23corner; do
  run_one "$TAG" AIP_kwon.dll      Rule_mine_kwon.xml
  run_one "$TAG" AIP_junghwan.dll  Rule_mine_junghwan.xml
  run_one "$TAG" AIP_jink.dll      ""
  run_one "$TAG" ACE               ""
done

cp -f Rule_mine_junghwan.xml Rule_mine.xml    # 평상시 기본값으로
echo "=== 배치 A 완료 ==="
