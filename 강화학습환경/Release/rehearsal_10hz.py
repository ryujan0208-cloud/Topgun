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
import os
import numpy as np

# 대회 초기조건 모드. 미설정이면 legacy(5km·7000m) 그대로.
MATCH_MODE = os.getenv("TOPGUN_MATCH", "") not in ("", "0")

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from DogFightEnvWrapper import DogFightWrapper
from dogfight.ai.bt_action_provider import BTActionProvider


# ============================================================================
#  대회 초기조건 (TOPGUN_MATCH=1 일 때만 적용. 미설정이면 legacy 그대로)
# ============================================================================
# 사전등록: experiments/match_conditions/PREREG_2026-08-11.md (커밋 3d4cb46)
# 출처: `ai pilot 질문사항 종합.pdf` — 운영측 공식 답변
#   p49 (26-08-03) "6) 1 라운드 2000 2 라운드 2500 3 라운드 3000
#                   초기 속력과 위치는 양측 기체 동등하게 적용"
#   p15/p43        초기 고도 2000~30000ft, 속력 200~300m/s 매 라운드 랜덤
#   p53            2000/2500/3000ft는 고도가 아니라 **두 기체 간 거리**
#   p53            시나리오는 교전 뷰어의 HABFM(헤드온) — 우리 형태와 이미 일치
#
# ★ legacy(5km·7000m)는 삭제하지 않는다. 환경변수 미설정이면 종전 그대로 동작한다.
FT = 0.3048
MATCH_RANGES_FT = (2000.0, 2500.0, 3000.0)   # 뷰어 거리 버튼 = 라운드 1/2/3
MATCH_ALT_FT = (2000.0, 30000.0)             # 매 라운드 랜덤, 양측 동일
MATCH_SPEED_MPS = (200.0, 300.0)             # 매 라운드 랜덤, 양측 동일

# 뷰어 기하 프리셋: HABFM / OBFM_RED / OBFM_BLUE (스크린샷으로 확인된 세 버튼).
#   HABFM     = High Aspect BFM. 고애스펙트 = 서로 마주보는 중립 머지.
#   OBFM_RED  = Offensive BFM, **상대(RED)가 공세**로 시작 = 우리가 방어.
#   OBFM_BLUE = **우리(BLUE)가 공세**로 시작.
# ⚠ 각 프리셋의 정확한 각도는 뷰어 애셋(.uasset) 안이라 읽을 수 없다.
#   아래는 BFM 표준 셋업에 따른 **가정값**이며, 뷰어 실측으로 확정해야 한다.
#   가정: OBFM은 공세측이 방어측 뒤 30도 원뿔 안(= 표준 control zone 진입 직전).
MATCH_GEOM = os.getenv("TOPGUN_GEOM", "HABFM").upper()

# ★ OBFM 각도오프셋 — 2026-08-11 정정.
#  [문제] 공세측을 방어측 정확히 뒤에 **ATA 0도**로 두면, 거리 610m가 사격 조건
#    (152.4~914.4m AND LOS<=1.0도)을 **스폰 첫 프레임부터** 만족한다.
#    실측: t=0에 사격 성립, t=1.0s에 방어측 HP 1.000 -> 0.614. **1초에 39% 손실.**
#    실제 BFM의 OBFM(perch) 셋업은 공세측에 우위를 주되 **각도를 좁혀야 하는 상태**로
#    시작한다. 조준이 완성된 채로 시작하면 시나리오가 아니라 스폰킬이다.
#  [해법] 공세측 기수를 ANGLE_OFF 만큼 틀어 시작한다. 공세측은 그 각을 좁혀야 쏠 수 있다.
#    30도는 표준 perch 셋업의 angle-off 범위(30~45도)에서 가장 보수적인 값.
#  ⚠ 뷰어 실제 값은 애셋 안이라 못 읽는다. **가정값이며 결과에 병기한다.**
OBFM_ANGLE_OFF_DEG = float(os.getenv("TOPGUN_OBFM_ANGLE", "30"))


def apply_match_conditions(env, seed: int):
    """대회 초기조건을 이번 에피소드에 적용한다. env.reset() **직전**에 부른다.

    ★ `FighterSim.reset()`은 기체를 **`_init_pos_lat/lon/alt`** 로 만든다
      (`Fighter(..., _init_pos_lat, _init_pos_lon, _init_pos_alt*FT, ...)`).
      그 LLA는 **생성자에서 한 번만** NED로부터 계산된다.
      따라서 `_init_pos_n/e/d`만 바꾸면 **보고용 state 배열만 바뀌고 물리는 안 바뀐다.**
      (부수 발견: 그래서 `add_random_init_position`의 `radius` 위치 산란은
       지금까지 실제로 작동한 적이 없다 — 헤딩·롤·피치만 걸렸다.)
      여기서는 LLA를 직접 다시 계산해 넣는다.

    거리는 라운드 인덱스로 정해지므로 시드를 3으로 나눈 나머지를 라운드로 본다.
    고도는 시드 전용 난수 — 배치 순서가 바뀌어도 같은 시드면 같은 고도가 나온다.
    """
    import pymap3d as pm
    rng = np.random.default_rng(1_000_003 + seed)
    alt_m = float(rng.uniform(*MATCH_ALT_FT)) * FT
    spd   = float(rng.uniform(*MATCH_SPEED_MPS))      # 양측 동일(공식 답변)
    sep_m = MATCH_RANGES_FT[seed % len(MATCH_RANGES_FT)] * FT

    def place(f, n, e, d, heading):
        lla = pm.ned2geodetic(n, e, d, f._origin_lat, f._origin_lon, f._origin_alt)
        f._init_pos_lat, f._init_pos_lon, f._init_pos_alt = lla[0], lla[1], lla[2]
        f._init_pos_n, f._init_pos_e, f._init_pos_d = n, e, d   # 보고용 state도 맞춘다
        f._init_roll = 0.0
        f._init_pitch = 0.0
        f._init_heading = heading
        f._init_speed = spd

    # ★ 원칙: **어느 기하도 t=0에 사격이 성립해선 안 된다.**
    #   사격 조건이 거리 152.4~914.4m AND LOS<=1.0도인데 시작 거리가 610~914m다.
    #   기수를 상대에게 정확히 맞춰 두면 스폰 첫 프레임부터 맞는다(실측: 1초에 HP 39% 손실).
    a = OBFM_ANGLE_OFF_DEG
    if MATCH_GEOM == "OBFM_BLUE":
        # 우리가 공세: 상대가 앞에서 등을 보이고, 우리 기수를 a만큼 틀어 시작.
        #   상대는 우리 정북(N축) sep 지점.
        own_n, own_e, tgt_n, tgt_e = 0.0, 0.0, sep_m, 0.0
        own_hdg, tgt_hdg = a, 0.0
    elif MATCH_GEOM == "OBFM_RED":
        # 상대가 공세: 상대가 우리 뒤에 있고, 상대 기수를 a만큼 틀어 시작.
        own_n, own_e, tgt_n, tgt_e = 0.0, 0.0, sep_m, 0.0
        own_hdg, tgt_hdg = 180.0, 180.0 + a
    else:
        # HABFM = **3-9 셋업**(운영측 확인: "시작조건이 3-9 셋업인지" -> "맞습니다").
        #   서로의 3시/9시 방향에 나란히 서서 반대 방향을 본다 = 양쪽 ATA 90도.
        #   중립이고 t=0 사격이 성립하지 않는다. 정면 마주보기(ATA 0/0)는
        #   양쪽 스폰킬 + 충돌 코스가 되어 3-9 셋업이 아니다.
        own_n, own_e, tgt_n, tgt_e = 0.0, 0.0, 0.0, sep_m      # 상대는 우리 **동쪽**(3시)
        own_hdg, tgt_hdg = 0.0, 180.0                          # 서로 반대 방향

    place(env._sim,        own_n, own_e, -alt_m, own_hdg)
    place(env._target_sim, tgt_n, tgt_e, -alt_m, tgt_hdg)
    return {"seed": seed, "sep_m": sep_m, "alt_m": alt_m, "spd": spd,
            "geom": MATCH_GEOM, "angle_off": (a if MATCH_GEOM.startswith("OBFM") else 0.0),
            "round": seed % len(MATCH_RANGES_FT) + 1}


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
    tgt_dll = sys.argv[6] if len(sys.argv) > 6 else "AIP_kwon.dll"  # 스파링 상대 선택

    # 병렬 배치를 위해 ownship DLL을 프로세스별로 고를 수 있게 한다.
    # 미설정이면 종전대로 AIP_DCS_ownship.dll (legacy 경로 불변).
    own_dll = os.getenv("TOPGUN_OWN_DLL") or "AIP_DCS_ownship.dll"
    own = BTActionProvider(dll_name=own_dll)
    if tgt_dll.upper() == "ACE":
        from ace_pilot import AcePilot
        tgt = AcePilot()
    elif tgt_dll.upper() == "STRAIGHT":
        # 진짜 직선 수평 비행. AIP_dummy는 80도 뱅크로 계속 선회하는 기체였다(실측).
        from straight_pilot import StraightPilot
        tgt = StraightPilot()
    elif tgt_dll.upper() == "SEARCH":
        # 탐색형 상대: 매 틱 후보 조종안을 짧게 예측해보고 최선을 고른다(search_pilot.py).
        from search_pilot import SearchPilot
        tgt = SearchPilot()
    else:
        tgt = BTActionProvider(dll_name=tgt_dll)
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
    if MATCH_MODE:
        # 대회엔 이 산란이 없다. 게다가 add_random_init_position은 += 라 판마다 누적된다.
        cfg["ownship_randomization"] = {"enabled": False}
    elif seeds > 1 or start_seed > 0:  # run_batch_local과 동일한 랜덤 스폰
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
            if MATCH_MODE:
                mc = apply_match_conditions(env, k)
                print(f"[match] seed {k} {mc['geom']} round{mc['round']} "
                      f"sep={mc['sep_m']:.0f}m alt={mc['alt_m']:.0f}m "
                      f"spd={mc['spd']:.0f}m/s aoff={mc['angle_off']:.0f}deg", flush=True)
                obs, info = env.reset(seed=k)
            else:
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
