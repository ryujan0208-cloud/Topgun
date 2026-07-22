# -*- coding: utf-8 -*-
"""배치 특정 시드를 재현하고 tacview 로그를 저장(궤적 진단용).
run_batch_local.py 와 동일한 env 구성 + 단일 시드 + make_tacviewLog()."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path: sys.path.insert(0, str(SRC))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.bt_rule_manager import activate_rule_xml

p = argparse.ArgumentParser()
p.add_argument("--ownship-bt-dll", required=True)
p.add_argument("--target-bt-dll", required=True)
p.add_argument("--seed", type=int, required=True)
p.add_argument("--max-engage-time", type=float, default=200.0)
a = p.parse_args()

env_config = {
    "observation_mode": "tactical16", "observation_module": "",
    "ownship_control_mode": "rl", "target_mode": "rl",
    "max_engage_time": a.max_engage_time, "episode_step_limit": 18000, "min_altitude": 300.0,
    "ownship_randomization": {"enabled": True, "radius": 1500.0, "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 180.0},
}
with activate_rule_xml(None, ROOT):
    env = DogFightWrapper(
        env_config=env_config,
        ownship_action_provider=BTActionProvider(dll_name=a.ownship_bt_dll),
        target_action_provider=BTActionProvider(dll_name=a.target_bt_dll),
    )
    try:
        # 배치와 동일 경로 재현: seed 0..target 순차 reset (reset이 누적상태에 의존)
        for k in range(0, a.seed + 1):
            obs, info = env.reset(seed=k)
            term = trunc = False; tot = 0.0; steps = 0
            while not (term or trunc):
                obs, r, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))
                tot += float(r); steps += 1
            print(f"seed={k} reward={tot:.1f} own={info.get('ownship_health')} tgt={info.get('target_health')}")
        env.make_tacviewLog()  # 마지막(target) seed 판 궤적 기록
        print("log saved (target seed)")
    finally:
        env.close()
