#!/bin/bash
# ★ 절제 실험의 대조군 검증 — 이것이 통과하지 못하면 이후 측정은 전부 무의미하다.
#
# AIP_dtfix.dll 을 TOPGUN_ABLATE 미설정으로 돌린 결과가
# AIP_v32.dll 과 **완전히 동일**해야 한다. 게이트는 무동작이어야 하기 때문이다.
# (코덱스가 CV01에서 계측 DLL의 정상 경로 해시 일치로 검증한 방식과 같다)
#
# 상대 선택: v7(실제 BT, 전체 기하를 쓴다) + STRAIGHT(오늘 v39에서 가장 민감했다)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_ABLATE

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32"' EXIT

for OPP in AIP_v7.dll STRAIGHT; do
  for WHICH in v32 dtfix; do
    cp -f "AIP_${WHICH}.dll" AIP_DCS_ownship.dll
    echo "########## ${WHICH} vs ${OPP} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
      | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
      || echo "  !! 비정상 종료"
    echo ""
  done
done
echo "=== 대조군 완료 ==="
