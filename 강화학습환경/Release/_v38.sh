#!/bin/bash
# v38: 코너속도 감속의 거리 게이트(dist<2500) 제거.
#   진짜 병목은 스로틀 하한이 아니라 **원거리 풀스로틀**이었다(계측: 직진 상대전 스로틀 0.98~0.99).
#   그 결과 500m/s까지 가속되고 선회반경 28km가 되어 한 번 지나치면 5km가 벌어진다.
# ※ 사전 고정 기준: 메커니즘(직진전 평균속도 496m/s 감소 + 원거리 88.2% 감소)
#    + 퇴행금지(ACE>=14 kwon>=11 v7>=14 sync>=3 jink>=15 onecircle 패<=2)
#    + 총량(승>=58 패<=3 순이득>=+30.067)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32 복구"' EXIT
cp -f AIP_v38.dll AIP_DCS_ownship.dll
for OPP in STRAIGHT AIP_dummy.dll; do
  echo "@@@ 메커니즘 $OPP"
  "$PY" rehearsal_10hz.py 6 6 200 1 0 "$OPP" 2>&1 | grep -aE "^\[seed|^SUMMARY|^\[THR\] team=1" | tail -3
  ls -t artifacts/logs/*ownship*.csv | head -1 | sed 's/.*logs\///; s/_ownship.*//' | sed "s/^/STAMP $OPP /"
done
echo ""
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v38 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
