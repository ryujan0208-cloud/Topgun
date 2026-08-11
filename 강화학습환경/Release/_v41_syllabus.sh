#!/bin/bash
# CLAUDE.md 판정원칙 5: "채택은 Syllabus + 15시드 실전 둘 다."
# A(Evade 제거)와 기준선 v40을 **같은 실행에서** 재서 드리프트를 없앤다.
# v40 아카이브 기록: PASS 1 / WEAK 7 / FAIL 4
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_ABLATE
trap 'unset TOPGUN_RULE' EXIT

echo "########## 기준선 v40 (Rule_v40.xml) ##########"
unset TOPGUN_RULE
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)"
echo ""
echo "########## A: Evade 제거 (Rule_noevade.xml) ##########"
export TOPGUN_RULE="./Rule_noevade.xml"
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)"
echo "=== Syllabus 대조 완료 ==="
