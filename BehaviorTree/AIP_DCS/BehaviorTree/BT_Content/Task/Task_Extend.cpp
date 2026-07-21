#include "Task_Extend.h"
#include <iostream>

PortsList Action::Task_Extend::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Extend::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyRight        = (*BB)->MyRightVector;

	// 수평 성분만 사용(Z=0)해서 상대 반대방향을 구함 -- 상대가 나보다 높거나 낮아도
	// 이 방향 자체가 강하/상승을 요구하지 않도록 함(Controller_CY 다이브 제약 회피).
	Vector3 LOSHorizontal = TargetLocation - MyLocation;
	LOSHorizontal.Z = 0.0;

	Vector3 AwayHorizontal;
	if (LOSHorizontal.length() < 1.0)
	{
		// 상대가 거의 바로 위/아래(수평 성분 거의 없음): 임의의 안전한 횡방향으로 대체
		AwayHorizontal = MyRight;
	}
	else
	{
		LOSHorizontal.normalize();
		AwayHorizontal = LOSHorizontal * -1.0;
	}

	// Use world-up so this never asks the controller to dive (2026-06-29 confirmed limitation)
	Vector3 WorldUp(0.0, 0.0, 1.0);
	Vector3 ExtendDir = AwayHorizontal * 0.7 + WorldUp * 0.6;
	ExtendDir.normalize();

	(*BB)->VP_Cartesian = MyLocation + ExtendDir * 4000.0;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] Extend Z=" << MyLocation.Z << std::endl;

	return NodeStatus::SUCCESS;
}
