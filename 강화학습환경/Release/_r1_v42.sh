#!/bin/bash
# [커버리지] v42를 라운드1(610m)에서 재측정. v42는 라운드2·3만 쟀다.
#   MinAlt를 바꿨으므로 v41의 라운드1 수치(77/5/8)를 그대로 물려받을 수 없다.
# 시드 3의 배수 = 라운드1. 상대 2종(jh2, ACE) x 3기하 x 15시드 = 90판.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_RULE="./Rule_v42.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for G in HABFM OBFM_BLUE OBFM_RED; do
  export TOPGUN_GEOM=$G
  for OPP in AIP_jh2.dll ACE; do
    echo "########## v42 / 라운드1 / $G / $OPP ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) "$OPP" 2>&1 \
        | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_)" \
        || echo "  !! seed 비정상"
    done
    echo ""
  done
done
echo "=== v42 라운드1 완료 ==="
