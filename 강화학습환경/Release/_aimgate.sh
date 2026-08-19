#!/usr/bin/env bash
# v46 종말조준 게이트 확대 시험 — 2026-08-19
#  사용자 제안: "사거리 안인데 사격각이 안 나올 때 VP를 상대에 정확히 찍는다"
#  v27 게이트(ATA<10도, 발동률 0.3~5.7%)를 15/20/30도로 넓혀 셋을 함께 잰다.
#
# ★ 판정 기준 (결과 보기 전 고정)
#   채택: yuno 순이득 개선 AND jung·jh2 준데미지 퇴행 없음
#   즉시 기각: 어느 상대든 준데미지가 줄면. 그게 v25의 실패 양식이다
#             (v25: 거리로 리드 제거 -> dealt 4.34 -> 1.53 붕괴, 6승9무0패 -> 4승10무1패).
#   셋을 다 잰다: 30도가 나쁘고 15도가 좋을 수 있다. 하나만 재면
#   "방향이 틀렸다"와 "임계값이 틀렸다"를 못 가른다(v33 CAP 25/40 교훈).
#
# ★ 상대 바깥루프: 배치가 자주 끊기므로 **yuno(핵심)를 먼저** 끝낸다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_aimgate.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v46test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT

for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
  for MODE in base aim15 aim20 aim30; do
    if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
    echo "########## ${MODE} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
    done
  done
done
echo "########## DONE ##########"
