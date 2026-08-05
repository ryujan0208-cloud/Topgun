#pragma once
/*
 v34: 급감속 스냅샷 (Snap Decel) — 뒤를 잡힌 채 교착된 구간을 깬다.

 [왜 만들었나 — 세 갈래가 같은 곳을 가리켰다]
  1) 실측한 구조적 공백: 상대가 우리 6시 1350m에 붙어 70초간 거리·고도·각이 고정된
     완전 교착이 관측됐다. 그런데 Task_Evade는 `거리<1100m`에서만 발동하므로
     그 구간엔 **아무 분기도 걸리지 않았다.**
  2) 오프라인 기동 탐색(tools_diag/vp_probe.py, 대회 규칙 8구간 x 8후보):
     우리 ATA >= 136도인 구간 3개에서 '감속+당김'이 3/3 1위,
     순이득 +0.646 ~ +0.925 (다른 후보 최고 +0.388). ATA < 110도인 5구간에서는 0/5.
  3) 사용자가 제시했던 기동 사양의 미구현 항목: "급감속 스냅샷 사격 -> 재가속".

 [원리 - 상대 불문]
  뒤를 잡힌 상태에서 감속하면 추적자는 폐쇄율을 못 죽여 **앞질러 나간다(오버슈트 강요)**.
  동시에 당기면 기수가 돌아와 역전 기하를 만든다. 이건 BFM 정석이지 특정 상대 대응이 아니다.

 [주의]
  - 지속 발동하면 에너지를 전부 잃는다. 탐색에서 검증한 건 **5초 창**이므로 지속시간을 제한하고
    쿨다운을 둔다(측정한 조건을 그대로 재현한다).
  - BT는 VP와 Throttle만 설정한다. 탐색의 (pitch=-1.0, throttle=0.20)을
    "기수 기준 위쪽 VP + 저스로틀"로 옮긴다.
  - VP는 오프보어사이트 클램프(75도)에 걸리지 않도록 70도로 둔다.
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_SnapDecel : public SyncActionNode
	{
	public:
		Task_SnapDecel(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_SnapDecel()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
