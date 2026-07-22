# v13

상대 뱅크각 변화량 EMA로 회피강도 추정 -> 회피 강하면 풀스로틀(v7), 약하면 감속(v11). 검증 진행 중.

## 구성
- AIP_v13.dll (Rule_v13.xml 로드) + Rule_v13.xml
- 핵심 노드: Task_LeadPredict (버전별 스로틀 정책 차이)

기준선: v7 = mean +28.30 (vs v0 15시드 랜덤스폰)
