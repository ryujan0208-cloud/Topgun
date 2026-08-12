#!/bin/bash
# [M700 legacy 재실행] junghwan 구간만. 1차 실행이 4시간 행 상태로 멈춰 강제 종료했다.
#   증상: 섹션 헤더는 찍혔는데 python이 출력도 트랙도 안 만들고 4시간 정지.
#   Rule_mine.xml은 junghwan판으로 정상이었다(XML 충돌 아님).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_RULE="./Rule_m700.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE TOPGUN_MATCH TOPGUN_GEOM
trap 'unset TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
cp -f Rule_mine_junghwan.xml Rule_mine.xml
FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'
echo "########## M700 vs AIP_junghwan.dll ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_junghwan.dll 2>&1 | grep -avE "$FILT" || echo "  !! junghwan 비정상"
echo ""
echo "=== junghwan 재실행 완료 ==="
