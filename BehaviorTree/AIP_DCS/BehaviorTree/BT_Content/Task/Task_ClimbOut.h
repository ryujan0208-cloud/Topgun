#pragma once
#include "../../behaviortree_cpp_v3/action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_ClimbOut : public SyncActionNode
	{
	public:
		Task_ClimbOut(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_ClimbOut()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
