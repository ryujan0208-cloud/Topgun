#!/bin/bash
# CLAUDE.md 판정원칙 5: "채택은 Syllabus + 15시드 실전 둘 다."
# A(Evade 제거)와 기준선 v40을 **같은 실행에서** 재서 드리프트를 없앤다.
# v40 아카이브 기록: PASS 1 / WEAK 7 / FAIL 4  (6시나리오 x 2상대 = 12셀)
#
# ★★ 2026-08-11 1차 실행 실패 — CLAUDE.md에 적힌 함정에 그대로 걸렸다.
#   Syllabus 기본 상대가 v7,kwon인데 직전 legacy 배치의 trap이 Rule_mine.xml을
#   junghwan판으로 되돌려 놔서 kwon이 초기화 실패했다:
#     "Node not recognized: DECO_TargetLOSCheck" -> OSError 0xe06d7363 -> 파이썬 사망
#   그 실행의 "PASS 0 / WEAK 1 / FAIL 0"은 측정값이 아니라 **죽은 결과**였다.
#   AIP_v7.dll은 ./Rule_v7.xml, AIP_kwon.dll은 ./Rule_mine.xml을 읽는다(실측).
#   -> kwon판을 깔아두면 전 구간 정상.
# ★ 실행 후 셀 수를 세어 12셀이 나왔는지 확인한다. 안 나오면 죽은 것이다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_ABLATE
trap 'cp -f Rule_mine_junghwan.xml Rule_mine.xml; unset TOPGUN_RULE' EXIT

cp -f Rule_mine_kwon.xml Rule_mine.xml
grep -q "DECO_TargetLOSCheck" Rule_mine.xml && { echo "!! Rule_mine.xml이 여전히 junghwan판이다. 중단"; exit 1; }
echo "[준비] Rule_mine.xml = kwon판 (DECO_TargetLOSCheck 없음) 확인"
echo ""

FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'

echo "########## 기준선 v40 (Rule_v40.xml) ##########"
unset TOPGUN_RULE
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "$FILT"
echo ""
echo "########## A: Evade 제거 (Rule_noevade.xml) ##########"
export TOPGUN_RULE="./Rule_noevade.xml"
"$PY" bfm_syllabus.py --own AIP_v40.dll 2>&1 | grep -avE "$FILT"
echo "=== Syllabus 대조 완료 ==="
