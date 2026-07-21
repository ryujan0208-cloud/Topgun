#include "Task_TailChase.h"
#include <iostream>

PortsList Action::Task_TailChase::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 (v4 실험): GetTail(적 6시 500m 조준) + 코너속도 감속.
// [문제] 저속 선회 표적조차 뒤를 못 잡음(WEZ 2.6초). 사거리/조준 로직(LagEntry)이
//   검증조차 안 되는 근본 원인.
// [가설] 항상 풀스로틀이라 선회반경이 커서 상대 안쪽을 못 파고든다(BFM 코너속도).
//   뒤잡기 선회 중 감속(0.65)해 선회반경을 줄이면 안쪽 진입이 가능한지 확인한다.
//   GetTail의 조준점(500m 상수)은 팀원 검증값이라 미변경, throttle만 추가.

NodeStatus Action::Task_TailChase::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TargetForward  = (*BB)->TargetForwardVector;
	TargetForward.normalize();

	Vector3 TailPoint = TargetLocation - TargetForward * 500.0;

	double Distance = MyLocation.distance(TargetLocation);
	double climbSlope = Distance * 0.5;
	double diveSlope  = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (TailPoint.Z < minZ) TailPoint.Z = minZ;
	if (TailPoint.Z > maxZ) TailPoint.Z = maxZ;
	if (TailPoint.Z < 3500.0) TailPoint.Z = 3500.0;
	(*BB)->VP_Cartesian = TailPoint;

	// 코너속도 감속: 뒤잡기 선회 반경 축소
	(*BB)->Throttle = 0.65f;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] TailChase dist=" << Distance << std::endl;

	return NodeStatus::SUCCESS;
}
