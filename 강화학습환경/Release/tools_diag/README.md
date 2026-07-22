# 진단 도구 (BT 개발용)

점수(mean reward)로 판단하지 않고 **원인 지표를 직접 측정**하기 위한 스크립트 모음.
모든 스크립트는 `artifacts/logs`의 tacview CSV 쌍을 읽는다. cwd 무관, stamp만 넘기면 된다.

```bash
python tools_diag/wez_audit.py 2026_7_23_6_17_51
```

| 스크립트 | 측정 대상 | 언제 쓰나 |
|---|---|---|
| `wez_audit.py <stamp>` | 사거리 체류 / **사격조건(ATA<=1.0deg) 도달 틱** / 거리대별 최소 ATA / 데미지 추정 | 조준이 실제로 성립했는지 |
| `ata_split.py <stamp>` | **ATA를 수평(요)/수직(피치) 성분으로 분해** + VP Z클램프 발동률 | 조준 실패가 좌우인지 상하인지 (v18 규명의 결정타) |
| `alt_trace.py <stamp>` | 고도 추이, 고도차 편향, 클램프 트리거 | 고도 제약에 갇혔는지 |
| `overshoot.py <stamp>` | 뒤잡음 구간 틱추적 (거리/ATA/속도/dV/상대롤) | 추월(오버슈트) 여부 |
| `engage_timeline.py <stamp>` | 10초 간격 거리/양측 ATA/고도 | **교전이 왜 성립/불성립인지** (고착거리 규명) |
| `split_episodes.py <stamp>` | 배치 연결 로그를 판별로 분리 -> `<stamp>_s00..sNN` | 배치 결과를 판별 리플레이로 보기 |
| `traj.py`, `diagnose_bands.py` | 속도/선회율/방위 타임라인, 거리대별 ATA | 보조 |

## 검증 표준
```bash
# 제출조건(ACTION_REPEAT=6 = BT 10Hz) 에뮬레이션. 이게 기본 검증이다.
python rehearsal_10hz.py 6 6 200 15        # 우리6/상대6, 200초, 15시드
python rehearsal_10hz.py 6 6 200 6 0       # 시드0~5 재현 + 마지막 판 리플레이 저장
```
- **60Hz 단판 검증은 시합 조건과 다른 값을 측정한다.** 6/6이 기준.
- **5시드로 채택 판단 금지** — v18의 패배 모드 2개(지면추락사/피격추)를 5시드는 전혀 못 봤다.
  **15시드 이상.**
- 상대 DLL이 에피소드 간 내부 상태를 유지하므로 **같은 시드 순서로 돌려야 재현**된다
  (단독 seedN != 배치 seedN). 이 조건에서는 bit-identical 확인됨.
