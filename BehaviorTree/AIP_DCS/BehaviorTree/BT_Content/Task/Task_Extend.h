#pragma once
/*
 DBFM(방어/에너지열세) 전용 분리 기동 Task.
 상대와 정면으로 계속 맞붙지 않고, 상대 반대방향(수평)으로 벌어지면서 동시에
 상승(WorldUp)하는 조준점(VP)을 생성해 에너지를 회복한다.
 Controller_CY가 능동 강하 명령을 낼 수 없는 구조적 제약(2026-06-29 확정)을 피하기 위해
 Task_Evade/Task_ClimbOut과 동일하게 Z를 낮추는 방향은 절대 요구하지 않고
 수평 이탈 + 상승만 사용한다.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Extend : public SyncActionNode
	{
	private:

	public:

		Task_Extend(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Extend()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
