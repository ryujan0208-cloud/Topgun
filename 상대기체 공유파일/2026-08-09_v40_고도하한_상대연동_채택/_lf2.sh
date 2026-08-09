#!/bin/bash
# lowfloor2 — "낮추되 상대보다 더 내려가지 않는다" 전체 검증.
#
# [근거] lowfloor(무조건 800)는 jh2를 4승11패 -> 11승3패로 뒤집었으나
#   kwon이 11승 -> 8승 퇴행했다. 실측으로 원인 확정:
#     kwon 최저고도 1490~1538m (kwon은 1500m 아래로 안 내려간다)
#     우리 최저 1865 -> 1160m / 중앙 5963 -> 5006m (우리만 1000m 더 내려간다)
#     준 데미지 10.99 -> 7.02 (36% 감소) = 상대 없는 고도로 내려가 있다
#   -> 고도를 내주는 건 상대를 따라갈 때만 이득이다.
#      하한 = clamp(상대고도 - 300, 800, 1500). 상대 **고도**로만 표현 = 특정상대 튜닝 아님.
#
# ★ 사전등록 채택 기준 (v32 10상대 기준선 = 101승 34무 15패 / 순이득 +51.66)
#   채택 : 승 >= 101  AND  패 <= 15  AND  순이득 >= +51.66
#          AND 어떤 상대도 승수 3 이상 하락 없음
#          AND 우리 고도이탈 패배 <= 2
#   ※ lowfloor는 승 101 / 패 7 / +65.72 였으나 **kwon -3**으로 마지막 조항에 걸렸다.
#
# ★ 예상 (결과 보기 전)
#   kwon      : 회복한다(11승 근처). 상대가 안 내려가면 우리도 안 내려간다.
#   jh2       : lowfloor만큼은 아니어도 크게 개선(8승 이상). 상대가 실제로 내려가므로 따라간다.
#   sync·SEARCH·v7 : lowfloor에서 -2였던 것이 회복될 것.
#   ACE       : 15승 유지 또는 14승.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT

# --- 대조군: 미설정이 v32와 동일한가 ---
for WHICH in v32 lf2; do
  cp -f "AIP_${WHICH}.dll" AIP_DCS_ownship.dll
  unset TOPGUN_ABLATE TOPGUN_RULE
  echo "########## ${WHICH} vs AIP_v7.dll ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_v7.dll 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done

# --- 본 시험: 10상대 ---
cp -f AIP_lf2.dll AIP_DCS_ownship.dll
export TOPGUN_ABLATE=lowfloor2
export TOPGUN_RULE=./Rule_lowfloor.xml

run_one () {   # $1=상대 $2=Rule_mine
  local OPP="$1"; local MINE="$2"
  [ -n "$MINE" ] && cp -f "$MINE" Rule_mine.xml
  echo "########## lowfloor2 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
}

run_one AIP_kwon.dll      Rule_mine_kwon.xml
run_one AIP_junghwan.dll  Rule_mine_junghwan.xml
run_one AIP_jh2.dll       ""
run_one ACE               ""
run_one AIP_onecircle.dll ""
run_one AIP_v7.dll        ""
run_one AIP_sync.dll      ""
run_one AIP_jink.dll      ""
run_one SEARCH            ""
run_one STRAIGHT          ""

cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "=== lowfloor2 완료 ==="
