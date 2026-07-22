#include "Task_LeadPredict.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_LeadPredict::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 (v6): v5 SmoothPursuit + 상대 회피 예측 lead (사용자 4번 아이디어).
// [문제] v5 pure pursuit은 상대가 가만있으면 잘 잡지만, 상대가 선회 회피하면
//   계속 지나쳐(오버슈트) 조준 유지 실패 -> 격추 마무리 못 함(랜덤스폰 무승부).
// [해법] 상대 속도로 요격점을 리드하고, 상대 뱅크각(롤)으로 선회방향을 예측해
//   그 안쪽 앞에 VP를 찍는다. 상대가 왼쪽 뱅크면 왼쪽 선회 예측 -> 왼쪽 앞 조준.
//   예측이 틀리면 매 틱 상대 실제 자세로 재계산(폐루프)되어 자동 보정된다.
//   풀스로틀 유지(v5 교훈: 감속은 에너지 손실로 뒤처짐).

NodeStatus Action::Task_LeadPredict::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TgtFwd   = (*BB)->TargetForwardVector;   TgtFwd.normalize();
	Vector3 TgtRight = (*BB)->TargetRightVector;      TgtRight.normalize();

	double dist   = MyLocation.distance(TargetLocation);
	double mySpd  = (*BB)->MySpeed_MS;   if (mySpd < 1.0) mySpd = 1.0;
	double tgtSpd = (*BB)->TargetSpeed_MS;

	// 요격 리드: 상대 진행방향으로 미래위치 예측 (리드시간 = 거리/내속도, 캡 3초)
	// v7 (v8 롤백): 전 거리에서 예측 lead. 사거리 순수조준(v8)은 상대 회피를
	// 못 따라가 -40점 악화로 확인되어 원복. 사거리에서도 예측이 필요.
	double leadTime = dist / mySpd;
	if (leadTime > 3.0) leadTime = 3.0;
	Vector3 predicted = TargetLocation + TgtFwd * (tgtSpd * leadTime);

	double rollDeg = (*BB)->TargetRotation_EDegree.Roll;
	if (std::fabs(rollDeg) > 10.0)
	{
		double s = (rollDeg > 0.0) ? 1.0 : -1.0;
		double bankFactor = std::fabs(rollDeg) / 90.0;
		if (bankFactor > 1.0) bankFactor = 1.0;
		double turnMag = bankFactor * 0.25 * dist;
		if (turnMag > 600.0) turnMag = 600.0;
		if (dist < 600.0) turnMag *= (dist / 600.0);
		predicted = predicted + TgtRight * (s * turnMag);
	}

	// 강하각 클램프 (기존 정책)
	double climbSlope = dist * 0.5;
	double diveSlope  = dist * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (predicted.Z < minZ) predicted.Z = minZ;
	if (predicted.Z > maxZ) predicted.Z = maxZ;
	if (predicted.Z < 3500.0) predicted.Z = 3500.0;
	(*BB)->VP_Cartesian = predicted;

	// v9: 근접 폐쇄율 관리 — "뒤를 잡고도 추월하는" 문제 해결(리플레이서 확인).
	// 원거리는 풀스로틀 유지(v5 교훈: 원거리 감속은 에너지 손실로 뒤처짐).
	// 사거리 근처에서 상대보다 유의미하게 빠를 때만 소폭 감속해 지나치지 않게 한다.
	// (v1 TrackHold의 폐쇄율 로직. 당시엔 뒤를 못 잡아 검증 불가였으나 v7은 WEZ 31초 유지)
	// v11: 연속 + 서서히 변하는 스로틀 (사용자 지적 반영).
	//   v9/v10 실패는 "감속" 자체가 아니라 계단식 급변(1.0<->0.55 요동)이 원인일 수 있음.
	//   v5 교훈(VP 급변=기동 불안정)을 스로틀에도 그대로 적용한다.
	//   (1) 목표 스로틀은 거리/속도차/뱅크각에 연속 비례 (계단 없음, 최대 0.75까지만)
	//   (2) 실제 스로틀은 틱당 0.004씩만 이동 -> 초당 0.24, 급변 불가
	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	double speedMargin = mySpd - tgtSpd;
	double tgtBank = std::fabs((*BB)->TargetRotation_EDegree.Roll);

	// v14: dV(속도차)를 0으로 수렴시키는 속도매칭 폐루프.
	//  [실측 근거] overshoot.py 틱추적: 뒤를 잡고 ATA 3~5°까지 조준이 완벽한데도
	//    dV=+38m/s가 시종일관 일정해 233m->0m를 8초에 관통, 사거리를 그냥 통과함.
	//    => 문제는 조준이 아니라 폐쇄율. 제어 대상은 "스로틀 값"이 아니라 "dV" 자체다.
	//  [설계] 목표는 감속이 아니라 dV -> 0 (상대와 같은 속도로 뒤에 머물기).
	//    사거리 밖: 풀스로틀로 최대한 빨리 접근(에너지 유지)
	//    사거리 안: dV를 0으로 수렴시켜 그 자리 유지 -> ATA를 조일 시간을 번다
	//    너무 근접: 목표 dV를 음수로 둬 적극적으로 뒤로 빠져 관통·충돌 방지
	const double WEZ_MAX = 914.0, WEZ_MIN = 152.0;

	double dvTarget;                       // 목표 속도차(m/s)
	if (dist > WEZ_MAX)      dvTarget = 999.0;                 // 사거리 밖: 제한 없음(풀스로틀)
	else if (dist > 400.0)   dvTarget = 0.0;                   // 사거리 안: 속도 매칭
	else if (dist > WEZ_MIN) dvTarget = -10.0;                 // 근접: 살짝 뒤로 빠짐
	else                     dvTarget = -25.0;                 // 과근접: 확실히 뒤로

	double dvErr = speedMargin - dvTarget;  // +면 내가 너무 빠름 -> 줄여야
	float target;
	if (dvTarget > 900.0) {
		target = 1.0f;                      // 사거리 밖은 무조건 풀스로틀
	} else {
		// dV 오차에 비례해 스로틀 조정 (0.55~1.0). 폐루프라 dV가 목표에 수렴한다.
		double u = 1.0 - dvErr * 0.012;     // dvErr +38 -> 0.54 / 0 -> 1.0 / -20 -> 1.0(상한)
		if (u > 1.0) u = 1.0;
		if (u < 0.55) u = 0.55;
		target = (float)u;
	}
	(void)tgtBank;

	static float lastThr[2] = { 1.0f, 1.0f };
	const float STEP = 0.008f;              // 틱당 최대 변화 (60Hz -> 초당 0.48, 약 1초에 걸쳐 부드럽게)
	float cur = lastThr[__ti];
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LeadPredict dist=" << dist << " dV=" << speedMargin << " thr=" << cur << std::endl;

	return NodeStatus::SUCCESS;
}
