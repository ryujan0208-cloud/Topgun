#!/bin/bash
# [실험 C — 대조군] 미러 매치로 **방어측 천장**을 잰다.
#
# 사전등록: experiments/match_conditions/PREREG_defense_2026-08-11.md
# 같은 기체끼리 붙이면 기량이 상쇄되므로 **공격측 승률 = 기하의 순수 이득**이다.
#   미러에서 공격측 15/15 -> 이 기하는 결정적. 우리 3승은 par 이상. 투자 중단.
#   미러에서 공격측 8~10/15 -> 방어 여지가 5~7승 남아 있다. 계속 판다.
#
# ★ ct.cdll.LoadLibrary는 같은 경로를 dedupe해 한 모듈을 공유한다.
#   따라서 ownship은 **이름을 바꾼 사본**이어야 한다. jh2는 XML 경로가 DLL에 박혀 있어
#   사본도 ./Rule_junghwan_cf49f0e.xml을 읽는다(읽기 전용이라 공유 무해).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

cp -f AIP_jh2.dll AIP_jh2_mirror.dll
export TOPGUN_MATCH=1 TOPGUN_GEOM=OBFM_RED
export TOPGUN_OWN_DLL="AIP_jh2_mirror.dll"
unset TOPGUN_ABLATE TOPGUN_RULE
trap 'unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_OWN_DLL' EXIT

echo "########## C: jh2(방어) vs jh2(공격) / OBFM_RED ##########"
for k in $(seq 0 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) AIP_jh2.dll 2>&1 \
    | grep -avE "^\[(PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag|ACTIVE|DECO_|EVADE_DIAG)" \
    || echo "  !! seed $k 비정상"
done
echo "=== C 완료 ==="
