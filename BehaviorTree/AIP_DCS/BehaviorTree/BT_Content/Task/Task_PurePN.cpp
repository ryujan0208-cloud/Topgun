#include "Task_PurePN.h"
#include <algorithm>
#include <iostream>

PortsList Action::Task_PurePN::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_PurePN::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;

	double Distance = MyLocation.distance(TargetLocation);

	Vector3 LOS = TargetLocation - MyLocation;
	LOS.normalize();

	// 시뮬은 고정 60Hz로 틱됨(다른 Task들의 30틱 스로틀 로그와 동일 가정, 2026-07-03 확인).
	const double SIM_HZ = 60.0;

	Vector3 LOSRate(0.0, 0.0, 0.0);
	if (_hasPrevLOS)
	{
		LOSRate = (LOS - _prevLOS) * SIM_HZ;
	}
	_prevLOS = LOS;
	_hasPrevLOS = true;

	// PN 보정: 상대 속도벡터를 외삽하는 대신, LOS 자체의 회전을 관측해서 그 회전이
	// 계속될 방향으로 조준선을 미리 보정한다. N(항법상수)*LEAD_T초 만큼 앞선 LOS를
	// 조준점으로 사용 -- 상대가 선회 중이어도 LOS 회전을 직접 따라가므로 상대의
	// 순간 기수방향만 보는 기존 방식보다 강건하다.
	const double N = 3.0;
	const double LEAD_T = 0.5;
	Vector3 AimDir = LOS + LOSRate * (N * LEAD_T);
	AimDir.normalize();

	double standoff = std::max(Distance, 200.0);
	Vector3 VP = MyLocation + AimDir * standoff;

	// 강하각 클램프: Task_Pure/Task_Lead와 동일한 비대칭 클램프(상승 관대/강하 보수적)를
	// 그대로 적용해 Controller_CY의 능동강하 불가 제약을 건드리지 않는다.
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
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] PurePN Z=" << MyLocation.Z << " VPZ=" << VP.Z << std::endl;

	return NodeStatus::SUCCESS;
}
