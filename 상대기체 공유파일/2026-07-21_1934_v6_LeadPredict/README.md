# v6 LeadPredict (2026-07-21 아카이브)
v5 SmoothPursuit + 상대 회피 예측 lead (사용자 4번 아이디어).
상대 뱅크각(롤)으로 선회방향 예측 -> 미리 그 앞에 VP.

## 성적 (v6 vs v0, 15시드 랜덤스폰)
- mean reward **+19.25** (v5의 -4.96에서 +24 개선)
- **배치에서 첫 데미지**: seed1 적HP 0.98, seed3 0.93
- 0/0/15 (완전격추는 아직). seed 편차 큼(뒤잡기 안정성이 다음 병목)

## 구성
- AIP_v6.dll (Rule_v6.xml 로드) + Rule_v6.xml
- 핵심: Task_LeadPredict (요격리드 + 롤기반 선회예측 + 풀스로틀)
