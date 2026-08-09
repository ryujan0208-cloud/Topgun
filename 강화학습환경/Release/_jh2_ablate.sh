#!/bin/bash
# 신형 도전자 상대로 절제/수정 변형을 시험한다 (진단 목적, 채택 판정 아님).
#
# [배경] 사용자가 리플레이에서 "뒤를 잡고도 사인함수처럼 왔다갔다 하다 추월당한다"를 관찰.
#   실측: v21 뱅크 횡예측이 상대 롤 부호로 조준점을 좌우로 민다.
#     - 상대가 |roll|>90 인 시간이 **44%** (onecircle 18%, jink 34%)
#     - `bankFactor=|roll|/90` 상한 1 이라 |roll|>=90이면 **항상 최대 횡이동**
#     - `s=sign(roll)` 이 ±180 근처에서 뒤집혀 조준점이 **중앙 306m** 점프(6회/분)
#     - 실제로 t=52.0~53.0에 +233 -> -238 -> +241m (480m 스윙 2회)
#   원 설계는 `omega>0.06` 게이트로 롤 위글을 막으려 했으나
#   **dt 버그로 omega가 6~9배라 게이트가 항상 열린다.**
#
# ★ 예상 (결과 보기 전에 적는다). v32 기준 = 4승 0무 11패 / 순이득 -7.42
#   v21 off     : **개선**한다 (승 > 4). 부호 뒤집힘 노이즈가 사라진다.
#   v17 off     : 악화한다. 궤도추종은 절제 1위(-18승)였다.
#   dtfix_full  : **개선**한다 (승 > 4). 기하가 올바르면 조준점이 안정된다.
#   -> v21 off와 dtfix_full 중 하나라도 개선하면 "조준점 진동"이 실재하는 원인이다.
#      둘 다 악화하면 진동은 결과이지 원인이 아니다(다른 데서 밀리고 있다).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; unset TOPGUN_ABLATE' EXIT
cp -f AIP_dtfix.dll AIP_DCS_ownship.dll     # 미설정=v32 동일 검증됨. 절제·dt 게이트 모두 포함.

run_one () {
  local TAG="$1"
  echo "########## ${TAG} vs AIP_jh2.dll ##########"
  TOPGUN_ABLATE="$TAG" "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

run_one v21
run_one dtfix_full
run_one v17
echo "=== jh2 절제 완료 ==="
