#include "Task_SyncMirror.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_SyncMirror::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_SyncMirror::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TgtFwd = (*BB)->TargetForwardVector; TgtFwd.normalize();
	Vector3 MyFwd  = (*BB)->MyForwardVector;     MyFwd.normalize();
	double  mySpd  = (*BB)->MySpeed_MS;
	double  tgtSpd = (*BB)->TargetSpeed_MS;
	double  dist   = MyLocation.distance(TargetLocation);

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	double dt = (*BB)->DeltaSecond;
	if (dt < 1e-4) dt = 1.0 / 60.0;

	// ── 상대(우리 기체)의 실적 회전 측정: 0.2초 전 기수와 비교 ──
	static Vector3 fwdHist[2][16];
	static int     histIdx[2] = { 0, 0 };
	static int     histCnt[2] = { 0, 0 };
	static double  lastRun[2] = { -1.0, -1.0 };
	const int      HIST = 12;

	double runTime = (*BB)->RunningTime;
	if (runTime < lastRun[__ti]) { histCnt[__ti] = 0; histIdx[__ti] = 0; }  // 에피소드 경계
	lastRun[__ti] = runTime;

	Vector3 fwdOld = fwdHist[__ti][(histIdx[__ti] + 16 - HIST) % 16];
	bool haveHist  = (histCnt[__ti] >= HIST);
	fwdHist[__ti][histIdx[__ti]] = TgtFwd;
	histIdx[__ti] = (histIdx[__ti] + 1) % 16;
	if (histCnt[__ti] < 100000) histCnt[__ti]++;

	// ── 같은 회전축·같은 각속도로 내 기수를 돌린 방향에 VP를 찍는다 ──
	//    (로드리게스 회전공식으로 내 전방벡터를 상대와 동일한 회전량만큼 돌린다)
	Vector3 aimDir = MyFwd;
	if (haveHist)
	{
		Vector3 axis = fwdOld.cross(TgtFwd);
		double axisLen = axis.length();
		double turnAng = fwdOld.angleBetween(TgtFwd);          // 0.2초간 회전량(rad)
		double omega = turnAng / (HIST * dt);                  // rad/s

		if (axisLen > 1e-9 && omega > 0.02)
		{
			Vector3 k = axis / axisLen;                        // 정규화된 회전축
			double theta = omega * 1.5;                        // 1.5초 앞을 향해 같은 비율로 선회
			if (theta > 1.2) theta = 1.2;                      // 과회전 방지

			double ct = std::cos(theta), st = std::sin(theta);
			Vector3 kxv = k.cross(MyFwd);
			double kdv = k.dot(MyFwd);
			aimDir = MyFwd * ct + kxv * st + k * (kdv * (1.0 - ct));
			aimDir.normalize();
		}
	}

	Vector3 vp = MyLocation + aimDir * 2000.0;

	// 고도도 상대에 맞춘다(고도 우위를 주지 않는다). 단 급격하지 않게.
	double altErr = TargetLocation.Z - MyLocation.Z;
	if (altErr >  400.0) altErr =  400.0;
	if (altErr < -400.0) altErr = -400.0;
	vp.Z += altErr;
	if (vp.Z < 2000.0) vp.Z = 2000.0;         // 지면 충돌 방지
	(*BB)->VP_Cartesian = vp;

	// ── 속도도 상대와 일치시킨다(에너지 우위를 주지 않는다) ──
	static float lastThr[2] = { 1.0f, 1.0f };
	double dv = mySpd - tgtSpd;                // +면 내가 빠름
	double u = 0.75 - dv * 0.010;              // 같은 속도면 0.75 유지, 빠르면 줄임
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
		std::cerr << "[SYNC] dist=" << dist << " dV=" << dv << " thr=" << cur << std::endl;

	return NodeStatus::SUCCESS;
}
