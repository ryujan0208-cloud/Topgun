#!/bin/bash
# 프로세스 생명주기가 결과를 바꾸는가 — 우리 트리에서 직접 확인.
#
# [코덱스 CV17 vs CV19] 같은 시드(15~29)·같은 DLL인데 생명주기만 바꾸자:
#     kwon   ordered(1프로세스 15연전)  lowfloor 13승 / final_v40 12승
#            cold(경기별 새 프로세스)   lowfloor 11승 / final_v40 12승
#   -> baseline 승수가 2 바뀌고 순위가 뒤집힌다.
#   원인: `BTActionProvider.reset()`이 no-op이라 native BT 상태가 판을 넘어 이어진다.
#
# [왜 중요한가] 우리 표준 배치(`rehearsal_10hz.py ... 15 0 <상대>`)는 **warm**이다.
#   대회가 경기마다 프로세스를 새로 띄운다면 우리 측정 전체에 상태 오염이 섞여 있다.
#   v40 채택 근거(jh2 12승 2패)가 warm 산물인지 확인해야 한다.
#
# ⚠ seed 0은 비교에서 뺀다. `rehearsal_10hz.py`는 `seeds>1 || start_seed>0`일 때만
#   랜덤 스폰을 켠다. cold에서 seeds=1,start_seed=0이면 **고정 스폰**이 되어
#   warm의 seed 0과 다른 판이 된다. 시드 1~14만 비교한다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
OPP="${1:-AIP_jh2.dll}"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT
cp -f AIP_v40.dll AIP_DCS_ownship.dll
unset TOPGUN_ABLATE TOPGUN_RULE

echo "########## WARM v40 vs ${OPP} ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
  | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
  || echo "  !! 비정상"
echo ""

echo "########## COLD v40 vs ${OPP} ##########"
for k in $(seq 1 14); do
  "$PY" rehearsal_10hz.py 6 6 200 1 "$k" "$OPP" 2>&1 \
    | grep -aE "^\[seed" \
    || echo "  !! seed $k 비정상"
done
echo ""
echo "=== 생명주기 확인 완료 ==="
