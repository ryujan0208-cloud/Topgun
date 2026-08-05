# -*- coding: utf-8 -*-
"""
오프라인 기동 탐색 (counterfactual probe) — "그 순간 진짜 최적은 뭐였나?"를 실제 시뮬로 묻는다.

[왜 이게 되는가 — 2026-07-24 MPC 기각과의 결정적 차이]
그때 기각한 건 **경기 중(온라인)** BT 안에서 롤아웃하는 것이었다. 100ms 예산 안에
6DOF와 상대 정책을 예측할 forward model이 없다는 게 기각 근거였다.
**이건 오프라인이다. 진짜 시뮬레이터가 forward model이다.** 그 기각 근거가 통째로 사라진다.
재개 조건("forward model 정확도가 검증되면 재검토")이 가장 강한 형태로 충족된 셈.

[무엇을 하나]
1. 기준 판을 결정론적으로 재생한다(같은 시드 순서면 bit-identical — 검증됨).
2. 지정한 시간창 [t0, t1]에서만 우리 조종을 **후보 기동**으로 덮어쓴다.
3. 창이 끝나면 BT로 복귀한다.
4. 여러 지평선(+5초 / +20초 / 판 끝)에서 결과를 잰다.

[왜 VP가 아니라 기동을 덮어쓰나]
VP를 갈아끼우려면 DLL을 고쳐야 한다. 기동 덮어쓰기는 코드 변경 없이 되고,
답하려는 질문("그 순간 다른 기동이 나았나")에 더 직접적이다.

[반드시 지킬 것 — 이 도구의 함정]
* **국소 최적 != 전체 최적.** 5초 뒤 각도를 얻는 기동이 30초 뒤엔 에너지를 잃어 질 수 있다.
  그래서 **여러 지평선에서 동시에 재고 순위가 유지되는지** 본다.
  순위가 뒤집히면 그 구간 목표함수가 틀린 것이고, **그 뒤집힘 자체가 발견**이다.
* **상대가 반응한다(closed-loop).** 찾은 '최적'은 그 상대에 대한 최적이다.
  진단엔 문제없지만 **학습 목표로 쓰면 과적합**이다.
* **구간별 탐욕 탐색은 진짜 최적이 아니다.** 결합 최적은 K^M이라 계산 불가. 진단용으로만.

사용:
  python tools_diag/vp_probe.py <상대> <시드> <t0> [창길이=5]
  예) python tools_diag/vp_probe.py AIP_onecircle.dll 3 90
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

# 후보 기동. action = [roll, pitch, yaw, throttle]
#   부호 규약(ace_pilot.py에서 교정 확인): pitch<0 = 기수 올림, roll>0 = 오른쪽
#   "하강나선"은 뱅크를 90도 넘겨(=1.0) 당기는 것 — 실측상 지속 25.4deg/s로 수평선회의 2.2배.
CANDIDATES = [
    ("BT(기준)",        None),
    ("우선회+당김",      ( 1.0, -1.0, 0.0, 0.85)),
    ("좌선회+당김",      (-1.0, -1.0, 0.0, 0.85)),
    ("우하강나선",       ( 1.0, -1.0, 0.0, 0.30)),
    ("좌하강나선",       (-1.0, -1.0, 0.0, 0.30)),
    ("수직당김(상승)",   ( 0.0, -1.0, 0.0, 1.00)),
    ("이탈(수평전속)",   ( 0.0,  0.0, 0.0, 1.00)),
    ("감속+당김",        ( 0.0, -1.0, 0.0, 0.20)),
]


def _geom(me, en):
    """거리 / 우리 ATA / 고도차(상대-나). ace_pilot.py와 동일한 상태 접근 규약을 쓴다."""
    lat, lon, alt = float(me[StateIndex.LAT]), float(me[StateIndex.LON]), float(me[StateIndex.ALT])
    yaw, pit = math.radians(float(me[StateIndex.YAW])), math.radians(float(me[StateIndex.PITCH]))
    tlat, tlon, talt = float(en[StateIndex.LAT]), float(en[StateIndex.LON]), float(en[StateIndex.ALT])
    c = math.cos(math.radians(lat))
    de, dn, du = (tlon - lon) * c * MLAT, (tlat - lat) * MLAT, talt - alt
    d = math.sqrt(de * de + dn * dn + du * du) or 1.0
    fe, fn, fu = math.sin(yaw) * math.cos(pit), math.cos(yaw) * math.cos(pit), math.sin(pit)
    ata = math.degrees(math.acos(max(-1.0, min(1.0, (fe * de + fn * dn + fu * du) / d))))
    return d, ata, du


class Override(ActionProvider):
    """[t0,t1] 구간에서만 내부 BT 출력을 후보 기동으로 덮어쓴다. 창 밖에서는 BT 그대로.
    기하 기록도 여기서 한다 — context 안에서만 상대 상태(opponent_sim)에 접근할 수 있다."""
    def __init__(self, inner, t0, t1, act):
        self._inner, self._t0, self._t1, self._act = inner, t0, t1, act
        self.trace = []          # (t, dist, ata, du)

    def compute_action(self, context):
        me = context.sim.get_state()
        t = float(me[StateIndex.SIM_TIME])
        try:
            en = context.opponent_sim.get_state()
            self.trace.append((t,) + _geom(me, en))
        except Exception:
            pass
        r = self._inner.compute_action(context)
        if self._act is not None and self._t0 <= t < self._t1:
            return ActionResult(action=np.array(self._act, dtype=np.float32), source="probe")
        return r

    def reset(self, context=None):
        self.trace.clear()
        return self._inner.reset(context)

    def __getattr__(self, n):
        return getattr(self._inner, n)


class Repeat(ActionProvider):
    """제출 조건(ACTION_REPEAT=6=10Hz) 에뮬레이션. rehearsal_10hz.py와 동일해야 비교가 성립."""
    def __init__(self, inner, n):
        self._inner, self._n, self._c, self._last = inner, max(1, n), 0, None
    def compute_action(self, context):
        if self._c % self._n == 0 or self._last is None:
            self._last = self._inner.compute_action(context)
        self._c += 1
        return self._last
    def reset(self, context=None):
        self._c, self._last = 0, None
        return self._inner.reset(context)
    def __getattr__(self, n):
        return getattr(self._inner, n)


def run(opp, seed, t0, t1, act, horizons):
    ov  = Override(BTActionProvider(dll_name="AIP_DCS_ownship.dll"), t0, t1, act)
    own = Repeat(ov, 6)
    if str(opp).upper() == "ACE":
        from ace_pilot import AcePilot
        tgt = Repeat(AcePilot(), 6)
    else:
        tgt = Repeat(BTActionProvider(dll_name=opp), 6)

    cfg = {"observation_mode": "tactical16", "ownship_control_mode": "rl", "target_mode": "rl",
           "max_engage_time": 200.0, "episode_step_limit": 18000, "min_altitude": 300.0,
           "ownship_randomization": {"enabled": True, "radius": 1500.0,
                                     "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 180.0}}
    env = DogFightWrapper(env_config=cfg, ownship_action_provider=own, target_action_provider=tgt)
    try:
        env.reset(seed=seed)
        term = trunc = False
        info = {}
        while not (term or trunc):
            _, _, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))
        oh = float(info.get("ownship_health", 1.0)); th = float(info.get("target_health", 1.0))
    finally:
        env.close()

    # 지평선별 스냅샷을 trace에서 뽑는다(창이 끝난 시점 기준).
    snaps = {}
    for h in horizons:
        want = t1 + h
        best = None
        for (t, d, ata, du) in ov.trace:
            if t >= want:
                best = (d, ata, du); break
        if best: snaps[h] = best
    # 창 이후 사거리 안에서의 최소 ATA — "쏠 수 있었나"의 직접 지표
    inr = [a for (t, d, a, _) in ov.trace if t >= t1 and 152.4 <= d <= 914.4]
    snaps["minATA"] = min(inr) if inr else None
    snaps["wez"] = len(inr)
    return snaps, oh, th


def main():
    opp   = sys.argv[1] if len(sys.argv) > 1 else "AIP_onecircle.dll"
    seed  = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    t0    = float(sys.argv[3]) if len(sys.argv) > 3 else 90.0
    span  = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
    t1    = t0 + span
    HOR   = [5.0, 20.0]

    print(f"\n[기동 탐색] {opp} seed={seed}  덮어쓰기 창 {t0:.0f}~{t1:.0f}초")
    hdr = f"{'후보':<16}"
    for h in HOR: hdr += f"{('+%ds 거리/ATA' % h):>17}"
    hdr += f"{'창後최소ATA':>12}{'사거리틱':>9}{'준':>8}{'받은':>8}"
    print(hdr); print("-" * len(hdr))

    rows = []
    for name, act in CANDIDATES:
        snaps, oh, th = run(opp, seed, t0, t1, act, HOR)
        line = f"{name:<16}"
        for h in HOR:
            if h in snaps:
                d, ata, _ = snaps[h]
                line += f"{d:10.0f}m/{ata:3.0f}°"
            else:
                line += f"{'--':>17}"
        m = snaps.get("minATA")
        line += f"{(('%.1f°' % m) if m is not None else '-'):>12}{snaps.get('wez',0):>9}"
        line += f"{1-th:>8.4f}{1-oh:>8.4f}"
        print(line, flush=True)
        rows.append((name, snaps, 1-th, 1-oh))

    # 지평선별 순위가 유지되는지 = 이 진단을 믿어도 되는지의 핵심 판정
    print("-" * len(hdr))
    for h in HOR:
        ok = sorted([(r[0], r[1][h][1]) for r in rows if h in r[1]], key=lambda x: x[1])
        print(f"  +{h:.0f}초 ATA 순위 : " + " > ".join(n for n, _ in ok[:4]))
    mn = sorted([(r[0], r[1]["minATA"]) for r in rows if r[1].get("minATA") is not None],
                key=lambda x: x[1])
    if mn: print(f"  창後 최소ATA 순위: " + " > ".join(f"{n}({v:.1f}°)" for n, v in mn[:4]))
    bd = sorted(rows, key=lambda r: -r[2])[:4]
    print(f"  최종 준데미지 순위: " + " > ".join(f"{n}({d:.3f})" for n, _, d, _ in bd))
    print("\n  ※ 지평선마다 순위가 크게 다르면 그 구간 목표함수가 틀린 것이다 — 그 자체가 발견.")
    print("  ※ 여기서 나온 '최적'은 이 상대에 대한 최적이다. 학습 목표로 쓰면 과적합.")
    print("  ※ 구간별 탐욕 탐색이라 진짜 최적이 아니다. 가설 생성용이지 채택 근거가 아니다.")


if __name__ == "__main__":
    main()
