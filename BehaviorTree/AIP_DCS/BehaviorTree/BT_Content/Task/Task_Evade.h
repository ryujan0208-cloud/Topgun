#pragma once
/*
 방어 기동(Break Turn) Task.
 적이 내 후방 위협각(AspectAngle) 안에 들어왔을 때, 적이 있는 방향으로 강하게 횡선회(브레이크 턴)하면서
 약간 상승하여 적의 추적/조준을 어렵게 만드는 추적점(VP)을 생성한다.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Evade : public SyncActionNode
	{
	private:


	public:


		Task_Evade(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Evade()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
