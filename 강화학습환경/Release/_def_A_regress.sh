#!/bin/bash
# [실험 A 비퇴행 관문] Evade 제거가 다른 두 기하에서 퇴행을 부르는지 본다.
#
# 사전등록: experiments/match_conditions/PREREG_defense_2026-08-11.md
#   "A가 통과해도 그것만으로 채택하지 않는다. HABFM/OBFM_BLUE에서 패가 늘지 않을 것."
#
# 기준선 (v40, 상대 2종 x 15시드 = 30판씩):
#   HABFM      28승 0무  0패 / +13.60
#   OBFM_BLUE  25승 0무  5패 /  +7.71
# A의 OBFM_RED 결과: 6승 3무 6패 / +0.928  (기준선 3승 0무 12패 / -9.438)
#
# ★ 미리 적어둔 예측: Evade는 v15에서 "일방 격추" 때문에 도입된 유일한 방어다.
#   빼면 공세 기하에서도 역전당할 때 되돌아올 것으로 본다. 즉 패가 늘 것이다.
#   빗나가면 그대로 기록한다.
#
# ★ STAMP를 남긴다 — S1 배치가 안 남겨서 다른 기하의 거리 분포를 못 봤다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1
export TOPGUN_RULE="./Rule_noevade.xml"
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL; rm -f /tmp/_before_$$ /tmp/_after_$$' EXIT

ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_before_$$

for G in HABFM OBFM_BLUE; do
  export TOPGUN_GEOM=$G
  for OPP in AIP_jh2.dll ACE; do
    echo "########## A_noevade / ${G} / ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) "$OPP" 2>&1 \
        | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|EVADE_DIAG)" \
        || echo "  !! seed $k 비정상"
      # ★ ls -t 금지: 다른 배치가 동시에 트랙을 쓰면 그쪽 파일을 집는다(실제로 당함).
      #   실행 전후 목록의 차집합으로 이 판이 만든 파일만 특정한다.
      ls artifacts/logs/*_target_*.csv 2>/dev/null | sort > /tmp/_after_$$
      NEW=$(comm -13 /tmp/_before_$$ /tmp/_after_$$ | head -1)
      NEW=$(basename "$NEW" 2>/dev/null); NEW="${NEW%%_target_*}"
      echo "STAMP A ${G} ${OPP} seed$((k*3)) ${NEW:-없음}"
      mv -f /tmp/_after_$$ /tmp/_before_$$
    done
    echo ""
  done
done
echo "=== A 비퇴행 완료 ==="
