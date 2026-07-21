#include "DECO_TailThreatCheck.h"

namespace Action
{
	PortsList DECO_TailThreatCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("ThreatAngle")
		};
	}

	// Returns SUCCESS when enemy is behind me (angle between MyForward and Me->Target > ThreatAngle)
	// ThreatAngle=135: enemy is within rear 45deg cone -> evade
	NodeStatus DECO_TailThreatCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> ThreatAngleStr = getInput<std::string>("ThreatAngle");

		Vector3 MyLocation    = (*BB)->MyLocation_Cartesian;
		Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
		Vector3 MyForward     = (*BB)->MyForwardVector;

		Vector3 MyToTarget = TargetLocation - MyLocation;
		float angleRad = MyToTarget.angleBetween(MyForward);
		float angleDeg = angleRad * 57.2958f;

		float threshold = std::stof(ThreatAngleStr.value());

		if (angleDeg >= threshold)
		{
			return NodeStatus::SUCCESS;
		}
		else
		{
			return NodeStatus::FAILURE;
		}
	}
}
