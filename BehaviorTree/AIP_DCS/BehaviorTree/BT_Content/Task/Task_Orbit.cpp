#include "Task_Orbit.h"
#include <iostream>

PortsList Action::Task_Orbit::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 신설: 스파링/조준측정용 표적. 일정 뱅크로 예측 가능한 큰 원을 돈다.
// 전방 멀리 + 오른쪽 약간에 VP를 두면 완만한 정상선회가 되고, 매 틱 기체가
// 돌면 VP도 같이 돌아 원을 유지한다(도달 불가능한 상대 좌표라 영구 선회).
// 조종은 안 하고 예측 가능하게만 날아, 우리 기체가 뒤를 잡고 ATA를 몇 도까지
// 조일 수 있는지(= Controller_CY 조준 정밀도의 상한)를 측정하는 데 쓴다.
// 이후 Phase 2에서 공격형/방어형 등 다른 성격의 스파링 상대로 확장한다.

NodeStatus Action::Task_Orbit::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
	Vector3 MyForward  = (*BB)->MyForwardVector;
	Vector3 MyRight    = (*BB)->MyRightVector;
	MyForward.normalize();
	MyRight.normalize();

	// 검증용 표적: 완만한 우선회 + 저속(0.6) -> 우리 기체가 안쪽 파고들어 뒤를
	// 확실히 잡을 수 있게 함(사거리/조준 로직 검증용). 실전 상대는 Phase2에서 다양화.
	Vector3 VP = MyLocation + MyForward * 3000.0 + MyRight * 500.0;

	// 고도 유지(추락 방지): 4000m 밑으로는 안 내려가게, 급강하 클램프
	if (VP.Z < MyLocation.Z - 200.0) VP.Z = MyLocation.Z - 200.0;
	if (VP.Z < 4000.0) VP.Z = 4000.0;
	(*BB)->VP_Cartesian = VP;

	// 저속(뒤를 확실히 내주도록)
	(*BB)->Throttle = 0.6f;

	static int __dbg = 0;
	if (++__dbg % 60 == 0)
		std::cerr << "[ORBIT] Z=" << MyLocation.Z << std::endl;

	return NodeStatus::SUCCESS;
}
