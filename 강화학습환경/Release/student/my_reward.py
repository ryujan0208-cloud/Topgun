# -*- coding: utf-8 -*-
"""
[학생 작성 파일] 보상 함수 설계

이 파일이 AI의 "목표"를 결정합니다.
compute_reward()는 매 프레임(1/60초)마다 호출되며,
반환값이 높아지도록 AI가 행동을 학습합니다.

★ 커리큘럼 호환 주의 ★
  커리큘럼(curriculum.py)은 Stage마다 reward_config의 특정 키를 덮어씁니다.
  MY_REWARD_CONFIG의 키 이름이 커리큘럼의 reward_overrides 키와 일치해야
  Stage별 보상 조정이 우리 함수에도 올바르게 적용됩니다.

  커리큘럼이 사용하는 키 목록:
    survival_bonus, pursuit_scale, pursuit_half_angle_deg, pursuit_range_m,
    damage_scale, low_altitude_penalty, win_reward, loss_reward, draw_reward,
    guard_fail_penalty
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from dogfight.sim.state_schema import StateIndex


# =============================================================================
# 보상 파라미터 — 기본값 (커리큘럼이 Stage마다 일부 키를 덮어씀)
# =============================================================================
MY_REWARD_CONFIG = {
    # ── 생존 보너스 ──────────────────────────────────────────────────────────
    # Stage 0에서 커리큘럼이 0.05로 올림 → "살아있으면 매 프레임 +보상"
    # 기본값 0.0: 전투 단계에서는 생존 자체를 보상할 필요 없음
    "survival_bonus": 0.0,

    # ── 매 프레임 패널티 ─────────────────────────────────────────────────────
    "step_penalty": -0.01,

    # ── 추적 보상 (ATA × 거리 gradient) ──────────────────────────────────────
    # Stage마다 커리큘럼이 이 값들을 조정:
    #   Stage 0: pursuit_scale=0.0  → 전투 불필요, 생존만
    #   Stage 1: pursuit_scale=0.5, pursuit_half_angle_deg=60° → 느슨하게 추격
    #   Stage 2~: pursuit_scale=0.3, pursuit_half_angle_deg=30° → 정밀 추격
    "pursuit_scale": 0.4,
    "pursuit_half_angle_deg": 45.0,  # 45° 이내 ATA일 때만 보상
    "pursuit_range_m": 4000.0,       # 4km 이내일 때만 보상

    # ── WEZ 진입 보너스 ───────────────────────────────────────────────────────
    # 격추 가능 구역(거리 152~914m, 시선각 2° 이내) 진입 시 보너스
    "wez_bonus": 2.0,

    # ── 고도 패널티 ───────────────────────────────────────────────────────────
    # 키 이름 반드시 low_altitude_penalty (커리큘럼과 일치)
    # Stage 0에서 커리큘럼이 1.0으로 올림 → "낮게 날면 강하게 패널티"
    # 기본값 0.1 (완만한 패널티)
    "low_altitude_penalty": 0.1,
    # 고도 패널티 적용 기준선 (미터). 대회 사망 고도 305m(1000ft)보다 여유 있게.
    "safe_altitude_m": 450.0,

    # ── 피해 보상 ─────────────────────────────────────────────────────────────
    # Stage 0에서 커리큘럼이 0.0으로 설정 → 생존 단계에서는 전투 보상 없음
    "damage_scale": 25.0,

    # ── 종료 보상 ─────────────────────────────────────────────────────────────
    # Stage 0에서 커리큘럼이 win=0.0, draw=0.0 으로 설정 → 이기고 지는 것 무관
    # 전투 단계에서는 이 값이 복원되어 승패가 가장 큰 보상
    "win_reward": 200.0,
    "loss_reward": -200.0,
    "draw_reward": -50.0,

    # ── Two-Circle 헤드온 가드 실패 패널티 (Stage 4~13에서 사용) ─────────────
    "guard_fail_penalty": -50.0,

    # ── 유리한 위치 선점 ─────────────
    "positioning_scale": 0.3,
    "positioning_half_angle_deg": 60.0,   # AA 60° 이내일 때만 보상
    # ── 불리한 위치 패널티 ─────────────
    "wez_threat_penalty": 2.0,   # 적 사거리에 조준당하면 매 프레임 -2.0 (wez_bonus의 거울상)
}


# =============================================================================
# 보상 계산 함수
# =============================================================================
def compute_reward(
    ownship_state,
    target_state,
    ownship_damage: float,
    target_damage: float,
    geo_info,
    wez_config: dict,
    reward_config: dict,   # MY_REWARD_CONFIG + 커리큘럼 Stage 덮어쓰기가 합쳐진 값
    terminated: bool,
    truncated: bool,
    end_condition: str,
) -> tuple[float, dict]:

    components: dict[str, float] = {}

    # ── 1. 생존 보너스 ────────────────────────────────────────────────────────
    # Stage 0에서만 0.05로 올라감. 다른 Stage에서는 0.0 → 효과 없음
    components["survival"] = float(reward_config.get("survival_bonus", 0.0))

    # ── 2. 매 프레임 패널티 ───────────────────────────────────────────────────
    components["step"] = float(reward_config["step_penalty"])

    # ── 3. 추적 보상 (ATA × 거리 gradient) ───────────────────────────────────
    distance = geo_info._get_distance(ownship_state, target_state)
    ata = abs(geo_info._get_antenna_train_angle(ownship_state, target_state, False))

    half_angle = float(reward_config["pursuit_half_angle_deg"])
    pursuit_range = float(reward_config["pursuit_range_m"])

    ata_factor   = max(0.0, 1.0 - ata / half_angle)
    range_factor = max(0.0, 1.0 - distance / pursuit_range)

    components["pursuit"] = float(reward_config["pursuit_scale"]) * ata_factor * range_factor

    # ── 3.5. 위치우위 보상 (AA × 거리) ──────────────────────────────────
    aa = abs(geo_info._get_aspect_angle(ownship_state, target_state, False))
    positioning_half = float(reward_config["positioning_half_angle_deg"])
    aa_factor = max(0.0, 1.0 - aa / positioning_half)
    # range_factor는 위 pursuit에서 이미 계산됨 → 재사용
    components["positioning"] = float(reward_config["positioning_scale"]) * aa_factor * range_factor

    # ── 4. WEZ 진입 보너스 ────────────────────────────────────────────────────
    in_wez = False
    if wez_config:
        wez_half_angle = float(wez_config.get("angle_deg", 2.0)) / 2.0
        in_wez = (
            float(wez_config["min_range_m"]) <= distance <= float(wez_config["max_range_m"])
            and ata <= wez_half_angle
        )
    components["wez"] = float(reward_config.get("wez_bonus", 0.0)) if in_wez else 0.0

    # ── 4.5. 회피 페널티 (적이 나를 WEZ에 잡으면 −) ──────────────────────
    target_ata = abs(geo_info._get_antenna_train_angle(target_state, ownship_state, False))
    in_enemy_wez = False
    if wez_config:
        enemy_wez_half = float(wez_config.get("angle_deg", 2.0)) / 2.0
        in_enemy_wez = (
            float(wez_config["min_range_m"]) <= distance <= float(wez_config["max_range_m"])
            and target_ata <= enemy_wez_half
        )
    components["wez_threat"] = -float(reward_config.get("wez_threat_penalty", 0.0)) if in_enemy_wez else 0.0

    # ── 5. 고도 패널티 ────────────────────────────────────────────────────────
    altitude = float(ownship_state[StateIndex.ALT])
    safe_alt = float(reward_config.get("safe_altitude_m", 450.0))
    if altitude < safe_alt:
        # 낮을수록 패널티를 강하게 (0~2배 스케일)
        depth = (safe_alt - altitude) / safe_alt
        components["altitude"] = -float(reward_config["low_altitude_penalty"]) * (1.0 + depth)
    else:
        components["altitude"] = 0.0

    # ── 6. 피해 보상 ──────────────────────────────────────────────────────────
    components["damage"] = float(reward_config["damage_scale"]) * (target_damage - ownship_damage)

    # ── 7. 종료 보상 ──────────────────────────────────────────────────────────
    terminal = 0.0
    if terminated or truncated:
        ownship_health = float(ownship_state[StateIndex.HEALTH])
        target_health  = float(target_state[StateIndex.HEALTH])

        if end_condition == "two circle headon guard fail":
            # Stage 4~13: 헤드온 가드 실패 (규정된 궤도 이탈)
            terminal = float(reward_config.get("guard_fail_penalty", -50.0))
        elif target_health <= 0.0 < ownship_health:
            terminal = float(reward_config["win_reward"])
        elif ownship_health <= 0.0 < target_health:
            terminal = float(reward_config["loss_reward"])
        else:
            terminal = float(reward_config["draw_reward"])
    components["terminal"] = terminal

    return float(sum(components.values())), components


__all__ = ["MY_REWARD_CONFIG", "compute_reward"]
