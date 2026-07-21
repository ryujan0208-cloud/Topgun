//타겟과의 거리 업데이트 노드

#include "DistanceUpdate.h"
#include <iostream>

namespace Action
{
	PortsList DistanceUpdate::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB")
		};
	}

	NodeStatus DistanceUpdate::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

		Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
		Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;

		float Distance = MyLocation.distance(TargetLocation);
		
		(*BB)->Distance = Distance;

		static int __dbg = 0;
		if (++__dbg % 30 == 0) std::cerr << "[DIST] team=" << (int)(*BB)->Team << " EnemyN=" << (*BB)->Enemy.size()
			<< " MyZ=" << MyLocation.Z << " TgtZ=" << TargetLocation.Z << " Dist=" << Distance << std::endl;

		//std::cout << "DistanceUpdate : " << TargetLocation.X << " " << TargetLocation.Y << " " << TargetLocation.Z << std::endl;
		// BTFunc::AddNodeExcute(&(*BB)->Temp_Text, 
		// 	std::string("Distance Update"));
		// BTFunc::AddNodeExcute(&(*BB)->Temp_Text, 
		// 	std::string("  -Distance :") + std::to_string(Distance) + "m");
		return NodeStatus::SUCCESS;
	}

}