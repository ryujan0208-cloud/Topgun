#!/bin/bash
# [A 비퇴행 - legacy 10상대] 사전등록의 세 번째 관문.
#   "legacy 10상대 15시드 순이득이 v40 +68.14 대비 -5 이내"
#
# 기준선 v40 (2026-08-09 채택 검증): 10상대 150판 102승 42무 6패 / 순이득 +68.14
# 방법론을 기준선과 맞춘다: legacy 조건(TOPGUN_MATCH 미설정 = 5km/7000m),
#   `rehearsal_10hz.py 6 6 200 15 0 <상대>` = 한 프로세스 15시드(warm).
#
# ★★ kwon과 junghwan은 같은 사람(권정환)의 기체이고 **둘 다 ./Rule_mine.xml을 읽는다.**
#   한 배치에 그냥 넣으면 뒤엣것이 앞엣것 XML을 덮어써 초기화 실패로 죽는다.
#   (2026-08-06에 실제로 당했고 이틀간 못 봤다) -> 상대마다 XML을 갈아끼운다.
# ★ 상대 DLL 초기화 실패 시 파이썬이 죽는다. SUMMARY 개수로 10구간을 반드시 확인할 것.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"

export TOPGUN_RULE="./Rule_noevade.xml"
export TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE TOPGUN_MATCH TOPGUN_GEOM
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_RULE TOPGUN_OWN_DLL' EXIT

FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'

for OPP in ACE AIP_onecircle.dll AIP_sync.dll AIP_jink.dll AIP_v7.dll SEARCH STRAIGHT AIP_jh2.dll; do
  echo "########## A_noevade vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "$FILT" || echo "  !! ${OPP} 비정상"
  echo ""
done

# 권정환 기체 2종 — XML을 갈아끼우고 따로 돈다
cp -f Rule_mine_kwon.xml Rule_mine.xml
echo "########## A_noevade vs AIP_kwon.dll ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_kwon.dll 2>&1 | grep -avE "$FILT" || echo "  !! kwon 비정상"
echo ""

cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "########## A_noevade vs AIP_junghwan.dll ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_junghwan.dll 2>&1 | grep -avE "$FILT" || echo "  !! junghwan 비정상"
echo ""

echo "=== A legacy 10상대 완료 ==="
