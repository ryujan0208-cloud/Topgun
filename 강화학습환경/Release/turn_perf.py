# -*- coding: utf-8 -*-
"""
선회 성능 곡선 실측 — 우리 기체의 진짜 코너속도와 최소선회반경을 확정한다.

왜 필요한가:
  코드 세 곳(Task_LeadPredict의 CORNER=260, Task_Evade의 CORNER_D=260, 스파링 봇)이
  같은 상수를 쓰는데, 이 값은 **실전 로그에서 관측된 상위5%로 추정**한 것일 뿐
  제대로 검증한 적이 없다. 틀렸다면 그 위에 쌓은 모든 것이 어긋난다.

무엇을 재는가:
  각 스로틀 설정에서 **최대 G 수평 선회**를 시켜 정상상태에 도달시킨 뒤
  (속도, 선회율)을 측정한다. 반경 r = v / omega.
  - **선회율(rate)이 최대인 속도** = 코너속도 -> 투서클(각속도) 싸움에 유리
  - **반경(radius)이 최소인 속도** -> 원써클(반경) 싸움에 유리
  둘은 일반적으로 **다른 속도**다. 우리는 지금 하나의 값만 쓰고 있다.

방법:
  뱅크각을 목표치로 유지하며 최대 당김(pitch=-1). 스로틀을 바꿔 여러 정상상태를 만든다.
  (부호: pitch<0 = 기수 올림, roll>0 = 우측 롤 — 실측 보정 완료)
"""
from __future__ import annotations
import sys, math
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0


class TurnTest(ActionProvider):
    """목표 뱅크각을 유지하며 최대 G로 선회. 스로틀은 고정."""

    def __init__(self, throttle: float, bank_deg: float = 82.0):
        self.thr = throttle
        self.bank = bank_deg
        self.log = []          # (t, alt, yaw, speed)
        self._prev = None

    def compute_action(self, context) -> ActionResult:
        s = context.sim.get_state()
        t = float(s[StateIndex.SIM_TIME])
        lat, lon, alt = float(s[StateIndex.LAT]), float(s[StateIndex.LON]), float(s[StateIndex.ALT])
        roll, yaw = float(s[StateIndex.ROLL]), float(s[StateIndex.YAW])

        # 속도(위치 차분)
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
        self.log.append((t, alt, yaw, v))

        # 뱅크각 유지 (우선회 기준) + 최대 당김
        err = self.bank - roll
        roll_cmd = max(-1.0, min(1.0, err * 0.05))
        pitch_cmd = -1.0                       # 최대 당김(기수 올림)
        return ActionResult(action=np.array([roll_cmd, pitch_cmd, 0.0, self.thr], dtype=np.float32),
                            source="turntest")


def run(throttle, secs=45.0):
    p = TurnTest(throttle)
    env = DogFightWrapper(
        env_config={"observation_mode": "tactical16", "ownship_control_mode": "rl",
                    "target_mode": "rl", "max_engage_time": secs,
                    "episode_step_limit": 18000, "min_altitude": 300.0},
        ownship_action_provider=p,
        target_action_provider=BTActionProvider(dll_name="AIP_dummy.dll"))
    try:
        env.reset()
        term = trunc = False
        while not (term or trunc):
            _, _, term, trunc, _ = env.step(np.zeros(4, dtype=np.float32))
    finally:
        env.close()

    # 정상상태 = 마지막 40% 구간
    lg = [x for x in p.log if x[3] > 20.0]
    if len(lg) < 60:
        return None
    tail = lg[int(len(lg) * 0.6):]
    # 선회율: yaw 누적 변화 / 시간
    tot = 0.0
    for i in range(1, len(tail)):
        d = tail[i][2] - tail[i-1][2]
        d = (d + 180) % 360 - 180
        tot += abs(d)
    dur = tail[-1][0] - tail[0][0]
    if dur <= 0:
        return None
    omega = tot / dur                                    # deg/s
    v = sum(x[3] for x in tail) / len(tail)              # m/s
    alt_lost = tail[0][1] - tail[-1][1]
    r = v / math.radians(omega) if omega > 0.1 else float("inf")
    return dict(thr=throttle, v=v, omega=omega, r=r, alt_lost=alt_lost/dur)


if __name__ == "__main__":
    print("\n선회 성능 곡선 실측 (최대 G 수평 선회, 정상상태)")
    print(f"{'스로틀':>6} {'속도':>7} {'선회율':>8} {'반경':>8} {'고도손실':>9}")
    print("-" * 46)
    rows = []
    for thr in [0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.00]:
        rr = run(thr)
        if rr:
            rows.append(rr)
            print(f"{rr['thr']:6.2f} {rr['v']:6.0f}m/s {rr['omega']:6.1f}°/s "
                  f"{rr['r']:7.0f}m {rr['alt_lost']:7.1f}m/s")
    if rows:
        best_rate = max(rows, key=lambda x: x["omega"])
        best_rad = min(rows, key=lambda x: x["r"])
        print("-" * 46)
        print(f"★ 선회율 최대(코너속도) : {best_rate['v']:.0f} m/s  →  {best_rate['omega']:.1f}°/s")
        print(f"★ 반경 최소            : {best_rad['v']:.0f} m/s  →  {best_rad['r']:.0f} m")
        print(f"  현재 코드 상수 CORNER = 260 m/s")
