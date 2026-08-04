#include "Task_Evade.h"
#include <iostream>
#include <cmath>

PortsList Action::Task_Evade::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Evade::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 MyRight = (*BB)->MyRightVector;
	Vector3 MyUp = (*BB)->MyUpVector;

	Vector3 LOSToTarget = TargetLocation - MyLocation;
	LOSToTarget.normalize();

	// Use world-up to avoid diving when aircraft is banked/inverted
	Vector3 WorldUp(0.0, 0.0, 1.0);

	double Side = MyRight.dot(LOSToTarget);

	// 2026-07-12 수정: 타겟이 정확히 내 6시(Evade 발동조건 자체)에 있을 때는
	// Side가 구조적으로 0 근처라 매틱 부호가 뒤집혀 브레이크 방향을 못 정하는
	// chattering이 실측 확인됨([[session-2026-07-12-evasion-root-cause]], 58초
	// 스트릭에서 turnSign 21% 반전, 반전률과 스트릭 길이가 뚜렷이 상관).
	// |Side|가 임계치 미만이면 새로 판단하지 않고 직전 방향을 유지(hysteresis)해서
	// 한쪽으로 계속 밀어붙이는 각속도가 쌓이도록 한다. 확실히 한쪽으로 넘어갔을
	// 때만(|Side|>=0.15) 방향을 갱신.
	const double SIDE_HYSTERESIS = 0.15;
	static double __lastTurnSign[2] = { 1.0, 1.0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	double TurnSign;
	if (std::abs(Side) < SIDE_HYSTERESIS)
	{
		TurnSign = __lastTurnSign[__t];
	}
	else
	{
		TurnSign = (Side >= 0.0) ? 1.0 : -1.0;
	}
	__lastTurnSign[__t] = TurnSign;

	// ================= v24: 방어 기동 재설계 =================
	// [문제] 기존 Evade = "상대 쪽 순수 수평 브레이크턴" 하나뿐. 스로틀도 방치(직전 값 유지).
	//   BFM Syllabus S3(적이 우리 800m 뒤) 실측: 물림 35~39%, 피격 45.5틱, 최소ATA 176.9°
	//   (한 번도 기수를 못 돌림). v7 로그에서도 Evade 발동 45초 내내 거리 777->150m로
	//   오히려 좁혀지며 82틱 피격 = 트리거는 정상인데 기동 자체가 무력.
	// [원인] ①단일 평면이라 추적자가 리드를 그대로 유지 ②등속이라 예측당함
	//        ③선회율이 속도에 반비례하는데 420m/s 과속 상태로 돌아 선회가 안 됨.
	// [해법 — BFM 정석 3요소, 전부 물리 원리라 상대 불문]
	//   (1) out-of-plane: 수평이 아니라 기수를 낮춘 사선 브레이크.
	//       추적자의 조준면을 강제로 3D로 만들어 리드 해를 깨고,
	//       중력이 선회를 도와 같은 G에서 선회율이 올라간다.
	//   (2) 코너속도: 방어의 목표는 도주가 아니라 "더 빨리 도는 것".
	//       과속이면 감속해 선회율을 확보한다(실측 260m/s에서 27°/s vs 420m/s에서 7°/s).
	//   (3) 고도 안전: 저고도에선 하강 성분을 없애 지면 충돌을 막는다(규정상 300m=즉시 패배).
	const double CORNER_D = 260.0;
	double myAlt = MyLocation.Z;
	double mySpd = (*BB)->MySpeed_MS;

	Vector3 BreakDirection = MyRight * TurnSign;
	BreakDirection.normalize();

	// (1) out-of-plane 성분: 기본은 기수를 낮춘 사선 브레이크.
	//     고도가 낮으면 하강을 줄이고, 아주 낮으면 오히려 살짝 올린다.
	// v31: 고도가 충분하면 **하강 나선**으로 전환 (실측 근거).
	//  [측정] 총 각속도 기준 선회 성능(turn_perf2.py):
	//    수평선회(뱅크82) 지속 11.3°/s, 순간 17.9°/s / 반경 610~1007m
	//    **하강나선(뱅크110) 지속 25.4°/s, 순간 42.8°/s / 반경 493~518m**  ← 2~3배
	//    (이전에 "물리 한계"라 했던 건 yaw로만 재고 수평선회만 시험한 오류였다)
	//  [대가] 고도손실/속도 ≈ 1.0 = 거의 수직 강하. 156° 되돌리는 데 **고도 2000m**.
	//    측정 중 실제로 altitude below min으로 죽은 케이스 발생.
	//  [설계] 그래서 **고도 게이트 필수**. 3000m 위에서만 하강 나선을 쓰고,
	//    그 아래에서는 기존의 완만한 out-of-plane(느리지만 안전)으로 되돌아간다.
	//    규정상 고도 300m는 즉시 패배이므로 안전 여유를 크게 둔다.
	double downMix;
	if (myAlt > 3000.0)
	{
		// 하강 나선: 고도가 높을수록 깊게(최대 1.8). 3000m에서 0.55로 연속 접속.
		double head = (myAlt - 3000.0) / 2000.0;      // 3000m:0 -> 5000m:1
		if (head > 1.0) head = 1.0;
		downMix = 0.55 + head * 1.25;                 // 0.55 ~ 1.80
	}
	else if (myAlt > 2200.0)
	{
		downMix = 0.55 * ((myAlt - 2200.0) / 800.0);  // 2200~3000m: 0 -> 0.55
	}
	else
	{
		downMix = -0.25;                              // 저고도: 상승 성분으로 전환
	}

	Vector3 WorldDown(0.0, 0.0, -1.0);
	Vector3 EvadeDir = BreakDirection + WorldDown * downMix;
	EvadeDir.normalize();

	Vector3 vp = MyLocation + EvadeDir * 3000.0;
	if (vp.Z < 1500.0) vp.Z = 1500.0;            // VP 절대 하한(고도 안전망과 동일 기준)
	(*BB)->VP_Cartesian = vp;

	// (2) 코너속도 확보: 과속이면 감속해 선회율을 얻는다. 이미 느리면 그대로 둔다.
	//     Evade는 원래 스로틀을 안 건드려 직전 값(대개 1.0)이 유지되고 있었다.
	{
		// v29: 에피소드 경계(위치 점프)에서 스로틀 상태 초기화.
		//  RunningTime 기반 판정이 작동하지 않아 직전 판의 스로틀을 물려받고 있었다.
		static float   lastEvThr[2] = { 1.0f, 1.0f };
		static Vector3 evLastPos[2];
		static bool    evHavePos[2] = { false, false };
		if (evHavePos[__t] && MyLocation.distance(evLastPos[__t]) > 2000.0)
			lastEvThr[__t] = 1.0f;
		evLastPos[__t] = MyLocation;
		evHavePos[__t] = true;
		float tgt = 1.0f;
		if (mySpd > CORNER_D + 30.0)
		{
			double over = (mySpd - CORNER_D) / 200.0;   // 0~1
			if (over > 1.0) over = 1.0;
			double u = 1.0 - over * 0.70;               // 최저 0.30
			if (u < 0.30) u = 0.30;
			tgt = (float)u;
		}
		float cur = lastEvThr[__t];
		const float STEP_D = 0.040f;                    // 방어는 즉응이 중요
		if (tgt > cur) { cur += STEP_D; if (cur > tgt) cur = tgt; }
		else           { cur -= STEP_D; if (cur < tgt) cur = tgt; }
		lastEvThr[__t] = cur;
		(*BB)->Throttle = cur;
	}
	// =========================================================

	static int __dbg[2] = { 0, 0 };
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] Evade Z=" << MyLocation.Z << std::endl;

	// 2026-07-12 진단: 장시간(15초+) 끊기지 않는 순수 Evade 스트릭의 원인 규명용.
	// Side(=MyRight·LOS)가 0 근처에서 진동하면 TurnSign이 매틱 뒤집혀 브레이크
	// 방향이 결정을 못 내리는 가설, ATA/Dist가 실제로 개선되고 있는지 여부를 확인.
	static int __evDiag[2] = { 0, 0 };
	if (++__evDiag[__t] % 10 == 0)
	{
		// DECO_TailThreatCheck와 동일 공식(MyToTarget.angleBetween(MyForward))으로
		// 재계산한 "진짜" ATA. BB->MyAngleOff_Degree는 이름과 달리 실제로는
		// AngleOffUpdate.cpp에서 "내 기수 vs 타겟 기수" 각(heading crossing angle)을
		// 담고 있어 TailThreat 게이트가 쓰는 값과 다름 -- 혼동 방지용으로 별도 계산.
		Vector3 MyForward = (*BB)->MyForwardVector;
		float trueAtaDeg = MyLocation.distance(TargetLocation) > 1e-3
			? (float)((TargetLocation - MyLocation).angleBetween(MyForward) * 57.2958)
			: 0.0f;
		std::cerr << "[EVADE_DIAG] team=" << (*BB)->Team
			<< " side=" << Side
			<< " turnSign=" << TurnSign
			<< " dist=" << (*BB)->Distance
			<< " trueAta=" << trueAtaDeg
			<< " headingXAngle=" << (*BB)->MyAngleOff_Degree
			<< " aa=" << (*BB)->MyAspectAngle_Degree
			<< std::endl;
	}

	return NodeStatus::SUCCESS;
}
