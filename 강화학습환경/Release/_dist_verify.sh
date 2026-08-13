#!/bin/bash
# [배포본 검증] AIP_ryujan_v42.dll + Rule_ryujan_v42.xml (환경변수 없음)이
#   채택본 v42(AIP_v40.dll + TOPGUN_RULE=Rule_v42.xml)와 시드별로 일치해야 한다.
#   팀원에게 주는 스파링 기체이므로 "우리 v42와 같다"는 게 증명돼야 의미가 있다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
echo "########## 채택본 v42 (AIP_v40 + env) ##########"
export TOPGUN_OWN_DLL="AIP_v40.dll" TOPGUN_RULE="./Rule_v42.xml"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|DUTY)" || echo "  !! 비정상"
done
echo ""
echo "########## 배포본 (AIP_ryujan_v42, env 없음) ##########"
unset TOPGUN_RULE
export TOPGUN_OWN_DLL="AIP_ryujan_v42.dll"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|DUTY)" || echo "  !! 비정상"
done
echo ""
echo "=== 배포본 검증 완료 ==="
