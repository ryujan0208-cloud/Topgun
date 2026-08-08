#!/bin/bash
# 제출 바이너리 검증 — AIP_final.dll이 정말 v32인가.
#
# [왜] AIP_final.dll과 AIP_v32.dll은 크기(454,144)와 시각(8/5 20:14)이 같은데 해시가 다르다.
#   같은 소스를 따로 빌드한 것으로 보이지만 **그건 추정**이고 제출물에 추정을 쓸 수 없다.
#   전례: AIP_final.dll이 v27인 채로 있었고 XML이 v27~v32 동일해서 안 보였다.
#   해시가 다르면 동작으로 증명해야 한다(절제 대조군과 같은 방법).
#
# AIP_final.dll은 ./Rule_forTraining.xml 을 읽는다(Rule_v32.xml과 내용 동일 확인됨).
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
unset TOPGUN_ABLATE

trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship -> v32"' EXIT

for OPP in AIP_v7.dll STRAIGHT; do
  for WHICH in v32 final; do
    cp -f "AIP_${WHICH}.dll" AIP_DCS_ownship.dll
    echo "########## ${WHICH} vs ${OPP} ##########"
    "$PY" rehearsal_10hz.py 6 6 200 15 0 "$OPP" 2>&1 \
      | grep -avE "^\[(ACTIVE|EVADE_DIAG|DECO_|SYNC|PURE_ATA|ROOT|SelectTarget|DIST|ONECIRCLE|CLAMP_DIAG|DUTY|THR|BFM|WEZ|Lead|Pure|Lag)" \
      || echo "  !! 비정상 종료"
    echo ""
  done
done
echo "=== 제출본 검증 완료 ==="
