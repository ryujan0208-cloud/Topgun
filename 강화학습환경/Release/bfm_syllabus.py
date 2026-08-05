# -*- coding: utf-8 -*-
"""
BFM 상황 훈련표(Syllabus) 러너.

핵심 사상: **상대를 이기는지가 아니라, 상황을 처리하는지를 본다.**
  - 대회 상대는 미지 -> 특정 상대 대응 튜닝은 과적합.
  - 공중전 상황은 유한하고 알려져 있다(정면머지/공세/방어/에너지열세·우세/측면).
  - 판정 기준을 상대와 무관한 절대값으로 두면, 상대 수준이 낮아도 진단이 유효하다.

사용:
  python bfm_syllabus.py                        # 전 시나리오 x 기본 상대
  python bfm_syllabus.py --scenarios 1,3        # 특정 시나리오만
  python bfm_syllabus.py --opponents AIP_v7.dll,AIP_kwon.dll
  python bfm_syllabus.py --repeats 5            # 시나리오당 반복(초기 소량 랜덤)
  python bfm_syllabus.py --own AIP_v22c.dll     # 시험할 우리 기체

출력: 시나리오 x 상대 판정표 + 원인 지표(코너속도 준수율, 선회율, 사격틱, 피격틱).
"""
from __future__ import annotations
import sys, math, json, argparse
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

# Windows 콘솔(cp949)에서도 한글/기호가 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0
CORNER_LO, CORNER_HI = 210.0, 290.0      # 실측 코너속도대(선회율 최대 구간)
WEZ_MIN, WEZ_MAX, WEZ_ATA = 152.4, 914.4, 1.0


# ───────────────────────── 시나리오 정의 ─────────────────────────
# NED 기준: n=북(+), e=동(+), d=아래(+) 이므로 고도 h -> d = -h
# heading: 0=북, 90=동
def SC(n, e, h, hdg, spd):
    return dict(init_n=n, init_e=e, init_d=-h, init_heading=hdg, init_speed=spd,
                init_roll=0, init_pitch=0)

SCENARIOS = {
    1: dict(name="정면 머지",
            desc="3km 정면 접근, 동고도·동속. 머지 각도전 시험(최대 약점)",
            own=SC(0, 0, 7000, 0, 300), tgt=SC(3000, 0, 7000, 180, 300),
            focus="merge"),
    2: dict(name="공세 BFM",
            desc="우리가 적 800m 뒤. 킬 전환력 시험",
            own=SC(0, 0, 7000, 0, 300), tgt=SC(800, 0, 7000, 0, 300),
            focus="offense"),
    3: dict(name="방어 BFM",
            desc="적이 우리 800m 뒤. Evade 실효성 시험",
            own=SC(800, 0, 7000, 0, 300), tgt=SC(0, 0, 7000, 0, 300),
            focus="defense"),
    4: dict(name="에너지 열세",
            desc="우리가 1500m 아래 + 저속. 에너지 관리 시험",
            own=SC(0, 0, 5500, 0, 230), tgt=SC(2500, 0, 7000, 180, 320),
            focus="energy_lo"),
    5: dict(name="에너지 우세",
            desc="우리가 1500m 위 + 고속. 우위 활용 시험",
            own=SC(0, 0, 7000, 0, 320), tgt=SC(2500, 0, 5500, 180, 230),
            focus="energy_hi"),
    6: dict(name="측면 진입",
            desc="90° 교차(빔). 일반 기하 시험",
            own=SC(0, 0, 7000, 0, 300), tgt=SC(1500, 1500, 7000, 270, 300),
            focus="beam"),
}


# ───────────────────────── 측정 ─────────────────────────
class Probe:
    """교전 중 상대 무관 지표를 누적한다."""
    def __init__(self):
        self.n = 0
        self.wez_ticks = 0          # 우리가 사격 성립
        self.hit_ticks = 0          # 우리가 피격
        self.tail_ticks = 0         # 우리가 뒤(ATA<45 & 사거리권)
        self.tailed_ticks = 0       # 우리가 뒤 잡힘
        self.corner_ticks = 0       # 코너속도대 체류
        self.spd_sum = 0.0
        self.min_ata = 999.0
        self.min_alt = 99999.0
        self.turn_max = 0.0
        self._prev_yaw = None
        self._prev_t = None

    def update(self, me, en):
        self.n += 1
        c = math.cos(math.radians(float(me[StateIndex.LAT])))
        de = (float(en[StateIndex.LON]) - float(me[StateIndex.LON])) * c * MLAT
        dn = (float(en[StateIndex.LAT]) - float(me[StateIndex.LAT])) * MLAT
        du = float(en[StateIndex.ALT]) - float(me[StateIndex.ALT])
        d = math.sqrt(de*de + dn*dn + du*du)

        def ata(s, vx, vy, vz):
            y, p = math.radians(float(s[StateIndex.YAW])), math.radians(float(s[StateIndex.PITCH]))
            f = (math.sin(y)*math.cos(p), math.cos(y)*math.cos(p), math.sin(p))
            return math.degrees(math.acos(max(-1, min(1, (f[0]*vx+f[1]*vy+f[2]*vz)/max(d, 1e-6)))))

        myA = ata(me, de, dn, du)
        enA = ata(en, -de, -dn, -du)
        inr = (WEZ_MIN <= d <= WEZ_MAX)
        if inr and myA <= WEZ_ATA: self.wez_ticks += 1
        if inr and enA <= WEZ_ATA: self.hit_ticks += 1
        if inr and myA < 45: self.tail_ticks += 1
        if inr and enA < 45: self.tailed_ticks += 1
        if inr: self.min_ata = min(self.min_ata, myA)
        self.min_alt = min(self.min_alt, float(me[StateIndex.ALT]))

        # 속도(상태의 KCAS가 아니라 실제 TAS를 위치로 못 구하므로 시뮬 제공값 사용)
        v = float(me[StateIndex.KCAS])
        self.spd_sum += v

        # 선회율
        t = float(me[StateIndex.SIM_TIME]); yaw = float(me[StateIndex.YAW])
        if self._prev_t is not None and t > self._prev_t:
            dy = abs(yaw - self._prev_yaw); dy = min(dy, 360 - dy)
            rate = dy / (t - self._prev_t)
            if rate < 120: self.turn_max = max(self.turn_max, rate)
        self._prev_t, self._prev_yaw = t, yaw

    def summary(self):
        n = max(self.n, 1)
        return dict(ticks=self.n,
                    wez=self.wez_ticks, hit=self.hit_ticks,
                    tail_pct=100.0*self.tail_ticks/n, tailed_pct=100.0*self.tailed_ticks/n,
                    min_ata=(None if self.min_ata > 900 else self.min_ata),
                    min_alt=self.min_alt, turn_max=self.turn_max)


# ───────────────────────── 실행 ─────────────────────────
def run_scenario(sid, own_dll, tgt_dll, max_time, jitter, seed):
    sc = SCENARIOS[sid]
    env = DogFightWrapper(
        env_config={"observation_mode": "tactical16",
                    "ownship_control_mode": "rl", "target_mode": "rl",
                    "max_engage_time": max_time, "episode_step_limit": 18000,
                    "min_altitude": 300.0},
        ownship_action_provider=BTActionProvider(dll_name=own_dll),
        target_action_provider=BTActionProvider(dll_name=tgt_dll),
    )
    probe = Probe()
    try:
        env.reset()
        rng = np.random.default_rng(seed)
        def jit(v, amt): return float(v + (rng.uniform(-amt, amt) if jitter else 0.0))
        o, t = sc["own"], sc["tgt"]
        # 초기 배치 강제 (약간의 흔들림으로 단일 결과 과신 방지)
        env.change_init_position(flight="ownship",
            init_n=jit(o["init_n"], 150), init_e=jit(o["init_e"], 150), init_d=jit(o["init_d"], 100),
            init_roll=0, init_pitch=0, init_heading=jit(o["init_heading"], 8),
            init_speed=jit(o["init_speed"], 12), target_type=2)
        env.change_init_position(flight="target",
            init_n=jit(t["init_n"], 150), init_e=jit(t["init_e"], 150), init_d=jit(t["init_d"], 100),
            init_roll=0, init_pitch=0, init_heading=jit(t["init_heading"], 8),
            init_speed=jit(t["init_speed"], 12), target_type=2)
        env.reset()

        term = trunc = False
        while not (term or trunc):
            _, _, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))
            probe.update(env._sim.get_state(), env._target_sim.get_state())
        s = probe.summary()
        s["own_hp"] = float(info.get("ownship_health", 1.0))
        s["tgt_hp"] = float(info.get("target_health", 1.0))
        s["end"] = info.get("end_condition", "")
        return s
    finally:
        env.close()


def verdict(sid, r):
    """상대와 무관한 절대 기준 판정."""
    f = SCENARIOS[sid]["focus"]
    oh, th = r["own_hp"], r["tgt_hp"]
    dead = oh <= 0 or "altitude below min" in (r["end"] or "")
    if dead: return "FAIL", "격추/추락"
    if f == "defense":
        # 방어: 생존이 최소조건, 뒤집으면 성공
        if r["tailed_pct"] > 25: return "FAIL", f"계속 물림({r['tailed_pct']:.0f}%)"
        if r["tail_pct"] > 10:   return "PASS", "반전 성공"
        return "WEAK", "생존만"
    if f in ("offense", "energy_hi"):
        if r["wez"] >= 30: return "PASS", f"사격 {r['wez']}틱"
        if th < 0.99:      return "WEAK", f"데미지만({th:.2f})"
        return "FAIL", "전환 실패"
    if f == "merge":
        if r["tail_pct"] > 20 and r["tailed_pct"] < 10: return "PASS", "머지 우세"
        if r["tailed_pct"] > 20: return "FAIL", f"머지 열세({r['tailed_pct']:.0f}%)"
        return "WEAK", "중립"
    if f == "energy_lo":
        if r["tail_pct"] > 10: return "PASS", "열세 극복"
        if r["tailed_pct"] > 30: return "FAIL", "열세 고착"
        return "WEAK", "생존"
    # beam
    if r["tail_pct"] > 20: return "PASS", "뒤 확보"
    return "WEAK" if r["tailed_pct"] < 20 else "FAIL", f"뒤{r['tail_pct']:.0f}/물림{r['tailed_pct']:.0f}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--own", default="AIP_DCS_ownship.dll")
    p.add_argument("--opponents", default="AIP_v7.dll,AIP_kwon.dll")
    p.add_argument("--scenarios", default="1,2,3,4,5,6")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--time", type=float, default=120.0)
    p.add_argument("--no-jitter", action="store_true")
    a = p.parse_args()

    sids = [int(x) for x in a.scenarios.split(",")]
    opps = [x.strip() for x in a.opponents.split(",")]
    print(f"\n시험 기체: {a.own}   상대: {', '.join(opps)}   반복 {a.repeats}회/조합  {a.time:.0f}초\n")
    table = []
    for sid in sids:
        sc = SCENARIOS[sid]
        print(f"[{sid}] {sc['name']} - {sc['desc']}")
        for opp in opps:
            agg = []
            for k in range(a.repeats):
                r = run_scenario(sid, a.own, opp, a.time, not a.no_jitter, seed=1000*sid+k)
                agg.append(r)
            # ★ 2026-08-06 수정: 판정과 표시가 어긋나 있었다.
            #  [문제] 판정은 **최악 1판**으로 하면서 표시는 **평균**이라
            #    'FAIL(전환 실패) 사격187.5'처럼 모순돼 보이는 줄이 나온다
            #    (평균 187.5면 기준 30틱을 한 판은 확실히 넘었다는 뜻).
            #    게다가 repeats 기본이 2라 **우리 자체 규칙(15시드 이상)을 위반**한다.
            #    한 판만 나빠도 FAIL로 찍혀 'PASS 0'이 실제보다 과장된다.
            #  [수정] 판정 분포를 함께 표시한다. 헤드라인은 보수적으로 최악을 유지하되
            #    'PASS 3/8' 같은 형태로 몇 판이 통과했는지 보이게 한다.
            vs = [verdict(sid, r) for r in agg]
            order = {"FAIL": 0, "WEAK": 1, "PASS": 2}
            worst = min(vs, key=lambda v: order[v[0]])
            npass_r = sum(1 for v in vs if v[0] == "PASS")
            nfail_r = sum(1 for v in vs if v[0] == "FAIL")
            dist = f"P{npass_r}/W{len(vs)-npass_r-nfail_r}/F{nfail_r}"
            wez = sum(r["wez"] for r in agg) / len(agg)
            hit = sum(r["hit"] for r in agg) / len(agg)
            tail = sum(r["tail_pct"] for r in agg) / len(agg)
            tailed = sum(r["tailed_pct"] for r in agg) / len(agg)
            mnalt = min(r["min_alt"] for r in agg)
            mnata = min((r["min_ata"] or 999) for r in agg)
            print(f"     vs {opp:20} {worst[0]:5} [{dist}] ({worst[1]})   "
                  f"사격{wez:5.1f} 피격{hit:5.1f} 뒤{tail:4.0f}% 물림{tailed:4.0f}% "
                  f"최소ATA{mnata:5.1f}° 최저고도{mnalt:5.0f}m")
            table.append(dict(scenario=sid, name=sc["name"], opp=opp, verdict=worst[0],
                              note=worst[1], dist=dist, npass_r=npass_r, nrep=len(vs),
                              wez=wez, hit=hit, tail=tail, tailed=tailed,
                              min_ata=mnata, min_alt=mnalt))
        print()
    # 요약
    tot_r  = sum(t.get("nrep", 0) for t in table)
    pass_r = sum(t.get("npass_r", 0) for t in table)
    npass = sum(1 for t in table if t["verdict"] == "PASS")
    nweak = sum(1 for t in table if t["verdict"] == "WEAK")
    nfail = sum(1 for t in table if t["verdict"] == "FAIL")
    print(f"=== 종합: PASS {npass} / WEAK {nweak} / FAIL {nfail}  (총 {len(table)})")
    out = ROOT / "artifacts" / f"syllabus_{Path(a.own).stem}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"    결과 저장: {out.name}")


if __name__ == "__main__":
    main()
