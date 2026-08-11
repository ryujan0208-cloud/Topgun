#!/bin/bash
# S1 축소판 — "방어로 시작하면 무너지는가"만 먼저 답한다.
# 사전등록: experiments/match_conditions/PREREG_2026-08-11_rev2.md (커밋 aa09cce)
#
# 규모: 3기하 x 15시드 x 2상대 x 2버전 = 180판 (~1.4h)
#   상대는 jh2(최강)와 ACE(3D 공세)만. 시드는 규칙대로 셀당 15개를 채운다.
#   거리는 예선 조건인 **N2000 고정**(예선은 단판제).
#
# ★ 예측(사전등록에 기록): OBFM_RED에서 v32·v40 둘 다 크게 나쁠 것.
#   우리 트리엔 방어 분기가 Evade 하나뿐이고, dead-six 300~500m 탈출 능력이 없다는 게
#   legacy 부검에서 이미 나왔다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1
unset TOPGUN_ABLATE TOPGUN_RULE
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_OWN_DLL' EXIT

for GEOM in HABFM OBFM_BLUE OBFM_RED; do
  export TOPGUN_GEOM="$GEOM"
  for V in v32 v40; do
    export TOPGUN_OWN_DLL="AIP_${V}.dll"
    for OPP in AIP_jh2.dll ACE; do
      echo "########## ${V}_${GEOM} vs ${OPP} ##########"
      for k in $(seq 0 14); do
        # 예선 조건: N2000 고정. 시드 k는 3의 배수로 줘서 항상 round1(2000ft)이 되게 한다.
        "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3)) "$OPP" 2>&1 \
          | grep -aE "^\[match|^\[seed|Node not recognized" \
          || echo "  !! seed $k 비정상"
      done
      echo ""
    done
  done
done
echo "=== S1 probe 완료 ==="
