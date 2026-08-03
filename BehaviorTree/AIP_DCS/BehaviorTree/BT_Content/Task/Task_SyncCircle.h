#pragma once
/*
 스파링 전용 상대기체 노드: 싱크 + 원써클 (반경 축소 옵션).

 목적 - 두 기체가 "같은 원" 위 서로 반대편에 자리잡고 함께 돌면서(싱크), 속도·고도까지
   맞춰 어느 쪽도 각도 우위를 못 얻게 만드는 교착을 강제한다.
   Shrink > 0 이면 매 틱 안쪽으로 조금씩 파고들어 **원 반경을 서서히 줄인다.**
   -> 사용자가 원래 우리 기체에 요구했던 기동(원써클 싱크 -> 반경 축소)을 상대가 구사하는 것.
      이 상대에게 밀린다면 그 기동이 실제로 강하다는 증거이고, 우리 기체에 도입할 근거가 된다.

 구현 - 두 기체의 중점을 원 중심 C로 잡고(수평면), 내 위치의 접선 방향으로 VP를 찍는다.
   접선 방향은 현재 기수와 같은 쪽을 선택해 방향이 튀지 않게 한다.
   Shrink는 접선에 "중심 방향" 성분을 섞어 나선형으로 조여든다.

 포트 - BB, Shrink(0.0 = 순수 원써클 유지 / 0.2~0.35 = 반경 축소)

 주의 - 이 노드는 우리 제출 기체의 Rule XML에서는 절대 사용하지 않는다.
        Rule_synccircle.xml / Rule_shrink.xml 전용.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_SyncCircle : public SyncActionNode
	{
	public:
		Task_SyncCircle(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_SyncCircle()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
