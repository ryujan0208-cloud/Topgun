#!/usr/bin/env bash
# mergeslow 독립 표본 — 새 시드 15개 (기존은 k*3+1, 여기는 k*3+2)
#  [왜] 1차 15시드에서 순이득 +0.674 중 seed34가 61%, seed34+43이 95%를 차지했다.
#       판정원칙3에 따르면 분산과 구분되지 않는다. 독립 표본으로 재확인한다.
#  ★ 판정 기준(사전 고정): 새 15시드에서도 순이득 개선 AND 최대1판 제외 후에도 부호 유지.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_mergeslow2.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v47test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for MODE in base mergeslow; do
  if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
  echo "########## ${MODE} :: AIP_yuno.dll ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+2)) AIP_yuno.dll 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error|Traceback"
  done
done
echo "########## DONE ##########"
