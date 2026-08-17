#!/usr/bin/env bash
# divefree 재시험 — 2026-08-16
#
# [왜 다시 하나] v40 시절 "4승->1승"으로 기각됐으나, 그 기각 사유가 사라졌다.
#   당시 기각 사유: "조준만 내리고 **벽은 그대로** = 최악의 조합"
#   당시 벽: DECO_AltitudeCheck MinAlt=1800, 조준 절대하한 1500m 고정
#   현재  : MinAlt=700(v42), 조준 하한 800~1500 동적(v40)  -> 두 벽 다 내려갔다
#
# [기대 메커니즘] diveSlope = dist*0.5 는 강하각을 약 27도로 묶는다.
#   하강나선(뱅크110도)은 지속 25.4도/s를 내지만 그 기하에 들어갈 수가 없다.
#   실측: 우리 실전 지속 선회율 13~15.6도/s = 수평선회(11.3) 수준.
#   yuno가 강요하는 LOS 각속도는 600~900m에서 16.1~17.4도/s.
#
# ★ 판정 기준 (결과 보기 전 고정)
#   채택: yuno 순이득 개선 AND jung·jh2 퇴행 없음 AND **우리 추락 0건**
#   기각: 추락 1건이라도 나면 즉시. 또는 어디서든 준데미지 감소.
#   ⚠ 최저고도를 함께 본다. "측정 중 실제 altitude below min 사망" 기록이 있다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_divefree.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
# 제출본과 같은 조합으로 잰다(AIP_final.dll + Rule_forTraining.xml, 환경변수 없이)
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE 2>/dev/null || true

for MODE in base divefree; do
  if [ "$MODE" = "divefree" ]; then export TOPGUN_ABLATE="divefree"; else unset TOPGUN_ABLATE; fi
  for OPP in AIP_yuno.dll AIP_jung.dll AIP_jh2.dll; do
    echo "########## ${MODE} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 \
        | grep -aE "^\[seed |^SUMMARY|below min|destroyed|Error|Traceback"
    done
  done
done
echo "########## DONE ##########"
