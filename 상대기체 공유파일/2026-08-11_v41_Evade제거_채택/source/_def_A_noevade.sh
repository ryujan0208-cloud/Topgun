#!/bin/bash
# [실험 A] Evade 분기를 통째로 제거하고 OBFM_RED(방어 시작)를 다시 돌린다.
#
# 사전등록: experiments/match_conditions/PREREG_defense_2026-08-11.md
# 가설 H-A: 근거리 6시 위협에는 이탈(Evade)보다 선회진입(LeadPredict)이 낫다.
# 기준선:  v40 = 3승 0무 12패 / 순이득 -9.44
# 통과선:  승 >= 7/15  (부분 5~6, 기각 <=4)
#
# ★ 빌드 없음. Rule_noevade.xml = Rule_v40.xml에서 Evade Sequence만 삭제한 것.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_RULE="./Rule_noevade.xml"
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_RULE TOPGUN_OWN_DLL' EXIT

echo "########## A: v40+noevade / OBFM_RED / jh2 ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_|EVADE_DIAG)" \
    || echo "  !! seed $k 비정상"
done
echo "=== A 완료 ==="
