# -*- coding: utf-8 -*-
"""
선회 성능 재측정 v2 — turn_perf.py의 결함을 고친다.

[turn_perf.py의 결함 3가지]
 1) 선회율을 **yaw 변화로만** 측정 -> 하강 나선에서 pitch로 일어나는 회전을 놓쳐 과소평가.
    (이 오류로 "고ATA 선회율 붕괴"라는 허상을 만든 전례가 있는데 성능시험에서 반복했다)
 2) **지속(sustained)만 측정.** 방어 반전은 13초 지속이 아니라 몇 초의 버스트다.
    순간(instantaneous) 능력을 재야 "156도를 얼마나 빨리 되돌릴 수 있나"를 안다.
 3) **수평 선회만 시험.** 수직 기동(당김)은 중력이 도와 더 빠를 수 있다.

[재측정]
 - 총 각속도 = 기수 벡터의 실제 회전량 / 시간  (yaw+pitch 모두 포함)
 - 지속값(정상상태 중앙)과 순간 최대값을 함께 보고
 - 기동 3종: 수평선회(뱅크82) / 수직당김(뱅크0) / 하강나선(뱅크110=약간 넘김)
 - 반경 r = v / omega_total
"""
from __future__ import annotations
import sys, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
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


class Test(ActionProvider):
    def __init__(self, throttle, bank_deg):
        self.thr = throttle; self.bank = bank_deg
        self.log = []; self._prev = None

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
                            source="perf2")


def run(throttle, bank, secs=45.0):
    p = Test(throttle, bank)
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
    if len(lg) < 120: return None
    K = 12                                    # 0.2초 창
    rates = []
    for i in range(K, len(lg)):
        f0 = fwd_vec(lg[i-K][2], lg[i-K][3])
        f1 = fwd_vec(lg[i][2],   lg[i][3])
        dt = lg[i][0] - lg[i-K][0]
        if dt <= 0: continue
        ang = math.degrees(math.acos(max(-1, min(1, float(np.dot(f0, f1))))))
        rates.append((ang/dt, lg[i][4]))
    if not rates: return None
    tail = rates[int(len(rates)*0.5):]         # 정상상태
    tail_sorted = sorted(x[0] for x in tail)
    sustained = tail_sorted[len(tail_sorted)//2]
    peak = sorted(x[0] for x in rates)[int(len(rates)*0.98)]   # 상위2% = 순간 능력
    v = sum(x[1] for x in tail)/len(tail)
    return dict(v=v, sus=sustained, peak=peak,
                r_sus=v/math.radians(sustained) if sustained > 0.1 else 9e9,
                r_peak=v/math.radians(peak) if peak > 0.1 else 9e9)


if __name__ == "__main__":
    print("\n선회 성능 재측정 (총 각속도 = yaw+pitch 전체)")
    print(f"{'기동':>10} {'스로틀':>6} {'속도':>7} {'지속':>8} {'순간':>8} {'지속반경':>9} {'순간반경':>9}")
    print("-" * 66)
    best = []
    for name, bank in [("수평선회", 82.0), ("수직당김", 0.0), ("하강나선", 110.0)]:
        for thr in [0.30, 0.60, 0.85]:
            r = run(thr, bank)
            if r:
                best.append((name, thr, r))
                print(f"{name:>10} {thr:6.2f} {r['v']:6.0f}m/s {r['sus']:6.1f}°/s {r['peak']:6.1f}°/s "
                      f"{r['r_sus']:8.0f}m {r['r_peak']:8.0f}m")
    if best:
        bp = max(best, key=lambda x: x[2]["peak"])
        br = min(best, key=lambda x: x[2]["r_peak"])
        print("-" * 66)
        print(f"★ 순간 선회율 최대: {bp[0]} thr{bp[1]:.2f}  {bp[2]['peak']:.1f}°/s @ {bp[2]['v']:.0f}m/s")
        print(f"   -> 156도 되돌리는 데: {156/bp[2]['peak']:.1f}초  (기존 주장 13초)")
        print(f"★ 순간 반경 최소  : {br[0]} thr{br[1]:.2f}  {br[2]['r_peak']:.0f}m")
        print(f"   -> 사거리 상한 914m 대비: {'안쪽!' if br[2]['r_peak'] < 914 else '바깥'}  (기존 주장 1007m)")
