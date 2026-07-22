#include "Task_LeadPredict.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_LeadPredict::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// 2026-07-21 (v6): v5 SmoothPursuit + 상대 회피 예측 lead (사용자 4번 아이디어).
// [문제] v5 pure pursuit은 상대가 가만있으면 잘 잡지만, 상대가 선회 회피하면
//   계속 지나쳐(오버슈트) 조준 유지 실패 -> 격추 마무리 못 함(랜덤스폰 무승부).
// [해법] 상대 속도로 요격점을 리드하고, 상대 뱅크각(롤)으로 선회방향을 예측해
//   그 안쪽 앞에 VP를 찍는다. 상대가 왼쪽 뱅크면 왼쪽 선회 예측 -> 왼쪽 앞 조준.
//   예측이 틀리면 매 틱 상대 실제 자세로 재계산(폐루프)되어 자동 보정된다.
//   풀스로틀 유지(v5 교훈: 감속은 에너지 손실로 뒤처짐).

NodeStatus Action::Task_LeadPredict::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TgtFwd   = (*BB)->TargetForwardVector;   TgtFwd.normalize();
	Vector3 TgtRight = (*BB)->TargetRightVector;      TgtRight.normalize();

	double dist   = MyLocation.distance(TargetLocation);
	double mySpd  = (*BB)->MySpeed_MS;   if (mySpd < 1.0) mySpd = 1.0;
	double tgtSpd = (*BB)->TargetSpeed_MS;

	// 요격 리드: 상대 진행방향으로 미래위치 예측 (리드시간 = 거리/내속도, 캡 3초)
	// v7 (v8 롤백): 전 거리에서 예측 lead. 사거리 순수조준(v8)은 상대 회피를
	// 못 따라가 -40점 악화로 확인되어 원복. 사거리에서도 예측이 필요.
	double leadTime = dist / mySpd;
	if (leadTime > 3.0) leadTime = 3.0;
	Vector3 predicted = TargetLocation + TgtFwd * (tgtSpd * leadTime);

	double rollDeg = (*BB)->TargetRotation_EDegree.Roll;
	if (std::fabs(rollDeg) > 10.0)
	{
		double s = (rollDeg > 0.0) ? 1.0 : -1.0;
		double bankFactor = std::fabs(rollDeg) / 90.0;
		if (bankFactor > 1.0) bankFactor = 1.0;
		double turnMag = bankFactor * 0.25 * dist;
		if (turnMag > 600.0) turnMag = 600.0;
		if (dist < 600.0) turnMag *= (dist / 600.0);
		predicted = predicted + TgtRight * (s * turnMag);
	}

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	// ================= v17: 궤도 추종 (점 추종 -> 궤도 추종) =================
	// [v16 실패의 교훈] 거리만 제어하면 각도를 잃는다. 500m로 물러나는 사이
	//   상대가 선회로 내 뒤를 잡아 격추(t=110s, bearing 179 = 등을 보임).
	//   v15는 각도는 유지했으나 53~90m로 파고들어 사거리(152m) 미달.
	//   => 거리와 각도를 "동시에" 잡으려면 점이 아니라 궤도를 목표로 해야 한다.
	// [설계] 상대의 실제 기수 변화율로 선회 궤도(중심C, 반경R)를 복원하고,
	//   그 궤도 위에서 상대보다 300m 뒤인 지점(TailSlot)에 미리 VP를 찍는다.
	//   - 상대 뒤쪽 궤도점을 겨누므로 구조적으로 앞지를 수 없다(= lag pursuit).
	//   - 순간 뱅크각이 아니라 0.2초 실적 회전을 쓰므로 롤 리버설에 속지 않는다.
	//   - 슬롯에 도달하면(w->0) 조준점이 요격 lead로 자연스럽게 넘어가 사격각을 만든다.
	//   - 상대가 직진하면 R->무한대라 자동으로 기존 추격으로 퇴화한다.
	static Vector3 fwdHist[2][16];
	static int     histIdx[2] = { 0, 0 };
	static int     histCnt[2] = { 0, 0 };
	const int      HIST = 12;                       // 0.2초(60Hz) 전 기수와 비교

	double dt = (*BB)->DeltaSecond;
	if (dt < 1e-4) dt = 1.0 / 60.0;

	// v19 상태 (선언은 여기, 로직은 궤도추종 블록 뒤)
	static double distHist_v19[2][16];
	static int    distIdx_v19[2] = { 0, 0 };
	static int    distCnt_v19[2] = { 0, 0 };
	static bool   ecoOn_v19[2]   = { false, false };
	static int    ecoArm_v19[2]  = { 0, 0 };

	// v18: 에피소드 경계에서 static 상태 초기화.
	//  DLL 전역 static은 reset을 넘어 살아남아, 배치의 다음 판 첫 12틱이 직전 판의
	//  기수 이력으로 오염되고 스로틀도 직전 판 마지막 값에서 출발했다(배치 신뢰성 문제).
	//  RunningTime이 되감기면 새 에피소드로 판단한다(되감기지 않는 환경에선 무해).
	static double lastRunTime[2] = { -1.0, -1.0 };
	static bool   needThrReset[2] = { false, false };
	double runTime = (*BB)->RunningTime;
	if (runTime < lastRunTime[__ti])
	{
		histCnt[__ti] = 0;
		histIdx[__ti] = 0;
		needThrReset[__ti] = true;
		distCnt_v19[__ti] = 0;      // v19 상태도 에피소드 경계에서 초기화
		ecoOn_v19[__ti] = false;
		ecoArm_v19[__ti] = 0;
	}
	lastRunTime[__ti] = runTime;

	Vector3 fwdOld  = fwdHist[__ti][(histIdx[__ti] + 16 - HIST) % 16];
	bool haveHist   = (histCnt[__ti] >= HIST);
	fwdHist[__ti][histIdx[__ti]] = TgtFwd;
	histIdx[__ti] = (histIdx[__ti] + 1) % 16;
	if (histCnt[__ti] < 100000) histCnt[__ti]++;

	if (haveHist)
	{
		Vector3 axis   = fwdOld.cross(TgtFwd);      // 회전축(우수계: 진행방향 = +)
		double axisLen = axis.length();
		double turnAng = fwdOld.angleBetween(TgtFwd);
		double omega   = turnAng / (HIST * dt);     // 선회 각속도 rad/s

		// 선회 중(3.4deg/s 이상) + 교전거리일 때만 궤도 모드
		if (axisLen > 1e-9 && omega > 0.06 && dist < 2500.0 && tgtSpd > 30.0)
		{
			Vector3 a = axis; a.normalize();
			double R = tgtSpd / omega;              // 선회 반경
			if (R < 200.0)  R = 200.0;
			if (R > 8000.0) R = 8000.0;

			Vector3 toC = a.cross(TgtFwd); toC.normalize();
			Vector3 C   = TargetLocation + toC * R; // 선회 중심
			Vector3 rT  = TargetLocation - C;       // 중심->적 반지름 벡터

			double phi = 300.0 / R;                 // 뒤로 300m 만큼의 호 각도
			if (phi > 0.6)  phi = 0.6;
			if (phi < 0.05) phi = 0.05;

			// 진행 반대(-phi)로 회전 = 궤도상 적의 바로 뒤 자리
			Vector3 axr = a.cross(rT);
			Vector3 tailSlot = C + (rT * std::cos(phi) - axr * std::sin(phi));

			Vector3 myFwd = (*BB)->MyForwardVector; myFwd.normalize();
			Vector3 toSlot = tailSlot - MyLocation;
			if (toSlot.dot(myFwd) > 0.0)            // 슬롯이 내 앞일 때만 유효
			{
				// 슬롯에서 멀면 슬롯으로, 슬롯에 붙으면 요격 lead로 연속 전환
				double w = toSlot.length() / 400.0;
				if (w > 1.0) w = 1.0;
				predicted = tailSlot * w + predicted * (1.0 - w);
			}
		}
	}
	// =======================================================================

	// ================= v19: 도주-추격 교착 해제 (에너지 축적 -> 요격) =================
	// [실측 근거, 6/6 리허설 시드 비교] 승패가 "추격이 어느 거리에서 고착되나"로 갈렸다.
	//   seed2(격추): dead-six 750~850m 고착 = 사거리 안 -> 132초 누적 데미지로 격추
	//   seed0(무득점): 같은 dead-six인데 1400~1900m 고착 + 상대는 상승 도주(3.2->15.8km),
	//     우리도 같이 따라 올라 폐쇄율 0으로 130초 낭비. 동일 기체 풀스로틀 직선 추격은
	//     dV=0이라 추격이 성립한 순간의 거리가 그대로 얼어붙는다(순전히 초기 기하의 운).
	// [설계] 상대가 "상승 도주"로 에너지를 고도에 버리는 동안 우리는 따라 오르지 않고
	//   수평 가속으로 속도 우위(dV)를 만든 뒤 정상 추격으로 복귀해 요격한다.
	//   스로틀은 안 건드리고(감속금지 교훈) VP 수직만 캡한다(v18과 같은 안전한 축).
	//   [미검증 가정] 수평 풀스로틀이 상대의 상승 풀스로틀보다 빨라진다 -> 실측으로 확인할 것.
	{
		bool haveDistH = (distCnt_v19[__ti] >= HIST);
		double distOld = distHist_v19[__ti][(distIdx_v19[__ti] + 16 - HIST) % 16];
		distHist_v19[__ti][distIdx_v19[__ti]] = dist;
		distIdx_v19[__ti] = (distIdx_v19[__ti] + 1) % 16;
		if (distCnt_v19[__ti] < 100000) distCnt_v19[__ti]++;
		double closure = haveDistH ? (distOld - dist) / (HIST * dt) : 999.0;  // +면 접근중 m/s

		Vector3 los = TargetLocation - MyLocation;
		double losLen = los.length(); if (losLen < 1.0) losLen = 1.0;
		los = los / losLen;
		Vector3 myFwdN = (*BB)->MyForwardVector; myFwdN.normalize();
		bool chasing = (myFwdN.dot(los) > 0.90);      // 내 ATA < ~26deg (내가 물고 있음)
		bool fleeing = (TgtFwd.dot(los) > 0.85);      // 상대 기수가 LOS와 정렬 = 도주 중
		bool stalled = haveDistH && (closure < 8.0);  // 접근이 사실상 멈춤
		bool inBand  = (dist > 1000.0 && dist < 3000.0);

		if (!ecoOn_v19[__ti])
		{
			if (chasing && fleeing && stalled && inBand)
			{
				if (++ecoArm_v19[__ti] >= 20) ecoOn_v19[__ti] = true;  // 지속 확인 후 진입(히스테리시스)
			}
			else ecoArm_v19[__ti] = 0;
		}
		else
		{
			double dvNow = mySpd - tgtSpd;
			// 해제: dV 확보 / 사거리 근접 / 상대 반전·이탈 (즉시)
			if (dvNow > 45.0 || dist < 950.0 || !fleeing || !chasing || dist > 3200.0)
			{
				ecoOn_v19[__ti] = false;
				ecoArm_v19[__ti] = 0;
			}
		}

		if (ecoOn_v19[__ti])
		{
			double zCap = MyLocation.Z + 60.0;   // 따라 오르지 않는다 (하강 리드는 그대로 허용)
			if (predicted.Z > zCap) predicted.Z = zCap;
		}
	}
	// =======================================================================

	// ============ v18: 고도 제약 재설계 (조준 불가의 진짜 원인) ============
	// [실측] v17 vs 권정환 200초 로그(ata_split.py / alt_trace.py):
	//   사거리 내 수평오차 5.86deg 인데 수직오차 22.88deg. 조준을 막는 건 상하각이다.
	//   우리 고도가 t=20s 이후 3358~3492m에 고정 = VP Z하한 3500에 붙어 있었음(80% 틱).
	//   상대는 3066m, 최저 2160m까지 자유롭게 내려가 고도차 -274m가 구조적으로 고정.
	//   => 사거리 안에 87초를 있어도 내려다보기만 해 사격각이 안 나옴. 데미지 0의 주범.
	// [근거] 실제 종료 하한은 min_altitude = 300m (config.py). 3500m는 11.7배 과보수적.
	//   ClimbOut(MinAlt 3000)도 하한 위라 200초간 0회 발동하는 죽은 분기였다.
	// [수정] 하한 3500 -> 1500 (종료까지 1200m 여유), 강하 클램프를 상승과 대칭으로.
	//   강하 가속(26.6deg에서 4.4m/s^2)은 v14 dV 폐루프의 스로틀 여유(1.0->0.55,
	//   약 4.5m/s^2)로 상쇄 가능하다고 보고 감수한다. 안전망은 ClimbOut을 1800m로
	//   내려 하한보다 위에서 실제로 작동하게 살린다(Rule_v18.xml).
	double climbSlope = dist * 0.5;
	double diveSlope  = dist * 0.5;         // v18: 0.2 -> 0.5 (하강 조준각 11.3->26.6deg)
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (predicted.Z < minZ) predicted.Z = minZ;
	if (predicted.Z > maxZ) predicted.Z = maxZ;
	if (predicted.Z < 1500.0) predicted.Z = 1500.0;   // v18: 3500 -> 1500
	(*BB)->VP_Cartesian = predicted;

	// v9: 근접 폐쇄율 관리 — "뒤를 잡고도 추월하는" 문제 해결(리플레이서 확인).
	// 원거리는 풀스로틀 유지(v5 교훈: 원거리 감속은 에너지 손실로 뒤처짐).
	// 사거리 근처에서 상대보다 유의미하게 빠를 때만 소폭 감속해 지나치지 않게 한다.
	// (v1 TrackHold의 폐쇄율 로직. 당시엔 뒤를 못 잡아 검증 불가였으나 v7은 WEZ 31초 유지)
	// v11: 연속 + 서서히 변하는 스로틀 (사용자 지적 반영).
	//   v9/v10 실패는 "감속" 자체가 아니라 계단식 급변(1.0<->0.55 요동)이 원인일 수 있음.
	//   v5 교훈(VP 급변=기동 불안정)을 스로틀에도 그대로 적용한다.
	//   (1) 목표 스로틀은 거리/속도차/뱅크각에 연속 비례 (계단 없음, 최대 0.75까지만)
	//   (2) 실제 스로틀은 틱당 0.004씩만 이동 -> 초당 0.24, 급변 불가
	double speedMargin = mySpd - tgtSpd;
	double tgtBank = std::fabs((*BB)->TargetRotation_EDegree.Roll);

	// v14: dV(속도차)를 0으로 수렴시키는 속도매칭 폐루프.
	//  [실측 근거] overshoot.py 틱추적: 뒤를 잡고 ATA 3~5°까지 조준이 완벽한데도
	//    dV=+38m/s가 시종일관 일정해 233m->0m를 8초에 관통, 사거리를 그냥 통과함.
	//    => 문제는 조준이 아니라 폐쇄율. 제어 대상은 "스로틀 값"이 아니라 "dV" 자체다.
	//  [설계] 목표는 감속이 아니라 dV -> 0 (상대와 같은 속도로 뒤에 머물기).
	//    사거리 밖: 풀스로틀로 최대한 빨리 접근(에너지 유지)
	//    사거리 안: dV를 0으로 수렴시켜 그 자리 유지 -> ATA를 조일 시간을 번다
	//    너무 근접: 목표 dV를 음수로 둬 적극적으로 뒤로 빠져 관통·충돌 방지
	// v16(거리 setpoint 500m 캐스케이드) = 실패, 격추당함 -> v14로 원복.
	//  [실패 메커니즘] 거리만 제어하고 각도를 방치. 500m로 물러나는 사이 상대에게
	//    선회 여유를 줘 상대가 내 뒤를 잡음(t=110s, 거리728m, bearing179 = 등을 보임).
	//    거리 문제는 스로틀이 아니라 궤도(위 v17 TailSlot)로 푸는 것이 옳다.
	const double WEZ_MAX = 914.0, WEZ_MIN = 152.0;
	double dvTarget;                       // 목표 속도차(m/s)
	if (dist > WEZ_MAX)      dvTarget = 999.0;   // 사거리 밖: 제한 없이 접근
	else if (dist > 400.0)   dvTarget =   0.0;   // 사거리 바깥쪽: 속도 매칭
	else if (dist > WEZ_MIN) dvTarget = -10.0;   // 사거리 안쪽: 살짝 뒤로
	else                     dvTarget = -25.0;   // 과근접: 적극적으로 뒤로

	double dvErr = speedMargin - dvTarget;  // +면 내가 너무 빠름 -> 줄여야
	float target;
	if (dvTarget > 900.0) {
		target = 1.0f;                      // 사거리 밖은 무조건 풀스로틀
	} else {
		// dV 오차에 비례해 스로틀 조정 (0.55~1.0). 폐루프라 dV가 목표에 수렴한다.
		double u = 1.0 - dvErr * 0.012;     // dvErr +38 -> 0.54 / 0 -> 1.0 / -20 -> 1.0(상한)
		if (u > 1.0) u = 1.0;
		if (u < 0.55) u = 0.55;
		target = (float)u;
	}
	(void)tgtBank;

	static float lastThr[2] = { 1.0f, 1.0f };
	const float STEP = 0.008f;              // 틱당 최대 변화 (60Hz -> 초당 0.48, 약 1초에 걸쳐 부드럽게)
	if (needThrReset[__ti]) { lastThr[__ti] = 1.0f; needThrReset[__ti] = false; }
	float cur = lastThr[__ti];
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LeadPredict dist=" << dist << " dV=" << speedMargin << " thr=" << cur
			<< " eco=" << (ecoOn_v19[__ti] ? 1 : 0) << std::endl;

	return NodeStatus::SUCCESS;
}
