#!/bin/bash
# v35: 오프보어사이트 클램프 75 -> 110. 트리는 v32와 동일(단일 변수 시험).
# ※ 사전 고정 기준: 메커니즘(클램프 발동률 79% 감소) + 퇴행금지(ACE>=14 kwon>=11 v7>=14
#    sync>=3 jink>=15 onecircle 패<=2) + 총량(승>=58 패<=3 순이득>=+30.067)
# ※ 도는 동안 시뮬/설정/도구를 수정하지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> 현역 v32 복구"' EXIT
cp -f AIP_v35.dll AIP_DCS_ownship.dll
for OPP in ACE AIP_onecircle.dll AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v35 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|SNAPDECEL)" \
    | grep -avE "^\[CLAMP_DIAG" || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
