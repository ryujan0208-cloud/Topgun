#include "DECO_AltitudeCheck.h"
#include <cmath>

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

		// v22c: predictive altitude guard. A plain altitude line (1800) is too late
		//  in a steep dive (seed11: pitch -79deg, hit 1800 at pitch -88deg and lost
		//  1461m more to 300m floor). Trigger on predicted altitude 5s ahead using
		//  vertical speed. In level flight (zdot~0) this equals the old behavior, so
		//  no interference with engagement (one-directional safety).
		double pitchRad = (*BB)->MyRotation_EDegree.Pitch * 3.14159265358979 / 180.0;
		double zdot = (double)(*BB)->MySpeed_MS * std::sin(pitchRad);   // negative = descending
		double predAlt = (double)CurrentAlt + zdot * 5.0;

		if (CurrentAlt < InputMinAlt || predAlt < (double)InputMinAlt)
		{
			return NodeStatus::SUCCESS;
		}
		else
		{
			return NodeStatus::FAILURE;
		}
	}
}
