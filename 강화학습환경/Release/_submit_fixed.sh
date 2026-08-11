#!/bin/bash
# ★ 교정본 재검증: AIP_final.dll + 교정 Rule_forTraining.xml(MinAlt=1000)이
#   채택본 AIP_v40.dll + Rule_v40.xml과 **시드별로 일치**해야 한다.
#   교정 전에는 3승12패 vs 12승1무2패로 11시드가 갈렸다.
# ★ 성적이 비슷한 정도로는 부족하다. 같은 소스 빌드 + 같은 XML이므로 시드별 완전일치가 기대값이다.
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
echo "=== 교정본 재검증 완료 ==="
