#!/bin/bash
# omega(상대 선회각속도) 계산이 맞는지 실측 검증.
#
# [의심] 이력 버퍼는 BT 틱마다 채워지는데 나눗셈에는 항상 1/60초를 쓴다.
#   제출 조건(ACTION_REPEAT=6, BT 10Hz)에서는 12틱 = 1.2초 창인데 0.2초로 나눈다 -> 6배.
#
# [결정적 실험] 같은 상대를 두 속도로 돌린다.
#   repeat=1 (60Hz) : 12틱 = 0.2초 = 코드가 나누는 값과 일치  -> om/실측 ≈ 1이어야
#   repeat=6 (10Hz) : 12틱 = 1.2초                            -> om/실측 ≈ 6이면 버그 확정
#
# 상대는 onecircle(가장 세게 도는 상대, 우리 최약 매치업)과 kwon(중간)을 쓴다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32"' EXIT
cp -f AIP_ablate.dll AIP_DCS_ownship.dll     # v32와 동일 검증됨. [ACTIVE] 진단 포함.
unset TOPGUN_ABLATE

run_one () {   # $1=repeat  $2=상대
  local REP="$1"; local OPP="$2"
  echo "########## repeat=${REP} vs ${OPP} ##########"
  # ★ [ACTIVE]를 버리지 않는다. om= 값이 필요하다.
  "$PY" rehearsal_10hz.py "$REP" "$REP" 200 1 0 "$OPP" 2>&1 \
    | grep -aE "^\[ACTIVE\]|^\[seed|^SUMMARY" \
    || echo "  !! 비정상 종료"
  local NEW
  NEW=$(ls -t artifacts/logs/*_target_*.csv 2>/dev/null | head -1)
  NEW=$(basename "$NEW"); NEW="${NEW%%_target_*}"
  echo "STAMP repeat=${REP} ${OPP} ${NEW}"
  echo ""
}

# kwon은 Rule_mine.xml 충돌이 있어 뺀다. jink(불규칙)로 대체.
for OPP in AIP_onecircle.dll AIP_jink.dll; do
  run_one 1 "$OPP"
  run_one 6 "$OPP"
done
echo "=== omega probe 완료 ==="
