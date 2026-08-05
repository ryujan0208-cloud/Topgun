#!/bin/bash
# v34(급감속 스냅샷) 검증. 대회 규칙(3단계 phase) 적용.
# ※ 사전 고정 판정기준 (결과 보기 전에 못박음):
#   주목표: onecircle 승>=2 또는 패<=1   (v32: 1승12무2패)
#   퇴행금지: ACE 승>=14, kwon>=11, v7>=14, sync>=3, jink>=15
#   총량: 순이득 합계 >= +30.067, 패 합계 <= 3
#   메커니즘: SNAPDECEL 발동 구간에서 ATA가 실제로 감소할 것
# ※ 이 배치가 도는 동안 시뮬/설정/도구를 절대 수정하지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship을 현역 v32로 복구"' EXIT
cp -f AIP_v34.dll AIP_DCS_ownship.dll
for OPP in AIP_onecircle.dll ACE AIP_kwon.dll AIP_v7.dll AIP_sync.dll AIP_jink.dll; do
  echo "########## v34 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|CLAMP_DIAG|ONECIRCLE|SNAPDECEL)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 완료 ==="
