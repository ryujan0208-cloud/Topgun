#!/usr/bin/env bash
# v44(변환을 ChangeData 한 곳으로) 회귀 검증 — 2026-08-15
#
# [왜 v43보다 위험한가] v43은 Step()만 고쳐서 로컬 경로가 아예 안 지나갔다.
#   v44는 **ChangeData를 바꿨고 로컬 경로는 ChangeData를 지난다.**
#   수식(LLAtoCartesian)과 원점이 같고 적용 시점만 옮겼으므로 결과가 같아야 하지만
#   그건 증명해야 할 것이지 가정할 것이 아니다.
#
# [기준] v42(AIP_v40.dll + Rule_v42.xml)와 **시드별 완전일치**. 한 판이라도 다르면 기각.
#   기준선은 _v43_verify.log 의 'v42기준' 구간을 재사용한다(같은 시드/같은 상대).
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"

LOCK="_v44_verify.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"
export TOPGUN_MATCH=1
export TOPGUN_OWN_DLL="AIP_ryujan_v44.dll"     # 환경변수 없이 자기 XML을 읽는다 = 배포 형태
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE' EXIT
unset TOPGUN_RULE 2>/dev/null || true

for OPP in AIP_jung.dll AIP_yuno.dll AIP_jh2.dll; do
  echo "########## v44배포 :: ${OPP} ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 | grep -aE "^\[seed |^SUMMARY|Error|Traceback"
  done
done
echo "########## DONE ##########"
