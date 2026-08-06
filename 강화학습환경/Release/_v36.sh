#!/bin/bash
# v36: CORNER 260 -> 287 (실측 선회율 최대점). 트리는 v32와 동일 = 단일 변수.
# ※ 사전 고정 기준: 메커니즘(선회율 11.7 초과) + 주목표(onecircle 승>=2 또는 패<=1)
#    + 퇴행금지(ACE>=14 kwon>=11 v7>=14 sync>=3 jink>=15) + 총량(승>=58 패<=3 순이득>=+30.067)
# ※ 도는 동안 시뮬/설정/도구를 수정하지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> 현역 v32 복구"' EXIT
cp -f AIP_v36.dll AIP_DCS_ownship.dll
for OPP in AIP_onecircle.dll ACE AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v36 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
