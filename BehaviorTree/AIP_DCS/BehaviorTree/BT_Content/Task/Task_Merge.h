#pragma once
/*
 HABFM(중립/머지) 전용 Task. 2026-07-05 신규 추가.

 GetTail(타겟 뒤 500m 고정점)도 Lead/Pure(리드 보정 조준점)도 아닌, 타겟의
 "현재 위치"를 그대로 조준점으로 삼는다. 서로 우세를 못 가린 머지 상황에서는
 아직 어느 쪽으로 선회할지 판단할 근거(에너지/각도)가 불충분하므로, 우선
 각을 죽이며 시야를 유지하는 게 정석 대응이라는 판단.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Merge : public SyncActionNode
	{
	private:

	public:

		Task_Merge(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Merge()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
