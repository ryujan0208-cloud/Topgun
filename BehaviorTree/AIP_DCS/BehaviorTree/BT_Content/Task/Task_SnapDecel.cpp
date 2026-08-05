#include "Task_SnapDecel.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_SnapDecel::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<double>("AtaMin"),      // 발동 최소 ATA(도). 실측 근거 136도 -> 기본 130
			InputPort<double>("DistMin"),     // Evade가 맡는 구간(1100m) 위부터
			InputPort<double>("DistMax"),     // 탐색 근거 범위 상한(2366m) -> 기본 2500
			InputPort<double>("HoldSec")      // 유지 시간. 탐색에서 검증한 창 = 5초
	};
}

NodeStatus Action::Task_SnapDecel::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	double ATA_MIN  = 130.0;
	double DIST_MIN = 1100.0;
	double DIST_MAX = 2500.0;
	double HOLD_SEC = 5.0;
	{
		Optional<double> v;
		v = getInput<double>("AtaMin");  if (v) ATA_MIN  = v.value();
		v = getInput<double>("DistMin"); if (v) DIST_MIN = v.value();
		v = getInput<double>("DistMax"); if (v) DIST_MAX = v.value();
		v = getInput<double>("HoldSec"); if (v) HOLD_SEC = v.value();
	}
	const double COOL_SEC = 8.0;      // 재발동 쿨다운. 연속 발동 시 에너지를 전부 잃는다.

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyFwd = (*BB)->MyForwardVector; MyFwd.normalize();
	Vector3 MyUp  = (*BB)->MyUpVector;      MyUp.normalize();

	double dist = MyLocation.distance(TargetLocation);

	Vector3 los = TargetLocation - MyLocation;
	double losLen = los.length(); if (losLen < 1.0) losLen = 1.0;
	los = los / losLen;
	double ataDeg = std::acos(std::max(-1.0, std::min(1.0, MyFwd.dot(los)))) * 57.2957795;

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;
	double dt = (*BB)->DeltaSecond;
	if (dt < 1e-4) dt = 1.0 / 60.0;

	// 에피소드 경계는 위치 점프로 판정한다(RunningTime은 되감기지 않는다 — v29에서 규명).
	static Vector3 sdLastPos[2];
	static bool    sdHavePos[2] = { false, false };
	static double  sdActive[2]  = { 0.0, 0.0 };   // 남은 유지 시간
	static double  sdCool[2]    = { 0.0, 0.0 };   // 남은 쿨다운
	if (sdHavePos[__ti] && MyLocation.distance(sdLastPos[__ti]) > 2000.0)
	{
		sdActive[__ti] = 0.0;
		sdCool[__ti]   = 0.0;
	}
	sdLastPos[__ti] = MyLocation;
	sdHavePos[__ti] = true;

	if (sdCool[__ti] > 0.0) sdCool[__ti] -= dt;

	// 조건: 뒤를 잡힌 기하(ATA 큼) + Evade가 안 맡는 거리대
	bool cond = (ataDeg >= ATA_MIN) && (dist >= DIST_MIN) && (dist <= DIST_MAX);

	if (sdActive[__ti] <= 0.0)
	{
		if (!cond || sdCool[__ti] > 0.0)
			return NodeStatus::FAILURE;          // 아래 분기(LeadPredict)로 넘긴다
		sdActive[__ti] = HOLD_SEC;               // 새로 발동
	}

	sdActive[__ti] -= dt;
	if (sdActive[__ti] <= 0.0) sdCool[__ti] = COOL_SEC;

	// ── 기동 생성 ──
	// 탐색에서 검증한 입력은 (roll=0, pitch=-1.0, throttle=0.20) = "뱅크 유지한 채 최대 당김".
	// BT는 VP만 설정하므로 **기수 기준 위쪽**에 VP를 찍어 같은 당김을 만든다.
	// 오프보어사이트 클램프가 75도이므로 70도로 둬서 잘리지 않게 한다(잘리면 방향이 바뀐다).
	const double PULL_DEG = 70.0;
	double c = std::cos(PULL_DEG * 0.0174532925);
	double s = std::sin(PULL_DEG * 0.0174532925);
	Vector3 dir = MyFwd * c + MyUp * s;
	dir.normalize();

	Vector3 vp = MyLocation + dir * 3000.0;
	if (vp.Z < 1500.0) vp.Z = 1500.0;            // 고도 안전망(다른 노드와 동일 기준)
	(*BB)->VP_Cartesian = vp;

	// 급감속. 탐색값 0.20을 그대로 쓴다.
	(*BB)->Throttle = 0.20f;

	static int __dbg[2] = { 0, 0 };
	if (++__dbg[__ti] % 30 == 0)
		std::cerr << "[SNAPDECEL] team=" << (*BB)->Team << " ata=" << ataDeg
		          << " dist=" << dist << " left=" << sdActive[__ti] << std::endl;

	return NodeStatus::SUCCESS;
}
