#!/bin/bash
# 스파링 세트 정화 효과 측정. 현역 v32 고정, 상대만 정화 전/후.
# 정화 전 DLL은 git에서 꺼내 쓴다(재빌드본이 덮어썼으므로).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
mkdir -p _old
for D in AIP_onecircle AIP_sync AIP_synccircle AIP_shrink; do
  git show "HEAD:강화학습환경/Release/${D}.dll" > "_old/${D}.dll" 2>/dev/null
done
for D in AIP_onecircle AIP_sync AIP_synccircle AIP_shrink; do
  for W in old new; do
    if [ "$W" = "old" ]; then cp -f "_old/${D}.dll" "${D}_t.dll"; else cp -f "${D}.dll" "${D}_t.dll"; fi
    echo "########## ${W} vs ${D} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "${D}_t.dll" 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC)" || echo "  !! 비정상 종료"
    echo ""
  done
  rm -f "${D}_t.dll"
done
echo "=== 완료 ==="
