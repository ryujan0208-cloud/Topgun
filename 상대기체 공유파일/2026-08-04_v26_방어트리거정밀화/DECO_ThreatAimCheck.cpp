#include "DECO_ThreatAimCheck.h"
#include <cmath>

namespace Action
{
	PortsList DECO_ThreatAimCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("AimAngle")
		};
	}

	// 적의 ATA(적 기수와 "적->나" 방향의 각)가 AimAngle 미만이면 SUCCESS = 실제 위협.
	NodeStatus DECO_ThreatAimCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> AimStr = getInput<std::string>("AimAngle");

		Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
		Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
		Vector3 TgtForward     = (*BB)->TargetForwardVector;

		Vector3 TargetToMe = MyLocation - TargetLocation;
		float angleDeg = (float)(TargetToMe.angleBetween(TgtForward) * 57.2957795);

		float threshold = 25.0f;
		if (AimStr) threshold = std::stof(AimStr.value());

		return (angleDeg < threshold) ? NodeStatus::SUCCESS : NodeStatus::FAILURE;
	}
}
