# -*- coding: utf-8 -*-
"""SearchPilot — 매 틱 여러 조종안을 짧게 예측해보고 가장 좋은 것을 고르는 상대기체.

[무엇인가]
사용자가 제시한 "VP를 여러 개 찍어 최적을 찾는 기체"의 구현.
RL이 **학습**으로 도달하는 정책("뒤를 잡는 최적 궤도")을 **탐색**으로 근사한다.
대회에서 만날 RL 상대의 대리 역할을 하되, 결정론적이라 재현·디버깅이 된다.

[왜 이게 되는가 — 2026-07-24 MPC 기각과 무엇이 다른가]
그때 기각한 건 **우리 제출 기체**에 대한 것이었다. 이유:
  (1) BT는 VP만 내고 실제 궤적은 Controller_CY(블랙박스) + JSBSim 6DOF가 만든다.
      "이 VP를 주면 T초 뒤 어디 있나"를 예측할 모델이 없었다.
  (2) 10Hz / 100ms 예산.
**상대기체에는 둘 다 해당하지 않는다:**
  (1) 상대는 VP를 쓸 필요가 없다. ACE처럼 **스틱을 직접** 낸다
      -> VP->제어기->스틱이라는 가장 어려운 부분이 통째로 빠진다.
  (2) 로컬 스파링용이라 연산 예산 제약이 없다.
그리고 **우리는 이미 포워드 모델을 실측해 갖고 있다**:
  tools_diag/corner_speed.py (속도별 선회율/반경/침하율)
  tools_diag/turn_perf2.py   (뱅크별 지속/순간 선회율)
1~2초 외삽에는 이 표로 충분하다.

[한계 — 정직하게]
* 근사 운동학이라 실제 6DOF와 어긋난다. 특히 실속·고받음각 영역은 못 맞춘다.
* 상대(=우리 BT)의 반응을 "현재 선회를 유지한다"고 가정한다(open-loop).
  근접 교전에서 상호작용이 강할 때 부정확하다.
* 구간별 탐욕 선택이라 전역 최적이 아니다.
-> 그래도 **우리 스파링 세트에 없는 종류의 상대**를 만든다는 목적에는 부합한다.
   기존 상대들은 전부 내가 손으로 규칙을 짠 것이라 내 가정을 공유한다.
   이건 "탐색이 고른 행동"이라 내 가정 밖으로 나갈 수 있다.
"""
from __future__ import annotations
import math
import numpy as np

from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0
D2R = math.pi / 180.0
R2D = 180.0 / math.pi

# ── 실측 포워드 모델 (tools_diag/corner_speed.py, 뱅크82 수평선회) ──
#    속도 -> 총 선회율(도/초). 사이는 선형 보간.
SPD_TBL  = [182.0, 191.0, 200.0, 204.0, 210.0, 220.0, 287.0, 329.0]
RATE_TBL = [  8.1,   8.6,   9.4,   9.8,  10.1,  11.0,  12.8,  11.0]
# 뱅크 보정 (turn_perf2: 뱅크82 지속 11.3 / 뱅크110 하강나선 25.4 -> 약 2.2배)
#   뱅크가 90도를 넘으면 중력이 선회를 돕는다. 82도를 1.0으로 정규화.
def bank_gain(bank_deg):
    b = abs(bank_deg)
    if b <= 82.0:
        return max(0.15, b / 82.0)          # 얕은 뱅크는 선회율이 준다
    return 1.0 + min(1.2, (b - 82.0) / 28.0 * 1.2)   # 110도에서 약 2.2배


def turn_rate(speed, bank_deg):
    """실측표 기반 총 선회율(도/초)."""
    s = max(SPD_TBL[0], min(SPD_TBL[-1], speed))
    for i in range(1, len(SPD_TBL)):
        if s <= SPD_TBL[i]:
            f = (s - SPD_TBL[i-1]) / (SPD_TBL[i] - SPD_TBL[i-1])
            base = RATE_TBL[i-1] + f * (RATE_TBL[i] - RATE_TBL[i-1])
            break
    else:
        base = RATE_TBL[-1]
    return base * bank_gain(bank_deg)


def vert_rate(speed, bank_deg, pull):
    """수직 속도(m/s). +면 상승.

    ★ 초판의 결함: sink_rate()가 **하강만** 표현해서 탐색이 고도 회복 선택지를
      아예 못 봤다. 3판 전부 지면 충돌(target altitude below min).
    [수정] 당김의 수직 성분은 cos(뱅크)에 비례한다.
      뱅크 0도  -> 순수 상승
      뱅크 90도 -> 수평 선회(고도 유지)
      뱅크 90도 초과 -> cos<0 = 하강 나선 (실측 뱅크110 하강나선과 일치)
      여기에 선회 항력에 의한 기본 침하를 더한다."""
    b = bank_deg * D2R
    climb = speed * pull * math.cos(b) * 0.45
    drag_sink = abs(math.sin(b)) * pull * 55.0        # 선회 자체의 에너지 손실
    return climb - drag_sink


class SearchPilot(ActionProvider):
    """후보 조종안을 각각 짧게 굴려보고 최선을 고른다."""

    # 후보 = (롤, 피치, 스로틀). 부호: pitch<0 = 기수 올림, roll>0 = 오른쪽
    CANDIDATES = [
        ( 0.0,  0.0, 1.00),   # 직진 가속
        ( 0.0, -1.0, 1.00),   # 수직 당김
        ( 1.0, -1.0, 0.85),   # 우선회
        (-1.0, -1.0, 0.85),   # 좌선회
        ( 1.0, -1.0, 0.30),   # 우하강나선(감속)
        (-1.0, -1.0, 0.30),   # 좌하강나선(감속)
        ( 1.0, -0.5, 1.00),   # 우완선회 가속
        (-1.0, -0.5, 1.00),   # 좌완선회 가속
        ( 0.0, -1.0, 0.20),   # 급감속 + 당김
        ( 0.0, -0.7, 1.00),   # 상승(고도 회복) — 초판에 없어서 바닥에 박았다
    ]

    HORIZON = 1.5        # 예측 지평선(초). 근사 모델이라 짧게.
    STEPS   = 6          # 롤아웃 스텝 수
    REPLAN  = 6          # N틱마다 재계획(그 사이엔 같은 명령 유지 = 10Hz 상당)

    def __init__(self, horizon=None, replan=None):
        if horizon: self.HORIZON = horizon
        if replan:  self.REPLAN = replan
        self._n = 0
        self._last = None
        self._prev = None            # (t, lat, lon, alt) 속도 추정용

    # ── 상태 추출 ──
    def _state(self, s):
        lat, lon, alt = float(s[StateIndex.LAT]), float(s[StateIndex.LON]), float(s[StateIndex.ALT])
        roll, pitch, yaw = (float(s[StateIndex.ROLL]), float(s[StateIndex.PITCH]),
                            float(s[StateIndex.YAW]))
        return lat, lon, alt, roll, pitch, yaw

    def _speed(self, t, lat, lon, alt):
        v = 250.0
        if self._prev is not None:
            dt = t - self._prev[0]
            if dt > 1e-6:
                c = math.cos(lat * D2R)
                dx = (lon - self._prev[2]) * c * MLAT
                dy = (lat - self._prev[1]) * MLAT
                dz = alt - self._prev[3]
                v = math.sqrt(dx*dx + dy*dy + dz*dz) / dt
        self._prev = (t, lat, lon, alt)
        return v if v > 20.0 else 250.0

    # ── 근사 롤아웃 ──
    def _rollout(self, me, en, cand):
        """후보 조종안을 HORIZON초 굴려 예상 ATA/거리를 낸다.
        me/en = (n, e, alt, heading_deg, pitch_deg, speed, bank_deg)"""
        roll_cmd, pitch_cmd, thr = cand
        mn, me_, malt, mhdg, mpit, mspd, mbank = me
        en_n, en_e, en_alt, en_hdg, en_pit, en_spd, en_rate = en

        dt = self.HORIZON / self.STEPS
        # 조종안이 만드는 목표 뱅크(롤 명령을 그대로 뱅크 속도로 본다)
        tgt_bank = mbank + roll_cmd * 60.0 * self.HORIZON
        tgt_bank = max(-140.0, min(140.0, tgt_bank))

        for _ in range(self.STEPS):
            mbank += (tgt_bank - mbank) * 0.5
            pull = -pitch_cmd                       # 0~1
            rate = turn_rate(mspd, mbank) * max(0.0, pull)
            mhdg += math.copysign(rate, mbank) * dt
            # 속도: 스로틀과 항력(선회)
            mspd += (thr - 0.55) * 40.0 * dt - abs(rate) * 0.35 * dt
            mspd = max(60.0, min(400.0, mspd))
            malt += vert_rate(mspd, mbank, pull) * dt
            mn += mspd * math.cos(mhdg * D2R) * dt
            me_ += mspd * math.sin(mhdg * D2R) * dt
            # 상대는 현재 선회를 유지한다고 가정(open-loop)
            en_hdg += en_rate * dt
            en_n += en_spd * math.cos(en_hdg * D2R) * dt
            en_e += en_spd * math.sin(en_hdg * D2R) * dt

        de, dn, du = en_e - me_, en_n - mn, en_alt - malt
        d = math.sqrt(de*de + dn*dn + du*du) or 1.0
        fe = math.sin(mhdg * D2R); fn = math.cos(mhdg * D2R)
        ata = math.degrees(math.acos(max(-1.0, min(1.0, (fe*de + fn*dn) / d))))
        return d, ata, malt, mspd

    def compute_action(self, context):
        self._n += 1
        if self._last is not None and (self._n % self.REPLAN) != 0:
            return self._last

        s = context.sim.get_state()
        o = context.opponent_sim.get_state()
        t = float(s[StateIndex.SIM_TIME])
        mlat, mlon, malt, mroll, mpit, myaw = self._state(s)
        elat, elon, ealt, eroll, epit, eyaw = self._state(o)
        mspd = self._speed(t, mlat, mlon, malt)

        c = math.cos(mlat * D2R)
        me = (0.0, 0.0, malt, myaw, mpit, mspd, mroll)
        en = ((elat - mlat) * MLAT, (elon - mlon) * c * MLAT, ealt, eyaw, epit,
              max(60.0, mspd), math.copysign(turn_rate(mspd, eroll), eroll) if abs(eroll) > 5 else 0.0)

        best, best_score = None, -1e18
        for cand in self.CANDIDATES:
            d, ata, alt, spd = self._rollout(me, en, cand)
            # 점수: 뒤를 잡는 것이 목표 -> ATA를 줄이고 사거리 안으로.
            score = -ata * 2.0
            if 152.4 <= d <= 914.4:
                score += 60.0                      # 사거리 안이면 보너스
            score -= abs(d - 500.0) * 0.02         # 500m 부근을 선호
            # 고도 안전은 **하드 제약**으로. 규정상 300m는 즉시 패배이고,
            # 지평선이 1.5초라 예측만으로는 위험을 늦게 본다(초판이 바닥에 박은 이유).
            if alt < 2000.0:
                score -= (2000.0 - alt) * 20.0     # 사실상 거부
            elif alt < 3000.0:
                score -= (3000.0 - alt) * 0.3
            if spd < 150.0:
                score -= (150.0 - spd) * 1.5       # 실속 회피
            if score > best_score:
                best_score, best = score, cand

        roll_cmd, pitch_cmd, thr = best
        self._last = ActionResult(
            action=np.array([roll_cmd, pitch_cmd, 0.0, thr], dtype=np.float32),
            source="search")
        return self._last

    def reset(self, context=None):
        self._n = 0
        self._last = None
        self._prev = None
