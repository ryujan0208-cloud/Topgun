#include "DECO_AltitudeCheck.h"

namespace Action
{
	PortsList DECO_AltitudeCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("MinAlt")
		};
	}

	// Returns SUCCESS when altitude(m) < MinAlt -> triggers recovery
	NodeStatus DECO_AltitudeCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> MinAltStr = getInput<std::string>("MinAlt");

		float CurrentAlt = (float)(*BB)->MyLocation_Cartesian.Z;
		float InputMinAlt = std::stof(MinAltStr.value());

		if (CurrentAlt < InputMinAlt)
		{
			return NodeStatus::SUCCESS;
		}
		else
		{
			return NodeStatus::FAILURE;
		}
	}
}
