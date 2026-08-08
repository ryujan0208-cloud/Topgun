#!/bin/bash
# v39: 접근 속도 상한 330m/s. 무제한 풀스로틀이 진짜 병목이었다(500m/s -> 선회반경 28km).
# v38과의 차이: v38은 "돌아야 할 때 감속"(ataDeg>12 필요)이라 직선 추격 중엔 안 걸렸다.
#               v39는 ATA와 무관한 순수 속도 상한이라 가속 자체를 막는다.
# ※ 사전 고정: 메커니즘(직진전 평균속도·원거리비율 감소)
#    + 유형별 커버리지(9상대 어느 유형도 승수 감소 없을 것)
#    + 총량(승>=97 패<=4 순이득>=+58.9)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32 복구"' EXIT
cp -f AIP_v39.dll AIP_DCS_ownship.dll
echo "@@@ 메커니즘 STRAIGHT 고정스폰"
"$PY" rehearsal_10hz.py 6 6 200 1 0 STRAIGHT 2>&1 | grep -aE "^\[seed|^SUMMARY"
ls -t artifacts/logs/*ownship*.csv | head -1 | sed 's/.*logs\///; s/_ownship.*//' | sed 's/^/STAMP /'
echo ""
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll AIP_junghwan.dll SEARCH STRAIGHT; do
  echo "########## v39 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
