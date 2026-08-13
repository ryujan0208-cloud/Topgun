# 🔴 서버 경로와 로컬 경로가 같은 필드에 다른 의미의 값을 넣는다 · 2026-08-13

## 요약

`OPlaneData.LocationX/Y/Z`는 **(위도°, 경도°, 고도m)**이다. 직교 좌표가 아니다.
그런데 **서버 경로는 Unreal 직교 좌표를 그 필드에 그대로 넣는다.**

**우리 270판 측정은 전부 로컬 경로만 지났다. 서버 경로는 한 번도 안 지났다.**

## 두 경로 (`bt_action_provider.py`)

```python
# 로컬 — compute_action()  : 우리 rehearsal_10hz.py가 쓰는 경로
my_opd = self.AIPilotDLL.ChangeData(my_id, force, 100.0, 0, my_navi)   # DLL이 변환
control_action = self.ai_pilot.Step(..., model.get_fdm_data(), ...)

# 서버 — _compute_remote_action() : 대회 서버가 쓰는 경로
control_action = self.ai_pilot.StepWithPlaneData(my_plane, target_plane)
```

`StepWithPlaneData`가 받는 `my_plane`은 `policies.py`가 이렇게 만든다:

```python
my_plane_data = AIPilot.BuildPlaneData(
    [own_plane.position.x, own_plane.position.y, own_plane.position.z],   # Unreal 직교
    ...)
```

## 실측 ① — `ChangeData`가 만드는 값의 정체

로컬 시뮬 한 스텝에서 `ChangeData` 출력을 가로챘다:

```
나=(37.9, 128.2, 7,000.1)   Speed=299.9
적=(38.0, 128.2, 7,002.8)   Speed=299.9
원본 항법: Lat=37923601  Lon=128181881  Alt=22966312
```

**LocationX = 위도(도), LocationY = 경도(도), LocationZ = 고도(m).**
DLL이 `Step` 내부에서 이 값을 직교로 변환해 `MyLocation_Cartesian`을 만든다.

## 실측 ② — 직교를 넣으면 거리가 11만 배가 된다

두 기체를 **정면 610m** 떨어뜨리고 서버 경로로 호출:

| 넣은 값 | BT가 계산한 거리 | BT가 만든 VP |
|---|---|---|
| **직교 그대로** `(0,0,3000)` / `(610,0,3000)` | **6.76 × 10⁷** | (63,418,988, −11,271,580, 3000) |
| **위경도로 변환** `(37.9236,128.1819,3000)` / `(+0.00548°,…)` | **607.25** ✅ | (1,605, 0.3, 3000) |

DLL이 `X=610`을 **"위도 610도"**로 해석한다.

팀원(junghwan)이 `SHARE_NOTES.md`에서 v32로 보고한 `Dist=4.67894e+07`과 **같은 자릿수**다.
**v32 고유 문제가 아니라 서버 경로 공통 문제다.**

## 거리가 6.76e7이면 우리 트리가 어떻게 되나

| 조건 | 실제 |
|---|---|
| `dist > 914` → 풀스로틀 | **항상 참** — 스로틀이 절대 안 내려감 |
| `leadTime = dist/속도` (상한 3초) | **항상 3초 최대 리드** |
| v17 궤도추종 `dist < 2500` | **한 번도 안 걸림** |
| v27 종말조준 `dist < 914` | **한 번도 안 걸림** |
| v21 뱅크 `turnMag = 0.25×dist` (상한 600) | **항상 600m로 포화** |

→ **계속 선회하며 쫓지만 절대 수렴하지 못하고 스쳐 지나간다.**
   (사용자가 뷰어 대전에서 관측한 "교전 없이 서로 기동만 하다 지나침"과 정합적이다.
   단 **인과는 아직 확정 아니다** — 아래 미확인 참조.)

## 실측 ③ — DLL의 변환 계수 (수정 시 필요)

| | 실측 | 이론 |
|---|---|---|
| 위도 | **110,800 m/도** | ~111,320 |
| 경도(위도 37.9°) | **87,900 m/도** | 111,320 × cos(37.9°) = 87,800 ✅ |

⚠ **고도는 설명이 안 된다.** 고도만 500m 차이를 주면 거리가 **707.11m**(= 500 × √2)로 나온다.
   500이어야 한다. 원인 미상. **수정 전에 반드시 규명해야 한다.**

## 미확인 — 넘겨짚지 않는다

1. **대회 서버가 보내는 `position`이 정말 직교인지 실측 안 했다.**
   운영측 답변(8/3)은 *"PlaneInfo — Unreal Engine 좌표계, Cartesian 좌표계(X, Y, Z(Alt: 양수))"* 이지만
   **우리가 값을 본 적은 없다.** 단위(m/cm)도 모른다.
2. **뷰어 현상의 인과가 이것이라고 확정되지 않았다.** 정합적일 뿐이다.
3. 고도 √2 이상(위 ⚠).

## 다음 — 서버 원시값 진단

`policies.py::_compute_provider_action`에 **환경변수로 켜는 로그**를 넣었다(기본 OFF, 최대 5줄).
로컬 측정 경로(`rehearsal_10hz.py`)는 `policies.py`를 쓰지 않으므로 **영향 없다.**

### 실행 방법

1. 뷰어 서버를 먼저 켠다 (`BattleViewer/BattleServer_V0.2/DogFightViewer.exe`)
2. `netstat -an | findstr 9999`로 포트가 열렸는지 확인
3. 클라이언트를 아래처럼 띄운다:

```bash
cd 강화학습환경/Release
TOPGUN_PROBE=1 "/c/Users/TFX5470H/anaconda3/envs/aip/python.exe" student/my_submission.py
```

PowerShell이면:

```powershell
$env:TOPGUN_PROBE=1; & "C:\Users\TFX5470H\anaconda3\envs\aip\python.exe" student\my_submission.py
```

4. 콘솔에 나오는 `[PROBE]` 5줄을 그대로 알려주면 된다:

```
[PROBE] frame=… own=(x, y, z) enemy=(x, y, z) |차이|=… own_rot=(…) own_vel=(…)
```

### 그 값으로 판별할 것

- `|차이|`가 **610~914 근처**면 → **미터 단위 직교** (라운드 시작 거리와 일치)
- `|차이|`가 **61,000~91,400 근처**면 → **센티미터 단위 직교**
- `own=(37.9, 128.2, …)` 형태면 → 이미 위경도 (문제 없음)
- `z`가 3000~9000 범위면 고도(m), 300,000 범위면 고도(cm)

## 수정 방향 (값 확인 후)

BT는 **상대 기하만** 쓰므로 참 위경도가 필요 없다. 거리만 보존하면 된다:

```python
LAT0 = 37.9236   # 기준점(임의). 경도 스케일에만 쓰인다
pseudo_lat = LAT0 + X_m / 110800.0
pseudo_lon = LON0 + Y_m / (110800.0 * cos(radians(LAT0)))
alt        = Z_m
```

⚠ 고도 √2 이상을 먼저 규명하지 않으면 이 수정도 반쪽이 된다.
