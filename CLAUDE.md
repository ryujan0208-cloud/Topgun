# 탑건 BT 프로젝트 — 작업 규칙

2026 AI 파일럿 탑건 챌린지. 1v1 F-16 도그파이트 BT.
**상세 기록은 `~/.claude/projects/.../memory/` (MEMORY.md가 색인). 이 파일은 매 세션 반드시 지킬 최소 규칙만.**

## 실행 환경 (틀리면 즉시 실패)
```bash
PY="/c/Users/TFX5470H/anaconda3/envs/aip/python.exe"   # 그냥 python 쓰면 pymap3d 없음
cd 강화학습환경/Release
"$PY" rehearsal_10hz.py 6 6 200 15 0 <상대>            # 검증 표준(제출조건 10Hz 에뮬)
```
- 상대: `ACE`(python 직접조종) 또는 DLL 이름(`AIP_kwon.dll` 등)
- ownship은 `AIP_DCS_ownship.dll` 고정 → `cp AIP_vNN.dll AIP_DCS_ownship.dll`
- **stderr를 `2>/dev/null`로 버리지 말 것.** import 실패를 놓친다. `2>&1 | grep -vE "^\[(ACTIVE|EVADE_DIAG|DECO_)"`

## 판정 원칙 (가장 중요 — 어기면 허상을 쫓는다)
1. **결과론 금지.** 점수·승수가 올랐다고 채택하지 않는다. **메커니즘을 설명할 수 있어야** 채택.
2. **퇴행 지표도 메커니즘으로 설명**한다. "부차적이니 무시"는 안 된다.
3. **집계값(SUMMARY)만 보고 해석하지 말 것.** 반드시 시드별 라인을 세고,
   **최대 기여 시드를 뺀 값**을 다시 계산한다. 한 판이 총합의 절반이면 그건 효과가 아니라 분산.
   (실제 사고: ACE "−54%"는 seed 11 하나가 54%, onecircle "5.6배"는 seed 7 하나가 99.9%)
4. **판정 기준은 결과를 보기 전에 고정**한다. 보고 나서 고르면 사후 합리화.
5. **채택은 Syllabus + 15시드 실전 둘 다.** 실전이 최종 기준.
   (v24는 둘 다 통과해 채택, v25는 Syllabus만 통과해 기각)
6. **5시드 금지, 15시드 이상.** 피격은 틱이 아니라 **HP**로 판정.

## 가치 순서 (목표 ≠ 판정 방법)
**승리 > 준 데미지 > 무피격.** 규정상 200초 타임아웃 → **HP 비교**이므로
압도할 필요 없이 **조금이라도 앞서면 이긴다.** 수준 높은 상대에겐 약간의 피격을 감수하고 공격.

## ★ 측정 도구를 먼저 의심할 것
**"물리 한계다 / 구조적으로 불가능하다"는 결론이 나오면 도구부터 의심한다.**
하루에 3번 당했다: `turn_perf.py`(yaw만/수평만/지속만 측정), `alt_trace.py`(v17 시절 임계값),
`ata_split.py`(v17 상수 + **위쪽 클램프를 아예 안 잼** → 최대 병목을 오래 못 봤다).
- 코드의 상수를 바꾸면 **그걸 재는 도구도 같이 고친다.** 도구 상수는 인자로 받게 할 것.
- **대칭 지표는 양쪽 다 재라**(위/아래, 좌/우).
- 새 버전을 잴 땐 **그 버전의 상수를 도구에 넘겼는지** 확인.

## ★ 코덱스와 투트랙 — 서로의 작업 디렉터리를 절대 건드리지 않는다
| | 우리(Claude) | 코덱스 |
|---|---|---|
| 위치 | `.topgun/` (main) | `.topgun/recordings/codex-state-policy-lab/` (**git worktree**) |
| 브랜치 | `main` | `codex/state-policy-lab` (기점 `770d7a0`) |
| 규약 파일 | `CLAUDE.md` | `AGENTS.md`(내용 동일) + `CODEX_WORKSTREAM.md` |
| 역할 | 기체 개선·실전 15시드 판정 | **상태-정책 실험실**(반사실 fork, 채택 판정 아님) |

- `recordings/`는 main의 `.gitignore`에 있어 **서로의 git status에 안 잡힌다.** 이게 격리 장치다.
- **교환은 커밋 해시와 리포트로만.** 상대 디렉터리를 편집하지 말 것(양쪽 다 합의).
- 코덱스 산출물 3단: 추적되는 압축색인 `experiments/state_policy/runs/CVnn/`(README+작은 CSV,
  SHA-256 명시) / 무시되는 원자료 `artifacts/state_policy/` / 아카이브 `상대기체 공유파일/날짜_CODEX_*`.
- 코덱스는 `tools_diag/tests/test_*.py`로 **도구에 단위테스트를 붙인다.** 우리도 그렇게 할 것.
- 코덱스 실험 DLL은 `AIP_DCS_lab.dll`(별도). 제출 DLL·Rule을 건드리지 않는다.

## 운영 (묻지 말고 그냥 할 것)
- **리플레이 기본 제공**: `"$PY" tools/dashboard.py --default-tab replay --logdir artifacts/logs --port 7860`
  + **로그 stamp를 함께** 알려 어느 판인지 특정.
- **버전 바뀌면 자동으로**: `상대기체 공유파일/날짜_vN_이름/`에 DLL+Rule XML+수정 .cpp+README(성적·근거)
  아카이브 → `git add -A` → commit. **기각한 버전도 기록.**
- **배치 3개 이상 병렬 금지** (PC 다운 전례). **PC 다운 시 두 곳을 확인**:
  1. `aircraft/f16/f16_init.xml` (3회 손상 전례)
  2. **`.git/refs/heads/main`** — 2026-08-11에 41바이트 전부 NULL이 됐다.
     증상: `fatal: your current branch appears to be broken`, `git status`가 전 파일을 `A`로 표시.
     복구: `tail -1 .git/logs/refs/heads/main`(reflog는 살아 있다)에서 마지막 해시를 꺼내
     `git cat-file -t <해시>`로 확인 후 `printf '<해시>\n' > .git/refs/heads/main`.
     끝나면 `git fsck`로 검증. **작업 파일과 객체DB는 멀쩡하다 — ref만 다시 쓰면 된다.**
- git push는 사용자 승인 후.

## ★ 사격 판정은 **3단계 phase**다 (2026-08-06 대회 자료 대조로 발견)
| Phase | 시각 | LOS | 거리 | 계수 |
|---|---|---|---|---|
| P1 | 0~100s | <1° | 500~3000ft | 1.0 |
| P2 | 100~150s | <2° | 500~3500ft | 0.3 |
| P3 | 150~200s | <3° | 500~4000ft | 0.1 |
활성 phase 중 **최대값** 채택. 콘 부피비 1:6.36:21.37 → 기대 대미지 1.0:1.9:2.1
= **후반이 오히려 유리**하다. 규칙은 `tools_diag/wez_rule.py` 한 곳에 모았다.
**v0~v32의 판정은 전부 P1 고정 기준이었다.**

## ★ 판정 전에 반드시 확인할 것 (2026-08-06에 전부 당함)
1. **트리거 발동률**만 보지 말고 **기동이 실제로 일어났는지** 재라 → `tools_diag/maneuver_check.py`
2. **스로틀은 세 번 건드려 세 번 다 무효였다**(v36/v37/v38). 상수 대신 **각 단계 값을 직접 기록**하라
3. **순위는 순이득(준−받은)**으로. 준 데미지만 정렬하면 얻어맞는 기동이 1위가 된다
4. **배치 도는 중에 시뮬/도구를 수정하지 마라** — 앞뒤가 다른 규칙으로 측정된다
5. **기각 시 DLL만 되돌리지 말고 소스도 되돌려라** — v31 코드가 v32에 섞여 들어갔다

## ★ 현재 채택 기체 = **v40** (2026-08-09, 커밋 `80d7d6a`)
`AIP_v40.dll` + `Rule_v40.xml`. 10상대 150판 **102승 42무 6패 / 순이득 +68.14**.
(v32는 101승 34무 15패 / +51.66)
```cpp
AIM_FLOOR = clamp(상대고도 - 300, 800, 1500)   // Task_LeadPredict. v32는 상수 1500
DECO_AltitudeCheck MinAlt: 1800 -> 1000         // Rule_v40.xml
```
**원리: 고도를 내주는 건 상대를 따라갈 때만 이득이다.** v32는 매 판 1800m 벽에 걸려
(우리 최저고도 중앙 1797m vs 상대 403m) 상대가 그 아래로 가면 트리가 통째로
ClimbOut으로 넘어가 **추격이 중단**됐다. 기동 공간 1000m를 버리고 있었다.
⚠ **조준하한과 MinAlt는 반드시 같이 낮춘다.** 하나만 낮추면 벽에 부딪혀 에너지만 잃는다
(`divefree` 기각 사유). 무조건 낮추는 것도 안 된다(`lowfloor`는 kwon −3으로 기각).
상세: `상대기체 공유파일/2026-08-09_v40_고도하한_상대연동_채택/README.md`

## 스파링 상대 (유형별)
`ACE`(3D공세) `AIP_onecircle`(수평선회·최약) `AIP_sync`(거울) `AIP_jink`(불규칙)
`AIP_kwon` `AIP_v7`(실제BT) `SEARCH`(탐색형) `STRAIGHT`(직진) `AIP_junghwan`(팀원 8/6판)
★ **`AIP_jh2`(팀원 최신 `cf49f0e`) — 가장 강한 상대.** v32는 4승11패(전부 격추)였다.
  XML이 `Rule_junghwan_cf49f0e.xml`로 고유해 `Rule_mine.xml` 충돌이 없다.
⚠ **`AIP_dummy.dll`은 직선이 아니다**(80도 뱅크 선회). 직진 대조군은 `STRAIGHT`.
⚠ 팀원 파일은 원래 `AIP_DCS.dll`이라 **그대로 복사하면 우리 파일을 덮어쓴다.**

### ★★ `kwon`과 `junghwan`은 같은 사람(권정환)의 기체다 — XML이 충돌한다
7/22판이 `AIP_kwon.dll`, 8/6판이 `AIP_junghwan.dll`. **둘 다 `./Rule_mine.xml`을 읽는다.**
8/6 16:49에 junghwan 패키지를 넣으면서 kwon용 XML을 덮어썼고, 그 뒤 **kwon 배치는 전부
초기화 실패로 죽었다**(`Node not recognized: DECO_TargetLOSCheck`). 이틀간 못 봤다.
```bash
cp -f Rule_mine_kwon.xml Rule_mine.xml       # kwon 돌리기 전
cp -f Rule_mine_junghwan.xml Rule_mine.xml   # junghwan 돌리기 전 / 평상시
```
- **한 배치에 둘 다 넣지 마라.** 넣으려면 상대마다 XML을 갈아끼워라(`_v39c.sh` 참고).
- 유형 카운트도 주의: 둘은 독립 유형이 **아니다**(같은 사람의 두 시점).
- **상대 DLL이 초기화에 실패하면 파이썬이 죽는다**(`OSError 0xe06d7363`). 배치 로그에
  `SUMMARY`가 없는 구간이 있으면 그 상대는 **측정된 게 아니라 죽은 것**이다. 반드시 확인.

## 뷰어 모의경기 (BattleViewer)
```
서버: BattleViewer/BattleServer_V0.2/DogFightViewer.exe   (한 대만)
클라: student/my_submission.py            (우리, Rule_v32)
      student/my_submission_junghwan.py   (팀원, Rule_mine 직접 읽음)
      student/my_submission_straight.py   (직진 표적, DLL 안 씀)
```
- **한 PC면 `SERVER_IP="127.0.0.1"` 필수.** 실제 IP를 쓰면 `udp_mode=connected`가 되어
  서버가 루프백으로 응답할 때 패킷을 전부 버린다.
- **서버가 포트를 연 뒤에** 클라이언트를 띄워라. 먼저 띄우면 ICMP port-unreachable →
  `OSError` → 클라이언트가 **즉시 종료**된다. `netstat -an | findstr 9999`로 확인.
- `activate_rule_xml`이 `Rule_forTraining.xml`을 덮어쓰므로 **한 폴더에서 두 클라이언트를
  돌릴 땐** 한쪽을 `BT_RULE_XML="Rule_forTraining.xml"`로 둬서 no-op으로 만들 것.

## 환경 규칙 (규정집)
- 사격: 거리 **152.4~914.4m** AND **|ATA| ≤ 1.0°**. 데미지 계수 = (914.4−dist)/762 → **가까울수록 큼**
- 200초/판, 타임아웃 시 HP 비교. **고도 < 300m 즉시 패배.** 무한회피 30+30초 → 무승부
- 제출 = BT DLL + Rule XML, **ACTION_REPEAT=6 = BT 10Hz** (로컬 개발은 60Hz)
- **BT는 VP만 설정**한다. 스틱은 `Controller_CY::GetStick`이 변환(제출 제약)

## ★★★ dt 버그 — 10Hz 실전 조건에서 상대 선회율을 7~9배로 읽는다 (2026-08-08 실측)
`DeltaSecond`가 생성자 값 `1/60`에 고정돼 있다(`SetBehaviorTreeDeltaTime`을 호스트가 안 부른다).
이력 버퍼는 **BT 틱마다** 채워지는데 `ACTION_REPEAT=6`이면 12틱 = **1.2초**인 창을 **0.2초**로 나눈다.
```
repeat=1(60Hz) onecircle  om  8.5°/s  실측 8.75  → 비율 0.98   (맞다)
repeat=6(10Hz) onecircle  om 84.0°/s  실측 9.36  → 비율 8.98   (틀리다)
```
→ `R = tgtSpd/omega`가 209m(실제 1880m)가 되고 `phi` 상한에 걸려 **TailSlot이 124m**에 찍힌다.
**사격 최소거리는 152.4m다.** onecircle 최약 매치업·"뒤 91% ATA 7°인데 0점"의 정체.
⚠ **고치는 게 곧 개선은 아니다.** v32 상수 전부가 이 위에서 조정됐고 v17은 절제 1위였다.
상세·재현: `강화학습환경/Release/experiments/dt_bug/FINDING_2026-08-08.md`

## 함정 (실제로 당한 것들)
- **★ 아카이브 후 `git ls-files`로 실제로 들어갔는지 확인할 것.** `.gitignore`의 부정(!) 규칙은
  **조용히 실패한다.** 26~27행이 인코딩 손상으로 깨져 있어 **7/11부터 아카이브 DLL 29개가
  한 번도 커밋된 적이 없었다**(채택본 v32, 팀배포본, 스파링 상대 전부 포함).
  `git add -A`는 성공하고 경고도 없다. 2026-08-08에 발견·복구.
- **진단을 필터로 버리면 진단을 못 본다.** 배치 스크립트가 `[ACTIVE]`를 걸러내 dt 버그를 오래 못 봤다.
- **`[ACTIVE]` 진단에서 우리 기체는 `[RED]`로 찍힌다** (DLL 내부 Team enum이 시뮬의 Blue/Red와 반대).
  판별법: 상대 DLL을 안 쓰는 `STRAIGHT`로 돌려보면 우리 것만 나온다.
- **`AIP_final.dll`과 `AIP_v32.dll`은 해시가 다르지만 동작은 같다**(같은 소스 별도 빌드).
  8/8에 시드별 30판 일치로 검증했다. 해시가 다르다고 곧 다른 기체는 아니다 — **동작으로 증명할 것.**
- **제출본이 낡을 수 있다.** `AIP_final.dll`이 v27인 채로 있었다(XML은 v27~v32 동일해서 안 보였음).
  **크기/해시로 현역 DLL과 대조할 것.**
- **XML 이름 충돌.** `AIP_trinity.dll`은 `./Rule_forTraining.xml`을 읽는다 — 우리가 덮어쓰면
  팀원 원본이 죽는다. trinity 검증 시 `Rule_forTraining_orig.xml`로 되돌릴 것.
- **레거시 미사용 노드를 그대로 투입 금지.** 우리 최신 개선(out-of-plane/코너속도)을 모른다.
  아이디어만 추출해 우리 노드에 이식.
- **에피소드 경계**: 배치 로그는 판이 이어붙어 있다. 고도·위치가 점프하므로 분석 시 제외할 것.

## 대전제
**우리는 "어떤 기체일지 모르는 고도화된 상대"를 이겨야 한다.**
특정 상대 대응 튜닝 금지. 모든 수정은 **원리/물리**로 표현할 것. 과적합을 항상 자문.
