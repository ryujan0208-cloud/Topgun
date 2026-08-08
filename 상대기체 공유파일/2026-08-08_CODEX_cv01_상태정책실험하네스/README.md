# CODEX cv01 — 상태정책 인과실험 하네스

## 용도와 상태

- 제출용/채택용 BT가 아니라 연구 전용 버전이다.
- v32의 일반 `Step` 경로는 유지하고, 실험 시에만 BT가 만든 VP를 교체하는
  `StepWithVPOverride` export를 추가했다.
- 클로드의 main 작업공간이나 v39 작업에는 병합하지 않았다.
- 판정: **연구 하네스 채택, 기체 정책 변경 없음**.

## 포함 파일

- `AIP_DCS_lab.dll`: VP prefix fork용 실험 DLL
- `Rule_v32.xml`: DLL과 함께 검증한 규칙 파일
- `source/`: DLL 및 Python wrapper의 정확한 대응 소스
- `tools/`: 단일 사례 보존과 상태-행동 결과표 생성 도구

실험 결과와 원시 데이터 색인은
`강화학습환경/Release/experiments/state_policy/runs/CV01/README.md`에 있다.
원시 리플레이는 용량 때문에 Git 비추적
`강화학습환경/Release/artifacts/state_policy/forks/`에 보존한다.

## 불변성 검증

- override 비활성 일반 경로는 원본 v32와 양쪽 기체 전체 CSV 해시가 같다.
- 모든 20개 후보 실험은 분기 전 양쪽 기체 로그가 완전히 같다.
- 단위검증 22개 통과.

## 결론

같은 `pure` 행동이 두 장면에서는 사격 burst를 키웠으나, 무작위 초기조건
두 장면에서는 사격을 없앴다. 전역 override는 기각한다. 상태별 정책 연구는
계속하되 LOS rate와 현재 BT 행동을 계측한 뒤에만 상태 분기를 검토한다.
