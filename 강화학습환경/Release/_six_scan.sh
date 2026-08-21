#!/usr/bin/env bash
# 우리가 실제로 뒤를 잡히는 상대가 있나 — jh2 로그 수집 (5시드면 충분)
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_final.dll" PYTHONIOENCODING=utf-8
trap 'unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE' EXIT
unset TOPGUN_RULE 2>/dev/null || true
D=artifacts/geom_AIP_jh2; rm -rf $D; mkdir -p $D
for k in 0 1 2 3 4; do
  S=$((k*3+1))
  rm -f artifacts/logs/*.csv 2>/dev/null
  "$PY" rehearsal_10hz.py 6 6 200 1 $S AIP_jh2.dll >/dev/null 2>&1
  O=$(ls -t artifacts/logs/*ownship*.csv 2>/dev/null | head -1)
  T=$(ls -t artifacts/logs/*target*.csv  2>/dev/null | head -1)
  [ -n "$O" ] && cp -f "$O" $D/s${S}_own.csv && cp -f "$T" $D/s${S}_tgt.csv && echo "seed $S 수집"
done
echo DONE
