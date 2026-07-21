#include "Task_TrackHold.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_TrackHold::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-20 신설 (v1): WEZ(<=914m) 진입 후 "뒤 잡은 상태 유지" 전용 태스크.
// 기존 Task_Pure를 같은 슬롯에서 대체한다. 조준(VP)은 Task_Pure와 동일하게 적의
// 현재 위치를 직접 겨눠 ATA를 조이되(자동 데미지 조건: 152~914m + ATA<=2도),
// 스로틀을 "거리 밴드 + 속도차" 폐루프로 제어해 오버슈트로 튕겨나가는 것을 막고
// WEZ 체류시간을 늘리는 것이 이번 버전의 가설.
// - 근거1: v0 거울전 노드분포 GetTail 338 vs Pure 6 -> 사거리 체류 실패가 병목.
// - 근거2: 07-03 "거리 비례 감속"은 실패, 07-09 "속도차 기반 근접 감속"은 성공
//   -> 거리 밴드는 상태 구분에만 쓰고, 감속 여부는 항상 속도차로 판단한다.
//   (상대가 최대속도면 speedMargin<=0 -> 감속 자체가 안 걸려서 밀리지 않는다)
// - 근거3: 원거리(Lead) 감속은 악화 확인(07-09) -> 이 태스크는 914m 이내 전용.

NodeStatus Action::Task_TrackHold::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;

	double Distance = MyLocation.distance(TargetLocation);

	// (1) 조준: 적 현재 위치 (Task_Pure와 동일 정책 + 동일 강하각 클램프)
	Vector3 VP = TargetLocation;

	double climbSlope = Distance * 0.5;
	double diveSlope  = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;
	(*BB)->VP_Cartesian = VP;

	// (2) 폐쇄율 폐루프: 거리 밴드로 상태를 나누고, 감속 여부는 속도차로 판단
	double speedMargin = (*BB)->MySpeed_MS - (double)(*BB)->TargetSpeed_MS;
	float throttle = 1.0f;

	if (Distance > 750.0)
	{
		// 벌어지는 중 -> 즉시 풀스로틀 복귀 (상대가 최대속도여도 안 밀리는 이유)
		throttle = 1.0f;
	}
	else if (Distance < 450.0)
	{
		// WEZ 하한(152m) 쪽으로 파고드는 중 -> 접근 자체를 멈춘다.
		// 이미 상대보다 느리면 과감속으로 뒤처지지 않게 하한을 둔다.
		throttle = (speedMargin > 0.0) ? 0.5f : 0.85f;
	}
	else
	{
		// 유지 밴드(450~750m): 빠르게 접근할 때만 늦춘다
		if (speedMargin > 15.0)       throttle = 0.7f;
		else if (speedMargin < -15.0) throttle = 1.0f;
		else                          throttle = 0.9f;
	}
	(*BB)->Throttle = throttle;

	// 진단 로그(30틱마다): 대결 후 리플레이/그래프 분석용. ATA는
	// DECO_TailThreatCheck와 동일 공식으로 직접 계산(BB->MyAngleOff_Degree는
	// 이름과 달리 heading crossing angle이라 쓰면 안 됨 -- Task_Evade 주석 참고).
	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0)
	{
		Vector3 MyForward = (*BB)->MyForwardVector;
		Vector3 MyToTarget = TargetLocation - MyLocation;
		float ata = (Distance > 1e-3)
			? (float)(MyToTarget.angleBetween(MyForward) * 57.2958)
			: 0.0f;
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] TrackHold dist=" << Distance
			<< " ata=" << ata
			<< " spdMargin=" << speedMargin
			<< " thr=" << throttle << std::endl;
	}

	return NodeStatus::SUCCESS;
}
