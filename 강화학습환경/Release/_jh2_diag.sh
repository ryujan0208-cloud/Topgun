#!/bin/bash
# 신형 도전자에게 왜 격추당하는지 — 진단 실행.
#
# [질문] 방어가 **안 걸리는 것**인가, **걸리는데 못 살아나는 것**인가.
#   우리 트리:  거리<1100 AND 상대조준각<25  -> Task_Evade
#   코덱스 전조: 거리<=914.4 AND |상대ATA|<=30 AND 우리ATA>=130 (피격 5초 전)
#   우리 트리거가 더 넓으므로(1100>914) 대부분 걸려야 정상이다. 실제로 걸리는지 잰다.
#
# ★ 진단을 필터로 버리지 않는다. [DUTY_EV](Evade 실행 틱 누적)와 [EVADE_DIAG]가 핵심이다.
#   (오늘 이 종류의 필터 때문에 dt 버그를 오래 못 봤다)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_ABLATE

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll' EXIT
cp -f AIP_v32.dll AIP_DCS_ownship.dll

echo "########## v32 vs AIP_jh2.dll (진단) ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_jh2.dll 2>&1 \
  | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_)" \
  || echo "  !! 비정상 종료"

NEW=$(ls -t artifacts/logs/*_target_*.csv 2>/dev/null | head -1)
NEW=$(basename "$NEW"); NEW="${NEW%%_target_*}"
echo "STAMP v32 AIP_jh2.dll ${NEW}"
echo "=== 진단 완료 ==="
