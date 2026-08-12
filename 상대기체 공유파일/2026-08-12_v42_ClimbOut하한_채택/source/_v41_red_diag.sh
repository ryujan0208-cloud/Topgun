#!/bin/bash
# [작업#13] v41 OBFM_RED 잔여 패배 부검. 라운드2·3(가장 나쁜 셀)에서 진단을 켜고 다시 돈다.
#   v41의 29패 중 21패가 OBFM_RED다(라운드2 11 / 라운드3 10).
#
# ★ STAMP를 반드시 남긴다. _def_A / _r23 배치가 안 남겨서 트랙 분석을 못 했다. 세 번째다.
# ★ ls -t 금지 — 동시 실행 중인 배치 파일을 집는다. 실행 전후 차집합으로 특정한다.
# ★ [ACTIVE] 진단을 남긴다(노드 구성이 승패를 갈랐던 전례).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./Rule_noevade.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL; rm -f /tmp/_b$$ /tmp/_a$$' EXIT
ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_b$$
for R in 1 2; do
  echo "########## v41 / 라운드$((R+1)) / OBFM_RED / jh2 ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) AIP_jh2.dll 2>&1 \
      | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_)" \
      || echo "  !! seed 비정상"
    ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_a$$
    NEW=$(comm -13 /tmp/_b$$ /tmp/_a$$ | head -1)
    NEW=$(basename "$NEW" 2>/dev/null); NEW="${NEW%%_target_*}"
    echo "STAMP v41 라운드$((R+1)) seed$((k*3+R)) ${NEW:-없음}"
    mv -f /tmp/_a$$ /tmp/_b$$
  done
  echo ""
done
echo "=== v41 OBFM_RED 부검 완료 ==="
