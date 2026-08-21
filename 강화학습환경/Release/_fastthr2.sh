#!/usr/bin/env bash
# fastthr 독립표본 — 새 시드 15개(k*3+2), 3상대
# ★ 판정기준(사전 고정, 승패 기준으로 재설정)
#   1차 결과: 27승13무5패 -> 30승12무3패 (+3승 -2패), 뒤집힌 8판 중 개선6/악화2
#   채택: 새 표본에서도 **합계 승수 증가 AND 패수 비증가** AND 우리 추락 0
#   기각: 승수가 줄거나 패수가 늘면
#   ※ 준데미지 감소는 이제 단독 기각 사유가 아니다 — 규정이 HP 비교라
#     받은 데미지가 0인 상대에서 준데미지 5% 감소는 승패에 영향이 없다.
#     (v25는 준데미지와 **승수가 함께** 붕괴했다. 그게 진짜 실패 양식이었다.)
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_fastthr2.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "★ 이미 돌고 있다"; exit 3; fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v48test.dll" TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
  for MODE in base fastthr; do
    if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
    echo "########## ${MODE} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+2)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|below min|Error"
    done
  done
done
echo "########## DONE ##########"
