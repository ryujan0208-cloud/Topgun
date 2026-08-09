#!/bin/bash
# 강하 클램프 완화(`divefree`) 시험.
#
# [측정된 근거] 신형 도전자는 1000m 이상 아래로 강하하며 선회한다.
#   그 국면에서 필요 강하각 41~65도 vs 허용 30~50도 -> seed0 6/7, seed6 5/7 구간이 막힌다.
#   막히면 기수가 안 내려가고 선회율이 안 나온다(우리 8.3°/s vs 상대 14.8°/s).
#   v32의 최대 성과가 **상승 클램프 해제**였는데 강하는 안 건드렸다.
#   당시 근거 "아래로 잘림 13.5%"는 **낡은 상대 세트**에서 잰 값이다.
#
# [변경] diveSlope: dist*0.5 -> dist*3.0 (상승과 대칭), 절대 상한 650m -> 2000m.
#   안전망은 그대로: 조준점 절대 하한 1500m + 고도<1800m면 ClimbOut 최우선.
#
# ★ 예상 (결과 보기 전에 적는다)
#   jh2 상대   : 개선한다. 패 11 -> 8 이하.  (막힌 구간이 71~86%였으므로)
#   onecircle  : 개선하거나 중립. 수평선회 상대라 고도차가 작다.
#   STRAIGHT   : 중립. 고도차가 거의 없다.
#   ACE·kwon   : **모르겠다.** 깊은 다이브로 고도를 잃어 악화할 수 있다.
#   고도이탈 패배(<300m)가 늘어나면 그것만으로 기각한다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_ABLATE' EXIT

# --- 1) 대조군: 미설정이 v32와 동일한가 (통과 못 하면 이후 측정 무의미) ---
for WHICH in v32 divefix; do
  cp -f "AIP_${WHICH}.dll" AIP_DCS_ownship.dll
  echo "########## ${WHICH} vs AIP_v7.dll ##########"
  unset TOPGUN_ABLATE
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_v7.dll 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done

# --- 2) 본 시험 ---
cp -f AIP_divefix.dll AIP_DCS_ownship.dll
for OPP in AIP_jh2.dll ACE AIP_onecircle.dll STRAIGHT; do
  echo "########## divefree vs ${OPP} ##########"
  TOPGUN_ABLATE=divefree "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== divefree 완료 ==="
