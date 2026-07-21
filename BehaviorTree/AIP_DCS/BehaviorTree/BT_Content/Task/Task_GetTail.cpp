#include "Task_GetTail.h"
#include <iostream>

PortsList Action::Task_GetTail::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_GetTail::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TargetForward  = (*BB)->TargetForwardVector;

	TargetForward.normalize();

	// 타겟 6시 방향 지점을 조준점으로 설정 -> 정면 추적이 아닌 후방 전환 기동
	// (2026-07-05: 거리비례 오프셋으로 바꿔봤다가 기준선을 -30.32 -> -122.13으로
	// 크게 망가뜨림(완전 무교전) -> 원래 고정 500m로 원복. 이 태스크는 baseline이
	// 이미 촘촘히 튜닝해둔 부분이라 값 하나만 바꿔도 궤적이 크게 갈라지는 것으로 보임)
	Vector3 TailPoint = TargetLocation - TargetForward * 500.0;

	// 강하각 클램프 pursuit: 상승은 관대(~26.5도), 강하는 보수적(~11도)으로 비대칭 제한.
	// 바닥도 ClimbOut 트리거(3000m)보다 위로 올려서 회복 여유 확보.
	double Distance = MyLocation.distance(TargetLocation);
	double climbSlope = Distance * 0.5;
	double diveSlope = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (TailPoint.Z < minZ) TailPoint.Z = minZ;
	if (TailPoint.Z > maxZ) TailPoint.Z = maxZ;
	if (TailPoint.Z < 3500.0) TailPoint.Z = 3500.0;

	(*BB)->VP_Cartesian = TailPoint;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] GetTail Z=" << MyLocation.Z << " VPZ=" << TailPoint.Z << std::endl;

	return NodeStatus::SUCCESS;
}
