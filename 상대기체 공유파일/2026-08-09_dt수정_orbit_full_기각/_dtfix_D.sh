#!/bin/bash
# dt 수정 배치 D — Rule_mine.xml을 쓰는 상대(kwon/junghwan)를 **이 배치에만** 모았다.
#   배치 E는 Rule_mine.xml을 안 건드리므로 동시 실행이 안전하다.
#
# ★ ownship DLL은 어느 배치도 바꾸지 않는다. 실행 전 1회 넣고 둘 다 끝난 뒤 되돌린다.
#     cp -f AIP_dtfix.dll AIP_DCS_ownship.dll     <- 실행 전
#     cp -f AIP_v32.dll   AIP_DCS_ownship.dll     <- 둘 다 끝난 뒤
#
# ★ [DUTY]와 [ACTIVE]를 **버리지 않는다.** 사전등록한 메커니즘 확인 지표다.
#   (오늘 이 필터 때문에 dt 버그를 오래 못 봤다)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

run_one () {   # $1=변형 $2=상대 $3=Rule_mine에 넣을 파일
  local TAG="$1"; local OPP="$2"; local MINE="$3"
  [ -n "$MINE" ] && cp -f "$MINE" Rule_mine.xml
  echo "########## ${TAG} vs ${OPP} ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

for TAG in dtfix_orbit dtfix_full; do
  run_one "$TAG" AIP_kwon.dll       Rule_mine_kwon.xml
  run_one "$TAG" AIP_junghwan.dll   Rule_mine_junghwan.xml
  run_one "$TAG" ACE                ""
  run_one "$TAG" AIP_onecircle.dll  ""
  run_one "$TAG" AIP_jink.dll       ""
done

cp -f Rule_mine_junghwan.xml Rule_mine.xml    # 평상시 기본값
echo "=== 배치 D 완료 ==="
