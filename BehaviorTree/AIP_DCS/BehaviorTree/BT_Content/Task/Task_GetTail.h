#pragma once
/*
 상대기 후방(6시 방향) 추적 Task.
 타겟의 현재 위치가 아니라 타겟 뒤쪽 일정 거리(TailStandoff)를 조준점(VP)으로 잡아,
 정면으로 붙는 대신 곡선으로 파고들어 상대 후방으로 전환(꼬리 물기)을 시도한다.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_GetTail : public SyncActionNode
	{
	private:

	public:

		Task_GetTail(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_GetTail()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
