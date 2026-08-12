#!/bin/bash
# [M700 비퇴행 ②] legacy 10상대. 기준선 v41 = 110승 37무 3패 / +70.00. 통과선 -5 이내.
# ★★ kwon과 junghwan은 둘 다 ./Rule_mine.xml을 읽는다 -> 상대마다 갈아끼운다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
export TOPGUN_RULE="./Rule_m700.xml" TOPGUN_OWN_DLL="AIP_v40.dll"
unset TOPGUN_ABLATE TOPGUN_MATCH TOPGUN_GEOM
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_RULE TOPGUN_OWN_DLL' EXIT
FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'
for OPP in ACE AIP_onecircle.dll AIP_sync.dll AIP_jink.dll AIP_v7.dll SEARCH STRAIGHT AIP_jh2.dll; do
  echo "########## M700 vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "$FILT" || echo "  !! ${OPP} 비정상"
  echo ""
done
cp -f Rule_mine_kwon.xml Rule_mine.xml
echo "########## M700 vs AIP_kwon.dll ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_kwon.dll 2>&1 | grep -avE "$FILT" || echo "  !! kwon 비정상"
echo ""
cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "########## M700 vs AIP_junghwan.dll ##########"
"$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_junghwan.dll 2>&1 | grep -avE "$FILT" || echo "  !! junghwan 비정상"
echo ""
echo "=== M700 legacy 완료 ==="
