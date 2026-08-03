#pragma once
/*
 위협 판정 데코레이터: "적이 실제로 나를 조준 중인가".

 기존 방어 트리거는 AA>120(내가 적의 앞쪽 반구에 있음)이었는데, 이는 적이 나를 겨누는지와
 무관하다. 실측 결과 ACE 상대로 경기의 **83%** 동안 켜져 우리가 영구 방어 모드에 갇혔다
 (내 ATA가 200초 내내 100도 아래로 못 내려감 = 공격 자체를 못 함).

 이 노드는 적 기수와 (적->나) 방향의 각(=적의 ATA)이 임계 미만일 때만 SUCCESS.
 사격 조건이 ATA<=1.0도 & 152.4~914.4m 이므로, AimAngle 25도 + 거리 1100m 조합은
 사격 가능 영역을 **구조적으로 완전히 포함**하면서(놓칠 수 없음) 방어 시간만 줄인다.

 실측(ACE전 3판 35997틱, 실제 피격 518틱):
   AA>120 & d<1500  -> 지속 83% / 피격커버 100%
   적ATA<20 & d<1000 -> 지속 41% / 피격커버 100%
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class DECO_ThreatAimCheck : public SyncActionNode
	{
	public:
		DECO_ThreatAimCheck(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~DECO_ThreatAimCheck()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
