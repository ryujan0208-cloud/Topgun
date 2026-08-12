#!/bin/bash
# 라운드 2·3 거리 검증 — v40
# 사전등록: experiments/match_conditions/PREREG_rounds23_2026-08-12.md
# ★ 시드를 3의 배수로 쓰면 항상 라운드1(610m)이 된다. 그게 이번 공백의 원인이었다.
#   라운드2 = seed%3==1, 라운드3 = seed%3==2
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
if [ "-" = "-" ]; then unset TOPGUN_RULE; else export TOPGUN_RULE="-"; fi
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for R in 1 2; do
  for G in HABFM OBFM_BLUE OBFM_RED; do
    export TOPGUN_GEOM=$G
    echo "########## v40 / 라운드$((R+1)) / $G / jh2 ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) AIP_jh2.dll 2>&1         | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|EVADE_DIAG)"         || echo "  !! seed 비정상"
    done
    echo ""
  done
done
echo "=== v40 라운드2·3 완료 ==="
