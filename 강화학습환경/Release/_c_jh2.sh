#!/usr/bin/env bash
# v48 후보 2종 — fastthr(스로틀 제한 해제) / divebait(예측 선행 5.0->1.5s)
# ★ 판정기준(사전 고정): 3상대 모두에서 준데미지 퇴행 없음 AND yuno 순이득 개선
#    AND **우리 추락 0건**(divebait는 추락 위험이 실재. 1건이라도 나면 즉시 기각)
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_c_jh2.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v48test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for MODE in base fastthr divebait; do
  if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
  echo "########## ${MODE} :: AIP_jh2.dll ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
  done
done
echo "########## DONE ##########"
