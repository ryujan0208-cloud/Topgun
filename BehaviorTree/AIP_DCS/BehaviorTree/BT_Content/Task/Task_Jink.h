#pragma once
/*
 스파링 전용 상대기체 노드: 불규칙 저킹(Jink).

 목적 - 우리 궤도추종(v17)이 "유령 원"을 쫓는지 반복 측정하기 위한 계측용 상대.
   우리 기체는 상대의 0.2초 실적 회전으로 선회 궤도(중심/반경)를 복원해 그 뒤에 VP를 찍는다.
   상대가 일관되게 돌면 이 추정이 맞지만, **불규칙하게 방향을 뒤집으면 매번 엉뚱한 원**을
   복원하게 된다. 그 취약성을 재현 가능하게 노출시킨다.

 설계 - 결정론적이면서 불규칙하게 선회 방향을 뒤집는다.
   간격 시퀀스를 고정 배열로 두어 매 판 동일하게 재현되므로 배치/회귀 검증에 쓸 수 있다
   (난수를 쓰면 재현이 깨져 우리 검증 체계와 맞지 않는다).
   선회는 코너속도에서 최대 선회율로 하고, 수직 성분을 섞어 조준면을 3D로 만든다.

 주의 - 우리 제출 기체 Rule에서는 사용하지 않는다. Rule_jink.xml 전용(AIP_jink.dll).
*/
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Jink : public SyncActionNode
	{
	public:
		Task_Jink(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Jink()
		{
		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
