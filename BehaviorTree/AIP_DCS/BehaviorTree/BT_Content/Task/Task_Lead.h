#pragma once
/*
 원거리 교전용 Lead Pursuit Task.
 타겟의 현재 속도(ForwardVector * Speed)와 거리/내 속도를 이용해 예상 요격 시간을 계산하고,
 그 시간만큼 타겟이 이동할 위치(Lead Point)를 추적점(VP)으로 설정한다.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Lead : public SyncActionNode
	{
	private:


	public:


		Task_Lead(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Lead()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
