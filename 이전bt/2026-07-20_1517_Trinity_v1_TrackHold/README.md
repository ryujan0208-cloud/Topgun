# Trinity v1 — TrackHold (2026-07-20 백업)

## 정체
v0 baseline + **`Task_TrackHold` 신설**. WEZ 슬롯(거리≤914m)의 `Task_Pure`를 TrackHold로
교체. 조준은 동일(적 현재위치)하되 스로틀을 거리밴드+속도차 폐루프로 제어해 오버슈트를
막고 사거리 체류를 늘리는 가설. 나머지 노드는 v0와 동일.

## 성적 (v1 vs v0, 15시드 배치)
- **0승 0패 15무**, mean reward **-83.18** (전부 200초 timeout, 무피해)
- TrackHold 발동 ~10초(0.3%)뿐 → **동급전은 뒤를 못 잡아 검증 불가**(설계상 예상).
  회귀는 없음(v0 대비 안전). 이 -83.18이 앞으로 버전 비교의 기준 벤치마크.

## 구성 (자기완결)
| 파일 | 역할 |
|---|---|
| `AIP_v1.dll` | BT 두뇌. **`Rule_v1.xml`을 하드코딩해 읽음** (파일명 유지 필수) |
| `Rule_v1.xml` | 트리 (WEZ 슬롯에 `<Task_TrackHold>`) |
| `결과/v1_vs_v0_15seed_*.csv` | 15시드 전적 |
| `결과/2026_7_20_14_20_27_*` | v1 vs v0 리플레이 로그 |

## 다른 PC에서 v1을 상대(target)로 붙이는 법
1. `AIP_v1.dll` + `Rule_v1.xml` 을 상대 `강화학습환경\Release\` 로 복사
2. `cd 강화학습환경\Release`
3. 실행:
```powershell
python run_local_dogfight.py `
  --ownship-backend bt --ownship-bt-dll <자기_DLL> `
  --target-backend  bt --target-bt-dll  AIP_v1.dll `
  --max-engage-time 200 --save-log
```
- **`--bt-rule-xml` 불필요**: v1 DLL이 `Rule_v1.xml`을 직접 읽는다.
- 자기 DLL도 고유 XML(예 `Rule_v0.xml`)을 읽으면 두 BT가 안 섞여 정상 대전된다.
- 상대 PC에 소스/빌드 불필요 — DLL에 TrackHold까지 다 컴파일돼 있음.
