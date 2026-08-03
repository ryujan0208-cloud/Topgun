# -*- coding: utf-8 -*-
"""
ACE — 스파링 전용 최강 상대기체 (BT 아님, 파이썬 직접 조종).

핵심 우위: **스틱을 직접 명령한다.**
  우리 제출 기체는 규격상 VP(조준점)만 찍고 Controller_CY가 스틱으로 변환한다.
  그 파이프라인에는 알려진 제약이 있다(LOS>=90도 피치 고착, off-boresight 클램프 등).
  ACE는 그 중간 단계를 건너뛰고 실제 전투기 조종 법칙을 그대로 쓴다.

조종 법칙 — 양력 벡터 제어(lift vector control):
  실제 전투기는 "가고 싶은 방향으로 롤해서 양력 벡터를 겨눈 뒤 당긴다".
  1) 목표 방향을 기체 좌표계로 변환
  2) 양력 벡터(-Z_body)가 목표를 향하도록 롤 명령
  3) 양력이 정렬된 만큼만 당김(정렬 안 됐는데 당기면 엉뚱한 방향으로 감)
  이것이 VP 방식보다 정확하고 빠르다.

전술 계층:
  - 공세: 리드 추적으로 뒤를 파고들되, 사거리 안에서는 실제 위치를 겨눠 사격각을 만든다
  - 방어: out-of-plane 브레이크(수직 성분 포함)로 상대 조준해를 깬다
  - 코너속도: 큰 선회가 필요하면 감속(실측 240~270m/s에서 선회율 최대 27deg/s,
    420m/s에서는 7deg/s로 1/4). 정렬되면 즉시 재가속
  - 에너지: 저속이면 기수를 낮춰 속도를 회복

부호 규약(실측 보정):
  pitch < 0 = 기수 올림(당김) / roll > 0 = 우측 롤 / throttle 0~1
"""
from __future__ import annotations
import math
import numpy as np

from dogfight.ai.action_provider import ActionProvider, ActionResult
from dogfight.sim.state_schema import StateIndex

MLAT = 111320.0
CORNER = 255.0          # 선회율 최대 속도대 중앙(실측 210~290)
WEZ_MIN, WEZ_MAX = 152.4, 914.4


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


class AcePilot(ActionProvider):
    def __init__(self, aggressive: float = 1.0):
        self.aggr = aggressive
        self._prev = {}          # 위치 이력(속도 추정용)

    def reset(self, context=None):
        self._prev = {}

    # ── 상태 → ENU(동,북,상) 좌표/속도 ──
    def _enu(self, s, ref_lat, ref_lon):
        c = math.cos(math.radians(ref_lat))
        return np.array([
            (float(s[StateIndex.LON]) - ref_lon) * c * MLAT,
            (float(s[StateIndex.LAT]) - ref_lat) * MLAT,
            float(s[StateIndex.ALT]),
        ])

    def _body_axes(self, s):
        """기체 좌표축(전방 X, 우측 Y, 하방 Z)을 ENU로 표현."""
        yaw = math.radians(float(s[StateIndex.YAW]))
        pit = math.radians(float(s[StateIndex.PITCH]))
        rol = math.radians(float(s[StateIndex.ROLL]))
        # 전방
        X = np.array([math.sin(yaw)*math.cos(pit), math.cos(yaw)*math.cos(pit), math.sin(pit)])
        # 롤 0일 때의 우측/하방
        Y0 = np.array([math.cos(yaw), -math.sin(yaw), 0.0])
        Z0 = np.cross(X, Y0)          # 하방
        # 롤 적용(X축 회전)
        Y = Y0*math.cos(rol) + Z0*math.sin(rol)
        Z = -Y0*math.sin(rol) + Z0*math.cos(rol)
        return X, Y, Z

    def compute_action(self, context) -> ActionResult:
        me = context.sim.get_state()
        en = context.opponent_sim.get_state()

        ref_lat, ref_lon = float(me[StateIndex.LAT]), float(me[StateIndex.LON])
        P = self._enu(me, ref_lat, ref_lon)
        Q = self._enu(en, ref_lat, ref_lon)
        t = float(me[StateIndex.SIM_TIME])

        # ── 속도 추정(위치 차분) ──
        vP = np.zeros(3); vQ = np.zeros(3)
        pv = self._prev
        if pv and t > pv.get("t", -1) and (t - pv["t"]) < 1.0:
            dt = t - pv["t"]
            # 이전 프레임의 ENU는 그때의 기준점 기반이므로 위경도로 다시 계산
            c = math.cos(math.radians(ref_lat))
            pP = np.array([(pv["plon"]-ref_lon)*c*MLAT, (pv["plat"]-ref_lat)*MLAT, pv["palt"]])
            pQ = np.array([(pv["qlon"]-ref_lon)*c*MLAT, (pv["qlat"]-ref_lat)*MLAT, pv["qalt"]])
            vP = (P - pP) / dt
            vQ = (Q - pQ) / dt
        self._prev = dict(t=t,
                          plat=ref_lat, plon=ref_lon, palt=float(me[StateIndex.ALT]),
                          qlat=float(en[StateIndex.LAT]), qlon=float(en[StateIndex.LON]),
                          qalt=float(en[StateIndex.ALT]))

        spd = float(np.linalg.norm(vP))
        if spd < 1.0:
            spd = 250.0
        espd = float(np.linalg.norm(vQ))

        X, Y, Z = self._body_axes(me)
        eX, _, _ = self._body_axes(en)

        rel = Q - P
        dist = float(np.linalg.norm(rel))
        if dist < 1e-6:
            dist = 1e-6
        losn = rel / dist

        my_ata = math.degrees(math.acos(_clamp(float(np.dot(X, losn)), -1, 1)))
        en_ata = math.degrees(math.acos(_clamp(float(np.dot(eX, -losn)), -1, 1)))

        # ─────────── 전술 국면 판단 ───────────
        threatened = (en_ata < 45.0) and (dist < 1800.0)
        offensive = (my_ata < 70.0) and not threatened

        if threatened:
            # ── 방어: out-of-plane 브레이크 ──
            #    위협 쪽으로 최대선회하되 수직 성분을 섞어 상대 조준면을 3D로 만든다.
            side = np.cross(losn, np.array([0.0, 0.0, 1.0]))
            if np.linalg.norm(side) < 1e-6:
                side = Y.copy()
            side /= np.linalg.norm(side)
            if float(np.dot(side, Y)) < 0:
                side = -side                      # 현재 선회 방향 유지(요동 방지)
            # out-of-plane 성분: 고도에 따라 하강량을 줄이고, 낮으면 상승으로 전환
            alt_now = float(me[StateIndex.ALT])
            vmix = 0.5
            if alt_now < 4000.0:
                vmix = 0.5 * ((alt_now - 2800.0) / 1200.0)
            if alt_now < 2800.0:
                vmix = -0.4                       # 저고도: 위로 빼면서 방어
            aim_dir = side * 1.0 + np.array([0.0, 0.0, -1.0]) * vmix
            aim_dir /= np.linalg.norm(aim_dir)
            aim = P + aim_dir * 2000.0
        else:
            # ── 공세/중립: 리드 추적, 사거리 안에서는 실사격각 ──
            lead_t = _clamp(dist / max(spd, 1.0), 0.0, 2.5)
            aim = Q + vQ * lead_t
            if WEZ_MIN <= dist <= WEZ_MAX and my_ata < 25.0:
                aim = Q                            # 사격 판정은 "현재 위치" 기준

        # ── 저고도 안전(규정: 300m 이하 즉시 패배) ──
        #    자세를 따로 오버라이드하지 않고 **조준점을 위로 올려** 검증된 제어 경로를 그대로 쓴다.
        #    (오버라이드 방식은 반전 상태에서 오히려 지면으로 당기는 사고를 냈다)
        if P[2] < 3000.0:
            urg = _clamp((3000.0 - P[2]) / 1500.0, 0.0, 1.0)
            aim = aim.copy()
            aim[2] = max(float(aim[2]), P[2] + 400.0 + 2000.0 * urg)

        # ─────────── 양력 벡터 제어 ───────────
        d = aim - P
        dn = float(np.linalg.norm(d))
        if dn < 1e-6:
            dn = 1e-6
        d = d / dn

        bx = float(np.dot(d, X)); by = float(np.dot(d, Y)); bz = float(np.dot(d, Z))
        offaxis = math.acos(_clamp(bx, -1, 1))            # 기수와 목표의 각(rad)

        # 양력 벡터(-Z_body)를 목표 쪽으로 두기 위한 롤 오차
        roll_err = math.atan2(by, -bz)
        roll_cmd = _clamp(roll_err * 1.4, -1.0, 1.0)

        # 정렬된 만큼만 당긴다 (엉뚱한 방향으로 당기는 것 방지)
        align = max(0.0, math.cos(roll_err))
        pull = _clamp(offaxis * 1.6, 0.0, 1.0) * align * self.aggr
        # 목표가 뒤쪽이면(offaxis 큼) 최대 당김으로 빠르게 기수를 돌린다
        if offaxis > math.radians(60.0):
            pull = max(pull, 0.85 * align)
        pitch_cmd = -pull                                  # 음수 = 기수 올림

        # 미세 조준: 거의 정렬됐으면 러더로 다듬는다
        yaw_cmd = _clamp(by * 2.0, -0.4, 0.4) if offaxis < math.radians(12.0) else 0.0

        # ─────────── 속도(코너속도) 관리 ───────────
        need_hard_turn = offaxis > math.radians(15.0)
        if need_hard_turn and spd > CORNER + 25.0:
            over = _clamp((spd - CORNER) / 200.0, 0.0, 1.0)
            thr = _clamp(0.9 - over * 0.75, 0.15, 1.0)     # 선회율 확보를 위해 감속
        elif spd < 190.0:
            thr = 1.0                                       # 에너지 회복
        elif dist > 1500.0:
            thr = 1.0                                       # 접근
        else:
            # 사거리 유지: 너무 빠르면 지나치고, 느리면 놓친다
            dv = spd - espd
            thr = _clamp(0.85 - dv * 0.010, 0.30, 1.0)

        # 저고도에서는 감속 금지(에너지가 없으면 못 빠져나온다)
        if P[2] < 2500.0:
            thr = 1.0

        act = np.array([roll_cmd, pitch_cmd, yaw_cmd, thr], dtype=np.float32)
        return ActionResult(action=act, source="ace", confidence=1.0)
