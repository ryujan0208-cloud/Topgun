#include "Task_LevelOff.h"

PortsList Action::Task_LevelOff::providedPorts()
{
	return {
		InputPort<CPPBlackBoard*>("BB")
	};
}

// High altitude recovery: aim VP forward at target altitude to descend
NodeStatus Action::Task_LevelOff::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
	Vector3 MyForward  = (*BB)->MyForwardVector;

	// Aim 5000m ahead at 4000m altitude to induce controlled descent
	Vector3 VP = MyLocation + MyForward * 5000.0f;
	VP.Z = 4000.0f;

	(*BB)->VP_Cartesian = VP;

	return NodeStatus::SUCCESS;
}
