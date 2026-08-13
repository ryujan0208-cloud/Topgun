#!/bin/bash
# [실험 J 자기검증] 환경변수 없이 돌린 새 빌드가 v42와 **시드별 완전일치**해야 한다.
#   일치하지 않으면 실험 코드가 기본 경로에 새고 있다는 뜻이므로 즉시 중단.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED TOPGUN_RULE="./Rule_v42.xml"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for D in AIP_v40.dll AIP_j.dll; do
  export TOPGUN_OWN_DLL="$D"
  echo "########## $D (env 없음) / OBFM_RED 라운드2 / jh2 ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 \
      | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|DUTY)" \
      || echo "  !! seed 비정상"
  done
  echo ""
done
echo "=== J 자기검증 완료 ==="
