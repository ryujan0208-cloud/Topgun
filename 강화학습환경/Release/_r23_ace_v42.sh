#!/bin/bash
# [마지막 커버리지] v42 x ACE 라운드2·3. 지금까지 라운드2·3은 jh2만 쟀다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_RULE="./Rule_v42.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for R in 1 2; do
  for G in HABFM OBFM_BLUE OBFM_RED; do
    export TOPGUN_GEOM=$G
    echo "########## v42 / 라운드$((R+1)) / $G / ACE ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) ACE 2>&1 \
        | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|DUTY)" \
        || echo "  !! seed 비정상"
    done
    echo ""
  done
done
echo "=== v42 x ACE 라운드2·3 완료 ==="
