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

	// ★ 2026-08-06: 에피소드 경계 리셋 추가 (스파링 세트 정화).
	//  [문제] lastThr는 static이라 판이 바뀌어도 직전 판의 스로틀을 그대로 물려받았다.
	//    우리 BT는 v29에서 이걸 고쳤는데 **스파링 상대는 안 고쳐서**, 상대의 초반 거동이
	//    직전 판에 의존했다 = 배치 결과가 시드 순서에 오염된다.
	//    (교착 결과를 "구조적 교착"으로 해석해 왔는데 그 근거 자체가 흔들린다)
	//  [방식] RunningTime은 되감기지 않으므로(생성자에서만 0, 매 틱 증가) 쓸 수 없다.
	//    리셋 시 기체는 km 단위로 순간이동하므로 1틱 2km 이상 이동 = 새 에피소드.
	static Vector3 ocLastPos[2];
	static bool    ocHavePos[2] = { false, false };
	if (ocHavePos[__ti] && MyLocation.distance(ocLastPos[__ti]) > 2000.0)
		lastThr[__ti] = 1.0f;
	ocLastPos[__ti] = MyLocation;
	ocHavePos[__ti] = true;

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
