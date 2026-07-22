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

	(*BB)->Throttle = 1.0f;  // 에너지 유지

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LeadPredict dist=" << dist << std::endl;

	return NodeStatus::SUCCESS;
}
