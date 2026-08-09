#!/bin/bash
# lowfloor의 kwon 퇴행(11승4무 -> 8승7무, 순이득 10.99 -> 7.02) 원인 규명.
#
# [가설] kwon은 권정환 7/22판이라 하한이 높은(FloorHard 1800 / FloorSoft 3200) 기체다.
#   즉 **안 내려간다.** 우리만 하한을 낮추면 내려갈 이유가 없는데 내려가서
#   에너지(고도)를 잃고 상대는 위에 남는다 -> 각도를 못 만들어 무승부가 는다.
#   패가 0으로 동일한 것도 이 가설과 맞다(더 맞는 게 아니라 못 끝내는 것).
#
# ★ 배치 로그는 stamp를 안 찍는다. 실행 직후 최신 트랙에서 stamp를 직접 박는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT
cp -f Rule_mine_kwon.xml Rule_mine.xml

run_one () {   # $1=라벨
  local LAB="$1"
  echo "########## ${LAB} vs AIP_kwon.dll ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_kwon.dll 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  local NEW
  NEW=$(ls -t artifacts/logs/*_target_*.csv 2>/dev/null | head -1)
  NEW=$(basename "$NEW"); NEW="${NEW%%_target_*}"
  echo "STAMP ${LAB} AIP_kwon.dll ${NEW}"
  echo ""
}

cp -f AIP_v32.dll AIP_DCS_ownship.dll
unset TOPGUN_ABLATE TOPGUN_RULE
run_one v32

cp -f AIP_lowfloor.dll AIP_DCS_ownship.dll
export TOPGUN_ABLATE=lowfloor
export TOPGUN_RULE=./Rule_lowfloor.xml
run_one lowfloor

echo "=== kwon probe 완료 ==="
