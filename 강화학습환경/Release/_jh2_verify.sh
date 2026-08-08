#!/bin/bash
# 신형 도전자(팀원 cf49f0e) 독립 검증.
#
# [배경] 코덱스 CV09가 v32 vs 이 기체를 **4승 0무 11패**로 측정했다.
#   패배 11판이 전부 "ownship destroyed" — 점수패가 아니라 격추다.
#   우리 기준선의 AIP_junghwan.dll(8/6 빌드)은 15승 0패라, 기준선이 실제 수준을 과대평가한다.
#
# [검증] 코덱스 결과를 그대로 받지 않고 **우리 표준 절차로 재현**한다.
#   DLL/XML 해시는 코덱스 기록과 일치 확인함(15C03F17... / 5CFAFCFD...).
#   XML 이름이 고유해서(Rule_junghwan_cf49f0e.xml) Rule_mine.xml 충돌은 없다.
#
# 함께: 8/6판 junghwan도 다시 돌려 두 세대를 같은 조건에서 비교한다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_ABLATE

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; cp -f Rule_mine_junghwan.xml Rule_mine.xml' EXIT
cp -f AIP_v32.dll AIP_DCS_ownship.dll
cp -f Rule_mine_junghwan.xml Rule_mine.xml

for OPP in AIP_jh2.dll AIP_junghwan.dll; do
  echo "########## v32 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
    | grep -avE "^\[(EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|THR|BFM|WEZ|Lead|Pure|Lag)" \
    || echo "  !! 비정상 종료"
  echo ""
done
echo "=== 도전자 검증 완료 ==="
