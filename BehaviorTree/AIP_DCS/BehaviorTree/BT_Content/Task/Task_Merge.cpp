#include "Task_Merge.h"
#include <iostream>

PortsList Action::Task_Merge::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Merge::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;

	// 타겟의 현재 위치를 그대로 조준점으로 사용 (리드/트레일 오프셋 없음).
	Vector3 VP = TargetLocation;

	// 강하각 클램프 pursuit: 다른 Task와 동일한 패턴 (상승 관대/강하 보수적).
	double Distance = MyLocation.distance(TargetLocation);
	double climbSlope = Distance * 0.5;
	double diveSlope = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;

	(*BB)->VP_Cartesian = VP;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] Merge Z=" << MyLocation.Z << " VPZ=" << VP.Z << std::endl;

	return NodeStatus::SUCCESS;
}
