#!/usr/bin/env bash
# 무승부 기하 스캔 — 상대별로 "왜 득점이 안 되는가"를 시드마다 잰다.
# [검증됨] tools_diag/draw_geometry.py 는 seed43 vs yuno 에서 상대 득점틱 21을 잡아
#   실제 taken=0.1868 과 일치했다(우리 득점틱 0 = dealt 0.0000). 도구는 신뢰할 수 있다.
set -u
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
cd "$(dirname "$0")"
OPP="${1:?사용법: _geom_scan.sh <상대DLL> [시드수]}"
N="${2:-15}"

LOCK="_geom_$(basename "$OPP" .dll).lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "★ 이미 돌고 있다 (PID $(cat "$LOCK"))" >&2; exit 3
fi
echo $$ > "$LOCK"

export TOPGUN_MATCH=1 TOPGUN_OWN_DLL="AIP_v40.dll" TOPGUN_RULE="./Rule_v42.xml"
export PYTHONIOENCODING=utf-8
trap 'rm -f "$LOCK"; unset TOPGUN_MATCH TOPGUN_OWN_DLL TOPGUN_RULE' EXIT

D="artifacts/geom_$(basename "$OPP" .dll)"
rm -rf "$D"; mkdir -p "$D"

for k in $(seq 0 $((N-1))); do
  S=$((k*3+1))
  rm -f artifacts/logs/*.csv artifacts/logs/*_summary.json 2>/dev/null
  RES=$("$PY" rehearsal_10hz.py 6 6 200 1 "$S" "$OPP" 2>&1 | grep -aE "^\[seed|^SUMMARY" | tr '\n' ' ')
  OWN=$(ls -t artifacts/logs/*ownship*.csv 2>/dev/null | head -1)
  TGT=$(ls -t artifacts/logs/*target*.csv  2>/dev/null | head -1)
  echo "===== seed $S ====="
  echo "  $RES"
  if [ -n "$OWN" ] && [ -n "$TGT" ]; then
    cp -f "$OWN" "$D/s${S}_own.csv"; cp -f "$TGT" "$D/s${S}_tgt.csv"
    "$PY" tools_diag/draw_geometry.py "$OWN" "$TGT" --cone 1.0 --quiet 2>&1
  else
    echo "  ★ CSV 없음"
  fi
done
echo "===== DONE $OPP ====="
