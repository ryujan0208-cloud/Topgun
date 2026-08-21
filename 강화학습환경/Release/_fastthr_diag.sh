#!/usr/bin/env bash
# fastthr 메커니즘 규명 — 궤적을 남겨 무엇이 달라지는지 잰다
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v48test.dll" TOPGUN_RULE="./Rule_v42.xml" PYTHONIOENCODING=utf-8
trap 'unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE TOPGUN_ABLATE' EXIT
for MODE in base fastthr; do
  if [ "$MODE" = "base" ]; then unset TOPGUN_ABLATE; else export TOPGUN_ABLATE="$MODE"; fi
  D=artifacts/ft_$MODE; rm -rf $D; mkdir -p $D
  for S in 1 34 43 4; do
    rm -f artifacts/logs/*.csv 2>/dev/null
    "$PY" rehearsal_10hz.py 6 6 200 1 $S AIP_yuno.dll >/dev/null 2>&1
    O=$(ls -t artifacts/logs/*ownship*.csv 2>/dev/null | head -1)
    T=$(ls -t artifacts/logs/*target*.csv  2>/dev/null | head -1)
    [ -n "$O" ] && cp -f "$O" $D/s${S}_own.csv && cp -f "$T" $D/s${S}_tgt.csv
  done
  echo "$MODE 수집 완료"
done
