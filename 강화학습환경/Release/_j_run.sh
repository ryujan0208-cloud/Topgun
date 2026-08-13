#!/bin/bash
# [실험 J] 개전 30초 사격해 교란. 사전등록: PREREG_p1survival_2026-08-13.md
# 인자: $1 = 태그(j1/j2/j3)
# 기준선 v42: 21승 0무 9패 / +11.12, P1 받은 6.853
# 주 판정: P1 받은 HP <= 4.5   동반: 승 >= 19/30   안전: 추락 0
# ★ 자기검증 통과 확인함(env 없이 v42와 시드일치 15/15) — 기본 경로에 안 샌다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./Rule_v42.xml" TOPGUN_OWN_DLL="AIP_j.dll" TOPGUN_ABLATE="$1"
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL TOPGUN_ABLATE; rm -f /tmp/_jb$$ /tmp/_ja$$' EXIT
ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_jb$$
for R in 1 2; do
  echo "########## $1 / 라운드$((R+1)) / OBFM_RED / jh2 ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+R)) AIP_jh2.dll 2>&1 \
      | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_)" \
      || echo "  !! seed 비정상"
    ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_ja$$
    NEW=$(comm -13 /tmp/_jb$$ /tmp/_ja$$ | head -1); NEW=$(basename "$NEW" 2>/dev/null); NEW="${NEW%%_target_*}"
    echo "STAMP $1 라운드$((R+1)) seed$((k*3+R)) ${NEW:-없음}"
    mv -f /tmp/_ja$$ /tmp/_jb$$
  done
  echo ""
done
echo "=== $1 완료 ==="
