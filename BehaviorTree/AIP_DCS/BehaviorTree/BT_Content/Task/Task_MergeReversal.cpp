#include "Task_MergeReversal.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_MergeReversal::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-20 신설 (v2): 정면 엇갈림(merge) 직후 상대가 뒤로 넘어가는 순간, 큰 원
// (GetTail)으로 늘어지지 말고 급선회로 상대 쪽으로 되돌아 꼬리를 빨리 무는 반전 기동.
// VP를 상대 위치에 찍으면 LOS>90 -> Step()의 boresight 75도 클램프가 최대선회로
// 변환해주고, 감속(0.65)으로 선회반경을 줄여 반전을 앞당긴다(사용자 제안).
// 발동 게이트(자체): ATA 100~150 + 중거리(300~2500m).
//   - ATA>150 (거의 정확히 뒤)   : BreakAndReverse(900m내)/Evade(3000m내)가 방어로 처리 -> 상한 150
//   - ATA<100 (상대가 전방권)     : GetTail/Lead가 추격 -> 하한 100
//   조건 밖이면 FAILURE 반환해 ReactiveFallback이 다음 노드로 넘어가게 한다.
// 가설: v1 검증 실패의 원인 "동급전에서 뒤를 못 잡음"을 이 선제 반전으로 뚫어,
//   뒤를 잡으면 GetTail -> TrackHold(v1)로 자연 인계되어 사거리 안착까지 이어진다.

NodeStatus Action::Task_MergeReversal::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyForward      = (*BB)->MyForwardVector;

	double Distance = MyLocation.distance(TargetLocation);

	Vector3 MyToTarget = TargetLocation - MyLocation;
	float ata = (Distance > 1e-3)
		? (float)(MyToTarget.angleBetween(MyForward) * 57.2958)
		: 0.0f;

	// 자체 게이트: 엇갈림 반전 구간만
	if (Distance > 2500.0 || Distance < 80.0)  return NodeStatus::FAILURE;
	if (ata < 100.0f || ata > 150.0f)          return NodeStatus::FAILURE;

	// 상대 쪽으로 급선회 (LOS>90 -> boresight 클램프가 최대선회로 변환) + 강하각 클램프
	Vector3 VP = TargetLocation;
	double climbSlope = Distance * 0.5;
	double diveSlope  = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;
	(*BB)->VP_Cartesian = VP;

	// 감속으로 선회반경 축소 (사용자 제안: "vp 반대쪽 + 속도 줄여서")
	(*BB)->Throttle = 0.65f;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] MergeReversal dist=" << Distance << " ata=" << ata << std::endl;

	return NodeStatus::SUCCESS;
}
