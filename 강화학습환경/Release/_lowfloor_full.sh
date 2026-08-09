#!/bin/bash
# lowfloor 전체 검증 — 나머지 6상대 (kwon/v7/sync/jink/junghwan/SEARCH).
# 이미 측정: jh2 11승1무3패 / ACE 15승0패 / onecircle 2승11무2패 / STRAIGHT 13승2무0패
#
# ★ kwon은 ./Rule_mine.xml 을 읽는다(우리는 TOPGUN_RULE로 Rule_lowfloor.xml을 읽으므로 충돌 없음).
#   junghwan(8/6판)은 junghwan용 Rule_mine.xml이 필요하다. 상대마다 갈아끼운다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT

cp -f AIP_lowfloor.dll AIP_DCS_ownship.dll
export TOPGUN_ABLATE=lowfloor
export TOPGUN_RULE=./Rule_lowfloor.xml

run_one () {   # $1=상대 $2=Rule_mine에 넣을 파일(없으면 그대로)
  local OPP="$1"; local MINE="$2"
  [ -n "$MINE" ] && cp -f "$MINE" Rule_mine.xml
  echo "########## lowfloor vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

run_one AIP_kwon.dll      Rule_mine_kwon.xml
run_one AIP_junghwan.dll  Rule_mine_junghwan.xml
run_one AIP_v7.dll        ""
run_one AIP_sync.dll      ""
run_one AIP_jink.dll      ""
run_one SEARCH            ""

cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "=== lowfloor 전체 검증 완료 ==="
