#!/bin/bash
# [M700 비퇴행 ①] HABFM·OBFM_BLUE 라운드2·3. 사전등록: PREREG_minalt_2026-08-12.md
# 기준선 v41: 라운드2 HABFM 10/5/0, BLUE 10/4/1 / 라운드3 HABFM 12/3/0, BLUE 7/8/0
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_RULE="./Rule_m700.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for R in 1 2; do
  for G in HABFM OBFM_BLUE; do
    export TOPGUN_GEOM=$G
    echo "########## M700 / 라운드$((R+1)) / $G / jh2 ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) AIP_jh2.dll 2>&1 \
        | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_)" \
        || echo "  !! seed 비정상"
    done
    echo ""
  done
done
echo "=== M700 비퇴행 완료 ==="
