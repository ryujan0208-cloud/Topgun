# -*- coding: utf-8 -*-
"""BT가 계산하는 상대 선회각속도(omega)가 실제와 맞는지 검증한다.

[의심의 근거 — 코드]
  Task_LeadPredict:  const int HIST = 12;                       // 12 "BT 틱"
                     omegaNow = angleBetween(fwdOld, TgtFwd) / (HIST * dt);
  CPPBlackBoard:     DeltaSecond = 0.0166666;                   // 1/60, 생성자 값
  LibMain:           SetBehaviorTreeDeltaTime()은 DLL이 노출하지만
                     파이썬 하네스가 **호출하지 않는다**(선언한 함수 6개에 없음).

  제출 조건은 ACTION_REPEAT=6 = BT 10Hz다. RepeatProvider가 "6회 중 1회만 BT 호출"
  하므로 이력 버퍼는 0.1초 간격으로 채워진다. 12틱 = **1.2초** 창인데
  나눗셈에는 12 x (1/60) = **0.2초**를 쓴다.  -> omega가 6배 부풀려진다는 의심.

[검증 방법]
  코드만 읽고 결론 내지 않는다. `[ACTIVE]` 진단이 찍는 om= 값의 분포와,
  같은 판의 트랙 CSV에서 직접 계산한 실제 선회율 분포를 비교한다.
  om ≈ 6 x (1.2초 창 실측) 이면 의심이 확정된다.

사용: python tools_diag/omega_check.py <stamp> <ACTIVE로그>
"""
import csv
import math
import os
import re
import statistics as st
import sys

R = r"C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs"
MLAT = 111320.0
OM = re.compile(r"om=([\d.eE+-]+)")


def load_fwd(stamp):
    """트랙에서 상대의 진행방향 단위벡터 시계열을 만든다. (t, fwd)"""
    p = os.path.join(R, f"{stamp}_target_(F-16)[Red].csv")
    rows = []
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((float(r["Time"]), float(r["Longitude"]),
                         float(r["Latitude"]), float(r["Altitude"])))
    out = []
    for i in range(1, len(rows)):
        t0, t1 = rows[i - 1], rows[i]
        dt = t1[0] - t0[0]
        if dt <= 0:
            continue
        c = math.cos(math.radians(t0[2]))
        dx = (t1[1] - t0[1]) * c * MLAT
        dy = (t1[2] - t0[2]) * MLAT
        dz = t1[3] - t0[3]
        n = math.sqrt(dx * dx + dy * dy + dz * dz)
        if n < 1e-6 or n / dt > 700.0:      # 판 경계(위치 순간이동) 제외
            continue
        out.append((t1[0], (dx / n, dy / n, dz / n)))
    return out


def turn_rate(fwd, window_s):
    """window_s 초 창에서의 실제 선회 각속도(rad/s) 목록."""
    if len(fwd) < 2:
        return []
    step = fwd[1][0] - fwd[0][0]
    k = max(1, int(round(window_s / step)))
    out = []
    for i in range(k, len(fwd)):
        t0, a = fwd[i - k]
        t1, b = fwd[i]
        gap = t1 - t0
        if gap <= 0 or abs(gap - window_s) > window_s * 0.5:
            continue                        # 판 경계를 걸친 구간
        d = max(-1.0, min(1.0, a[0]*b[0] + a[1]*b[1] + a[2]*b[2]))
        out.append(math.acos(d) / gap)
    return out


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 3:
        print(__doc__)
        return
    stamp, active_log = sys.argv[1], sys.argv[2]

    oms = []
    with open(active_log, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            # ★ 우리 기체는 [RED]로 찍힌다. DLL 내부 Team enum이 시뮬의 Blue/Red와 반대다.
            #   (상대 DLL 없는 STRAIGHT 실행에서도 [RED]가 나오는 것으로 확인)
            if "[ACTIVE]" not in line or "[RED]" not in line:
                continue
            m = OM.search(line)
            if m:
                try:
                    v = float(m.group(1))
                except ValueError:
                    continue
                if v > 0:
                    oms.append(v)

    fwd = load_fwd(stamp)
    if not fwd:
        print("트랙을 못 읽었다:", stamp)
        return
    tick = fwd[1][0] - fwd[0][0]
    print(f"트랙 {stamp}  샘플 {len(fwd)}  간격 {tick*1000:.1f}ms")
    print(f"[ACTIVE] om= 샘플 {len(oms)}")
    if not oms:
        print("om= 값이 없다. 배치에서 [ACTIVE]를 필터로 버렸는지 확인할 것.")
        return

    om_med = st.median(oms)
    print()
    print(f"{'창':<14}{'실측 중앙 rad/s':>16}{'deg/s':>10}{'om/실측':>10}")
    print("-" * 52)
    for w in (0.2, 0.6, 1.2, 2.0):
        tr = turn_rate(fwd, w)
        if not tr:
            continue
        med = st.median(tr)
        ratio = om_med / med if med > 1e-9 else float("nan")
        mark = "  <-- 코드가 나누는 창" if abs(w - 0.2) < 1e-9 else ""
        mark += "  <-- 10Hz 실제 창" if abs(w - 1.2) < 1e-9 else ""
        print(f"{w:>5.1f}초{'':<8}{med:>16.5f}{med*57.2958:>10.2f}{ratio:>10.2f}{mark}")

    print()
    print(f"BT가 쓰는 om 중앙값 = {om_med:.5f} rad/s ({om_med*57.2958:.2f} deg/s)")
    print()
    print("판정 기준: 1.2초 창 실측의 약 6배면 dt 버그가 확정된다.")
    print("           0.2초 창 실측과 비슷하면 버그가 아니다(창이 실제로 0.2초).")


if __name__ == "__main__":
    main()
