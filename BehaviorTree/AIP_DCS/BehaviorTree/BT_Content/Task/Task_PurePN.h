#pragma once
/*
 사격 존(WEZ, 152~914m) 전용 정밀 조준 Task.
 기존 Task_Pure/Task_Lead의 리드추적 공식(상대 현재 속도벡터를 직선 외삽)은 상대가
 선회 중일 때 조준각(ATA) 오차가 커진다 -- WEZ 피해 판정은 ATA가 ±1도 이내여야만
 발생할 만큼 매우 좁아서, 이 오차가 명중률에 직접 영향을 준다.
 이 Task는 상대의 "현재 속도"가 아니라 조준선(LOS) 자체의 회전 속도를 관측해서
 그 회전을 상쇄하는 방향으로 조준점을 미리 보정한다(비례항법/PN 유도의 핵심 아이디어를
 VP 산출에 응용) -- 상대가 어떻게 기동하든 LOS 자체의 움직임만 보므로 선회하는
 상대에도 더 강건하게 수렴한다.
 Task_Pure는 Rule_Trinity.xml이 그대로 쓰는 공유 태스크라서 절대 손대지 않고,
 이 Task는 Rule_BFMSelect.xml의 WEZ 분기에서만 사용한다(2026-07-07 신설).
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_PurePN : public SyncActionNode
	{
	private:
		Vector3 _prevLOS;
		bool _hasPrevLOS = false;

	public:

		Task_PurePN(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_PurePN()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
