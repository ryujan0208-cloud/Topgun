# 보상함수 설계 가이드 (DogFight RL)

> 2026 AI Pilot Top Gun Challenge — RL 파트 작업 문서
> 우리 팀 방향: **독립 파이터형** (RL이 전투 전체 수행, 제출 시 BT와 residual hybrid 결합)

---

## 0. 한눈에 보기

```
보상함수 = 재료 창고 (모든 컴포넌트)   ← 커리큘럼에 종속되지 않음
커리큘럼 = 코스 순서 (단계마다 스케일로 컴포넌트를 켜고 끔)
메커니즘 = 함수는 고정, 커리큘럼 reward_overrides가 각 컴포넌트의 "볼륨"을 단계마다 조절
```

- **구조는 새로 설계하지 않는다.** 주최측 15단계 커리큘럼 + 보상 레시피를 그대로 활용.
- **우리가 하는 일** = 주최측 레시피에 있는데 `my_reward.py`에 빠진 컴포넌트 구현 + 스케일/조합을 실험(ablation)으로 튜닝.
- **차별화는 구조가 아니라 값과 조합의 최적화에서 온다.** (AlphaDogfight 교훈)

---

## 1. 보상함수란

`compute_reward()`는 시뮬레이션 **매 프레임(1/60초)** 호출되며, 반환하는 점수가 높아지도록 AI가 행동을 학습한다. 즉 이 함수가 **AI의 목표 그 자체**다.

파일: `student/my_reward.py`

### 함수 계약 (반드시 지킬 형식)

```python
def compute_reward(
    ownship_state,      # 내 비행기 상태 벡터 (StateIndex로 접근)
    target_state,       # 적 비행기 상태 벡터
    ownship_damage,     # 내가 받은 누적 피해
    target_damage,      # 적이 받은 누적 피해
    geo_info,           # 기하 계산 객체 (_get_distance, _get_antenna_train_angle, _get_aspect_angle)
    wez_config,         # WEZ 설정 dict (angle_deg, min_range_m, max_range_m)
    reward_config,      # MY_REWARD_CONFIG + 커리큘럼 Stage 덮어쓰기가 합쳐진 최종 값
    terminated,         # 에피소드 종료 여부 (격추/추락 등)
    truncated,          # 시간/스텝 초과 종료 여부
    end_condition,      # 종료 사유 문자열
) -> tuple[float, dict]:
    ...
    return float(total), components   # (총 보상, 컴포넌트별 dict)
```

**계약 2가지:**
1. 반환 = `(float 총보상, dict 컴포넌트)`
2. `components` 키는 분석 가능한 이름으로 (`pursuit`, `damage` ○ / `r1`, `x` ✗) — dashboard가 컴포넌트별 그래프를 자동으로 그린다.

---

## 2. 기하학 기초 (보상의 재료)

보상 컴포넌트는 대부분 아래 기하량으로 만든다. (참고: `reward_design_concept_slides.html`)

| 기호 | 이름 | 의미 | 계산 |
|---|---|---|---|
| distance | 거리 | 두 기체 간 거리(m) | `geo_info._get_distance(own, tgt)` |
| altitude | 고도 | 내 고도(m) | `ownship_state[StateIndex.ALT]` |
| **ATA** | Antenna Train Angle | **내 기수가 적을 향하나** (0°=정조준) | `geo_info._get_antenna_train_angle(own, tgt, False)` |
| **AA** | Aspect Angle | **내가 적 뒤에 있나** (0°=적 6시) | `geo_info._get_aspect_angle(own, tgt, False)` |
| 적 ATA | (회피용) | **적이 나를 조준하나** | `geo_info._get_antenna_train_angle(tgt, own, False)` ← 인자 순서 뒤집기 |
| WEZ | Weapon Engagement Zone | 사거리(152~914m) + 시선각(2°) 안 | wez_config로 판정 |
| Energy | Specific Energy | 고도 + 속도² 우위 | state에서 직접 계산 |

### ATA vs AA — 헷갈리기 쉬움

```
pursuit (ATA)     "내 기수가 적을 향하나?"   = 내가 조준했나
positioning (AA)  "내가 적 뒤에 있나?"      = 유리한 위치인가
→ 둘 다 작아야 "적 뒤에서 + 조준" = 완벽한 공격 위치
```

---

## 3. 보상 컴포넌트 전체 목록

주최측 레시피 기준. 부호·강도는 정성적 권장이며 실제 값은 실험으로 조정.

| 컴포넌트 | 기반 | 의도 | 부호·강도 | 상태 |
|---|---|---|---|---|
| survival | 생존 | 살아있으면 + (Stage 0 전용) | +약 | ✅ 구현 |
| step | 스텝 | 우물쭈물 금지 | −매우약 | ✅ 구현 |
| pursuit | ATA | 적에게 기수를 두라 | +중 | ✅ 구현 |
| **positioning** | AA | 적 6시 뒤로 가라 | +중 | 🔶 설계함 |
| wez | WEZ 진입 | 내 사거리 + 정조준 | +강 | ✅ 구현 |
| **wez_threat** | 적 ATA+거리 | 적 사거리에서 벗어나라 (회피) | −강 | ⬜ 다음 작업 |
| altitude | 최저고도 | 지면 충돌 금지 | −매우강 | ✅ 구현 |
| **energy** | 고도·속도 | 에너지 우위 유지 | +약 | ⬜ 다음 작업 |
| damage | 피해 차 | 맞히고 안 맞기 | +/−큰 | ✅ 구현 |
| terminal | 승/패/무 | 결과 | ±매우큰 | ✅ 구현 |

상태: ✅ 이미 구현 / 🔶 설계 완료(코드 입력 중) / ⬜ 설계 예정

### 3.1 현재 MY_REWARD_CONFIG (기본값)

```python
MY_REWARD_CONFIG = {
    "survival_bonus": 0.0,           # Stage 0에서 커리큘럼이 0.05로 올림
    "step_penalty": -0.01,
    "pursuit_scale": 0.4,
    "pursuit_half_angle_deg": 45.0,
    "pursuit_range_m": 4000.0,
    "wez_bonus": 2.0,
    "low_altitude_penalty": 0.1,     # Stage 0에서 1.0으로 강화됨
    "safe_altitude_m": 450.0,
    "damage_scale": 25.0,
    "win_reward": 200.0,
    "loss_reward": -200.0,
    "draw_reward": -50.0,
    "guard_fail_penalty": -50.0,
    # ── 추가 예정 ──
    # "positioning_scale": 0.3, "positioning_half_angle_deg": 60.0,
    # "wez_threat_penalty": ..., "energy_scale": ...,
}
```

### 3.2 컴포넌트별 코드

**survival / step** — 단순 상수
```python
components["survival"] = float(reward_config.get("survival_bonus", 0.0))
components["step"]     = float(reward_config["step_penalty"])
```

**pursuit (ATA × 거리)** — 적을 향해 기수, 가까울수록 +
```python
distance = geo_info._get_distance(ownship_state, target_state)
ata = abs(geo_info._get_antenna_train_angle(ownship_state, target_state, False))
half_angle    = float(reward_config["pursuit_half_angle_deg"])
pursuit_range = float(reward_config["pursuit_range_m"])
ata_factor   = max(0.0, 1.0 - ata / half_angle)
range_factor = max(0.0, 1.0 - distance / pursuit_range)
components["pursuit"] = float(reward_config["pursuit_scale"]) * ata_factor * range_factor
```

**positioning (AA × 거리)** — 🔶 적 6시 점유 (pursuit과 동일 구조)
```python
aa = abs(geo_info._get_aspect_angle(ownship_state, target_state, False))
positioning_half = float(reward_config["positioning_half_angle_deg"])
aa_factor = max(0.0, 1.0 - aa / positioning_half)
components["positioning"] = float(reward_config["positioning_scale"]) * aa_factor * range_factor
```

**wez (사거리 진입 보너스)** — 이산형
```python
in_wez = False
if wez_config:
    wez_half_angle = float(wez_config.get("angle_deg", 2.0)) / 2.0
    in_wez = (
        float(wez_config["min_range_m"]) <= distance <= float(wez_config["max_range_m"])
        and ata <= wez_half_angle
    )
components["wez"] = float(reward_config.get("wez_bonus", 0.0)) if in_wez else 0.0
```

**wez_threat (회피)** — ⬜ 적의 ATA+거리로 "내가 적 사거리에 있나" 판정 → 페널티 (다음 작업에서 설계)

**altitude (저고도 페널티)** — 낮을수록 강한 −
```python
altitude = float(ownship_state[StateIndex.ALT])
safe_alt = float(reward_config.get("safe_altitude_m", 450.0))
if altitude < safe_alt:
    depth = (safe_alt - altitude) / safe_alt   # 0~1
    components["altitude"] = -float(reward_config["low_altitude_penalty"]) * (1.0 + depth)
else:
    components["altitude"] = 0.0
```

**energy (에너지 우위)** — ⬜ specific energy = 고도 + 속도²/(2g) 의 적 대비 우위 (다음 작업에서 설계)

**damage (피해 차)**
```python
components["damage"] = float(reward_config["damage_scale"]) * (target_damage - ownship_damage)
```

**terminal (종료 보상)** — 에피소드 끝에 한 번
```python
terminal = 0.0
if terminated or truncated:
    own_hp = float(ownship_state[StateIndex.HEALTH])
    tgt_hp = float(target_state[StateIndex.HEALTH])
    if end_condition == "two circle headon guard fail":
        terminal = float(reward_config.get("guard_fail_penalty", -50.0))
    elif tgt_hp <= 0.0 < own_hp:
        terminal = float(reward_config["win_reward"])
    elif own_hp <= 0.0 < tgt_hp:
        terminal = float(reward_config["loss_reward"])
    else:
        terminal = float(reward_config["draw_reward"])
components["terminal"] = terminal
```

---

## 4. 커리큘럼과의 관계

함수는 **모든 컴포넌트를 항상 계산**한다. 커리큘럼이 단계마다 `reward_overrides`로 각 스케일을 0으로 끄거나 키운다.

### Stage 0 (생존) 예시 — 믹싱 콘솔

| 컴포넌트 | Stage 0 볼륨 | 효과 |
|---|---|---|
| altitude | 🔊 1.0 (10배) | 낮게 날면 큰 벌 |
| survival | 🔉 0.05 | 살아있으면 + |
| loss(추락) | 🔊 -50 | 추락 큰 벌 |
| pursuit | 🔇 0.0 | 추격 끔 |
| damage | 🔇 0.0 | 전투 끔 |
| win | 🔇 0.0 | 승리 무관 |

```
Stage 0:  생존만 켬
Stage 1:  + pursuit 켬
Stage 2:  + wez 켬
...        단계마다 한 능력씩 추가 = "보상을 차근차근 쌓기"
```

⚠️ Stage 0에서 `wez_bonus`는 override에 없어 2.0이 살아있음 → 검토 거리 (생존 단계에 전투 채널 하나 열림).

---

## 5. 학습 오류를 막는 설계 원칙 ★중요★

보상 설계 실수는 학습을 조용히 망친다(오류 없이 이상한 행동만 학습). 아래를 학습 전·후로 점검한다.

### 5.1 NaN / Inf 방지
```
· 0으로 나누기:  half_angle, pursuit_range, safe_altitude_m 등이 0이면 NaN
                 → config 값이 0이 되지 않게, 또는 분모에 가드
· max(0, ...) 로 음수 factor 차단 (현재 코드가 이미 사용)
· 누적 보상이 발산하지 않게 (매 프레임 보상 × 수천 프레임)
```

### 5.2 키 이름 일치 (★실제로 겪은 문제)
```
MY_REWARD_CONFIG의 키 == 커리큘럼 reward_overrides의 키 여야 덮어쓰기가 적용됨.
예: altitude_penalty (X)  →  low_altitude_penalty (O, 커리큘럼과 일치)
불일치 시 커리큘럼의 Stage별 조정이 우리 함수에 안 먹는다.
커리큘럼이 쓰는 키: survival_bonus, pursuit_scale, pursuit_half_angle_deg,
  pursuit_range_m, damage_scale, low_altitude_penalty, win_reward, loss_reward,
  draw_reward, guard_fail_penalty
```

### 5.3 단위 일관성
```
· 각도: degree냐 radian이냐 (ATA/AA는 degree. cos를 쓰려면 radians() 변환)
· 거리: m냐 ft냐 (환경은 m. 대회 사망고도 305m=1000ft)
· 컴포넌트끼리 크기 차이가 "단위 때문"은 아닌지
```

### 5.4 상쇄 위험
```
컴포넌트끼리 반대 방향을 가리키지 않는지.
예: pursuit(ATA)와 positioning(AA)이 헤드온에서 충돌 → 의도된 구분인지 확인.
```

### 5.5 스케일 균형 (sparse vs dense)
```
· terminal(±200)이 step(-0.01)·shaping 대비 너무 크면 → sparse, 학습 느림
· 너무 작으면 → 이기든 지든 무관해져 의미 없음
· shaping 합이 terminal을 압도하면 → "이기기"보다 "보상 긁기"를 학습
```

### 5.6 안전 페널티 충분히
```
추락·연료고갈 페널티가 작으면 회피를 학습 안 함.
Stage 0에서 altitude를 10배로 키우는 이유.
```

### 5.7 Reward Hacking (편법 학습) 경계
```
AI는 "의도"가 아니라 "보상"을 최적화한다. 편법 사례:
· step 페널티를 피하려 일부러 빨리 추락/자살
· altitude 보상을 악용해 전투 안 하고 고도만 유지
· WEZ 근처에서 빙글빙글 (보상 긁기)만 하고 격추 안 함
→ 보상 그래프만 보지 말고 Replay로 실제 궤적을 눈으로 확인 (5.8)
```

### 5.8 검증은 그래프가 아니라 궤적으로
```
"가르치고 싶은 행동" == "보상이 실제로 만드는 행동" 인지는
reward 곡선이 아니라 실제 교전 궤적(Tacview/dashboard Replay)에서만 보인다.
```

---

## 6. 검증 방법 (ablation)

### 5대 지표
```
reward_mean      학습 안정성 (단독으로는 부족)
crash_rate       추락률 (0.05↑면 안전 페널티 재검토)
ep_min_distance  최소 접근 거리 (추격/회피 진단)
ep_wez_steps     WEZ 점유 시간 (추격형 신호)
win_rate         최종 평가 (reward와 분리될 수 있음)
```

### ablation 3원칙
```
① 한 번에 한 변수만 바꾼다 (두 개 바꾸면 원인 불명)
② random seed 여러 개로 평균 (RL은 분산이 커서 한 번 결과는 운)
③ cherry-picking 금지 (제일 잘 나온 run만 고르지 않기)
```

### 도구
```
output.name/tag    실험을 폴더로 분리 (records/에 reward.py 자동 보존)
training_log.csv   5대 지표 자동 기록
dashboard          여러 run 그래프 비교
run_local_dogfight RL vs BT 실제 교전 + Replay
```

---

## 7. 현재 진행 상황 / 다음 작업

```
[완료]   pursuit, wez, altitude, damage, terminal, survival, step
[설계]   positioning (AA) — 코드 입력 중
[다음]   wez_threat (회피), energy (에너지 우위)
[그후]   각 컴포넌트를 커리큘럼 단계별로 켜는 reward_overrides 설계
         → 단계별 끊어 학습 + 검증 (ablation)
```

### ⚠️ 학습 시작 전 필수 (별도 버그)
```
train_curriculum.py 버그 2개 수정 필요:
① 메트릭 추출 (_extract_custom_metrics) → crash_rate 등이 n/a로 안 잡힘
② training record 저장 ('iteration' 에러) → reward.py 자동 보존 실패
train_rllib.py는 정상. train_curriculum만 옛 코드라 RLlib 2.54와 안 맞음.
```
