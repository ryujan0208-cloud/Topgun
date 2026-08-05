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
	const int      HIST = 12;

	// ★ 2026-08-06: 에피소드 경계 판정을 **위치 점프**로 교체 (스파링 세트 정화).
	//  [버그] 기존 `if (runTime < lastRun)`은 **한 번도 발동한 적이 없다.**
	//    RunningTime은 BlackBoard 생성자에서만 0이고 매 틱 증가하며,
	//    BTActionProvider.reset()이 BT를 재생성하지 않으므로 되감기는 일이 없다.
	//    우리 BT에서 v29로 고친 바로 그 버그인데 **스파링 상대는 안 고쳤다.**
	//    -> sync는 판이 바뀌어도 직전 판의 선회 이력과 스로틀을 물려받고 있었다.
	//       "sync는 구조적으로 교착"이라는 해석의 근거 자체가 오염돼 있었다.
	//  [해법] 리셋 시 기체는 km 단위로 순간이동한다(60Hz에서 2km = 120km/s = 정상 비행 불가).
	static Vector3 smLastPos[2];
	static bool    smHavePos[2] = { false, false };
	bool smEpisodeReset = false;
	if (smHavePos[__ti] && MyLocation.distance(smLastPos[__ti]) > 2000.0)
	{
		histCnt[__ti] = 0;
		histIdx[__ti] = 0;
		smEpisodeReset = true;          // 아래 스로틀도 함께 초기화
	}
	smLastPos[__ti] = MyLocation;
	smHavePos[__ti] = true;

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
	if (smEpisodeReset) lastThr[__ti] = 1.0f;  // 2026-08-06: 판 경계에서 스로틀도 초기화
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
