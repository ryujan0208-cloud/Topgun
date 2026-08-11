#!/bin/bash
# [A 비퇴행 - 다른 공격자] OBFM_RED에서 ACE 상대. 기준선 v40 = 15승 0패.
# A가 jh2의 공격 정책에만 맞은 것인지 가리는 필수 대조다.
# 과적합 점검: 상대가 바뀌어도 유지돼야 원리적 개선이다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./Rule_noevade.xml"
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
echo "########## A_noevade / OBFM_RED / ACE ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) ACE 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|EVADE_DIAG)" \
    || echo "  !! seed $k 비정상"
done
echo "=== A×ACE 완료 ==="
