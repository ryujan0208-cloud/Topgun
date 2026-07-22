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

	// 강하각 클램프 (기존 정책)
	double climbSlope = dist * 0.5;
	double diveSlope  = dist * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (predicted.Z < minZ) predicted.Z = minZ;
	if (predicted.Z > maxZ) predicted.Z = maxZ;
	if (predicted.Z < 3500.0) predicted.Z = 3500.0;
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
	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	double speedMargin = mySpd - tgtSpd;
	double tgtBank = std::fabs((*BB)->TargetRotation_EDegree.Roll);

	// v13: 적응형 스로틀 — 상대 회피 강도에 따라 감속 정책을 연속 전환.
	//  [근거] 감속의 유불리가 상대에 따라 정반대:
	//    동급(회피 잘함 v0): 풀스로틀 v7 +28.30 > 감속 v11 -3.87
	//    약한상대(dummy)   : 감속 v11 +853.28 > 풀스로틀 v7 +499.28
	//  [감지] 상대 뱅크각 변화량의 지수이동평균. dummy는 완만·일정(작음),
	//         v0는 급기동으로 뱅크가 요동(큼).
	//  [전환] 임계값 대신 연속: 회피가 강할수록 감속량을 0으로 수렴시킨다.
	static double lastTgtRoll[2] = { 0.0, 0.0 }, evas[2] = { 0.0, 0.0 };
	static bool   evasInit[2] = { false, false };
	double tgtRollNow = (*BB)->TargetRotation_EDegree.Roll;
	if (!evasInit[__ti]) { lastTgtRoll[__ti] = tgtRollNow; evasInit[__ti] = true; }
	double rollDelta = std::fabs(tgtRollNow - lastTgtRoll[__ti]);
	if (rollDelta > 180.0) rollDelta = 360.0 - rollDelta;      // wrap 보정
	lastTgtRoll[__ti] = tgtRollNow;
	evas[__ti] = evas[__ti] * 0.998 + rollDelta * 0.002;       // 느린 EMA(약 8초)

	double evasNorm = evas[__ti] / 0.5;                        // 0.5deg/tick이면 완전 회피형
	if (evasNorm > 1.0) evasNorm = 1.0;

	double closeFactor = (dist < 2500.0) ? (2500.0 - dist) / 2500.0 : 0.0;
	double fastFactor = speedMargin / 60.0;
	if (fastFactor < 0.0) fastFactor = 0.0; if (fastFactor > 1.0) fastFactor = 1.0;
	double bankFactor = tgtBank / 90.0;
	if (bankFactor > 1.0) bankFactor = 1.0;

	// 회피 강한 상대일수록 (1-evasNorm)이 0에 가까워져 감속이 사라진다 = v7 거동
	double reduce = 0.25 * closeFactor * (0.6 * fastFactor + 0.4 * bankFactor) * (1.0 - evasNorm);
	float target = (float)(1.0 - reduce);

	static float lastThr[2] = { 1.0f, 1.0f };
	const float STEP = 0.004f;              // 틱당 최대 변화 (60Hz -> 초당 0.24)
	float cur = lastThr[__ti];
	if (target > cur) { cur += STEP; if (cur > target) cur = target; }
	else              { cur -= STEP; if (cur < target) cur = target; }
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LeadPredict dist=" << dist << std::endl;

	return NodeStatus::SUCCESS;
}
