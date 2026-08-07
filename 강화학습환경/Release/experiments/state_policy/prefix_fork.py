# -*- coding: utf-8 -*-
"""Run a deterministic, matched-prefix VP counterfactual experiment.

The laboratory DLL keeps the native BT ticking and advances its stateful
controller exactly once per action update. During the requested time window,
only the BT-produced virtual point is replaced. This file is a research harness
and is not a submission policy.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from DogFightEnvWrapper import DogFightWrapper  # noqa: E402
from dogfight.ai.action_provider import ActionContext, ActionResult, clip_action  # noqa: E402
from dogfight.ai.bt_action_provider import BTActionProvider  # noqa: E402
from dogfight.sim.state_schema import StateIndex  # noqa: E402
from rehearsal_10hz import RepeatProvider  # noqa: E402


CANDIDATES = ("baseline", "pure", "lead", "up", "down")


def neu_position(state: np.ndarray) -> np.ndarray:
    """Convert the environment NED position to the DLL's local NEU frame."""
    return np.array(
        [
            float(state[StateIndex.N]),
            float(state[StateIndex.E]),
            -float(state[StateIndex.D]),
        ],
        dtype=np.float64,
    )


def candidate_vp(
    candidate: str,
    target_position_neu: np.ndarray,
    target_velocity_neu: np.ndarray,
    lead_time_s: float,
    vertical_offset_m: float,
) -> np.ndarray:
    if candidate == "pure":
        return target_position_neu.copy()
    if candidate == "lead":
        return target_position_neu + target_velocity_neu * lead_time_s
    if candidate == "up":
        return target_position_neu + np.array([0.0, 0.0, vertical_offset_m])
    if candidate == "down":
        return target_position_neu - np.array([0.0, 0.0, vertical_offset_m])
    raise ValueError(f"candidate does not define an override VP: {candidate}")


class VPForkProvider(BTActionProvider):
    """BT provider that substitutes VP only inside one simulation-time window."""

    def __init__(
        self,
        dll_name: str,
        candidate: str,
        fork_start_s: float,
        fork_duration_s: float,
        lead_time_s: float,
        vertical_offset_m: float,
    ):
        super().__init__(dll_name=dll_name)
        if candidate not in CANDIDATES or candidate == "baseline":
            raise ValueError("VPForkProvider requires a non-baseline candidate")
        if fork_start_s < 0.0 or fork_duration_s <= 0.0:
            raise ValueError("fork window must have non-negative start and positive duration")
        if lead_time_s < 0.0 or vertical_offset_m < 0.0:
            raise ValueError("candidate parameters must be non-negative")
        self.candidate = candidate
        self.fork_start_s = float(fork_start_s)
        self.fork_end_s = float(fork_start_s + fork_duration_s)
        self.lead_time_s = float(lead_time_s)
        self.vertical_offset_m = float(vertical_offset_m)
        self._last_target_position: np.ndarray | None = None
        self._last_time_s: float | None = None
        self.override_updates = 0
        self.first_override_time_s: float | None = None
        self.last_override_time_s: float | None = None

    def reset(self, context: ActionContext | None = None) -> None:
        super().reset(context)
        self._last_target_position = None
        self._last_time_s = None
        self.override_updates = 0
        self.first_override_time_s = None
        self.last_override_time_s = None

    def _target_motion(self, context: ActionContext) -> tuple[float, np.ndarray, np.ndarray]:
        if context.ownship_state is None or context.target_state is None:
            raise RuntimeError("VP fork requires local ownship and target simulator states")
        time_s = float(context.ownship_state[StateIndex.SIM_TIME])
        position = neu_position(context.target_state)
        velocity = np.zeros(3, dtype=np.float64)
        if self._last_target_position is not None and self._last_time_s is not None:
            dt = time_s - self._last_time_s
            if dt > 1e-9:
                velocity = (position - self._last_target_position) / dt
        self._last_target_position = position.copy()
        self._last_time_s = time_s
        return time_s, position, velocity

    def compute_action(self, context: ActionContext) -> ActionResult:
        time_s, target_position, target_velocity = self._target_motion(context)
        active = self.fork_start_s <= time_s < self.fork_end_s
        if not active:
            result = super().compute_action(context)
            result.info.update({"vp_fork_active": False, "vp_fork_candidate": self.candidate})
            return result

        self._ensure_behavior_tree(context)
        model = context.sim.get_model()
        opponent_model = context.opponent_sim.get_model()
        override_vp = candidate_vp(
            self.candidate,
            target_position,
            target_velocity,
            self.lead_time_s,
            self.vertical_offset_m,
        )
        control_action = self.ai_pilot.StepWithVPOverride(
            model.fighterID,
            model._forceSide,
            opponent_model.fighterID,
            opponent_model._forceSide,
            model.get_fdm_data(),
            opponent_model.get_fdm_data(),
            override_vp,
        )
        action = clip_action(
            [
                control_action.RollCMD,
                control_action.PitchCMD,
                control_action.RudderCMD,
                control_action.Throttle,
            ]
        )
        if hasattr(context.sim, "action"):
            context.sim.action[:] = action
        if hasattr(context.sim, "VP"):
            context.sim.VP[:] = override_vp

        self.override_updates += 1
        if self.first_override_time_s is None:
            self.first_override_time_s = time_s
        self.last_override_time_s = time_s
        return ActionResult(
            action=action,
            source=f"bt-vp-fork:{self.candidate}",
            confidence=self.confidence,
            info={
                "vp": override_vp.astype(np.float32),
                "vp_valid": bool(np.all(np.isfinite(override_vp))),
                "vp_fork_active": True,
                "vp_fork_candidate": self.candidate,
                "vp_fork_time_s": time_s,
            },
        )


def _target_provider(name: str):
    if name.upper() == "ACE":
        from ace_pilot import AcePilot

        return AcePilot()
    if name.upper() == "STRAIGHT":
        from straight_pilot import StraightPilot

        return StraightPilot()
    if name.upper() == "SEARCH":
        from search_pilot import SearchPilot

        return SearchPilot()
    return BTActionProvider(dll_name=name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=CANDIDATES, required=True)
    parser.add_argument("--fork-start", type=float, default=152.75)
    parser.add_argument("--fork-duration", type=float, default=3.0)
    parser.add_argument("--lead-time", type=float, default=2.0)
    parser.add_argument("--vertical-offset", type=float, default=500.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--opponent", default="ACE")
    parser.add_argument("--max-time", type=float, default=200.0)
    parser.add_argument("--ownship-dll", default="AIP_DCS_lab.dll")
    args = parser.parse_args()

    if args.candidate == "baseline":
        inner_own = BTActionProvider(dll_name=args.ownship_dll)
        fork_provider = None
    else:
        fork_provider = VPForkProvider(
            args.ownship_dll,
            args.candidate,
            args.fork_start,
            args.fork_duration,
            args.lead_time,
            args.vertical_offset,
        )
        inner_own = fork_provider
    own = RepeatProvider(inner_own, 6)
    target = RepeatProvider(_target_provider(args.opponent), 6)
    env = DogFightWrapper(
        env_config={
            "observation_mode": "tactical16",
            "ownship_control_mode": "rl",
            "target_mode": "rl",
            "max_engage_time": args.max_time,
            "episode_step_limit": 18_000,
            "min_altitude": 300.0,
        },
        ownship_action_provider=own,
        target_action_provider=target,
    )
    try:
        own.reset()
        target.reset()
        _, _ = env.reset(seed=args.seed)
        terminated = truncated = False
        reward_total = 0.0
        info: dict[str, object] = {}
        while not (terminated or truncated):
            _, reward, terminated, truncated, info = env.step(
                np.zeros(4, dtype=np.float32)
            )
            reward_total += float(reward)
        own_health = float(info.get("ownship_health", 1.0))
        target_health = float(info.get("target_health", 1.0))
        print(
            f"[prefix_fork] candidate={args.candidate} seed={args.seed} "
            f"reward={reward_total:.6f} dealt={1.0 - target_health:.6f} "
            f"taken={1.0 - own_health:.6f} end={info.get('end_condition', '')}"
        )
        if fork_provider is not None:
            print(
                f"[prefix_fork] override_updates={fork_provider.override_updates} "
                f"first={fork_provider.first_override_time_s} "
                f"last={fork_provider.last_override_time_s}"
            )
        env.make_tacviewLog()
        print("tacview log saved")
    finally:
        env.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
