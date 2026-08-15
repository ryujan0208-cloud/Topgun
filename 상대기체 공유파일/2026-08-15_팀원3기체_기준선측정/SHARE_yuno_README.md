# yuno 기체 — 팀 배포용 (2026-08-15)

기준 커밋 `0ad491e` + 안전성 수정. 저장소: https://github.com/iamyuno12-hash/aip-dogfight-bt

## 파일 2개를 같이 두면 됩니다

```
AIP_yuno.dll        ← DLL
Rule_yuno.xml       ← 같은 작업디렉터리(Release)에 함께
```

**환경변수 불필요.** DLL이 `./Rule_yuno.xml`을 읽습니다.

⚠ **파일명 충돌을 피하려고 고유 이름으로 빌드했습니다.**
템플릿 원본은 `./Rule_mine.xml`을 상대경로로 하드코딩하는데, 여러 팀이 같은
이름을 쓰기 때문에 한 폴더에 두 DLL을 놓으면 **한쪽이 상대의 트리로 싸웁니다.**
에러가 아니라 조용한 오작동이라 눈치채기 어렵습니다.
`AIP_yuno.dll` + `Rule_yuno.xml` 조합은 다른 팀 기체와 같은 폴더에 둬도 안전합니다.

⚠ **XML 파일명은 바꾸지 마세요.** DLL 안에 박혀 있습니다.

---

## 뷰어(BattleViewer) 대전

1) 서버 PC에서 뷰어 실행 → Port 9999 → OpenServer → 시나리오 설정
   `BattleViewer\V0.2_2026_05_26_Latest\BattleServer_V0.2\DogFightViewer.exe`
   (저사양 PC는 같은 폴더 `BattleServer_Low_V0.2`)

2) 위 두 파일을 `DogFightEnv\Release`에 복사한 뒤:

```
python run_unreal_inference.py --mode bt --ai-type rule ^
  --server-ip <서버IP> --server-port 9999 ^
  --bt-dll AIP_yuno.dll --team-name YUNO ^
  --ownship-force-side 1 --target-force-side 2
```

상대 쪽은 `--ownship-force-side 2 --target-force-side 1`로 띄웁니다.
같은 PC에서 양쪽을 돌리려면 `--server-ip 127.0.0.1`.

⚠ `--bt-rule-xml` 옵션은 쓰지 마세요. 그 옵션은 지정 파일을 `Rule.xml`로
복사하는 방식이라 이 DLL에는 효과가 없습니다.

## 헤드리스 배치

```python
BTActionProvider(dll_name="AIP_yuno.dll")   # target_action_provider 로 주면 상대기체
```
BLUE/RED 양쪽 다 동작합니다.

## 교전 로그를 웹으로 보기

배치를 `--save-log --artifacts-dir artifacts/logs_x`로 돌린 뒤:
```
python tools\web_log_viewer\server.py --logdir artifacts\logs_x --port 7871
```
브라우저에서 `http://127.0.0.1:7871`. 표준 라이브러리만 쓰므로 추가 설치 불필요합니다.
(`tools\dashboard.py`는 gradio/dogfight_dashboard가 배포본에 없어 동작하지 않습니다.)

---

## 성적 (우리 기준, 20시드 × two_circle_headon, 시드마다 새 env)

| 상대 | 승/패/무 | 가한 | 받은 |
|---|---|---|---|
| junghwan | **8 / 2 / 10** | 9.15 | 3.76 |
| 팀원 v18 | 3 / 0 / 17 | 2.89 | 0.43 |
| ryujan v42 | 0 / 0 / 20 | 1.25 | 1.15 |
| Trinity | 0 / 0 / 20 | 1.29 | 0.32 |
| 직선표적(loiter, 등속수평) | **20 / 0 / 0** | 20.11 | 8.24 |

⚠ 대회 공식 3-phase/200초 규칙이 아니라 **기본 환경 300초 단일 구간** 기준입니다.
다른 팀 README 수치와 직접 비교하지 마세요.

## 이 기체의 성격

- **모드 기반**: BFMDecision이 매 틱 OBFM/HABFM/DBFM/DETECTING을 재판정하고 분기합니다.
- **기동은 전부 관성계 VP**입니다. 몸체축 오프셋 VP(`my + R*4000` 류)는 기체가 롤하면
  VP도 같이 돌아 제어기가 수렴하지 못하고 에일러론 롤만 하다 직진합니다.
  BreakTurn/Jinking/Scissors를 전부 관성계로 바꿔 큰 이득을 봤습니다.
- **방어는 break-into**: 6시를 잡히면 공격자 쪽으로 최대선회 + 풀스로틀.
- **접근은 Lead, 사거리 안은 Pure**: lag pursuit은 사거리 밖 ~1km 평형을 만들어 기각했습니다.

## 알려진 약점

- **정면 총격전.** WEZ 채점이 양방향이라 서로 ±1°에 들면 둘 다 깎이는데, 회피 분기가
  없어 정면으로 들어갑니다. 직선표적 20판에서 받은 8.24가 대부분 머지 첫 1.6초입니다.
  회피를 두 번 시도해 v1은 기각(공격력 81% 손실), v2는 유망하나 미검증입니다.
- **수직 파이터 미검증.** 수직 전용 분기가 없습니다.
