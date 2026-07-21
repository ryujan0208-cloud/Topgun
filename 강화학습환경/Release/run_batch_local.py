# -*- coding: utf-8 -*-
"""BT vs BT 시드 배치 검증 하네스 (우리 팀 자작, 2026-07-20).

run_local_dogfight.py 는 시드/랜덤 스폰 개념이 없어 매판 동일한 정면 5km 시나리오만
반복한다. 이 스크립트는 같은 환경 구성을 그대로 쓰되, env.reset(seed=k) +
ownship_randomization 으로 판마다 다른 초기 배치를 만들어 N시드 회귀 검증을 돌린다.
(팀원의 run_batch_dogfight.py 와 같은 목적. 주최측 src/dogfight 는 수정하지 않음)

사용 예:
  python run_batch_local.py --ownship-bt-dll AIP_v1.dll --target-bt-dll AIP_v0.dll \
      --num-seeds 15 --max-engage-time 200 --tag v1_vs_v0
"""
from __future__ import annotations

import argparse
import csv
import time
from datetime import datetime
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent   # Release/ 루트
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider
from dogfight.ai.bt_rule_manager import activate_rule_xml


def parse_args():
    p = argparse.ArgumentParser(description="Seeded batch dogfight harness (BT vs BT).")
    p.add_argument("--ownship-bt-dll", required=True)
    p.add_argument("--target-bt-dll", required=True)
    p.add_argument("--bt-rule-xml", default=None,
                   help="(선택) Rule_forTraining.xml 을 임시 교체할 XML. 버전별 XML을 읽는 DLL이면 불필요.")
    p.add_argument("--num-seeds", type=int, default=15)
    p.add_argument("--start-seed", type=int, default=0)
    p.add_argument("--max-engage-time", type=float, default=200.0, help="실제 대회 규정 200초 기본")
    p.add_argument("--episode-step-limit", type=int, default=18000)
    p.add_argument("--min-altitude", type=float, default=300.0)
    p.add_argument("--radius", type=float, default=1500.0, help="ownship 초기위치 랜덤 반경(m)")
    p.add_argument("--r-heading", type=float, default=180.0, help="초기 헤딩 랜덤(±deg)")
    p.add_argument("--r-roll", type=float, default=10.0)
    p.add_argument("--r-pitch", type=float, default=5.0)
    p.add_argument("--tag", default="batch", help="결과 CSV 파일명 태그")
    return p.parse_args()


def classify(end_condition: str, own_hp: float, tgt_hp: float) -> str:
    e = (end_condition or "").lower()
    tgt_down = (tgt_hp is not None and tgt_hp <= 0.0) or ("target" in e and ("dead" in e or "below" in e))
    own_down = (own_hp is not None and own_hp <= 0.0) or ("ownship" in e and ("dead" in e or "below" in e))
    if tgt_down and not own_down:
        return "WIN"
    if own_down and not tgt_down:
        return "LOSS"
    if "fdm" in e or "nan" in e:
        return "ERROR"
    return "DRAW"


def main():
    args = parse_args()

    env_config = {
        "observation_mode": "tactical16",
        "observation_module": "",
        "ownship_control_mode": "rl",       # BT provider 가 액션을 밀어넣는 경로 (run_local_dogfight 동일)
        "target_mode": "rl",
        "max_engage_time": args.max_engage_time,
        "episode_step_limit": args.episode_step_limit,
        "min_altitude": args.min_altitude,
        "ownship_randomization": {
            "enabled": True,
            "radius": args.radius,
            "r_roll": args.r_roll,
            "r_pitch": args.r_pitch,
            "r_heading": args.r_heading,
        },
    }

    out_dir = ROOT / "artifacts" / "batch_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = out_dir / f"{args.tag}_{stamp}.csv"

    rows = []
    with activate_rule_xml(args.bt_rule_xml, ROOT):
        env = DogFightWrapper(
            env_config=env_config,
            ownship_action_provider=BTActionProvider(dll_name=args.ownship_bt_dll),
            target_action_provider=BTActionProvider(dll_name=args.target_bt_dll),
        )
        try:
            for k in range(args.start_seed, args.start_seed + args.num_seeds):
                t0 = time.time()
                obs, info = env.reset(seed=k)
                terminated = truncated = False
                total_reward = 0.0
                steps = 0
                while not (terminated or truncated):
                    obs, reward, terminated, truncated, info = env.step(np.zeros(4, dtype=np.float32))
                    total_reward += float(reward)
                    steps += 1
                own_hp = float(info.get("ownship_health", float("nan")))
                tgt_hp = float(info.get("target_health", float("nan")))
                end = str(info.get("end_condition", ""))
                outcome = classify(end, own_hp, tgt_hp)
                wall = time.time() - t0
                rows.append({
                    "seed": k, "outcome": outcome, "reward": round(total_reward, 2),
                    "steps": steps, "sim_s": round(steps / 60.0, 1),
                    "end_condition": end, "own_hp": own_hp, "tgt_hp": tgt_hp,
                    "wall_s": round(wall, 1),
                })
                print(f"[seed {k:>3}] {outcome:5} reward={total_reward:9.2f} "
                      f"steps={steps:5} end={end} hp(own/tgt)={own_hp:.2f}/{tgt_hp:.2f} "
                      f"({wall:.0f}s wall)", flush=True)
        finally:
            env.close()

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n = len(rows)
    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    losses = sum(1 for r in rows if r["outcome"] == "LOSS")
    draws = sum(1 for r in rows if r["outcome"] == "DRAW")
    errors = sum(1 for r in rows if r["outcome"] == "ERROR")
    mean_r = sum(r["reward"] for r in rows) / max(n, 1)
    print("\n===== SUMMARY =====")
    print(f"ownship={args.ownship_bt_dll}  vs  target={args.target_bt_dll}  ({n} seeds)")
    print(f"W/L/D{'/E' if errors else ''}: {wins}/{losses}/{draws}" + (f"/{errors}" if errors else ""))
    print(f"mean reward: {mean_r:.2f}")
    print(f"csv: {out_csv}")


if __name__ == "__main__":
    main()
