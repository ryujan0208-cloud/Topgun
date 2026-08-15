#!/usr/bin/env bash
# ★★★ 채점 규칙 결정 실험 (2026-08-15)
#
# [배경] 우리는 2026-08-06(eeecad5)에 로컬 시뮬을 P1단일 -> 3-phase로 고쳤고
#   v33~v42 판정이 전부 그 위에서 이뤄졌다. 메모리엔 "득점의 99%가 P2/P3"라고 적혀 있다.
#   팀원(jung)이 실서버 4판(08-13)으로 "실서버는 Phase 2/3를 주지 않는다"고 보고했다.
#   사실이면 우리 기체는 존재하지 않는 점수를 향해 튜닝된 것이다.
#
# [설계] 같은 기체·같은 시드로 두 채점을 돌려 비교한다.
#   A: 3-phase (현행 기본)
#   B: P1 단독 (|ATA|<=1.0도, 152.4~914.4m) = 대회 원본 시뮬 = jung 주장
#
# ★ 판정 기준 — 결과를 보기 전에 고정한다 (CLAUDE.md 판정원칙 4)
#   K1. 시드별 승/무/패가 두 채점 사이에서 뒤집히는 판 수. 0이면 채점은 순위에 무관하다.
#   K2. P1에서의 총 준 데미지 / 3-phase에서의 총 준 데미지.
#       메모리 주장이 맞으면 ~1% 가 나와야 한다. 50%를 넘으면 그 주장은 틀린 것이다.
#   K3. P1에서의 무승부 비율. 0.7을 넘으면 "아무도 득점 못 하는 상태"가 실재하는 것이고
#       사용자가 말한 "업그레이드해도 서로 무승부"의 직접 원인으로 지목할 수 있다.
#   ※ K1/K2/K3 중 어느 것도 "v42가 더 좋다/나쁘다"를 판정하지 않는다. 이 실험은
#     기체 채택 실험이 아니라 **자(측정도구)를 고르는 실험**이다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"

MODE="${1:?사용법: _wez_decisive.sh <3phase|p1>}"

# ★ 2026-08-15에 당한 것: 죽은 줄 알았던 배치가 살아 있는데 같은 파일에 또 돌려
#   같은 시드가 두 번 기록됐다. 집계가 조용히 두 배가 된다(로그를 안 봤으면 못 잡는다).
#   락 파일로 같은 MODE가 두 벌 돌지 못하게 막는다.
LOCK="_wez_${MODE}.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 ${MODE} 배치가 돌고 있다 (PID $(cat "$LOCK")). 중복 실행을 막았다." >&2
  exit 3
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT
case "$MODE" in
  3phase) unset TOPGUN_WEZ 2>/dev/null || true ;;
  p1)     export TOPGUN_WEZ=p1 ;;
  *) echo "MODE는 3phase 또는 p1"; exit 2 ;;
esac

# 검증된 v42 조합 (_dist_verify.sh와 동일)
export TOPGUN_MATCH=1
export TOPGUN_OWN_DLL="AIP_v40.dll"
export TOPGUN_RULE="./Rule_v42.xml"
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_WEZ' EXIT

SEEDS=15
# 셋 다 고유 XML을 읽으므로 한 배치에 넣어도 충돌하지 않는다(실측 확인).
#   jung -> ./Rule_jung.xml   yuno -> ./Rule_yuno.xml   jh2 -> ./Rule_junghwan_cf49f0e.xml
for OPP in AIP_jung.dll AIP_yuno.dll AIP_jh2.dll; do
  echo "########## ${MODE} :: ${OPP} ##########"
  for k in $(seq 0 $((SEEDS-1))); do
    # 상대 진단 출력이 매우 많다(jung은 틱마다 4줄). 요약 줄만 남긴다.
    # ★ stderr는 버리지 않는다 — import 실패/초기화 실패를 놓치지 않기 위해
    #   '실패/Error/Traceback'은 통과시킨다.
    "$PY" rehearsal_10hz.py 6 6 200 1 $((k*3+1)) "$OPP" 2>&1 \
      | grep -E "\[seed |SUMMARY|Error|error|Traceback|failed|Failed|실패|WEZ\]|Initialized"
  done
done
echo "########## DONE ${MODE} ##########"
