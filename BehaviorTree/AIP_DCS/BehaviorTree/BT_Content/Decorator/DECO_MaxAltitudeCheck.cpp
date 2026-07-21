#include "DECO_MaxAltitudeCheck.h"

namespace Action
{
	PortsList DECO_MaxAltitudeCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("MaxAlt")
		};
	}

	// Returns SUCCESS when altitude(m) > MaxAlt -> triggers level-off/descent
	NodeStatus DECO_MaxAltitudeCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> MaxAltStr = getInput<std::string>("MaxAlt");

		float CurrentAlt = (float)(*BB)->MyLocation_Cartesian.Z;
		float InputMaxAlt = std::stof(MaxAltStr.value());

		if (CurrentAlt > InputMaxAlt)
		{
			return NodeStatus::SUCCESS;
		}
		else
		{
			return NodeStatus::FAILURE;
		}
	}
}
