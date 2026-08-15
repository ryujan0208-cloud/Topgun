# -*- coding: utf-8 -*-
"""GetStick 좌표변환 검사 — 불변성 시험

[원리] 상대 기하가 같으면(내 자세 동일, 나->VP 상대벡터 동일) 스틱 출력도 같아야 한다.
  절대 위치만 옮겼는데 출력이 달라지면 = 위치에 좌표변환이 걸려 있다는 뜻이다.
  대회 서버는 Cartesian 미터를 보내므로, 거기에 LLAtoCartesian을 또 걸면
  미터를 도(degree)로 읽어 좌표가 무너진다.

★★ [반드시 지킬 것] 케이스 사이에 **상태를 초기화**해야 한다.
  Controller_CY 는 이런 상태를 들고 있다.
      int SumCount;                   // 호출 횟수 누적
      float MF[20]; int FilterIndex;  // 이동평균 필터 버퍼
      std::vector<float> ErrorSum;    // LOS 오차 60샘플 순환버퍼(적분항)
  리셋 없이 두 케이스를 연속으로 재면 두 번째가 첫 번째의 오차 이력에 오염돼
  **멀쩡한 DLL도 FAIL로 나온다.**
  이 스크립트는 케이스마다 **별도 프로세스**로 돌려 원천적으로 차단한다.
  (한 프로세스에서 하려면 케이스 사이에 Reset() + CreateBehaviorTree() 를 부를 것.)

사용:
    python getstick_invariance_test.py <DLL이름>            # 두 케이스 자동 실행
    python getstick_invariance_test.py <DLL> px py pz vx vy vz   # 단일 케이스(내부용)

판정: '같음' = 변환 없음(정상) / '다름' = 변환 있음(대회 서버에서 눈이 멂)
"""
import sys, os, subprocess, ctypes as ct

HERE = os.path.dirname(os.path.abspath(__file__))


def one_case(dll, px, py, pz, vx, vy, vz):
    """단일 케이스. 반드시 자기 프로세스에서만 돌 것."""
    sys.path.insert(0, "."); sys.path.insert(0, "src")
    for k in ("TOPGUN_RULE", "TOPGUN_ABLATE", "TOPGUN_MATCH"):
        os.environ.pop(k, None)
    from dogfight.ai.native_bt import AIPilot, OPlaneData

    class CV(ct.Structure):
        _fields_ = [("RollCMD", ct.c_float), ("PitchCMD", ct.c_float),
                    ("RudderCMD", ct.c_float), ("Throttle", ct.c_float)]

    ap = AIPilot(dll)
    ap.CreateBehaviorTree(0, 1)
    lib = ap.AIPilotDLL
    lib.GetStick.restype = CV
    lib.GetStick.argtypes = [ct.POINTER(OPlaneData), ct.c_float, ct.c_float, ct.c_float]

    p = OPlaneData()
    p.LocationX, p.LocationY, p.LocationZ = px, py, pz
    p.Roll = p.Pitch = p.Yaw = 0.0
    p.Speed = 200.0
    p.Resv0, p.Resv1, p.Resv2 = 0.0, 100.0, 0.0
    r = lib.GetStick(ct.byref(p), ct.c_float(vx), ct.c_float(vy), ct.c_float(vz))
    print(f"RESULT {r.RollCMD:+.6f} {r.PitchCMD:+.6f} {r.RudderCMD:+.6f}")


def run(dll, case):
    out = subprocess.run([sys.executable, os.path.abspath(__file__), dll] + [str(x) for x in case],
                         capture_output=True, text=True, errors="replace")
    for line in out.stdout.splitlines():
        if line.startswith("RESULT "):
            return tuple(float(v) for v in line.split()[1:4])
    return None


def main():
    if len(sys.argv) == 8:                      # 단일 케이스(자식 프로세스)
        one_case(sys.argv[1], *(float(v) for v in sys.argv[2:8]))
        return
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    dll = sys.argv[1]
    REL = (1000.0, 0.0, 0.0)                    # 나 -> VP 상대벡터 (두 케이스 동일)
    A = (0.0, 0.0, 5000.0)                      # 원점 근처
    B = (25000.0, -18000.0, 5000.0)             # 25km 밖
    ca = run(dll, list(A) + [A[i] + REL[i] for i in range(3)])
    cb = run(dll, list(B) + [B[i] + REL[i] for i in range(3)])
    if ca is None or cb is None:
        sys.exit(f"{dll}: 측정 실패 (DLL/XML이 작업디렉터리에 있는지 확인)")
    same = all(abs(x - y) < 1e-4 for x, y in zip(ca, cb))
    fmt = lambda t: "(" + ", ".join(f"{v:+.6f}" for v in t) + ")"
    print(f"{dll}")
    print(f"  A 원점    {fmt(ca)}")
    print(f"  B 25km밖  {fmt(cb)}")
    print(f"  -> {'같음 = 변환 없음 (정상)' if same else '다름 = 변환 있음 (서버에서 눈이 멂)'}")


if __name__ == "__main__":
    main()
