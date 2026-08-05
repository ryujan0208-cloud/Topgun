#!/bin/bash
# AIP_trinity.dll은 './Rule_forTraining.xml'을 읽는데 우리가 그 파일을 우리 트리로 덮어써서
# 팀원 원본 DLL이 우리 최신 노드(DECO_ThreatAimCheck)를 만나 죽었다. 원본으로 잠시 되돌린다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f Rule_forTraining.xml Rule_forTraining_ours_backup.xml
trap 'cp -f Rule_forTraining_ours_backup.xml Rule_forTraining.xml; echo "[restore] Rule_forTraining.xml 복구됨"' EXIT
cp -f Rule_forTraining_orig.xml Rule_forTraining.xml
for V in v29 v32; do
  cp -f "AIP_${V}.dll" AIP_DCS_ownship.dll
  echo "########## ${V} vs AIP_trinity.dll ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 AIP_trinity.dll 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)" || echo "  !! 비정상 종료"
  echo ""
done
