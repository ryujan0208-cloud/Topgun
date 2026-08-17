#!/usr/bin/env bash
# v45 standoff 절제 대조 — 2026-08-16
#
# ★ 판정 기준 (결과 보기 전 고정)
#   채택: yuno전 득점(준데미지) > 0        AND  jung·jh2 순이득 퇴행 없음
#   기각: 준데미지가 어디서든 줄면 즉시 기각.
#         "위치를 사고 사격을 파는" 것이 v33의 정체였고 행동강령 3 위반이다.
#   필수: standoff 발동률이 0이면 '효과 없음'이 아니라 '발동 안 함'이다. 로그로 확인.
#
# 같은 DLL(AIP_v45test.dll)로 플래그만 바꿔 돌린다 — 빌드 차이가 섞이지 않는다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_standoff.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v45test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT

for MODE in base standoff; do
  if [ "$MODE" = "standoff" ]; then export TOPGUN_ABLATE="standoff"; else unset TOPGUN_ABLATE; fi
  for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
    echo "########## ${MODE} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 \
        | grep -aE "^\[seed |^SUMMARY|standoff|Error|Traceback"
    done
  done
done
echo "########## DONE ##########"
