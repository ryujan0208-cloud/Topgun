#pragma once
/*
 스파링 전용 상대기체 노드: 원써클(One-Circle) 강제 기동.

 목적 - 우리 기체의 "코너속도/반경 싸움" 약점을 저격하는 드릴 상대.
   BFM에서 원써클은 서로 기수를 마주보며(nose-to-nose) 같은 원을 도는 반경 싸움이다.
   이 노드는 (1)상대 현재 위치로 순수 추적하되 (2)조준점 고도를 자기 고도로 맞춰
   수평면 선회를 강제하고 (3)스로틀을 코너속도에 고정해 선회율을 최대로 유지한다.
   -> 우리 기체가 과속(420m/s)으로 싸우면 선회율이 1/4이라 이 상대에게 각도를 계속 내준다.

 주의 - 이 노드는 우리 제출 기체의 Rule XML에서는 절대 사용하지 않는다.
        Rule_onecircle.xml 전용(AIP_onecircle.dll).
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_OneCircle : public SyncActionNode
	{
	public:
		Task_OneCircle(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_OneCircle()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
