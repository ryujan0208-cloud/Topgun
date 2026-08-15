#!/usr/bin/env bash
# v43(좌표 규약 자동판별) 검증 — 2026-08-15
#
# [무엇을 증명해야 하나]
#  1) 로컬 경로에서 v42와 **완전히 같아야** 한다. 한 판이라도 다르면 기각.
#     좌표 수정은 '입력이 LLA가 아닐 때만' 발동하므로 로컬은 한 비트도 안 바뀌어야 한다.
#     이건 가정이 아니라 증명해야 할 것이다.
#  2) 서버 경로에서 거리가 정상이어야 한다(별도 스크립트).
#
# [주의] 상대는 고유 XML을 읽는 것만 쓴다(jung/yuno/jh2). 충돌 없음.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"

LOCK="_v43_verify.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE' EXIT

SEEDS=15
for OPP in AIP_jung.dll AIP_yuno.dll AIP_jh2.dll; do
  # 기준선: 채택 v42 (AIP_v40.dll + Rule_v42.xml)
  echo "########## v42기준 :: ${OPP} ##########"
  export TOPGUN_OWN_DLL="AIP_v40.dll" TOPGUN_RULE="./Rule_v42.xml"
  for k in $(seq 0 $((SEEDS-1))); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
  done
  # 신규: v43 (환경변수 없이 자기 XML을 읽는다 = 배포 형태 그대로)
  echo "########## v43배포 :: ${OPP} ##########"
  unset TOPGUN_RULE
  export TOPGUN_OWN_DLL="AIP_ryujan_v43.dll"
  for k in $(seq 0 $((SEEDS-1))); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
  done
done
echo "########## DONE ##########"
