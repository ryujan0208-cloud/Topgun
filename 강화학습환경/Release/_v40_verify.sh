#!/bin/bash
# ★ v40 승격 검증: 환경변수 **없이** 돌린 AIP_v40.dll이
#   게이트로 돌린 lowfloor2와 **시드별로 동일**해야 한다.
#   제출본은 환경변수에 의존할 수 없으므로 이 확인이 필수다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT
cp -f Rule_mine_kwon.xml Rule_mine.xml

for OPP in AIP_jh2.dll AIP_kwon.dll; do
  # (1) 게이트판
  cp -f AIP_lf2.dll AIP_DCS_ownship.dll
  export TOPGUN_ABLATE=lowfloor2 TOPGUN_RULE=./Rule_lowfloor.xml
  echo "########## lf2게이트 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" || echo "  !! 비정상"
  echo ""
  # (2) v40 기본판 (환경변수 없음)
  cp -f AIP_v40.dll AIP_DCS_ownship.dll
  unset TOPGUN_ABLATE TOPGUN_RULE
  echo "########## v40기본 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" || echo "  !! 비정상"
  echo ""
done
cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "=== v40 승격 검증 완료 ==="
