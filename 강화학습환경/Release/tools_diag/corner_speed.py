# -*- coding: utf-8 -*-
"""코너속도 실측 — 선회율이 최대가 되는 속도를 찾는다.

[왜 필요한가]
onecircle 무승부 12판의 실체는 **선회율 열세**다(우리 11.7도/s vs 상대 11.9도/s).
선회 반경 r = v/omega 이므로 속도가 곧 반경이고, 같은 평면에서 반경이 큰 쪽이 진다.
우리 BT의 코너속도 목표는 `CORNER = 260`(v23b)인데 **이 값이 실측으로 검증된 적이 없다.**
상대(255)에 맞추는 건 과적합이지만, **우리 기체의 진짜 최적점을 찾는 건 원리다.**

[방법]
수평 선회(뱅크 82도)를 여러 스로틀로 유지시키고, 정상상태에서
  - 실제 정착 속도
  - 총 각속도(yaw+pitch 전체 — yaw만 재면 과소평가한다. turn_perf.py의 전례)
를 재서 **속도 대 선회율 곡선**을 그린다. 최대점이 코너속도다.

turn_perf2.py와 같은 측정 로직을 쓰되 스로틀을 촘촘히 훑는다.

사용: python tools_diag/corner_speed.py [뱅크각=82]
"""
from __future__ import annotations
import sys, math, os
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0


def fwd_vec(yaw_deg, pitch_deg):
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    return np.array([math.sin(y)*math.cos(p), math.cos(y)*math.cos(p), math.sin(p)])


class Hold(ActionProvider):
    """지정 뱅크를 유지하며 최대로 당긴다. 스로틀만 바꿔가며 정착 속도를 만든다."""
    def __init__(self, throttle, bank_deg):
        self.thr, self.bank = throttle, bank_deg
        self.log, self._prev = [], None

    def compute_action(self, context):
        s = context.sim.get_state()
        t = float(s[StateIndex.SIM_TIME])
        lat, lon, alt = float(s[StateIndex.LAT]), float(s[StateIndex.LON]), float(s[StateIndex.ALT])
        roll, pitch, yaw = float(s[StateIndex.ROLL]), float(s[StateIndex.PITCH]), float(s[StateIndex.YAW])
        v = 0.0
        if self._prev is not None:
            dt = t - self._prev[0]
            if dt > 0:
                c = math.cos(math.radians(lat))
                dx = (lon - self._prev[2]) * c * MLAT
                dy = (lat - self._prev[1]) * MLAT
                dz = alt - self._prev[3]
                v = math.sqrt(dx*dx + dy*dy + dz*dz) / dt
        self._prev = (t, lat, lon, alt)
        self.log.append((t, alt, yaw, pitch, v))

        err = self.bank - roll
        roll_cmd = max(-1.0, min(1.0, err * 0.05))
        return ActionResult(action=np.array([roll_cmd, -1.0, 0.0, self.thr], dtype=np.float32),
                            source="corner")


def run(throttle, bank, secs=50.0):
    p = Hold(throttle, bank)
    env = DogFightWrapper(
        env_config={"observation_mode": "tactical16", "ownship_control_mode": "rl",
                    "target_mode": "rl", "max_engage_time": secs,
                    "episode_step_limit": 18000, "min_altitude": 300.0},
        ownship_action_provider=p,
        target_action_provider=BTActionProvider(dll_name="AIP_dummy.dll"))
    try:
        env.reset(); term = trunc = False
        while not (term or trunc):
            _, _, term, trunc, _ = env.step(np.zeros(4, dtype=np.float32))
    finally:
        env.close()

    lg = [x for x in p.log if x[4] > 20.0]
    if len(lg) < 200: return None
    tail = lg[int(len(lg)*0.6):]          # 정상상태만(초반 가속 구간 제외)
    K = 12                                 # 0.2초 창
    rates = []
    for i in range(K, len(tail)):
        f0 = fwd_vec(tail[i-K][2], tail[i-K][3])
        f1 = fwd_vec(tail[i][2],   tail[i][3])
        dt = tail[i][0] - tail[i-K][0]
        if dt <= 0: continue
        ang = math.degrees(math.acos(max(-1, min(1, float(np.dot(f0, f1))))))
        rates.append(ang/dt)
    if not rates: return None
    rates.sort()
    med = rates[len(rates)//2]
    v = sum(x[4] for x in tail)/len(tail)
    alt_drop = tail[0][1] - tail[-1][1]
    dur = tail[-1][0] - tail[0][0]
    return dict(v=v, rate=med, r=v/math.radians(med) if med > 0.1 else 9e9,
                sink=alt_drop/dur if dur > 0 else 0.0)


if __name__ == "__main__":
    bank = float(sys.argv[1]) if len(sys.argv) > 1 else 82.0
    print(f"\n코너속도 실측 (뱅크 {bank:.0f}도 수평선회, 총 각속도 기준)")
    print(f"{'스로틀':>6} {'정착속도':>9} {'선회율':>9} {'반경':>8} {'침하율':>9}")
    print("-" * 46)
    rows = []
    for thr in [0.10, 0.20, 0.30, 0.40, 0.50, 0.65, 0.80, 1.00]:
        r = run(thr, bank)
        if r:
            rows.append((thr, r))
            print(f"{thr:6.2f} {r['v']:7.0f}m/s {r['rate']:6.1f}°/s {r['r']:7.0f}m "
                  f"{r['sink']:7.1f}m/s", flush=True)
    if rows:
        best = max(rows, key=lambda x: x[1]["rate"])
        tight = min(rows, key=lambda x: x[1]["r"])
        print("-" * 46)
        print(f"★선회율 최대 : 스로틀 {best[0]:.2f}  속도 {best[1]['v']:.0f}m/s  "
              f"{best[1]['rate']:.1f}°/s   <- 이게 코너속도")
        print(f"★반경 최소   : 스로틀 {tight[0]:.2f}  속도 {tight[1]['v']:.0f}m/s  "
              f"{tight[1]['r']:.0f}m")
        print(f"\n  현재 BT의 CORNER 상수 = 260 m/s")
        print(f"  onecircle(상대) 상수  = 255 m/s")
        print(f"  -> 실측 최적이 260과 다르면 우리 상수가 틀린 것이다(상대 무관한 원리).")
