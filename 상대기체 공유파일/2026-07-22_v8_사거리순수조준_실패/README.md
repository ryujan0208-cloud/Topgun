# v8

mean -11.41 (v7 +28.30 대비 -40). 사거리에서 예측 끄고 순수조준 -> 상대 회피를 못 따라가 악화. 롤백.

## 구성
- AIP_v8.dll (Rule_v8.xml 로드) + Rule_v8.xml
- 핵심 노드: Task_LeadPredict (버전별 스로틀 정책 차이)

기준선: v7 = mean +28.30 (vs v0 15시드 랜덤스폰)
