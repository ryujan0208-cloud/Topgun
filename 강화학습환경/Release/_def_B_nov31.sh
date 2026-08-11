#!/bin/bash
# [실험 B] v31 하강나선을 빼고(v29 원형) OBFM_RED(방어 시작)를 다시 돌린다.
#
# 사전등록: experiments/match_conditions/PREREG_defense_2026-08-11.md
# 가설 H-B: Task_Evade의 downMix(최대 1.80 = 정규화 87% 하강)가 우리를 249->388m/s로
#           가속시켜 코너속도를 벗어나게 만든다. 같은 파일 주석: "260m/s 27deg/s vs 420m/s 7deg/s".
# 기준선:  v40 = 3승 0무 12패 / 순이득 -9.44
# 통과선:  승 >= 7/15  (부분 5~6, 기각 <=4)
#
# ★ 빌드 없음. TOPGUN_ABLATE=v31 은 Task_Evade.cpp에 이미 배선돼 있다.
# ★ A와 절대 동시에 켜지 않는다(반쪽 수정 금지).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_ABLATE=v31
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_RULE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_ABLATE TOPGUN_OWN_DLL' EXIT

echo "########## B: v40+ablate(v31) / OBFM_RED / jh2 ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|DECO_|EVADE_DIAG)" \
    || echo "  !! seed $k 비정상"
done
echo "=== B 완료 ==="
