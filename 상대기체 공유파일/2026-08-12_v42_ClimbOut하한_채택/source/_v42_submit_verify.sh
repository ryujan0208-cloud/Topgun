#!/bin/bash
# ★★ v42 승격 검증 — v40에서 놓쳤던 구멍을 막는다.
#
# [v40의 사고] 채택 검증(_v40_verify.sh)이 "게이트판 vs 기본판"만 대조하고
#   **제출 빌드(AIP_final.dll + Rule_forTraining.xml)를 검증에 넣지 않았다.**
#   그래서 Rule_forTraining.xml의 MinAlt가 v32 값(1800)인 채로 이틀간 남았고,
#   제출 조합은 3승12패 / 채택본은 12승1무2패였다(같은 15시드, vs jh2).
#   -> FINDING_submission_broken_2026-08-11.md
#
# [이번 검증] **제출 빌드를 환경변수 없이 그대로 돌려** A(실험판)와 시드별 일치를 본다.
#   A는 TOPGUN_RULE=Rule_m700.xml로 쟀다. 제출본은 그 env를 못 쓴다.
#   두 경로가 같은 기체임을 증명해야 채택이다.
#
# 기대값: 시드별 완전일치. 성적이 "비슷하다"는 불충분하다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
FILT='^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)'
trap 'unset TOPGUN_OWN_DLL TOPGUN_RULE' EXIT

for OPP in AIP_jh2.dll ACE AIP_kwon.dll; do
  [ "$OPP" = "AIP_kwon.dll" ] && cp -f Rule_mine_kwon.xml Rule_mine.xml

  # (1) 실험 경로: AIP_v40.dll + TOPGUN_RULE=Rule_m700.xml  (= A를 쟀던 방식)
  unset TOPGUN_MATCH TOPGUN_GEOM TOPGUN_ABLATE
  export TOPGUN_OWN_DLL="AIP_v40.dll" TOPGUN_RULE="./Rule_m700.xml"
  echo "########## 실험경로(v40+env) vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "$FILT" || echo "  !! 비정상"
  echo ""

  # (2) 제출 경로: AIP_final.dll + Rule_forTraining.xml, **환경변수 없음**
  unset TOPGUN_RULE
  export TOPGUN_OWN_DLL="AIP_final.dll"
  echo "########## 제출경로(final, env없음) vs ${OPP} ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 | grep -avE "$FILT" || echo "  !! 비정상"
  echo ""
done
cp -f Rule_mine_junghwan.xml Rule_mine.xml
echo "=== v42 제출 검증 완료 ==="
