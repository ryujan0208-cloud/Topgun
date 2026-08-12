#!/bin/bash
# [작업#9] ClimbOut 실효 하한 낮추기. 사전등록: PREREG_minalt_2026-08-12.md
# 인자: $1 = XML (Rule_m700.xml 등)
# ★ 안전 기준 최우선: ownship altitude below min 1건이면 즉시 기각.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./$1" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL; rm -f /tmp/_mb$$ /tmp/_ma$$' EXIT
ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_mb$$
for R in 1 2; do
  echo "########## $1 / 라운드$((R+1)) / OBFM_RED / jh2 ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) AIP_jh2.dll 2>&1 \
      | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_)" \
      || echo "  !! seed 비정상"
    ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_ma$$
    NEW=$(comm -13 /tmp/_mb$$ /tmp/_ma$$ | head -1); NEW=$(basename "$NEW" 2>/dev/null); NEW="${NEW%%_target_*}"
    echo "STAMP $1 라운드$((R+1)) seed$((k*3+R)) ${NEW:-없음}"
    mv -f /tmp/_ma$$ /tmp/_mb$$
  done
  echo ""
done
echo "=== $1 완료 ==="
