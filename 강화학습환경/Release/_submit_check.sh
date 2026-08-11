#!/bin/bash
# ★ 제출본 검증: AIP_final.dll + Rule_forTraining.xml(MinAlt=1800)이
#   채택본 AIP_v40.dll + Rule_v40.xml(MinAlt=1000)과 **다른 기체인지** 동작으로 증명한다.
#   정적 분석: 두 DLL은 86바이트만 다르고 전부 타임스탬프/XML경로/밀린 상대주소 = 같은 소스 빌드.
#   XML만 다르다. 실측상 30판 중 27판이 1800m 아래로 내려가므로 차이가 나야 한다.
# ★ TOPGUN_RULE을 반드시 unset — 켜져 있으면 각 DLL의 기본 XML을 안 읽는다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_ABLATE TOPGUN_RULE TOPGUN_MATCH TOPGUN_GEOM
trap 'unset TOPGUN_OWN_DLL' EXIT
FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'
for OPP in AIP_jh2.dll ACE; do
  for D in AIP_final.dll AIP_v40.dll; do
    export TOPGUN_OWN_DLL="$D"
    echo "########## ${D} vs ${OPP} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "$FILT" || echo "  !! 비정상"
    echo ""
  done
done
echo "=== 제출본 대조 완료 ==="
