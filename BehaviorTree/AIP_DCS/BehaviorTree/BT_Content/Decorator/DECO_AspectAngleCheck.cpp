#include "DECO_AspectAngleCheck.h"

namespace Action
{
	PortsList DECO_AspectAngleCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("UpDown"),
			InputPort<std::string>("InputAA")
		};
	}

	NodeStatus DECO_AspectAngleCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> UpOrDown = getInput<std::string>("UpDown");
		Optional<std::string> IAA = getInput<std::string>("InputAA");

		float CurrentAA = (*BB)->MyAspectAngle_Degree;
		std::string UD = UpOrDown.value();
		float InputAspectAngle = std::stof(IAA.value());

		if (UD == "Greater")
		{
			if (CurrentAA >= InputAspectAngle)
			{

				return NodeStatus::SUCCESS;
			}
			else
				return NodeStatus::FAILURE;
		}
		else if (UD == "Less")
		{
			if (CurrentAA <= InputAspectAngle)
			{

				return NodeStatus::SUCCESS;
			}
			else
				return NodeStatus::FAILURE;
		}
		else
		{
			//UpDown 입력 문자열이 오타난건 아닌지 확인 필요!!!! Greater 나 Less 가 아님
			return NodeStatus::FAILURE;
		}

	}
}
