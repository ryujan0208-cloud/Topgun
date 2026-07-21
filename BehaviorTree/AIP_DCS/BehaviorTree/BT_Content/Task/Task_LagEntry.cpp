#include "Task_LagEntry.h"
#include <iostream>

PortsList Action::Task_LagEntry::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 (v3 재설계 핵심): 사거리 진입 전용 노드. Task_Pure의 pure pursuit
// 오버슈트를 lag pursuit로 해결한다.
// [진단 근거] 거리대별 최소 ATA: 원거리(2.5~4km) 0도까지 잡히는데 사거리(<914m)
//   진입 시 15~32도로 붕괴. BFM 정석대로 pure pursuit이 오버슈트를 만든 것.
// [해법] 조준점을 적 진행방향 반대(적 뒤)로 offset:
//   - 멀면(1500m) 크게 lag -> 기수가 적 뒤를 향해 곡선 접근, 오버슈트 방지
//   - 가까우면(<500m) offset 0으로 수렴 -> pure 조준(사격 ATA<2도 노림)
//   + 폐쇄율: 사거리 근처에서 빠르게 접근 중이면 감속해 체류시간 확보.

NodeStatus Action::Task_LagEntry::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TargetForward  = (*BB)->TargetForwardVector;
	TargetForward.normalize();

	double dist = MyLocation.distance(TargetLocation);

	// lag offset: dist 500~1500 구간에서 최대 500m -> 0 선형 (가까울수록 pure)
	double lag = 0.0;
	if (dist > 500.0)
	{
		lag = (dist - 500.0) / 1000.0;
		if (lag > 1.0) lag = 1.0;
		lag *= 500.0;
	}
	Vector3 VP = TargetLocation - TargetForward * lag;

	// 강하각 클램프 (기존 정책 동일)
	double climbSlope = dist * 0.5;
	double diveSlope  = dist * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;
	(*BB)->VP_Cartesian = VP;

	// 폐쇄율: 사거리(<900m) 근처에서 빠르게 접근 중이면 감속해 체류
	double speedMargin = (*BB)->MySpeed_MS - (double)(*BB)->TargetSpeed_MS;
	float throttle = 1.0f;
	if (dist < 900.0 && speedMargin > 10.0) throttle = 0.7f;
	(*BB)->Throttle = throttle;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0)
	{
		Vector3 MyForward = (*BB)->MyForwardVector;
		Vector3 MtT = TargetLocation - MyLocation;
		float ata = (dist > 1e-3) ? (float)(MtT.angleBetween(MyForward) * 57.2958) : 0.0f;
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LagEntry dist=" << dist << " lag=" << lag
			<< " ata=" << ata << " thr=" << throttle << std::endl;
	}

	return NodeStatus::SUCCESS;
}
