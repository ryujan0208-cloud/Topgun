#!/bin/bash
# v17 궤도추종의 유형별 갈림 규명용 대조 실행.
#
# [질문] 같은 기능이 왜 ACE/junghwan엔 필수(14승->4승)인데 v7엔 해로운가(+4.01->+9.14)?
#
# [주의] 배치 로그는 stamp를 안 찍는다. 생성 시각으로 상대를 **추정**하면
#   나중에 어느 판인지 확신할 수 없다(코덱스 리포트의 confidence:low 문제와 같다).
#   -> 실행 직후 최신 CSV를 읽어 **stamp를 로그에 직접 박는다.**
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32"' EXIT
cp -f AIP_ablate.dll AIP_DCS_ownship.dll

run_one () {   # $1=절제태그(빈문자면 v32) $2=상대
  local TAG="$1"; local OPP="$2"
  local LABEL="${TAG:-v32}"
  echo "########## ${LABEL} vs ${OPP} ##########"
  if [ -z "$TAG" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$TAG"; fi
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  unset TOPGUN_ABLATE
  # 방금 만들어진 트랙의 stamp를 확정 기록
  local NEW
  NEW=$(ls -t artifacts/logs/*_target_*.csv 2>/dev/null | head -1)
  NEW=$(basename "$NEW"); NEW="${NEW%%_target_*}"
  echo "STAMP ${LABEL} ${OPP} ${NEW}"
  echo ""
}

for OPP in AIP_v7.dll ACE AIP_junghwan.dll; do
  run_one ""    "$OPP"
  run_one "v17" "$OPP"
done

echo "=== v17 probe 완료 ==="
