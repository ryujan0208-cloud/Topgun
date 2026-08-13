#!/bin/bash
# [v42 누락 관문] CLAUDE.md 판정원칙 5: "채택은 Syllabus + 15시드 실전 둘 다."
#   v42(MinAlt 700)를 Syllabus 없이 채택했다. MinAlt 사전등록에 관문 4개를 적으면서
#   이 상시 규칙을 빠뜨렸다. 뒤늦게 메운다.
#   v41 기준: PASS 1 / WEAK 6 / FAIL 5 (같은 실행에서 v40은 PASS 0 / WEAK 7 / FAIL 5)
#
# ★ Syllabus 기본 상대는 v7,kwon이다. kwon은 ./Rule_mine.xml을 읽으므로 kwon판을 깔아야
#   한다. 안 그러면 "Node not recognized: DECO_TargetLOSCheck"로 파이썬이 죽는다(실제로 당함).
# ★ 실행 후 셀 수가 24(12셀 x 2버전)인지 확인한다. 안 나오면 죽은 것이다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_ABLATE
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_RULE' EXIT

cp -f Rule_mine_kwon.xml Rule_mine.xml
if grep -q "DECO_TargetLOSCheck" Rule_mine.xml; then echo "!! Rule_mine.xml이 junghwan판이다. 중단"; exit 1; fi
echo "[준비] Rule_mine.xml = kwon판 확인"
echo ""

FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'

echo "########## 기준선 v41 (Rule_v41.xml) ##########"
export TOPGUN_RULE="./Rule_v41.xml"
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "$FILT"
echo ""
echo "########## v42 (Rule_v42.xml) ##########"
export TOPGUN_RULE="./Rule_v42.xml"
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "$FILT"
echo "=== v42 Syllabus 대조 완료 ==="
