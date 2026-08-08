#!/bin/bash
# v39 잔여분: kwon(XML충돌로 무효였음 재측정) + SEARCH + STRAIGHT
#
# ★ Rule_mine.xml 이름 충돌 해소
#   AIP_kwon.dll(권정환 7/22판)과 AIP_junghwan.dll(권정환 8/6판)은 같은 사람의 기체라
#   둘 다 ./Rule_mine.xml 을 읽는다. 8/6 16:49에 junghwan판을 넣으면서 kwon판을 덮어써
#   그 이후 kwon 배치가 전부 초기화 실패(DECO_TargetLOSCheck 미등록)로 죽었다.
#   -> 상대별로 해당 XML을 넣고 돌린다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; echo "[trap] ownship->v32, Rule_mine->junghwan 복구"' EXIT

cp -f AIP_v39.dll AIP_DCS_ownship.dll

run_one () {   # $1=상대  $2=Rule_mine에 넣을 파일(없으면 그대로)
  local OPP="$1"; local MINE="$2"
  [ -n "$MINE" ] && cp -f "$MINE" Rule_mine.xml
  echo "########## v39 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

run_one AIP_kwon.dll Rule_mine_kwon.xml
run_one SEARCH ""
run_one STRAIGHT ""

echo "=== v39c 완료 ==="
