# Trinity v0 — baseline (2026-07-20 백업)

## 정체
팀원(dhks1573) **Trinity BT의 최신 스냅샷**(2026-07-13: AA 부호반전 수정 + Evade
hysteresis까지 반영)을, `THaip\AIP_DCS_2026_05_26` 전체 소스트리로 **우리가 직접
빌드**한 DLL이다. 이후 모든 개선 버전의 **상대 기체(baseline) 기준점**.

- 소스: `THaip\AIP_DCS_2026_05_26\AIP_DCS` (BT_Content 65개 파일)
- 빌드: Release x64, MSVC v143

## 성적 (팀원 20시드 배치 기준)
| 트리 | mean reward | 승/패/무 |
|---|---|---|
| Rule_Trinity   | **-77.73** | 0 / 0 / 20 |
| Rule_BFMSelect | -88.54     | 0 / 0 / 20 |

- **패배 0건이지만 승리도 0건.** 병목: 실사격 조건(ATA<2°) 도달 0/3785건.
- 거울전 노드 실행 분포(200초): GetTail 338 · Lead 195 · LoopAttack 146 ·
  BreakAndReverse 94 · Evade 18 · **Pure 6** → "뒤는 파고드는데 사거리 조준 유지 실패".

## 구성 (자기완결)
| 파일 | 역할 |
|---|---|
| `AIP_DCS.dll` | BT 두뇌 (배우+배역표 전부, Rule XML은 별도) |
| `Rule_Trinity.xml` | 주력 트리 (단순 우선순위) |
| `Rule_BFMSelect.xml` | 대체 트리 (BFM 분류 기반) |
| `결과/logs/` | 거울전 검증 로그 (`2026_7_17_15_59_46`, timeout 무승부) |

## 다른 PC에서 이 버전과 시합 거는 법
1. `AIP_DCS.dll` + `Rule_Trinity.xml` 을 상대 `강화학습환경\Release\` 로 복사
2. `cd 강화학습환경\Release`
3. 실행:
```powershell
python run_local_dogfight.py `
  --ownship-backend bt --ownship-bt-dll <자기_DLL> `
  --target-backend  bt --target-bt-dll  AIP_DCS.dll `
  --bt-rule-xml Rule_Trinity.xml `
  --max-engage-time 200 --save-log
```

## ⚠️ 알려진 제약 (두 BT를 붙일 때)
DLL이 `CPPBehaviorTree.cpp`에서 `"./Rule_forTraining.xml"` 을 **하드코딩**해 읽는다.
`--bt-rule-xml`은 인자가 1개뿐이라 ownship/target 두 DLL이 **같은 트리**를 공유한다.
서로 다른 두 BT를 한 판에 붙이려면 각 DLL을 **고유 XML 이름으로 재빌드**하거나
`run_batch_dogfight.py`(팀원 자작, 아직 미확보)가 필요하다.
