#include "Task_SmoothPursuit.h"
#include <iostream>

PortsList Action::Task_SmoothPursuit::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 (v5): 극단 단순 추격. 노드 전환을 최소화해 매끄러운 기동을 만든다.
// [배경] v4 궤적 분석: 복잡한 트리의 잦은 노드전환(GetTail<->Lead<->LagEntry<->
//   MergeReversal)으로 VP가 튀어 속도(208~358)/선회율(-2~19) 요동, 거리 1300~
//   5900m 진동. dummy(단일노드)는 340m/s 7deg/s 일정하게 우리를 앞섰다.
// [가설] pure pursuit(VP=적위치) + 풀스로틀(에너지 유지)만으로 단일 노드 추격하면
//   선회하는 표적을 쫓을 때 자연스러운 lag 곡선이 되고, 에너지를 안 잃어 따라잡는다.
//   v4의 감속(0.65)이 오히려 에너지를 잃게 해 뒤처진 것이 궤적에서 확인됨.

NodeStatus Action::Task_SmoothPursuit::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;

	double Distance = MyLocation.distance(TargetLocation);

	// VP = 적 현재 위치 (pure pursuit) + 강하각 클램프
	Vector3 VP = TargetLocation;
	double climbSlope = Distance * 0.5;
	double diveSlope  = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;
	(*BB)->VP_Cartesian = VP;

	// 풀스로틀: 에너지 유지 (감속하면 뒤처짐이 v4에서 확인됨)
	(*BB)->Throttle = 1.0f;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] SmoothPursuit dist=" << Distance << std::endl;

	return NodeStatus::SUCCESS;
}
