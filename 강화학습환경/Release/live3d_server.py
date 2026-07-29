# -*- coding: utf-8 -*-
"""
실시간 3D 조종 서버.

브라우저가 3D 화면을 그리면서 동시에 조종 입력을 받는다.
  - 시뮬레이션은 파이썬 스레드에서 진행 (human_pilot 파이프라인 재사용)
  - 브라우저 -> POST /api/input  : 조종 입력(roll/pitch/yaw/throttle)
  - 브라우저 <- GET  /api/state  : 양기 위치/자세/HP/거리/ATA (초당 20회 폴링)
  - 3D 메시는 기존 대시보드의 F-16 메시 API를 재사용

브라우저에서 조종하므로 창 포커스 문제가 없고, 마우스 휠로 스로틀 조절이 가능하다.
"""
from __future__ import annotations
import sys, os, json, math, time, threading, http.server, socketserver, webbrowser
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0
REC_DIR = ROOT / "recordings"


# ───────────────────────── 공유 상태 (스레드 간) ─────────────────────────
class Shared:
    def __init__(self):
        self.lock = threading.Lock()
        self.cmd = {"roll": 0.0, "pitch": 0.0, "yaw": 0.0, "thr": 1.0}
        self.state = {"running": False, "t": 0.0}
        self.paused = False
        self.quit = False
        self.frames = []          # 녹화
        self.result = None

    def get_cmd(self):
        with self.lock:
            c = self.cmd
            return np.array([c["roll"], c["pitch"], c["yaw"], c["thr"]], dtype=np.float32)

    def set_cmd(self, d):
        with self.lock:
            for k in ("roll", "pitch", "yaw", "thr"):
                if k in d:
                    v = float(d[k])
                    lo = 0.0 if k == "thr" else -1.0
                    self.cmd[k] = max(lo, min(1.0, v))

    def set_state(self, s):
        with self.lock:
            self.state = s

    def get_state(self):
        with self.lock:
            return dict(self.state)


SH = Shared()


# ───────────────────────── 조종 provider ─────────────────────────
class BrowserProvider(ActionProvider):
    """브라우저 입력으로 RED를 조종하고, 매 틱 상태를 공유 객체에 올린다."""

    def __init__(self, speed=1.0):
        self.speed = speed
        self._t = time.perf_counter()
        self.n = 0

    def compute_action(self, context) -> ActionResult:
        while SH.paused and not SH.quit:
            time.sleep(0.05)
        a = SH.get_cmd()
        SH.frames.append([round(float(x), 4) for x in a])
        self.n += 1
        if self.n % 3 == 0:
            self._publish(context)
        if self.speed > 0:                      # 실시간 페이싱
            tgt = 1.0 / 60.0 / self.speed
            dt = time.perf_counter() - self._t
            if dt < tgt: time.sleep(tgt - dt)
            self._t = time.perf_counter()
        return ActionResult(action=a, source="browser")

    def _publish(self, context):
        try:
            me = context.sim.get_state()          # RED (사람)
            en = context.opponent_sim.get_state() # BLUE (우리 BT)
        except Exception:
            return
        c = math.cos(math.radians(float(me[StateIndex.LAT])))
        de = (float(en[StateIndex.LON]) - float(me[StateIndex.LON])) * c * MLAT
        dn = (float(en[StateIndex.LAT]) - float(me[StateIndex.LAT])) * MLAT
        du = float(en[StateIndex.ALT]) - float(me[StateIndex.ALT])
        dist = math.sqrt(de * de + dn * dn + du * du)

        def ata(src, vx, vy, vz):
            y, p = math.radians(float(src[StateIndex.YAW])), math.radians(float(src[StateIndex.PITCH]))
            f = (math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p))
            return math.degrees(math.acos(max(-1, min(1, (f[0]*vx + f[1]*vy + f[2]*vz) / max(dist, 1e-6)))))

        myA = ata(me, de, dn, du)
        enA = ata(en, -de, -dn, -du)
        cmd = SH.get_cmd()
        SH.set_state({
            "running": True,
            "t": float(me[StateIndex.SIM_TIME]),
            # 상대좌표(m): 나 기준 적 위치 (E, N, Up)
            "rel": [de, dn, du],
            "me": {"lat": float(me[StateIndex.LAT]), "lon": float(me[StateIndex.LON]),
                   "alt": float(me[StateIndex.ALT]), "roll": float(me[StateIndex.ROLL]),
                   "pitch": float(me[StateIndex.PITCH]), "yaw": float(me[StateIndex.YAW]),
                   "kcas": float(me[StateIndex.KCAS]), "hp": float(me[StateIndex.HEALTH])},
            "en": {"alt": float(en[StateIndex.ALT]), "roll": float(en[StateIndex.ROLL]),
                   "pitch": float(en[StateIndex.PITCH]), "yaw": float(en[StateIndex.YAW]),
                   "hp": float(en[StateIndex.HEALTH])},
            "dist": dist, "myATA": myA, "enATA": enA,
            "inWEZ": bool(152 <= dist <= 914 and myA <= 1.0),
            "hit":   bool(152 <= dist <= 914 and enA <= 1.0),
            "cmd": {"roll": float(cmd[0]), "pitch": float(cmd[1]), "yaw": float(cmd[2]), "thr": float(cmd[3])},
        })


# ───────────────────────── 시뮬 스레드 ─────────────────────────
def sim_thread(max_time, speed, seed):
    cfg = {"observation_mode": "tactical16", "ownship_control_mode": "rl", "target_mode": "rl",
           "max_engage_time": max_time, "episode_step_limit": 18000, "min_altitude": 300.0}
    if seed is not None:
        cfg["ownship_randomization"] = {"enabled": True, "radius": 1500.0,
                                        "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 180.0}
    env = DogFightWrapper(
        env_config=cfg,
        ownship_action_provider=BTActionProvider(dll_name="AIP_DCS_ownship.dll"),
        target_action_provider=BrowserProvider(speed=speed),
    )
    try:
        obs, info = (env.reset(seed=seed) if seed is not None else env.reset())
        term = trunc = False
        while not (term or trunc) and not SH.quit:
            obs, r, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))
        env.make_tacviewLog()
        REC_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        out = REC_DIR / f"human_{stamp}.json"
        out.write_text(json.dumps({
            "created": stamp, "max_time": max_time, "speed": speed, "seed": seed,
            "ticks": len(SH.frames),
            "ownship_health": info.get("ownship_health"),
            "target_health": info.get("target_health"),
            "end_condition": info.get("end_condition"),
            "frames": SH.frames,
        }), encoding="utf-8")
        SH.result = {"end": info.get("end_condition"),
                     "blue": info.get("ownship_health"), "red": info.get("target_health"),
                     "rec": out.name}
        s = SH.get_state(); s["running"] = False; s["result"] = SH.result; SH.set_state(s)
        print(f"\n교전 종료: {SH.result['end']}  BLUE(우리BT) {SH.result['blue']}  RED(당신) {SH.result['red']}")
        print(f"녹화: recordings/{out.name}  |  재생: python human_pilot.py replay recordings/{out.name}")
    finally:
        env.close()


# ───────────────────────── HTTP 서버 ─────────────────────────
def make_handler(page_html):
    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a): pass          # 콘솔 조용히

        def _send(self, code, body, ctype="application/json"):
            b = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.startswith("/api/state"):
                self._send(200, json.dumps(SH.get_state()))
            elif self.path.startswith("/vendor/"):
                # three.js 등 기존 대시보드 라이브러리 재사용
                name = os.path.basename(self.path.split("?")[0])
                f = ROOT / "tools" / "dogfight_dashboard" / "static" / "vendor" / name
                if f.exists():
                    ctype = "text/javascript" if name.endswith(".js") else "text/plain"
                    self._send(200, f.read_bytes(), ctype + "; charset=utf-8")
                else:
                    self._send(404, "not found", "text/plain")
            elif self.path in ("/", "/index.html"):
                self._send(200, page_html, "text/html; charset=utf-8")
            else:
                self._send(404, "{}")

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode("utf-8") if n else "{}"
            try: d = json.loads(raw)
            except Exception: d = {}
            if self.path.startswith("/api/input"):
                SH.set_cmd(d)
                if "paused" in d: SH.paused = bool(d["paused"])
                if d.get("quit"): SH.quit = True
                self._send(200, json.dumps({"ok": True}))
            else:
                self._send(404, "{}")
    return H


def main():
    import argparse
    p = argparse.ArgumentParser(description="브라우저에서 3D로 보며 상대기체 조종")
    p.add_argument("--time", type=float, default=200.0)
    p.add_argument("--speed", type=float, default=1.0, help="1.0=실시간, 0.5=반속")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--port", type=int, default=7870)
    args = p.parse_args()

    page = (ROOT / "tools" / "live3d.html").read_text(encoding="utf-8")
    handler = make_handler(page)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", args.port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    url = f"http://127.0.0.1:{args.port}/"
    print(f"\n  3D 조종 화면: {url}")
    print(f"  브라우저가 열립니다. 화면을 클릭한 뒤 조종하세요.")
    print(f"  (교전 {args.time}초 / 속도 {args.speed}x / 당신=RED, 상대=우리 현역 BT)\n")
    try: webbrowser.open(url)
    except Exception: pass

    time.sleep(2.0)   # 브라우저 로드 여유
    t = threading.Thread(target=sim_thread, args=(args.time, args.speed, args.seed), daemon=True)
    t.start()
    try:
        while t.is_alive():
            time.sleep(0.3)
    except KeyboardInterrupt:
        SH.quit = True
    time.sleep(0.5)
    srv.shutdown()


if __name__ == "__main__":
    main()
