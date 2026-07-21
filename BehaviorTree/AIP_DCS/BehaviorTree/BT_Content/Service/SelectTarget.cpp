#include "SelectTarget.h"
#include <iostream>

namespace Action
{
	PortsList SelectTarget::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB")
		};
	}



	NodeStatus SelectTarget::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

		//std::cout << "Size : " << (*BB)->Enemy.size() << std::endl;

		//�л����� 1��1�� ������ �׳� ������ Ÿ�� ����
		static int __dbg = 0;
		bool __shouldLog = (++__dbg % 30 == 0);

		if((*BB)->Enemy.size() > 0)
		{
			(*BB)->ACM = EF;

			(*BB)->TargetLocaion_Cartesian = (*BB)->Enemy.at(0).Location;
			(*BB)->TargetRotation_EDegree = (*BB)->Enemy.at(0).Rotation;
			(*BB)->TargetSpeed_MS = (*BB)->Enemy.at(0).Speed;

			if (__shouldLog) std::cerr << "[SelectTarget] team=" << (int)(*BB)->Team << " EnemyN=" << (*BB)->Enemy.size()
				<< " TgtZ=" << (*BB)->TargetLocaion_Cartesian.Z << std::endl;
		}
		else
		{
			if (__shouldLog) std::cerr << "[SelectTarget] team=" << (int)(*BB)->Team << " EnemyN=0 (Target is not Valid)" << std::endl;
		}
				
		return NodeStatus::SUCCESS;
	}

}