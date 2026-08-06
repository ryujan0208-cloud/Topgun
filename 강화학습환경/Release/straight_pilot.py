# -*- coding: utf-8 -*-
"""StraightPilot — 진짜 직선 수평 비행만 하는 상대. 순수 추격/조준 능력 측정용.

[왜 필요한가]
`AIP_dummy.dll`을 직선이라 가정하고 썼는데 실측해보니 **80도 뱅크로 계속 원선회**하는
기체였다(요 7.58도/s, 롤 중앙 80.5도). 가정을 검증 안 한 내 실수다.
상대가 아무것도 안 할 때 우리 기체의 순수 성능을 보려면 진짜 직선 상대가 필요하다.
"""
from __future__ import annotations
import numpy as np
from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex


class StraightPilot(ActionProvider):
    """날개 수평 + 고도 유지 + 일정 스로틀. 회피도 추격도 하지 않는다."""

    def __init__(self, throttle=0.75):
        self.thr = throttle

    def compute_action(self, context):
        s = context.sim.get_state()
        roll  = float(s[StateIndex.ROLL])
        pitch = float(s[StateIndex.PITCH])
        # 날개를 수평으로, 피치를 0으로 되돌리는 약한 비례 제어
        roll_cmd  = max(-1.0, min(1.0, -roll * 0.03))
        pitch_cmd = max(-1.0, min(1.0,  pitch * 0.03))   # pitch<0이 기수 올림이므로 부호 그대로
        return ActionResult(
            action=np.array([roll_cmd, pitch_cmd, 0.0, self.thr], dtype=np.float32),
            source="straight")

    def reset(self, context=None):
        return None
