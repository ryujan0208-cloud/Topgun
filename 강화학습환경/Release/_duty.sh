#!/bin/bash
# v34 실패 원인 규명: 이기고 있던 상대에서도 SNAPDECEL이 발동했나?
# (발동률이 높으면 트리거가 너무 넓다는 뜻 = 위협 조건 누락)
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll' EXIT
cp -f AIP_v34.dll AIP_DCS_ownship.dll
for OPP in AIP_onecircle.dll AIP_v7.dll AIP_sync.dll AIP_kwon.dll; do
  n=$("$PY" rehearsal_10hz.py 6 6 200 3 0 "$OPP" 2>&1 | grep -ac "SNAPDECEL")
  echo "${OPP} : SNAPDECEL 로그 ${n}줄  (3판, 1줄=30틱=0.5초)"
done
