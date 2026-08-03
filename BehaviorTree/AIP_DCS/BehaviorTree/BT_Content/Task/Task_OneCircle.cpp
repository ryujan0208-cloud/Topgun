#include "Task_OneCircle.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_OneCircle::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_OneCircle::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	double  mySpd          = (*BB)->MySpeed_MS;
	double  dist           = MyLocation.distance(TargetLocation);

	// (1) 조준점 = 상대 "현재" 위치 (리드 없음).
	//     리드를 쓰면 상대 선회 바깥으로 밀려 투서클이 되기 쉽다. 원써클은 순수 추적이 기본.
	// (2) 고도를 내 고도로 맞춘다 -> 수평면 선회 강제 = 순수 반경 싸움.
	//     (수직 성분이 섞이면 원써클이 깨지고 3차원 추격전이 된다)
	Vector3 vp = TargetLocation;
	vp.Z = MyLocation.Z;

	// 아주 가까우면 조준점이 뒤로 넘어가 제어가 튀므로, 최소 전방 거리를 확보한다.
	Vector3 toVp = vp - MyLocation;
	double toVpLen = toVp.length();
	if (toVpLen < 300.0)
	{
		Vector3 myFwd = (*BB)->MyForwardVector; myFwd.normalize();
		vp = MyLocation + myFwd * 300.0;
		vp.Z = MyLocation.Z;
	}
	if (vp.Z < 2000.0) vp.Z = 2000.0;     // 지면 충돌 방지(스파링 상대도 살아있어야 의미가 있다)
	(*BB)->VP_Cartesian = vp;

	// (3) 코너속도 고정: 선회율이 최대가 되는 속도대(실측 210~290m/s)에 머문다.
	//     너무 빠르면 선회가 안 되고, 너무 느리면 에너지가 죽는다.
	const double CORNER = 255.0;
	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;
	static float lastThr[2] = { 1.0f, 1.0f };

	double err = mySpd - CORNER;                 // +면 과속
	double u = 0.85 - err * 0.005;               // 255->0.85 / 355->0.35 / 155->1.0
	if (u > 1.0) u = 1.0;
	if (u < 0.20) u = 0.20;

	float target = (float)u;
	float cur = lastThr[__ti];
	const float STEP = 0.030f;
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	if (++__dbg[__ti] % 120 == 0)
		std::cerr << "[ONECIRCLE] dist=" << dist << " spd=" << mySpd << " thr=" << cur << std::endl;

	return NodeStatus::SUCCESS;
}
