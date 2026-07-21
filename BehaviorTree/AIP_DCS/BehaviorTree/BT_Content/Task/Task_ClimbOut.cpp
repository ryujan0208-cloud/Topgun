#include "Task_ClimbOut.h"
#include <iostream>

PortsList Action::Task_ClimbOut::providedPorts()
{
	return {
		InputPort<CPPBlackBoard*>("BB")
	};
}

// Low altitude recovery: climb by aiming VP forward-up
NodeStatus Action::Task_ClimbOut::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
	Vector3 MyForward  = (*BB)->MyForwardVector;
	Vector3 MyUp       = (*BB)->MyUpVector;

	// 전방 0.3 + 상방 1.0 방향으로 VP 설정 (Task_Evade 패턴과 동일, 위쪽 비중 증가)
	// Use world-up so recovery works even when aircraft is inverted
	Vector3 WorldUp(0.0f, 0.0f, 1.0f);
	Vector3 ClimbDir = MyForward * 0.3f + WorldUp;
	ClimbDir.normalize();

	(*BB)->VP_Cartesian = MyLocation + ClimbDir * 5000.0f;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] ClimbOut Z=" << MyLocation.Z << std::endl;

	return NodeStatus::SUCCESS;
}
