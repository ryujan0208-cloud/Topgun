#!/bin/bash
# PC 다운으로 중단된 v33 검증 재개 + v33b(CAP=40) 검증.
# v33은 ACE에서 이미 기각(2승11무2패). 남은 질문은 원 계열에서 lag가 약인가(행동강령 4:
# 특정 상황용 BT도 좋음)이므로 onecircle만 마저 본다.
# v33b는 사전 고정 대안이므로 ACE부터 = 기각/채택이 여기서 갈린다.
cd "$(dirname "$0")"
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"
trap 'cp -f AIP_v32.dll AIP_DCS_ownship.dll; echo "[trap] ownship을 현역 v32로 복구"' EXIT

run() {  # run <버전> <상대>
  cp -f "AIP_$1.dll" AIP_DCS_ownship.dll
  echo "########## $1 vs $2 ##########"
  "$PY" rehearsal_10hz.py 6 6 200 15 0 "$2" 2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)" || echo "  !! 비정상 종료"
  echo ""
}

run v33b ACE                      # 결정적 시험
run v33b AIP_onecircle.dll
run v33  AIP_onecircle.dll        # 원 계열에서 lag가 약인지 (v33 vs v33b 비교용)
run v33b AIP_kwon.dll
echo "=== 전체 완료 ==="
