#!/bin/bash
# 대회조건 cold 15시드 — 주 기준선. 사전등록: experiments/match_conditions/PREREG_2026-08-11.md
#
# cold = 시드마다 **새 프로세스**. BT/제어기 상태가 판을 넘어 이어지지 않는다.
# (warm/cold 차이 실측: v40 vs jh2가 11승 vs 8승, 0/14 시드 불일치)
#
# ★ ownship DLL을 TOPGUN_OWN_DLL로 직접 지정한다 -> AIP_DCS_ownship.dll을 안 건드리므로
#   두 배치를 동시에 돌려도 서로 간섭하지 않는다.
# ★ 단, Rule_mine.xml은 공유 자원이다(kwon/junghwan이 같은 이름을 읽는다).
#   그 둘을 쓰는 배치는 **하나만** 돌린다.
#
# 사용: _match_cold.sh <로그접두> <상대...>
#   버전은 아래 VERSIONS 배열로 순회한다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_MATCH=1
unset TOPGUN_ABLATE TOPGUN_RULE          # v40은 기본 동작이라 게이트가 필요 없다

run_version () {   # $1=라벨 $2=DLL $3.. =상대
  local LAB="$1"; local DLL="$2"; shift 2
  export TOPGUN_OWN_DLL="$DLL"
  for OPP in "$@"; do
    case "$OPP" in
      AIP_kwon.dll)     cp -f Rule_mine_kwon.xml     Rule_mine.xml ;;
      AIP_junghwan.dll) cp -f Rule_mine_junghwan.xml Rule_mine.xml ;;
    esac
    echo "########## ${LAB} vs ${OPP} ##########"
    for k in $(seq 0 14); do
      "$PY" rehearsal_10hz.py 6 6 200 1 "$k" "$OPP" 2>&1 \
        | grep -aE "^\[match|^\[seed|Node not recognized" \
        || echo "  !! seed $k 비정상"
    done
    echo ""
  done
}

run_version v32 AIP_v32.dll "$@"
run_version v40 AIP_v40.dll "$@"
echo "=== cold 완료 ==="
