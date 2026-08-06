#!/bin/bash
# v37: 스로틀 하한을 거리 의존으로(과근접 0.15 / 근접 0.35 / 원거리 0.55).
# 0.55 고정이 dV 폐루프의 감속 명령을 실행 불가능하게 만들고 있었다(액추에이터 포화).
# ※ 사전 고정 기준: 메커니즘(과근접 47.5% 감소 + 사거리 안 증가)
#    + 퇴행금지(ACE>=14 kwon>=11 v7>=14 sync>=3 jink>=15 onecircle 패<=2)
#    + 총량(승>=58 패<=3 순이득>=+30.067)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32 복구"' EXIT
cp -f AIP_v37.dll AIP_DCS_ownship.dll
# 먼저 메커니즘 확인용 단판(선회 상대 / 직선 상대)
for OPP in AIP_dummy.dll STRAIGHT; do
  echo "@@@ 메커니즘 $OPP"
  "$PY" rehearsal_10hz.py 6 6 200 1 0 "$OPP" 2>&1 | grep -aE "^\[seed|^SUMMARY"
  ls -t artifacts/logs/*ownship*.csv | head -1 | sed 's/.*logs\///; s/_ownship.*//' | sed "s/^/STAMP $OPP /"
done
echo ""
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v37 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
