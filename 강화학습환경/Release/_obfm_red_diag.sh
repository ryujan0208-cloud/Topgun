#!/bin/bash
# OBFM_RED(방어 시작) 28패 부검용 진단 실행.
#
# ★ 2026-08-11 재실행: 이전 판은 **스폰킬 셋업**이라 무효였다(_obfm_red_diag_INVALID_spawnkill.log).
#   수정 후 OBFM_RED = 상대가 우리 뒤, 상대 기수 30도 오프셋. t=0 사격 성립 없음.
#   수정 후 성적: v40 vs jh2 3승 12패 / vs ACE 15승 0패.
#
# [질문] 상대가 한 번이라도 추월(overshoot)하는가?
#   BFM에서 방어자의 일은 상대를 추월시킨 뒤 뒤집는 것이다.
#   - 추월이 아예 없다 -> 깨끗하게 진 것. 기동으로 못 푼다(에너지/성능 문제)
#   - 추월은 나오는데 못 살린다 -> **고칠 수 있다.** 반전 로직이 없는 것
#
# ★ 진단을 필터로 버리지 않는다. [EVADE_DIAG]와 [ACTIVE]가 핵심이다.
# ★ 시드마다 새 프로세스(cold)이므로 트랙이 시드별로 따로 나온다. stamp를 직접 기록한다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
unset TOPGUN_ABLATE TOPGUN_RULE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_OWN_DLL' EXIT

for OPP in AIP_jh2.dll ACE; do
  export TOPGUN_OWN_DLL="AIP_v40.dll"
  echo "########## v40_OBFM_RED vs ${OPP} ##########"
  for k in $(seq 0 14); do
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) "$OPP" 2>&1 \
      | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_)" \
      || echo "  !! seed $k 비정상"
    NEW=$(ls -t artifacts/logs/*_target_*.csv 2>/dev/null | head -1)
    NEW=$(basename "$NEW"); NEW="${NEW%%_target_*}"
    echo "STAMP v40 ${OPP} seed$((k*3)) ${NEW}"
  done
  echo ""
done
echo "=== OBFM_RED 진단 완료 ==="
