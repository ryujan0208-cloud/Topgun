# -*- coding: utf-8 -*-
"""독립 파이터 커리큘럼 — 4단계, 능력 하나씩 추가, 수동 진급.

  Stage 0: 생존        (fixed)        survival·altitude
  Stage 1: 기초 추격    (fixed)        +pursuit
  Stage 2: 위치+사거리  (loiter)       +positioning +wez
  Stage 3: 실전+회피    (behavior_tree) +damage +wez_threat +승패

진행 방식 (수동 진급 — advance_conditions={}):
  · 각 Stage를 학습 → training_log.csv의 지표(crash_rate 등)를 눈으로 확인
  · 충분하면 다음 Stage 주석을 풀고:
      python train_curriculum.py ... --start-stage N \
        --init-bundle artifacts/curriculum/trinity/<tag>/stage_<N-1>_<name>/final_bundle

Run:
  python scripts/run_experiment.py experiments/student_sac_mlp.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dogfight.ai.curriculum import CurriculumStage


def get_stages() -> list[CurriculumStage]:
    return [
        # ══════════════════════════════════════════════════════════════════
        # Stage 0: 순수 비행 생존
        #   목표: 추락하지 않고 오래 난다 (crash_rate < 0.20)
        # ══════════════════════════════════════════════════════════════════
        CurriculumStage(
            index=0,
            name="flight_survival",
            description="생존과 스로틀 제어. 고정 타겟.",
            target_mode="fixed",
            episode_step_limit=3600,          # 60초
            max_iterations=400,               # 생존 배울 시간 넉넉히 (200 → 400)
            checkpoint_interval=5,
            reward_overrides={
                # ── 켜는 것 (생존) ──
                "survival_bonus": 0.05,       # 살아있으면 매 프레임 +
                "low_altitude_penalty": 1.0,  # 낮게 날면 강한 벌 (기본 0.1의 10배)
                "loss_reward": -100.0,        # 추락하면 큰 벌 (-50 → -100, 회피 동기 강화)
                # ── 끄는 것 (0으로) ──
                "pursuit_scale": 0.0,
                "positioning_scale": 0.0,
                "wez_bonus": 0.0,
                "wez_threat_penalty": 0.0,
                "damage_scale": 0.0,
                "win_reward": 0.0,
                "draw_reward": 0.0,
            },
            randomization={
                "enabled": True,
                "radius": 1.0,                # 0이면 ValueError → 1.0 (사실상 위치 고정)
                "r_roll": 5.0,
                "r_pitch": 5.0,
                "r_heading": 15.0,
            },
            advance_conditions={},            # 수동 진급 (crash_rate 보고 판단)
            advance_window=10,
        ),

        # ══════════════════════════════════════════════════════════════════
        # Stage 1: 기초 추격  (Stage 0 졸업 후 주석 해제)
        #   목표: 고정 타겟에 기수를 정렬하고 접근 (ep_min_distance ↓)
        # ══════════════════════════════════════════════════════════════════
        # CurriculumStage(
        #     index=1,
        #     name="basic_pursuit",
        #     description="고정 타겟에 기수를 정렬하고 접근 (기초 추격).",
        #     target_mode="fixed",          # 기초는 고정 적부터
        #     episode_step_limit=3600,
        #     max_iterations=300,
        #     checkpoint_interval=5,
        #     reward_overrides={
        #         "survival_bonus": 0.02,       # 생존은 이미 배웠으니 낮춤
        #         "low_altitude_penalty": 0.7,  # 추격 중 추락 방지 (여전히 강하게)
        #         "loss_reward": -100.0,
        #         "pursuit_scale": 0.5,         # [ON] 기수를 적에게 정렬하면 +
        #         "positioning_scale": 0.0,     # 위치우위는 Stage 2
        #         "wez_bonus": 0.0,
        #         "wez_threat_penalty": 0.0,
        #         "damage_scale": 0.0,
        #         "win_reward": 0.0,            # "격추" 아니라 "접근"이 목표
        #         "draw_reward": 0.0,
        #     },
        #     randomization={
        #         "enabled": True,
        #         "radius": 300, "r_roll": 5, "r_pitch": 5, "r_heading": 30,
        #     },
        #     advance_conditions={},
        #     advance_window=10,
        # ),

        # ══════════════════════════════════════════════════════════════════
        # Stage 2: 위치우위 + 사거리  (Stage 1 졸업 후 주석 해제)
        #   목표: 선회하는 적의 6시로 진입 + WEZ 점유 (ep_wez_steps ↑)
        # ══════════════════════════════════════════════════════════════════
        # CurriculumStage(
        #     index=2,
        #     name="positioning_wez",
        #     description="선회하는 적(loiter)의 6시로 진입하고 사거리 안에 든다.",
        #     target_mode="loiter",         # 움직이는 적
        #     episode_step_limit=3600,
        #     max_iterations=400,
        #     checkpoint_interval=5,
        #     reward_overrides={
        #         "survival_bonus": 0.0,
        #         "low_altitude_penalty": 0.3,
        #         "loss_reward": -100.0,
        #         "pursuit_scale": 0.3,         # 추격 유지
        #         "positioning_scale": 0.3,     # [ON] 적 6시 뒤 점유
        #         "wez_bonus": 2.0,             # [ON] 사거리+정조준 보너스
        #         "wez_threat_penalty": 0.0,
        #         "damage_scale": 0.0,
        #         "win_reward": 50.0,
        #         "draw_reward": 0.0,
        #     },
        #     randomization={
        #         "enabled": True,
        #         "radius": 800, "r_roll": 10, "r_pitch": 8, "r_heading": 90,
        #     },
        #     advance_conditions={},
        #     advance_window=10,
        # ),

        # ══════════════════════════════════════════════════════════════════
        # Stage 3: 실전 + 회피  (Stage 2 졸업 후 주석 해제)
        #   목표: BT 상대로 실제 교전 — 격추 + 회피 (win_rate ↑)
        # ══════════════════════════════════════════════════════════════════
        # CurriculumStage(
        #     index=3,
        #     name="full_dogfight",
        #     description="BT 상대 실전. 격추하고, 맞지 않게 회피한다.",
        #     target_mode="behavior_tree",  # 공격하는 실제 상대
        #     episode_step_limit=3600,
        #     max_iterations=800,
        #     checkpoint_interval=5,
        #     reward_overrides={
        #         "survival_bonus": 0.0,
        #         "low_altitude_penalty": 0.1,
        #         "pursuit_scale": 0.3,
        #         "positioning_scale": 0.3,
        #         "wez_bonus": 2.0,
        #         "wez_threat_penalty": 2.0,    # [ON] 회피 (적이 공격하는 단계)
        #         "damage_scale": 25.0,         # [ON] 실제 피해
        #         "win_reward": 200.0,          # [ON] 승리
        #         "loss_reward": -200.0,
        #         "draw_reward": -50.0,
        #     },
        #     randomization={
        #         "enabled": True,
        #         "radius": 1500, "r_roll": 15, "r_pitch": 10, "r_heading": 180,
        #     },
        #     advance_conditions={},
        #     advance_window=10,
        # ),
    ]


__all__ = ["get_stages"]
