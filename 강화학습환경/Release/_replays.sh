#!/bin/bash
# 우리가 만든 스파링 상대별 대표 리플레이 1판씩 (v32 기준). 고정 스폰(seeds=1) = 재현 가능.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cp -f AIP_v32.dll AIP_DCS_ownship.dll
for OPP in ACE AIP_onecircle.dll AIP_sync.dll AIP_synccircle.dll AIP_shrink.dll AIP_jink.dll AIP_kwon.dll; do
  echo "### ${OPP}"
  "$PY" rehearsal_10hz.py 6 6 200 1 0 "$OPP" 2>&1 | grep -E "^SUMMARY|ownHP"
  ls -t artifacts/logs/*_ownship_*.csv | head -1 | sed 's/.*logs\///; s/_ownship.*//' | sed "s/^/STAMP ${OPP} /"
done
