#include "Task_SyncCircle.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_SyncCircle::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<double>("Shrink")
	};
}

NodeStatus Action::Task_SyncCircle::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	double shrink = 0.0;
	Optional<double> sIn = getInput<double>("Shrink");
	if (sIn) shrink = sIn.value();
	if (shrink < 0.0) shrink = 0.0;
	if (shrink > 0.8) shrink = 0.8;

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyFwd = (*BB)->MyForwardVector; MyFwd.normalize();
	double  mySpd  = (*BB)->MySpeed_MS;
	double  tgtSpd = (*BB)->TargetSpeed_MS;
	double  dist   = MyLocation.distance(TargetLocation);

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	// ── 원 중심 C = 두 기체의 중점(수평면). 나는 그 원 위를 돈다 ──
	Vector3 C = (MyLocation + TargetLocation) * 0.5;
	C.Z = MyLocation.Z;                       // 수평 원써클

	Vector3 r = MyLocation - C;
	r.Z = 0.0;
	double R = r.length();
	if (R < 60.0)                              // 너무 붙으면 원이 정의되지 않는다
	{
		// 접선을 못 구하므로 그냥 현재 기수를 유지하며 살짝 벌린다
		Vector3 vpN = MyLocation + MyFwd * 1200.0;
		if (vpN.Z < 2000.0) vpN.Z = 2000.0;
		(*BB)->VP_Cartesian = vpN;
		(*BB)->Throttle = 0.8f;
		return NodeStatus::SUCCESS;
	}
	Vector3 rn = r / R;

	// ── 접선 방향(수평). 현재 기수와 같은 쪽을 골라 방향이 튀지 않게 한다 ──
	Vector3 up(0.0, 0.0, 1.0);
	Vector3 tang = up.cross(rn);
	tang.normalize();
	if (tang.dot(MyFwd) < 0.0) tang = tang * -1.0;

	// ── Shrink: 중심 방향 성분을 섞어 나선형으로 반경을 줄인다 ──
	Vector3 inward = rn * -1.0;
	Vector3 dir = tang + inward * shrink;
	dir.normalize();

	Vector3 vp = MyLocation + dir * 1500.0;

	// ── 고도 싱크: 상대 고도를 따라가되 급격하지 않게 ──
	double altErr = TargetLocation.Z - MyLocation.Z;
	if (altErr >  350.0) altErr =  350.0;
	if (altErr < -350.0) altErr = -350.0;
	vp.Z = MyLocation.Z + altErr;
	if (vp.Z < 2000.0) vp.Z = 2000.0;          // 지면 충돌 방지
	(*BB)->VP_Cartesian = vp;

	// ── 속도 싱크: 상대와 같은 속도를 유지해 에너지 우위를 주지 않는다.
	//    단 선회를 위해 코너속도 상한을 둔다(과속이면 선회가 안 돼 원이 커진다).
	const double CORNER_CAP = 300.0;
	double refSpd = (tgtSpd < CORNER_CAP) ? tgtSpd : CORNER_CAP;
	static float lastThr[2] = { 1.0f, 1.0f };
	double err = mySpd - refSpd;                // +면 내가 빠름
	double u = 0.75 - err * 0.008;
	if (u > 1.0) u = 1.0;
	if (u < 0.25) u = 0.25;

	float target = (float)u;
	float cur = lastThr[__ti];
	const float STEP = 0.025f;
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	if (++__dbg[__ti] % 120 == 0)
		std::cerr << "[SYNCCIRCLE] R=" << R << " dist=" << dist
		          << " shrink=" << shrink << " thr=" << cur << std::endl;

	return NodeStatus::SUCCESS;
}
