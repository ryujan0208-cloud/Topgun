#!/usr/bin/env bash
# unlockpitch — 뒤잡힘 시 하강 반전 (2026-08-19)
# ★ 판정기준(사전 고정)
#   채택: 3상대 준데미지 퇴행 없음 AND yuno 순이득 개선 AND 우리 추락 0건
#        AND 분산검사(최대3판 제외 후 부호 유지)
#   즉시 기각: 추락 1건이라도 / 어느 상대든 준데미지 감소
# ★ 순차 실행 (코덱스 동시 작업 중)
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_unlock.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v50test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
  for MODE in base unlockpitch; do
    if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
    echo "########## ${MODE} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error"
    done
  done
done
echo "########## DONE ##########"
