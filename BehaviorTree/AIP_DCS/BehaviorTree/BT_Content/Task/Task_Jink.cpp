#include "Task_Jink.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_Jink::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Jink::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyFwd   = (*BB)->MyForwardVector;   MyFwd.normalize();
	Vector3 MyRight = (*BB)->MyRightVector;     MyRight.normalize();
	double  mySpd   = (*BB)->MySpeed_MS;
	double  dist    = MyLocation.distance(TargetLocation);
	double  runTime = (*BB)->RunningTime;

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	// ── 결정론적이면서 불규칙한 방향 전환 스케줄 ──
	//    난수를 쓰면 재현이 깨지므로 고정 시퀀스를 순환시킨다.
	static const double SEQ[8] = { 2.1, 1.3, 3.4, 1.7, 2.8, 1.1, 3.7, 1.9 };
	static double nextFlip[2] = { 0.0, 0.0 };
	static int    seqIdx[2]   = { 0, 0 };
	static double sign[2]     = { 1.0, 1.0 };
	static double lastRun[2]  = { -1.0, -1.0 };

	if (runTime < lastRun[__ti])           // 에피소드 경계 초기화
	{
		nextFlip[__ti] = 0.0; seqIdx[__ti] = 0; sign[__ti] = 1.0;
	}
	lastRun[__ti] = runTime;

	if (runTime >= nextFlip[__ti])
	{
		sign[__ti] = -sign[__ti];
		nextFlip[__ti] = runTime + SEQ[seqIdx[__ti] % 8];
		seqIdx[__ti]++;
	}

	// ── 저킹 방향: 좌우 급전환 + 수직 성분(조준면을 3D로) ──
	//    수직 성분도 좌우와 함께 뒤집어 나선이 아니라 "지그재그"가 되게 한다.
	Vector3 WorldUp(0.0, 0.0, 1.0);
	Vector3 dir = MyFwd * 0.35 + MyRight * (sign[__ti] * 1.0) + WorldUp * (sign[__ti] * 0.30);

	// 너무 멀어지면 상대 쪽으로 약간 끌어당겨 교전을 유지한다(계측 기회 확보).
	if (dist > 2500.0)
	{
		Vector3 los = TargetLocation - MyLocation;
		double l = los.length(); if (l < 1.0) l = 1.0;
		dir = dir + (los / l) * 0.9;
	}
	dir.normalize();

	Vector3 vp = MyLocation + dir * 2000.0;
	if (vp.Z < 2200.0) vp.Z = 2200.0;      // 지면 충돌 방지
	(*BB)->VP_Cartesian = vp;

	// ── 코너속도 유지(급전환 선회율 최대화) ──
	const double CORNER = 255.0;
	static float lastThr[2] = { 1.0f, 1.0f };
	double err = mySpd - CORNER;
	double u = 0.85 - err * 0.005;
	if (u > 1.0) u = 1.0;
	if (u < 0.25) u = 0.25;

	float target = (float)u;
	float cur = lastThr[__ti];
	const float STEP = 0.030f;
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	if (++__dbg[__ti] % 120 == 0)
		std::cerr << "[JINK] sign=" << sign[__ti] << " next=" << nextFlip[__ti]
		          << " dist=" << dist << " spd=" << mySpd << std::endl;

	return NodeStatus::SUCCESS;
}
