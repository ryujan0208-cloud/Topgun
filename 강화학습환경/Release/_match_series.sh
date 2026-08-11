#!/bin/bash
# 대회조건 BO3/BO5 persistent — **필수 게이트**. 사전등록: experiments/match_conditions/PREREG_2026-08-11.md
#
# 규정집 제4조: 본선 조별 라운드 3판 2승, 본선 토너먼트 5판 3선승.
# 규정집 제6조 3항 4호: **다전제에서 무승부는 해당 라운드 0점**(단판제만 0.5점).
#
# persistent = **한 프로세스에서 여러 라운드 연속**. BT/제어기 상태가 라운드를 넘어 이어진다.
#   -> cold 15시드(주 기준선)와 **다른 축**이다. 둘 다 통과해야 한다.
#
# 라운드별 초기 거리: 1라운드 2000ft / 2라운드 2500ft / 3라운드 3000ft (운영측 확답)
#   `rehearsal_10hz.py`가 시드 k를 k%3으로 라운드에 대응시키므로
#   start_seed=3*chunk 로 시작해 seeds=3(BO3) 또는 5(BO5)를 연속 실행하면
#   라운드1→2→3(→1→2) 순서가 그대로 나온다.
#
# 사용: _match_series.sh <BO3|BO5> <chunk수> <상대...>
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
MODE="${1:-BO3}"; CHUNKS="${2:-5}"; shift 2
case "$MODE" in
  BO3) N=3 ;;
  BO5) N=5 ;;
  *) echo "MODE는 BO3 또는 BO5"; exit 1 ;;
esac

export TOPGUN_MATCH=1
unset TOPGUN_ABLATE TOPGUN_RULE
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_MATCH TOPGUN_OWN_DLL' EXIT

run_version () {   # $1=라벨 $2=DLL $3..=상대
  local LAB="$1"; local DLL="$2"; shift 2
  export TOPGUN_OWN_DLL="$DLL"
  for OPP in "$@"; do
    case "$OPP" in
      AIP_kwon.dll)     cp -f Rule_mine_kwon.xml     Rule_mine.xml ;;
      AIP_junghwan.dll) cp -f Rule_mine_junghwan.xml Rule_mine.xml ;;
    esac
    for ((c=0; c<CHUNKS; c++)); do
      local S=$(( c * N ))
      echo "########## ${LAB} ${MODE} chunk${c} vs ${OPP} ##########"
      # 한 프로세스에서 N라운드 연속 (persistent)
      "$PY" rehearsal_10hz.py 6 6 200 "$N" "$S" "$OPP" 2>&1 \
        | grep -aE "^\[match|^\[seed|Node not recognized" \
        || echo "  !! chunk${c} 비정상"
      echo ""
    done
  done
}

run_version v32 AIP_v32.dll "$@"
run_version v40 AIP_v40.dll "$@"
cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "=== ${MODE} 게이트 완료 ==="
