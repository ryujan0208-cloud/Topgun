# -*- coding: utf-8 -*-
# 제출 경로 리허설: ACTION_REPEAT=6 에뮬레이션.
# 서버에선 BT가 6 PlaneInfo pair마다 1회 호출되고 CMD가 6프레임 유지된다.
# 로컬 env는 step_ratio와 무관하게 provider를 서브스텝(60Hz)마다 호출하므로,
# provider를 감싸 N회 중 1회만 DLL을 호출하고 나머지는 직전 스틱을 반환해 재현한다.
# 로깅은 60Hz 그대로라 기존 분석 스크립트(wez_audit/ata_split/overshoot)를 그대로 쓴다.
#
# 사용: (cwd = 강화학습환경/Release)
#   python rehearsal_10hz.py <ownship_repeat> <target_repeat> [max_time]
#   예: python rehearsal_10hz.py 6 1     -> 우리 10Hz vs 권정환 60Hz (최악 케이스)
#       python rehearsal_10hz.py 6 6     -> 양쪽 10Hz (대칭 케이스)
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider


class RepeatProvider:
    """N회 호출 중 1회만 내부 BT를 실제 호출, 나머지는 직전 결과 유지 (CMD hold 재현)."""
    def __init__(self, inner, n: int):
        self._inner = inner
        self._n = max(1, int(n))
        self._count = 0
        self._last = None

    def compute_action(self, context):
        if self._count % self._n == 0 or self._last is None:
            self._last = self._inner.compute_action(context)
        self._count += 1
        return self._last

    def reset(self, context=None):
        self._count = 0
        self._last = None
        return self._inner.reset(context)

    def __getattr__(self, name):          # close() 등 나머지는 위임
        return getattr(self._inner, name)


def main():
    own_rep = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    tgt_rep = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    max_t   = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
    seeds   = int(sys.argv[4]) if len(sys.argv) > 4 else 1   # 1이면 고정스폰 1판(기존 동작)
    start_seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0  # 특정 시드 재현용

    own = BTActionProvider(dll_name="AIP_DCS_ownship.dll")
    tgt = BTActionProvider(dll_name="AIP_kwon.dll")
    if own_rep > 1:
        own = RepeatProvider(own, own_rep)
    if tgt_rep > 1:
        tgt = RepeatProvider(tgt, tgt_rep)

    cfg = {
        "observation_mode": "tactical16",
        "ownship_control_mode": "rl",
        "target_mode": "rl",
        "max_engage_time": max_t,
        "episode_step_limit": 18000,
        "min_altitude": 300.0,
    }
    if seeds > 1 or start_seed > 0:  # run_batch_local과 동일한 랜덤 스폰
        cfg["ownship_randomization"] = {  # run_batch_local 기본값과 동일
            "enabled": True, "radius": 1500.0,
            "r_roll": 10.0, "r_pitch": 5.0, "r_heading": 180.0,
        }

    env = DogFightWrapper(
        env_config=cfg,
        ownship_action_provider=own,
        target_action_provider=tgt,
    )
    try:
        dmg_sum = 0.0; taken_sum = 0.0; results = []
        for k in range(start_seed, start_seed + seeds):
            if isinstance(own, RepeatProvider): own.reset()
            if isinstance(tgt, RepeatProvider): tgt.reset()
            obs, info = env.reset(seed=k) if (seeds > 1 or start_seed > 0) else env.reset()
            terminated = truncated = False
            total = 0.0
            while not (terminated or truncated):
                obs, r, terminated, truncated, info = env.step(np.zeros(4, dtype=np.float32))
                total += r
            oh = float(info.get("ownship_health", 1.0))
            th = float(info.get("target_health", 1.0))
            dmg_sum += (1.0 - th); taken_sum += (1.0 - oh)
            results.append((k, total, oh, th, info.get("end_condition", "")))
            print(f"[seed {k}] reward={total:9.2f} ownHP={oh:.4f} tgtHP={th:.4f} {info.get('end_condition','')}", flush=True)
        print(f"\n[rehearsal own_rep={own_rep} tgt_rep={tgt_rep} seeds={seeds}]")
        print(f"SUMMARY dealt={dmg_sum:.4f} taken={taken_sum:.4f} "
              f"mean_reward={sum(r[1] for r in results)/len(results):.2f}")
        env.make_tacviewLog()   # 마지막 에피소드 리플레이 저장
        print("tacview log saved (last episode)")
    finally:
        env.close()


if __name__ == "__main__":
    main()
