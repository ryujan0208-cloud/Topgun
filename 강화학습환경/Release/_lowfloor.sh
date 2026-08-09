#!/bin/bash
# 고도 하한 완화(`lowfloor`) 시험 — 팀원이 실제로 한 변경의 우리 쪽 대응.
#
# [발견] 팀원의 8/6판 -> cf49f0e 사이 XML 차이는 **59개 노드 중 딱 두 숫자**다:
#     PreventLandCrash  FloorHard 1800 -> 800,  FloorSoft 3200 -> 1500
#   그 한 변경으로 우리 상대 전적이 0승15패 -> 11승4패로 뒤집혔다.
#
# [실측] jh2전 15판:
#     우리 최저고도  중앙 1797m / 최소 1780m   <- 매 판 1800m 벽에 정확히 걸린다
#     상대 최저고도  중앙 1013m / 최소  403m   <- 즉사고도(300m) 103m 위까지 쓴다
#   `DECO_AltitudeCheck`는 ReactiveFallback의 **첫 분기**라, 상대가 1800m 아래로 가면
#   우리 트리는 통째로 ClimbOut으로 넘어가 **추격이 중단된다.**
#
# [변경] 두 개를 **같이** 낮춘다(하나만 낮추면 divefree와 같은 반쪽 수정이 된다):
#     XML  DECO_AltitudeCheck MinAlt 1800 -> 1000   (Rule_lowfloor.xml)
#     C++  조준점 절대 하한   1500 -> 800           (TOPGUN_ABLATE=lowfloor)
#   규정 즉사 고도는 300m. 상대는 하한 800m로 403m까지 갔다(여유 103m).
#
# ★ 예상 (결과 보기 전에 적는다). v32 기준: jh2 4승0무11패 / ACE 14승1패 / onecircle 1승12무2패
#   jh2       : **개선.** 패 11 -> 8 이하. 근거는 우리가 매 판 벽에 걸린다는 실측이다.
#   ACE       : 중립 또는 소폭 악화(저고도 교전이 늘면 에너지 손해)
#   onecircle : 중립
#   STRAIGHT  : 중립
#   ⚠ **고도이탈 패배(<300m)가 3판 이상이면 다른 지표와 무관하게 기각.**
#      이건 규정상 즉시 패배라 절대 타협하지 않는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; unset TOPGUN_ABLATE TOPGUN_RULE' EXIT

# --- 1) 대조군: 미설정이 v32와 동일한가 (XML 환경변수 추가가 무동작인지도 함께 확인) ---
for WHICH in v32 lowfloor; do
  cp -f "AIP_${WHICH}.dll" AIP_DCS_ownship.dll
  echo "########## ${WHICH} vs AIP_v7.dll ##########"
  unset TOPGUN_ABLATE TOPGUN_RULE
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_v7.dll 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done

# --- 2) 본 시험 ---
cp -f AIP_lowfloor.dll AIP_DCS_ownship.dll
export TOPGUN_ABLATE=lowfloor
export TOPGUN_RULE=./Rule_lowfloor.xml
for OPP in AIP_jh2.dll ACE AIP_onecircle.dll STRAIGHT; do
  echo "########## lowfloor vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== lowfloor 완료 ==="
