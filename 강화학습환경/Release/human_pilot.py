# -*- coding: utf-8 -*-
"""
사람이 상대기체(RED)를 실시간 조종해서 우리 기체(BLUE)와 교전시키는 도구.

목적: 수준 높은 공격형 스파링 상대를 못 구해서, 사람이 직접 조종해 우리 약점을 공략해본다.
  - 모드 1 (live)   : 키보드 실시간 조종. 조종 입력은 자동 녹화된다.
  - 모드 3 (replay) : 녹화된 입력을 그대로 재생 -> **재현 가능**해져서 15시드 배치 검증에 쓸 수 있다.

사용:
  python human_pilot.py live            # 조종 (기본 200초, 1배속)
  python human_pilot.py live --speed 0.5 --time 120
  python human_pilot.py replay recordings/xxx.json      # 녹화 재생(1판)
  python human_pilot.py list            # 녹화 목록

조작 (터미널 창을 포커스한 채로):
  A / D : 좌 / 우 롤        W / S : 기수 내림(pitch-) / 올림(pitch+)
  Q / E : 러더 좌/우        1~5   : 스로틀 0.25/0.5/0.75/1.0/AB(1.0)
  SPACE : 중립(스틱만 0)     P     : 일시정지     ESC/X : 종료
  키를 떼도 값이 유지된다(트림식). 반대 키를 누르거나 SPACE로 되돌린다.

주의:
  - 우리 기체(BLUE)는 AIP_DCS_ownship.dll(현역)이 그대로 조종한다. 사람은 RED만 조종.
  - live 모드는 재현 불가라 "탐색"용. 검증은 반드시 replay 모드로.
"""
from __future__ import annotations
import sys, os, json, time, math, argparse
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

REC_DIR = ROOT / "recordings"
MLAT = 111320.0

try:
    import msvcrt
except ImportError:
    msvcrt = None


# ─────────────────────────────── 조종 입력 ───────────────────────────────
class Stick:
    """트림식 스틱: 키를 누르면 값이 이동하고, 떼도 유지된다."""
    STEP = 0.25

    def __init__(self):
        self.roll = 0.0; self.pitch = 0.0; self.yaw = 0.0; self.thr = 1.0
        self.paused = False; self.quit = False

    def apply_key(self, ch: str):
        c = ch.lower()
        if   c == 'a': self.roll  = max(-1.0, self.roll  - self.STEP)
        elif c == 'd': self.roll  = min( 1.0, self.roll  + self.STEP)
        elif c == 'w': self.pitch = max(-1.0, self.pitch - self.STEP)
        elif c == 's': self.pitch = min( 1.0, self.pitch + self.STEP)
        elif c == 'q': self.yaw   = max(-1.0, self.yaw   - self.STEP)
        elif c == 'e': self.yaw   = min( 1.0, self.yaw   + self.STEP)
        elif c == ' ': self.roll = self.pitch = self.yaw = 0.0
        elif c in '12345': self.thr = [0.25, 0.5, 0.75, 1.0, 1.0]['12345'.index(c)]
        elif c == 'p': self.paused = not self.paused
        elif c in ('x', '\x1b'): self.quit = True

    def pump(self):
        """버퍼에 쌓인 키를 모두 소비 (논블로킹)."""
        if msvcrt is None: return
        while msvcrt.kbhit():
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):      # 특수키(방향키 등) 2바이트 — 무시
                if msvcrt.kbhit(): msvcrt.getch()
                continue
            try: self.apply_key(ch.decode('cp949', 'ignore'))
            except Exception: pass

    def action(self):
        return np.array([self.roll, self.pitch, self.yaw, self.thr], dtype=np.float32)


# ────────────────────────── provider (RED = 사람/녹화) ──────────────────────────
class HumanProvider(ActionProvider):
    """사람 조종 + 자동 녹화. compute_action 계약만 지키면 BT/RL과 동등하게 꽂힌다."""

    def __init__(self, stick: Stick, speed: float, hud_every: int = 3):
        self.stick = stick; self.speed = speed
        self.hud_every = hud_every
        self.frames = []          # 녹화 버퍼 (틱마다 4축)
        self.n = 0
        self._t_wall = time.perf_counter()
        self._last_hud = ""

    def compute_action(self, context) -> ActionResult:
        self.stick.pump()
        while self.stick.paused and not self.stick.quit:
            time.sleep(0.05); self.stick.pump()

        a = self.stick.action()
        self.frames.append([round(float(x), 4) for x in a])
        self.n += 1

        if self.n % self.hud_every == 0:
            self._hud(context)

        # 실시간 페이싱: 시뮬 1틱 = 1/60초 (speed=1.0이면 실시간)
        if self.speed > 0:
            target = 1.0 / 60.0 / self.speed
            dt = time.perf_counter() - self._t_wall
            if dt < target: time.sleep(target - dt)
            self._t_wall = time.perf_counter()
        return ActionResult(action=a, source="human", confidence=1.0)

    def _hud(self, context):
        """레이더 화면 + 계기. 매번 화면을 지우고 다시 그린다(스크롤 방지)."""
        try:
            me = context.sim.get_state()          # RED (내가 조종)
            en = context.opponent_sim.get_state() # BLUE (우리 BT)
        except Exception:
            return
        c = math.cos(math.radians(float(me[StateIndex.LAT])))
        de = (float(en[StateIndex.LON]) - float(me[StateIndex.LON])) * c * MLAT
        dn = (float(en[StateIndex.LAT]) - float(me[StateIndex.LAT])) * MLAT
        du = float(en[StateIndex.ALT]) - float(me[StateIndex.ALT])
        dist = math.sqrt(de*de + dn*dn + du*du)
        myyaw = float(me[StateIndex.YAW])
        yaw, pit = math.radians(myyaw), math.radians(float(me[StateIndex.PITCH]))
        fe, fn, fu = math.sin(yaw)*math.cos(pit), math.cos(yaw)*math.cos(pit), math.sin(pit)
        ata = math.degrees(math.acos(max(-1, min(1, (fe*de+fn*dn+fu*du)/max(dist, 1e-6)))))
        eyaw_d = float(en[StateIndex.YAW])
        eyaw, epit = math.radians(eyaw_d), math.radians(float(en[StateIndex.PITCH]))
        ee, en_, eu = math.sin(eyaw)*math.cos(epit), math.cos(eyaw)*math.cos(epit), math.sin(epit)
        eata = math.degrees(math.acos(max(-1, min(1, (ee*-de+en_*-dn+eu*-du)/max(dist, 1e-6)))))

        # ── 레이더: 내 기수를 항상 위(↑)로 두는 상대좌표(body frame) ──
        W, H = 31, 13                       # 화면 칸수(홀수)
        grid = [[' '] * W for _ in range(H)]
        rng = 3000.0                         # 레이더 반경(m). 근접 시 자동 확대
        if dist < 800: rng = 1000.0
        elif dist < 2000: rng = 2000.0
        # 적을 내 기준 좌표로 회전 (전방 = +y화면위)
        bx =  de * math.cos(yaw) - dn * math.sin(yaw)     # 우측(+)
        by =  de * math.sin(yaw) + dn * math.cos(yaw)     # 전방(+)
        cx, cy = W // 2, H // 2
        px = cx + int(round(bx / rng * cx))
        py = cy - int(round(by / rng * cy))
        # 거리 링(1000m)
        for ang in range(0, 360, 6):
            rr = 1000.0
            if rr < rng:
                gx = cx + int(round(math.sin(math.radians(ang)) * rr / rng * cx))
                gy = cy - int(round(math.cos(math.radians(ang)) * rr / rng * cy))
                if 0 <= gx < W and 0 <= gy < H and grid[gy][gx] == ' ': grid[gy][gx] = '·'
        # 내 기체(중앙, 항상 위 향함)
        grid[cy][cx] = '^'
        # 적 기체 + 적 기수 방향
        if 0 <= px < W and 0 <= py < H:
            rel = (eyaw_d - myyaw + 360) % 360      # 적 기수(내 기준)
            arrow = '↑↗→↘↓↙←↖'[int(((rel + 22.5) % 360) // 45)]
            grid[py][px] = arrow
        else:  # 화면 밖이면 가장자리에 방향 표시
            ang = math.degrees(math.atan2(bx, by)) % 360
            ex = cx + int(round(math.sin(math.radians(ang)) * cx))
            ey = cy - int(round(math.cos(math.radians(ang)) * cy))
            ex = max(0, min(W-1, ex)); ey = max(0, min(H-1, ey))
            grid[ey][ex] = '?'

        wez  = "★★사격중★★" if (152 <= dist <= 914 and ata <= 1.0) else \
               ("[사거리]" if 152 <= dist <= 914 else "        ")
        warn = "!!! 피격중 !!!" if (152 <= dist <= 914 and eata <= 1.0) else ""
        bar  = lambda v: ('=' * int(abs(v) * 8)).rjust(8) if v < 0 else ('=' * int(abs(v) * 8)).ljust(8)

        # ── 수직 단면(옆에서 본 화면): 가로=수평거리, 세로=고도차 ──
        VW, VH = 31, 13
        vgrid = [[' '] * VW for _ in range(VH)]
        hdist = math.sqrt(de*de + dn*dn)                  # 수평거리
        vrng_h = max(rng, 500.0)                          # 가로 스케일 = 레이더와 동일
        vrng_v = 1500.0                                   # 세로 ±1500m
        if abs(du) > 1200: vrng_v = 3000.0
        vcx, vcy = 2, VH // 2                             # 내 위치(좌측)
        # 수평선(내 고도 기준선)
        for x in range(VW):
            if vgrid[vcy][x] == ' ': vgrid[vcy][x] = '-'
        vgrid[vcy][vcx] = '>'                             # 나 (오른쪽 향함)
        vx = vcx + int(round(hdist / vrng_h * (VW - vcx - 2)))
        vy = vcy - int(round(du / vrng_v * (VH // 2)))
        vx = max(0, min(VW - 1, vx)); vy = max(0, min(VH - 1, vy))
        # 적 피치에 따른 기호
        epitch = float(en[StateIndex.PITCH])
        esym = 'A' if epitch > 15 else ('V' if epitch < -15 else 'E')
        vgrid[vy][vx] = esym

        L = []
        L.append(f"  T {float(me[StateIndex.SIM_TIME]):5.1f}s   적거리 {dist:6.0f}m   "
                 f"고도차 {-du:+5.0f}m   {wez}{warn}")
        L.append("   [위에서 본 화면]  반경{:.0f}m        [옆에서 본 화면] 상하±{:.0f}m".format(rng, vrng_v))
        L.append("  +" + "-" * W + "+  +" + "-" * VW + "+")
        for r in range(max(H, VH)):
            a = "|" + "".join(grid[r]) + "|" if r < H else " " * (W + 2)
            b = "|" + "".join(vgrid[r]) + "|" if r < VH else " " * (VW + 2)
            L.append("  " + a + "  " + b)
        L.append("  +" + "-" * W + "+  +" + "-" * VW + "+")
        L.append("   ^=나 화살표=적기수 ?=밖      >=나  E=적(A상승 V하강) 위=적이높음")
        L.append("")
        L.append(f"  내 조준각 ATA {ata:5.1f}°      적 조준각 {eata:5.1f}°")
        L.append(f"  고도 {float(me[StateIndex.ALT]):5.0f}m (적 {float(en[StateIndex.ALT]):5.0f}m)   "
                 f"속도 {float(me[StateIndex.KCAS]):3.0f}kt   피치 {float(me[StateIndex.PITCH]):+4.0f}°")
        L.append(f"  HP  나 {float(me[StateIndex.HEALTH]):.3f}   적 {float(en[StateIndex.HEALTH]):.3f}")
        L.append("")
        L.append(f"  롤   [{bar(self.stick.roll)}] {self.stick.roll:+.2f} (A/D)    "
                 f"피치 [{bar(self.stick.pitch)}] {self.stick.pitch:+.2f} (W/S)")
        L.append(f"  러더 [{bar(self.stick.yaw)}] {self.stick.yaw:+.2f} (Q/E)    "
                 f"스로틀 {self.stick.thr:.2f} (1~5)  SPACE=중립 P=정지 X=종료")

        out = "\n".join(L)
        # 커서를 홈으로 보내고 덮어쓰기 (스크롤 없음)
        sys.stdout.write("\033[H\033[J" + out + "\n")
        sys.stdout.flush()


class ReplayProvider(ActionProvider):
    """녹화된 입력을 그대로 재생 → 재현 가능(배치 검증용)."""
    def __init__(self, frames):
        self.frames = frames; self.i = 0
    def reset(self, context=None):
        self.i = 0
    def compute_action(self, context) -> ActionResult:
        if self.i < len(self.frames):
            a = np.array(self.frames[self.i], dtype=np.float32)
        else:
            a = np.array(self.frames[-1] if self.frames else [0, 0, 0, 1.0], dtype=np.float32)
        self.i += 1
        return ActionResult(action=a, source="replay", confidence=1.0)


# ─────────────────────────────── 실행 ───────────────────────────────
def build_env(red_provider, max_time, seed_random):
    cfg = {"observation_mode": "tactical16", "ownship_control_mode": "rl", "target_mode": "rl",
           "max_engage_time": max_time, "episode_step_limit": 18000, "min_altitude": 300.0}
    if seed_random:
        cfg["ownship_randomization"] = {"enabled": True, "radius": 1500.0,
                                        "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 180.0}
    # ownship(BLUE) = 우리 현역 BT, target(RED) = 사람/녹화
    return DogFightWrapper(
        env_config=cfg,
        ownship_action_provider=BTActionProvider(dll_name="AIP_DCS_ownship.dll"),
        target_action_provider=red_provider,
    )


def run_episode(env, seed=None):
    obs, info = (env.reset(seed=seed) if seed is not None else env.reset())
    term = trunc = False; total = 0.0
    while not (term or trunc):
        obs, r, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))
        total += r
    return total, info


def _enable_ansi():
    """Windows 콘솔에서 ANSI 이스케이프(화면 지우기/커서 이동)를 켠다."""
    if os.name != "nt": return
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)              # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        k.GetConsoleMode(h, ctypes.byref(mode))
        k.SetConsoleMode(h, mode.value | 0x0004)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except Exception:
        pass


def _silence_native_logs():
    """네이티브 DLL이 stderr로 뿜는 디버그 출력을 OS 레벨에서 막는다.
    (HUD가 [ACTIVE]/[DIST] 로그에 덮여서 조종이 불가능해지는 문제)"""
    try:
        sys.stderr.flush()
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, 2)          # fd 2 = stderr -> /dev/null
        os.close(devnull)
    except Exception:
        pass


def cmd_live(args):
    if msvcrt is None:
        print("이 도구는 Windows 터미널에서만 동작합니다(msvcrt 필요)."); return
    REC_DIR.mkdir(exist_ok=True)
    stick = Stick()
    prov = HumanProvider(stick, speed=args.speed)
    env = build_env(prov, args.time, seed_random=(args.seed is not None))
    print(__doc__.split("조작 (")[1].split("주의:")[0].strip())
    print(f"\n[{args.time}초 교전 시작 | 속도 {args.speed}x | 당신=RED, 상대=우리 현역 BT(BLUE)]")
    print("3초 후 시작...")
    time.sleep(3)
    _enable_ansi()             # 화면 갱신(커서 이동) 활성화
    _silence_native_logs()     # HUD 가림 방지 (반드시 env 생성 후, 교전 직전)
    try:
        total, info = run_episode(env, seed=args.seed)
        print()
        print(f"  종료: {info.get('end_condition','')}")
        print(f"  당신(RED) HP {info.get('target_health','?')} / 우리 BT(BLUE) HP {info.get('ownship_health','?')}")
        env.make_tacviewLog()
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = REC_DIR / f"human_{stamp}.json"
        out.write_text(json.dumps({
            "created": stamp, "max_time": args.time, "speed": args.speed,
            "seed": args.seed, "ticks": len(prov.frames),
            "ownship_health": info.get("ownship_health"), "target_health": info.get("target_health"),
            "end_condition": info.get("end_condition"),
            "frames": prov.frames,
        }), encoding="utf-8")
        print(f"  녹화 저장: {out.name} ({len(prov.frames)}틱)")
        print(f"  재생: python human_pilot.py replay recordings/{out.name}")
    finally:
        env.close()


def cmd_replay(args):
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    frames = data["frames"]
    print(f"[재생] {Path(args.file).name}  {len(frames)}틱  (원본 결과: "
          f"BLUE {data.get('ownship_health')} / RED {data.get('target_health')})")
    prov = ReplayProvider(frames)
    env = build_env(prov, data.get("max_time", 200), seed_random=(data.get("seed") is not None))
    try:
        total, info = run_episode(env, seed=data.get("seed"))
        print(f"  종료: {info.get('end_condition','')}")
        print(f"  우리BT(BLUE) HP {info.get('ownship_health')} / 녹화RED HP {info.get('target_health')}")
        print(f"  reward {total:.2f}")
        env.make_tacviewLog()
        print("  tacview 로그 저장됨")
    finally:
        env.close()


def cmd_list(args):
    REC_DIR.mkdir(exist_ok=True)
    fs = sorted(REC_DIR.glob("human_*.json"))
    if not fs: print("녹화 없음."); return
    print(f"{'파일':28} {'틱':>6} {'BLUE HP':>8} {'RED HP':>8}  종료")
    for f in fs:
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f"{f.name:28} {d.get('ticks',0):6} {str(d.get('ownship_health'))[:8]:>8} "
              f"{str(d.get('target_health'))[:8]:>8}  {d.get('end_condition','')}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="사람이 상대기체를 조종해 우리 BT와 교전")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("live");   a.add_argument("--time", type=float, default=200.0)
    a.add_argument("--speed", type=float, default=1.0, help="1.0=실시간, 0.5=반속(쉬움)")
    a.add_argument("--seed", type=int, default=None, help="지정 시 랜덤스폰")
    a.set_defaults(func=cmd_live)
    b = sub.add_parser("replay"); b.add_argument("file"); b.set_defaults(func=cmd_replay)
    c = sub.add_parser("list");   c.set_defaults(func=cmd_list)
    args = p.parse_args()
    args.func(args)
