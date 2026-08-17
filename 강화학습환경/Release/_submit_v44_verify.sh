#!/usr/bin/env bash
# 제출 쌍 검증 — 2026-08-16
#
# ★ CLAUDE.md: "제출본은 DLL과 XML을 쌍으로, 시드별 완전일치로 검증한다."
#   v40 채택 때 Rule_v40.xml만 고치고 제출용 Rule_forTraining.xml을 안 고쳐
#   **이틀간 제출 조합이 사실상 v32**였다(같은 15시드에서 3승12패 vs 12승1무2패, 시드일치 0/15).
#   해시·크기 비교로는 못 잡는다. 성적 비교로도 못 잡는다(약한 상대만 보면 안 보인다).
#   **같은 시드로 돌려 완전일치를 확인하는 것만이 증명이다.**
#
# 여기서 대조하는 두 조합은 **같은 소스·같은 트리**이므로 완전일치해야 한다:
#   제출본 : AIP_final.dll        + Rule_forTraining.xml (환경변수 없이)
#   검증본 : AIP_ryujan_v44.dll   + Rule_ryujan_v44.xml  (환경변수 없이)
# 한 판이라도 다르면 두 파일 중 하나가 의도와 다른 것이다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
LOCK="_submit_verify.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
unset TOPGUN_RULE TOPGUN_ABLATE 2>/dev/null || true

for OPP in AIP_jung.dll AIP_yuno.dll AIP_jh2.dll; do
  for TAG in 제출본 검증본; do
    if [ "$TAG" = "제출본" ]; then export TOPGUN_OWN_DLL="AIP_final.dll"
    else                             export TOPGUN_OWN_DLL="AIP_ryujan_v44.dll"; fi
    echo "########## ${TAG} :: ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 \
        | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
    done
  done
done
echo "########## DONE ##########"
