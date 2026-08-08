#!/bin/bash
# 절제 마무리 — REMOVE 후보(v21)와 보류(v27)를 **9상대 전체**로 재검증한다.
# 선별 세트에서 뺐던 onecircle/sync만 추가로 돌린다(나머지 7상대는 이미 측정됨).
#   ※ 이 두 상대는 최대기여시드 112.5%/50.2%라 단독 판정에 쓸 수 없다.
#      다만 "제거해도 퇴행이 없는가"의 안전 확인용으로는 필요하다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

run_one () {
  local TAG="$1"; local OPP="$2"
  echo "########## ablate=${TAG} vs ${OPP} ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

for TAG in v21 v27; do
  run_one "$TAG" AIP_onecircle.dll
  run_one "$TAG" AIP_sync.dll
done

echo "=== 배치 C 완료 ==="
