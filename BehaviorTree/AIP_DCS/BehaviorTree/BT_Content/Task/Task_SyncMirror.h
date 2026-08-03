#pragma once
/*
 스파링 전용 상대기체 노드: 싱크(Mirror) 기동.

 목적 - 우리 기체가 "대칭을 깨고 우위를 만들 수 있는가"를 시험하는 드릴 상대.
   상대(=우리 기체)의 실제 선회를 매 틱 읽어, 같은 회전축·같은 각속도로 자기 기수를
   돌린다. 속도와 고도도 따라 맞춘다. 결과적으로 상대가 무슨 기동을 하든 똑같이 따라해
   상대 각도 우위를 만들지 못하게 한다.
   -> 우리가 이 상대에게 각도를 못 얻으면, 그건 상대가 강해서가 아니라
      "우리 기동에 비대칭을 만드는 요소가 없다"는 뜻이다.

 주의 - 이 노드는 우리 제출 기체의 Rule XML에서는 절대 사용하지 않는다.
        Rule_sync.xml 전용(AIP_sync.dll).
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_SyncMirror : public SyncActionNode
	{
	public:
		Task_SyncMirror(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_SyncMirror()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
