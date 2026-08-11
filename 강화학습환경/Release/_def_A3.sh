#!/bin/bash
# [실험 A3] Evade 게이트 축소 — Rule_evade8.xml
# 사전등록 추가분: PREREG_defense_2026-08-11.md (커밋 e2a5fe0, 결과 전 고정)
# 기준선 v40 = 3승 0무 12패 / -9.438   A(완전제거) = 6승 3무 6패 / +0.928
# 통과선 승 >= 7/15 (A와 동일). 목적: 방어 안전망을 남긴 채 A의 이득을 얼마나 가져오는가.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./Rule_evade8.xml"
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
for OPP in AIP_jh2.dll ACE; do
  echo "########## A3 / OBFM_RED / ${OPP} ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) "$OPP" 2>&1       | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|EVADE_DIAG)"       || echo "  !! seed $k 비정상"
  done
  echo ""
done
echo "=== A3 완료 ==="
