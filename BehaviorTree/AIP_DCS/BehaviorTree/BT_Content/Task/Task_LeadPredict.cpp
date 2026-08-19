#include "Task_LeadPredict.h"
#include "../Ablation.h"
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

	// 내 기수와 상대 방향의 각(ATA). 리드 게이트와 코너속도 판정이 공용한다.
	Vector3 myFwdT = (*BB)->MyForwardVector; myFwdT.normalize();
	Vector3 losT = TargetLocation - MyLocation;
	double losLenT = losT.length(); if (losLenT < 1.0) losLenT = 1.0;
	losT = losT / losLenT;
	double ataDeg = std::acos(std::max(-1.0, std::min(1.0, myFwdT.dot(losT)))) * 57.2957795;

	int __ti = ((*BB)->Team == BLUE) ? 0 : 1;

	// ★ 2026-08-06 진단 계측 (DUTY): 우리가 켜져 있다고 믿는 기능이 실제로 몇 % 발동하나.
	//  계기: v23b 코너속도가 6상대 중 5상대에서 아예 안 걸린다는 게 v36에서 드러났고,
	//        기각한 v31 코드가 소스에 남아 v32에 들어가 있는 것도 발견됐다.
	//  트리거 발동만 보고 판정하던 관행을 끝내기 위한 계측이다.
	static long long DUTY_tick[2]  = {0,0};   // 이 노드가 tick된 횟수
	static long long DUTY_jink[2]  = {0,0};   // [실험 J] 사격해 교란이 실제 적용된 틱
	static long long DUTY_jtick[2] = {0,0};   // [실험 J] 게이트를 평가한 틱(발동률 분모)
	static long long DUTY_lead[2]  = {0,0};   // v27 종말조준 게이트
	// v45: standoff 발동률. **발동률은 중요도를 예측하지 못하지만**(절제실험 교훈),
	//  0%면 아예 안 걸린 것이므로 "효과 없음"과 "발동 안 함"을 가르는 데는 반드시 필요하다.
	static long long DUTY_standoff[2] = {0,0};
	static long long DUTY_bank[2]  = {0,0};   // v21 뱅크 횡예측
	static long long DUTY_orbit[2] = {0,0};   // v17 궤도추종(조건 통과)
	static long long DUTY_slot[2]  = {0,0};   // v17 궤도추종(슬롯 실제 적용)
	static long long DUTY_clmpU[2] = {0,0};   // 상승 클램프 발동
	static long long DUTY_clmpD[2] = {0,0};   // 강하 클램프 발동
	static long long DUTY_corner[2]= {0,0};   // v23b 코너속도: 조건 만족
	static long long DUTY_capp[2]  = {0,0};   // v23b 코너속도: **실제 적용**(u<target)
	DUTY_tick[__ti]++;

	double dt = (*BB)->DeltaSecond;
	if (dt < 1e-4) dt = 1.0 / 60.0;

	// 상대 기수 이력(0.2초 실적 회전) — v17 궤도추종과 v20 적응 리드가 공용
	static Vector3 fwdHist[2][16];
	static int     histIdx[2] = { 0, 0 };
	static int     histCnt[2] = { 0, 0 };
	const int      HIST = 12;

	// v18: 에피소드 경계에서 static 상태 초기화 (RunningTime 되감김 = 새 에피소드)
	// v29: 에피소드 경계 감지를 **위치 점프**로 교체.
	//  [버그] 기존엔 RunningTime 되감김으로 판정했는데, RunningTime은 BlackBoard 생성자에서만
	//    0이고 매 틱 증가만 한다. BTActionProvider.reset()이 BT를 재생성하지 않으므로
	//    ("Keep native BT alive across episode resets") 되감기는 일이 없어 **이 리셋은
	//    한 번도 발동한 적이 없다.** 새 판이 직전 판의 기수 이력/스로틀을 물려받고 있었다.
	//  [해법] 리셋 시 기체는 km 단위로 순간이동한다. 1틱에 2km 이상 움직이면 새 에피소드다
	//    (정상 비행으론 불가능: 60Hz에서 2km = 120km/s).
	static Vector3 lastPos[2];
	static bool    havePos[2] = { false, false };
	static bool    needThrReset[2] = { false, false };
	double moved = havePos[__ti] ? MyLocation.distance(lastPos[__ti]) : 0.0;
	bool epBoundary = (havePos[__ti] && moved > 2000.0);
	if (epBoundary)
	{
		histCnt[__ti] = 0;
		histIdx[__ti] = 0;
		needThrReset[__ti] = true;
	}

	// ★★★ 2026-08-08: 실제 BT 틱 간격을 스스로 추정한다 (dt 버그)
	//  [문제] `DeltaSecond`는 BlackBoard 생성자 값 1/60에 고정돼 있다 —
	//    DLL이 `SetBehaviorTreeDeltaTime`을 노출하는데 **호스트가 부르지 않는다**
	//    (파이썬이 선언한 함수 6개에 없고, 대회 제공 `unreal/policies.py`도 마찬가지).
	//    그런데 아래 이력 버퍼는 **BT 틱마다** 채워지고, 제출 조건(ACTION_REPEAT=6)에서
	//    BT는 0.1초마다 호출된다. 12틱 = 1.2초인 창을 0.2초로 나눠 omega가 6배로 커진다.
	//  [실측] repeat=1: om/실측 = 0.98(맞다) / repeat=6: 8.98(틀리다).
	//    onecircle 상대 om이 84deg/s로 찍힌다 — F-16이 낼 수 없는 값이다.
	//  [해법] 경과시간을 직접 잰다: |Δ내위치| / 내속도. 호출 주기가 바뀌어도 따라간다.
	//    선회 중 현/호 차이는 0.1초에 1도 선회 기준 0.005%로 무시 가능하다.
	static double tickDt[2] = { 0.0, 0.0 };
	if (havePos[__ti] && !epBoundary && mySpd > 50.0 && moved > 1e-3)
	{
		double est = moved / mySpd;
		if (est > 0.004 && est < 0.5)                 // 240Hz~2Hz 밖은 이상치로 버린다
			tickDt[__ti] = (tickDt[__ti] <= 0.0) ? est
			                                     : tickDt[__ti] * 0.95 + est * 0.05;
	}
	double dtEff = (tickDt[__ti] > 0.0) ? tickDt[__ti] : dt;

	// 어디까지 교정할지는 환경변수로 고른다(사전등록 PREREG_fix_2026-08-08.md).
	//  미설정 = v32 그대로. 제출 시 변수가 없으면 완전한 무동작이다.
	const bool DTFIX_FULL  = Ablation::sel("dtfix_full");
	const bool DTFIX_ORBIT = Ablation::sel("dtfix_orbit") || DTFIX_FULL;
	double dtOmega = DTFIX_FULL  ? dtEff : dt;   // omegaNow (v21·v17 게이트 공용)
	double dtOrbit = DTFIX_ORBIT ? dtEff : dt;   // v17 궤도 블록의 omega -> R -> phi

	lastPos[__ti] = MyLocation;
	havePos[__ti] = true;

	Vector3 fwdOld  = fwdHist[__ti][(histIdx[__ti] + 16 - HIST) % 16];
	bool haveHist   = (histCnt[__ti] >= HIST);
	fwdHist[__ti][histIdx[__ti]] = TgtFwd;
	histIdx[__ti] = (histIdx[__ti] + 1) % 16;
	if (histCnt[__ti] < 100000) histCnt[__ti]++;

	double omegaNow = 0.0;                          // 상대 선회 각속도 rad/s (실적)
	if (haveHist) omegaNow = fwdOld.angleBetween(TgtFwd) / (HIST * dtOmega);

	// 요격 리드: 상대 진행방향으로 미래위치 예측 (리드시간 = 거리/내속도, 캡 3초)
	// v7 (v8 롤백): 전 거리에서 예측 lead. 사거리 순수조준(v8)은 -40 악화로 원복.
	// v20a(omega 연동 리드 축소)는 폐기: 머지에서 3초 리드가 코너를 가로질러 각도전을
	//   이기는 우리 무기였음이 실측됨(리드 축소 시 six 장악 76%->30%로 붕괴, 상대에게
	//   겨눠지는 시간 53%). 리드는 만지지 않는다.
	double leadTime = dist / mySpd;
	if (leadTime > 3.0) leadTime = 3.0;

	// ※ v25(사거리 내 리드 연속 제거) = **기각**. 리드를 건드리지 말 것.
	//   [실측] Syllabus 사격틱은 55->89.5로 늘었으나 실전 15시드는 오히려 붕괴:
	//     dealt 4.34->1.53, taken 0.0->0.57, 격추 2->0, 6승9무0패 -> 4승10무1패.
	//   [규명] "이 환경엔 총알 비행시간이 없으니 리드 불필요"는 절반만 맞다.
	//     **리드는 사격이 아니라 '추종 기하'를 위한 것이다.** 선회하는 상대를 계속
	//     따라가려면 그가 갈 곳으로 돌아야 한다. 순수 조준은 항상 "지금 있는 곳"만
	//     향하므로 상대 선회 안쪽으로 못 파고들고 뒤로 밀린다(BFM의 pure pursuit
	//     -> overshoot). 짧은 세트피스는 순간 조준이 좋아져 사격틱이 늘지만,
	//     긴 실전은 추종이 무너져 데미지가 급감한다. v8(-40)과 동일 메커니즘.
	//
	// v27: 종말 조준 게이트 — "이미 거의 조준된 상태"에서만 리드를 끈다.
	//  [실측 근거] onecircle전: 사거리 체류 311초인데 사격틱 0. 최소 ATA **1.21°**로
	//    사격조건(1.0°)을 0.21° 차이로 못 넘긴다. 위치·에너지 문제가 아니다 —
	//    우리 315m/s·11.7°/s vs 상대 289m/s·11.9°/s로 선회 능력이 대등하다.
	//    선회 중인 상대에게 **직선 리드**를 쓰면 곡선 경로에서 구조적으로 어긋나
	//    마지막 1°를 못 좁힌다(사격 판정엔 총알 비행시간이 없어 리드가 순이득이 아님).
	//  [v25(기각)와의 결정적 차이] v25는 "거리"로 리드를 껐다가 추격 국면까지 순수조준이
	//    되어 추종 기하가 붕괴했다(dealt 4.34->1.53). v27은 **ATA로 게이트**한다:
	//    ATA가 크면(추격 중) 리드 100% 유지, ATA가 작을 때만(종말 조준) 끈다.
	//    -> 추종 기하는 보존하고 마지막 조준만 다듬는다.
	// [절제 A4] v27 종말조준. 발동률 0.3~5.7%로 v27의 간판 개선치고 거의 안 걸린다.
	// ★★ v46 시험 (2026-08-19): v27 게이트를 넓힌다 — 사용자 제안 "사거리 안인데
	//   사격각이 안 나올 때 VP를 상대에 정확히 찍는다".
	//  [왜 넓히나] 실측: 사거리 안 우리 ATA 중앙이 vs yuno 23.4~75.9도, vs 기준모델 100%가 3도 밖.
	//    그런데 v27 게이트는 ATA<10도에서만 열려 발동률이 0.3~5.7%다 = 거의 안 걸린다.
	//    즉 **사거리 안 대부분의 시간에 여전히 상대 앞 750m(3초 리드)를 겨눈다.**
	//  [위험 — 반드시 기억할 것] v25(거리로 리드 제거)는 **기각**됐다:
	//    dealt 4.34 -> 1.53, 6승9무0패 -> 4승10무1패.
	//    사유: "리드는 사격이 아니라 **추종 기하**를 위한 것이다. 순수 조준은 상대 선회
	//    안쪽으로 못 파고들고 뒤로 밀린다(pure pursuit -> overshoot)."
	//    이 시험은 v25(거리 게이트)와 v27(ATA 게이트) 사이다. 어느 쪽으로 기울지는 재봐야 안다.
	//  [설계] 게이트 각도를 절제 플래그로 셋 중 하나로 고른다. 하나만 재면
	//    "이 방향이 틀렸다"를 잘못 결론낸다(v33이 CAP 25/40 둘 다 재서 알아낸 교훈).
	//    fade 구간도 게이트에 맞춰 늘려 연속성을 유지한다(3도에서 순수조준은 그대로).
	double v27Gate = 10.0;                                  // 기본 = v27 그대로
	if      (Ablation::sel("aim15")) v27Gate = 15.0;
	else if (Ablation::sel("aim20")) v27Gate = 20.0;
	else if (Ablation::sel("aim30")) v27Gate = 30.0;
	if (!Ablation::off("v27") && dist < 914.0 && ataDeg < v27Gate)
	{
		DUTY_lead[__ti]++;
		double fade = (ataDeg - 3.0) / (v27Gate - 3.0);   // 게이트각:리드유지 -> 3도이하:순수조준
		if (fade < 0.0) fade = 0.0;
		if (fade > 1.0) fade = 1.0;
		leadTime *= fade;
	}
	// ★★ v45 STANDOFF (2026-08-16) — 절제 플래그 "standoff" 로만 켜진다(기본 꺼짐).
	//  [무엇을 하나] 조준점은 **한 톨도 건드리지 않는다.** 폐쇄율(스로틀)만 낮춘다.
	//    v33은 조준점을 상대 뒤로 옮겨 득점을 구조적으로 포기했고(준데미지 95% 감소) 기각됐다.
	//    여기서 바꾸는 것은 거리뿐이다.
	//  [근거 — 2026-08-16 실측, vs yuno 15판, 사거리 안 거리대별 LOS 각속도]
	//      150~300m 66.1도/s | 450~600m 29.9 | 750~900m 16.1 | 900~1050m 14.3
	//    우리 지속 선회율 최고는 15.6도/s(속도 250~275m/s 구간). 사격 사거리 상한은 914.4m.
	//    => 추종 가능 구간과 사격 구간이 **900~914m에서만 겹친다.**
	//    지금은 조준이 안 된 채 914m를 지나 최근접 중앙 216m까지 파고들고,
	//    거기서는 요구 선회율이 능력의 4배라 영영 못 맞춘다.
	//  [게이트를 ATA로 잡는 이유] LOS 각속도를 쓰면 안 된다.
	//    losRate는 (LHIST*dt)로 나누는데 호스트가 SetBehaviorTreeDeltaTime을 부르지 않아
	//    dt가 1/60에 고정된다. ACTION_REPEAT=6이면 6틱 창이 실제 0.6초인데 0.1초로 나눠
	//    **6배 과대평가**된다(2026-08-16 확인). 절대 임계값을 쓰면 의도한 지점에서 안 열린다.
	//    ATA는 dt와 무관하고, 두 매치업을 실제로 가른다:
	//      사거리 안 우리 ATA 중앙 — jung(이김) 6.12도  vs  yuno(짐) 23.4~75.9도
	//    "안으로 들어왔는데 각이 여전히 크면 그 접근은 헛되다"가 판별식이다.
	//  [노리는 것] 압도가 아니라 1틱. yuno전 15판 중 7판이 1.0000 대 1.0000이라
	//    아주 작은 데미지도 승패를 뒤집는다. 규정은 200초 HP 비교다.
	//  [기각 조건 — 결과 보기 전 고정] 어디서든 준데미지가 줄면 무조건 기각.
	bool standoffActive = false;   // 스로틀 최종 대입부(아래 v9/v23b)까지 플래그로 넘긴다
	// 두 가설을 절제 플래그로 갈라 잰다(둘 다 조준점은 안 건드리고 스로틀만 낮춘다):
	//  A "standoff"  : 각이 큰데 파고드는 것을 막는다 (ataDeg > 15)  — 헛된 접근 억제 가설
	//  B "dwell"     : 잘 겨눈 상태에서 통과를 늦춘다 (ataDeg < 15)  — 사격구역 체류 가설
	//    B는 메모리 bt_wez_transit("초당 23m로 파고들어 사격구역을 통과한다")과 직접 연결된다.
	if ((Ablation::sel("standoff") && dist < 880.0 && ataDeg > 15.0 && tgtSpd > 30.0)
	 || (Ablation::sel("dwell")    && dist < 880.0 && ataDeg < 15.0 && tgtSpd > 30.0))
		standoffActive = true;

	Vector3 predicted = TargetLocation + TgtFwd * (tgtSpd * leadTime);

	double rollDeg = (*BB)->TargetRotation_EDegree.Roll;
	// v21: 뱅크각 횡예측을 "실제 선회(omega) 동반 시"로 게이트. 롤 리버설(선회 없는
	//   롤 위글)은 무시한다.
	//   [근거] STEP1 s06 실측: 직선 추격(상대 turn 1~3deg/s) 중에도 상대 롤 위글에
	//   VP가 TgtRight로 ±600m 휘둘려, 우리가 -21~-67deg/s 선회 스파이크로 속도를 반복
	//   소모 -> dead-six인데도 상대가 15~40m/s 빨라 폐쇄 불가. 실제 선회는 v17 궤도가
	//   담당하므로 여기선 노이즈만 걸러진다. 머지는 omega가 높아 그대로 작동(v20a 실수
	//   회피 = 머지 무기 훼손 없음). omega>0.06rad/s = 3.4deg/s (궤도블록과 동일 임계).
	// [절제 A2] v21 뱅크 횡예측. **발동률 95~97%로 최대 지분인데 한 번도 검증된 적이 없다.**
	//   이 절제가 이번 실험에서 가장 중요하다.
	if (!Ablation::off("v21") && std::fabs(rollDeg) > 10.0 && omegaNow > 0.06)
	{
		DUTY_bank[__ti]++;
		double s = (rollDeg > 0.0) ? 1.0 : -1.0;
		double bankFactor = std::fabs(rollDeg) / 90.0;
		if (bankFactor > 1.0) bankFactor = 1.0;
		double turnMag = bankFactor * 0.25 * dist;
		if (turnMag > 600.0) turnMag = 600.0;
		if (dist < 600.0) turnMag *= (dist / 600.0);
		predicted = predicted + TgtRight * (s * turnMag);
	}

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
	//   (기수 이력/omega는 함수 상단에서 계산 -- v20부터 적응 리드와 공용)
	// [절제 A3] v17 궤도추종. 조건통과 68~93% / 슬롯적용 45~75%로 두 번째 지분.
	if (!Ablation::off("v17") && haveHist)
	{
		Vector3 axis   = fwdOld.cross(TgtFwd);      // 회전축(우수계: 진행방향 = +)
		double axisLen = axis.length();
		double turnAng = fwdOld.angleBetween(TgtFwd);
		// ★ 게이트와 기하를 분리한다(사전등록 PREREG_fix_2026-08-08.md).
		//   dtfix_orbit : 게이트는 v32 그대로 두고 **반경 계산만** 교정한다.
		//                 v32의 경험적 조정(발동률)을 보존한 채 슬롯 거리만 되돌리기 위해서다.
		//   dtfix_full  : 게이트도 교정한다 -> 발동률이 급감할 것이다(메커니즘 확인 지표).
		double omega    = turnAng / (HIST * dtOmega);  // 게이트용
		double omegaGeo = turnAng / (HIST * dtOrbit);  // 궤도 기하용

		// 선회 중(3.4deg/s 이상) + 교전거리일 때만 궤도 모드
		if (axisLen > 1e-9 && omega > 0.06 && dist < 2500.0 && tgtSpd > 30.0)
		{
			DUTY_orbit[__ti]++;
			Vector3 a = axis; a.normalize();
			double R = tgtSpd / omegaGeo;           // 선회 반경
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
				DUTY_slot[__ti]++;
				// 슬롯에서 멀면 슬롯으로, 슬롯에 붙으면 요격 lead로 연속 전환
				double w = toSlot.length() / 400.0;
				if (w > 1.0) w = 1.0;
				predicted = tailSlot * w + predicted * (1.0 - w);
			}
		}
	}
	// =======================================================================

	// ============ v33: 관통 임박 감지 -> lag pursuit 전환 ============
	// [왜] 오버슈트는 "나쁜 조준점"이 아니라 **물리적으로 못 도는 코너**다.
	//   LOS 회전율 w = V_perp / r 이라 근접에서 발산한다. 실측: 153m 관통 순간 필요 110deg/s,
	//   우리 능력은 순간 최대 42.8deg/s(turn_perf2). 3배 차이라 **어떤 VP를 골라도 못 돈다.**
	//   -> 못 돌 걸 알면서 리드(앞)를 겨누면 안쪽으로 파고들다 그대로 관통한다.
	//      BFM 정석은 이때 **lag pursuit**(상대 뒤쪽을 겨눔): 선회 여유를 벌고 폐쇄율을 낮춰
	//      상대 원 바깥에 남았다가 기하가 돌아오면 다시 붙는다.
	// [근거] 이건 예측(MPC)이 아니라 **규칙 하나**다. 과거 MPC 검토에서 내린 결론이기도 하다
	//   ("예측 엔진 정교화 대신 아는 행동을 규칙으로"). Syllabus S2 '전환 실패'(뒤를 잡고도
	//   사격 1틱)와 원 계열 교착이 같은 증상이다.
	// [리드는 건드리지 않는다] v20a/v25가 리드 자체를 줄였다가 두 번 다 기각됐다.
	//   여기서는 리드 계산을 그대로 두고, **관통이 임박한 순간에만** 최종 조준점을 뒤로 옮긴다.
	//   조건이 풀리면 즉시 원래 리드 추적으로 복귀한다(상태를 남기지 않는다).
	bool lagActive = false;      // 스로틀은 아래 v9/v23b 로직이 최종 대입하므로 플래그로 넘긴다
	{
		// LOS 단위벡터 이력으로 시선 회전율을 잰다(요만이 아니라 3D 전체 각).
		static Vector3 losHist[2][16];
		static int     losIdx[2] = { 0, 0 };
		static int     losCnt[2] = { 0, 0 };
		const int      LHIST = 6;                 // 0.1초 창(60Hz 기준)
		Vector3 losNow = TargetLocation - MyLocation;
		double  losLen = losNow.length();
		if (losLen < 1.0) losLen = 1.0;
		losNow = losNow / losLen;

		// v29와 동일한 위치점프 기반 에피소드 경계 처리(RunningTime은 작동하지 않는다)
		if (needThrReset[__ti]) { losCnt[__ti] = 0; losIdx[__ti] = 0; }

		Vector3 losOld = losHist[__ti][(losIdx[__ti] + 16 - LHIST) % 16];
		bool haveLos = (losCnt[__ti] >= LHIST);
		losHist[__ti][losIdx[__ti]] = losNow;
		losIdx[__ti] = (losIdx[__ti] + 1) % 16;
		if (losCnt[__ti] < 100) losCnt[__ti]++;

		if (haveLos)
		{
			double losRate = losOld.angleBetween(losNow) * 57.2957795 / (LHIST * dt);  // deg/s
			// 우리가 지속적으로 낼 수 있는 선회율(turn_perf2 실측: 하강나선 지속 25.4deg/s가 최대).
			// 이걸 넘는 시선 회전율은 구조적으로 추종 불가 = 관통 확정.
			const double TURN_CAP = 40.0;
			// ★★ v33/v33b 모두 기각(2026-08-05). 이 블록은 **비활성**이다. 되살리지 말 것.
			//  [실측 15시드] ACE  v32 13승1무1패 0.3791  ->  v33(CAP25) 2승 0.0417
			//                                            ->  v33b(CAP40) 2승 0.0182
			//                onecircle v32 3승  ->  v33/v33b 둘 다 0승, 준데미지 정확히 0.0000
			//  CAP을 25에서 40으로 올려도 똑같이 2승 = **임계값이 아니라 기동 자체가 틀렸다.**
			//  [메커니즘] 평균보상은 331->763으로 두 배가 됐다(위치는 실제로 좋아짐).
			//    그런데 준데미지는 95% 감소. lag는 **의도적으로 상대 뒤를 겨냥**하므로
			//    사격조건 ATA<=1.0도를 영원히 못 만든다. 위치를 사고 사격을 팔았는데,
			//    HP로 승부가 갈리는 경기에서 위치는 값이 0이다(행동강령 3 위반).
			//    게다가 v32의 성과(상승 클램프 해제로 '겨눌 수 있게' 된 것)와 정면 충돌한다.
			//  [얻은 답] "코너를 못 돈다"의 올바른 결론은 "lag로 포기"가 아니라
			//    **"애초에 그 기하에 안 들어간다"(선제 포지셔닝)**이다.
			//    lag는 유지(sustain) 전술이지 득점(score) 전술이 아니다.
			//  코드는 기록·재현을 위해 남기되 게이트로 끈다.
			// ★★ v45 STANDOFF (2026-08-16) — 절제 플래그 "standoff" 로만 켜진다(기본 꺼짐).
			//  [v33과 무엇이 다른가] v33은 **조준점을 상대 뒤로 옮겨** 득점을 구조적으로 포기했다
			//    (준데미지 95% 감소로 기각). 여기서는 **조준점을 한 톨도 건드리지 않는다.**
			//    바꾸는 것은 폐쇄율(스로틀)뿐이다. 겨눈 채로 거리를 유지한다.
			//  [근거 — 2026-08-16 실측, vs yuno 15판 사거리 안]
			//    거리대별 LOS 각속도 중앙        우리 지속 선회율 최고 15.6도/s
			//      150~300m  66.1도/s   불가        (250~275m/s 구간에서 측정)
			//      450~600m  29.9도/s   불가
			//      750~900m  16.1도/s   경계
			//      900~1050m 14.3도/s   **가능**
			//    사격 사거리 상한이 914.4m이므로 **추종 가능 구간과 사거리가 900~914m에서만 겹친다.**
			//    지금은 조준이 안 된 채 914m를 통과해 최근접 중앙 216m까지 파고든다.
			//    그 안쪽에서는 요구 선회율이 능력의 4배라 영영 못 맞춘다.
			//  [노리는 것] 압도가 아니라 **1틱**이다. yuno전 15판 중 7판이 1.0000 대 1.0000
			//    (양쪽 데미지 0)이므로 아주 작은 데미지도 승패를 뒤집는다. 규정은 HP 비교다.
			//  [기각 조건 — 결과 보기 전 고정] 준데미지가 줄면 무조건 기각.
			//    "위치를 사고 사격을 파는" 것이 v33의 정체였고 그건 행동강령 3 위반이다.
			const bool V33_LAG_ENABLED = false;
			if (V33_LAG_ENABLED && losRate > TURN_CAP && dist < 900.0 && tgtSpd > 30.0)
			{
				double excess = (losRate - TURN_CAP) / TURN_CAP;   // 0~
				if (excess > 1.0) excess = 1.0;
				// 초과분에 비례해 조준점을 상대 뒤쪽으로. 최대 0.6초분(약 150~180m).
				double lagT = 0.6 * excess;
				predicted = TargetLocation - TgtFwd * (tgtSpd * lagT);
				lagActive = true;          // 폐쇄율도 죽여야 관통이 막힌다(아래에서 적용)
			}
		}
	}
	// =================================================================

	// (v19 에너지 요격 블록은 전제 반증으로 제거 — 이 시뮬은 상승이 속도를 안 깎는다.
	//  기록: 상대기체 공유파일/2026-07-23_v19_에너지요격_실패/README.md)

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
	// ============ v32: 상승 클램프 해제 (조준 병목의 실체) ============
	// [실측] onecircle 4판, ata_split.py(양방향 수정본):
	//   사거리 내 5293틱 중 **위로 잘림 2691틱(50.8%)** / 아래로 잘림 713틱(13.5%)
	//   위로 잘린 틱의 **필요 앙각 중앙값 59.1deg** vs 한계 atan(0.5)=26.57deg (2.2배)
	//   조준이 가장 잘 된 400틱에서도 위로잘림 196/400(49%), 아래로잘림 0/400.
	//   유일한 사격 성공(278m)은 고도차 +127m로 위 한계 +139m 바로 아래 = 우연히 원뿔 안.
	//   => 사거리 안 88초 중 사격 2틱의 주범. 사거리 내 고도차 중앙값 +288.8m(상대가 위).
	// [원인] climbSlope는 diveSlope를 **대칭으로 복사**한 값이다. 그런데
	//   강하 클램프에는 지면 충돌(min_altitude=300m, 즉시 패배)이라는 물리적 근거가 있지만
	//   **상승에는 그런 위험이 없다.** 대칭이어야 할 이유가 처음부터 없었다.
	// [근거 보강] v19 블록 주석의 반증: "이 시뮬은 상승이 속도를 안 깎는다."
	//   상승이 에너지를 소모하지 않으므로 위로 조준하는 비용이 낮다.
	// [주의] Syllabus S5는 "고도 우위가 오히려 독"이라 기록했으나 그건 **미리 높이 떠서
	//   과속으로 진입**한 경우다. 여기는 상대를 조준하려 기수를 드는 것이고,
	//   과속은 v23b 코너속도 스로틀이 따로 잡는다. 같은 상황이 아니다.
	// [부수 효과] 위를 조준하면 상대 고도로 따라 올라가므로 고도 자산이 회복된다.
	//   실측상 교전의 46%를 '하강나선 불가' 구간(<3800m)에서 보내고 있는데 그것도 완화된다.
	// [절제 A5] v32 상승클램프 해제를 v29 값(0.5)으로 되돌린다.
	//   v32 채택의 근거였던 변경인데, 그 판정은 **P1 고정 사격규칙 하에서** 내려졌다.
	//   3단계 phase 규칙으로 바뀐 지금도 유효한지 다시 확인한다.
	// [절제 A6] v18 강하클램프를 v17 값(0.2)으로 되돌린다.
	double climbSlope = dist * (Ablation::off("v32clamp") ? 0.5 : 3.0);
	double diveSlope  = dist * (Ablation::off("v18dive")  ? 0.2 : 0.5);
	// ★ 2026-08-09: 강하 클램프 완화 시험 (`divefree`).
	//  [계기] 신형 도전자는 1000m 이상 아래로 강하하며 선회한다. 그 국면에서
	//    필요 강하각 41~65도 vs 허용 30~50도로 **7구간 중 5~6구간이 막힌다**(seed 0·6 실측).
	//    막히면 기수가 안 내려가고, 그러면 선회율이 안 나온다(우리 8.3°/s vs 상대 14.8°/s).
	//  [근거] v32의 최대 성과가 **상승 클램프 해제**(0.5->3.0)였는데 강하는 안 건드렸다.
	//    당시 주석: "아래로 잘림은 13.5%로 병목이 아니다" — 그 13.5%는 **낡은 상대 세트**
	//    에서 잰 값이다. 아래로 파고드는 상대에겐 결정적 구간에서 71~86% 막힌다.
	//  [위험] 지면 충돌. 고도 300m 즉시 패배다. 트리 레벨 안전망
	//    (DECO_AltitudeCheck MinAlt=1800 -> Task_ClimbOut)이 최우선으로 잡으므로
	//    이 완화는 그 위에서만 작동한다. 절대 하한 1500m도 아래에 그대로 있다.
	// ★★ v45 채택 (2026-08-16): 강하 클램프를 상승과 대칭으로 푼다. **기본 동작**이다.
	//  [왜 이제 되나] v40 때 "4승->1승"으로 기각됐던 사유는 "조준만 내리고 **벽은 그대로**"였다.
	//    당시 벽: DECO_AltitudeCheck MinAlt=1800, 조준 절대하한 1500m 고정.
	//    현재   : MinAlt=700(v42), 조준하한 800~1500 동적(v40). **두 벽이 다 내려갔다.**
	//    CLAUDE.md의 "반쪽 수정 금지"가 이 경우엔 반대로 작동했다 — 나머지 반쪽이 채워졌다.
	//  [메커니즘] diveSlope = dist*0.5 는 강하각을 약 27도로 묶어 **하강나선 기하에
	//    들어갈 수가 없었다.** 실측표(turn_perf2): 수평선회 지속 11.3도/s vs 하강나선 25.4도/s.
	//    우리 실전 지속 선회율이 13~15.6도/s로 수평선회 수준이던 이유가 이것이다.
	//    yuno가 강요하는 LOS 각속도는 600~900m에서 16.1~17.4도/s라 하강나선이면 추종 가능하다.
	//  [대가를 우리만 낼 수 있다] 156도 되돌리기에 고도 1967m가 든다.
	//    하한: 우리 700 / yuno 1800·3200 / TW 3000 / jung·jh2 800·1500.
	//  [실측 15시드 x 3상대, 판정기준 사전 고정]
	//    yuno  1승7무7패 -0.614(준0.07) -> 1승9무5패 -0.449(준0.21)
	//    jung 14승1무0패 +12.071(준12.07) -> 14승1무0패 +13.671(준13.67)
	//    jh2  11승4무0패  +8.377(준8.38) -> 12승3무0패 +11.092(준11.09)
	//    합계 +19.835 -> +24.314.  **우리 추락 0/45건.**
	//    판정원칙3: 최대1판 제외 +3.472, 최대3판 제외 +3.471 — 분산이 아니라 고르게 분포.
	//  ⚠ 되돌리려면 절제 플래그 "v45dive" 로 v18 값(0.5)으로 복귀한다.
	if (!Ablation::off("v45dive")) diveSlope = dist * 3.0;   // 상승과 대칭 (기본)
	//   ※ 강하는 그대로 둔다. 지면 충돌 위험은 실재하고, 아래로 잘림은 13.5%로 병목이 아니다.
	// v20: 강하 클램프에 절대 상한 650m. 사거리(<914m)에선 457m 이하라 v18 조준 성과에
	// 영향 없음(연속). 원거리에서만 죄어 "급기동 상대의 다이브 리드를 쫓는 깊은 다이브
	// 깔때기"를 차단 (seed0 실측: 2.2km 거리에서 939m까지 추락, 종료고도 300m 방향이었다).
	// ★ `divefree`는 이 상한도 함께 풀어야 의미가 있다.
	//   650m면 dist 1555m에서 원래(777)든 완화(4665)든 똑같이 650으로 잘려 **무동작**이 된다.
	//   실측상 필요한 강하량은 상대와의 고도차(~1150m)다.
	//   다만 v20이 이 상한을 넣은 이유는 실재한다("깊은 다이브 깔때기": 2.2km에서 939m까지
	//   추락해 종료고도 300m 방향). 그래서 무제한이 아니라 2000m로 둔다.
	//   최종 안전망은 그대로다: 조준점 절대 하한 1500m + 고도<1800m면 ClimbOut이 최우선.
	//  ★ v45: 이 상한도 함께 푼다. 650m면 dist 1555m에서 원래든 완화든 똑같이 650으로 잘려
	//    **무동작**이 되기 때문이다(위 주석 참조). 무제한은 아니고 2000m로 둔다 —
	//    v20이 이 상한을 넣은 이유("깊은 다이브 깔때기")는 실재한다.
	double diveCap = (!Ablation::off("v45dive")) ? 2000.0 : 650.0;
	if (diveSlope > diveCap) diveSlope = diveCap;
	// v22b: 안전망 ①(2200m부터 diveSlope 고도비례 축소)은 제거.
	//  [실측 반증] v22 vs 권정환: dealt 5.03->2.23 폭락. 무득점 판(s08/s12)이 사거리 20초
	//  체류에도 수직오차 23°. 그 판들은 상대가 오히려 위(고도차 +202/+439m)라 하향 억제가
	//  궤적 전체를 교란해 조준을 망침. => 광범위 하향 억제는 부작용이 과하다. 제거하고
	//  안전망 ②(강제 상승, 아래)만으로 바닥을 지킨다.
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (predicted.Z < minZ) { predicted.Z = minZ; DUTY_clmpD[__ti]++; }
	if (predicted.Z > maxZ) { predicted.Z = maxZ; DUTY_clmpU[__ti]++; }
	// ★ 2026-08-09 `lowfloor`: 조준점 절대 하한을 낮춘다.
	//  [실측] jh2전 15판에서 **우리 최저고도 중앙 1797m / 최소 1780m** — 매 판 1800m
	//    벽(DECO_AltitudeCheck)에 정확히 걸린다. 상대는 중앙 1013m / 최소 403m까지 쓴다.
	//    상대가 1800m 아래로 내려가면 ClimbOut이 트리 전체를 가져가 **추격이 중단된다.**
	//  [상대의 실제 변경] 팀원은 8/6판 -> cf49f0e에서 XML 59개 노드 중 **딱 두 숫자**만
	//    바꿨다: PreventLandCrash FloorHard 1800->800, FloorSoft 3200->1500.
	//    그 한 변경으로 우리 상대 전적이 0승15패 -> 11승4패로 뒤집혔다.
	//  ⚠ 하한만 낮추고 ClimbOut 임계(XML MinAlt)를 그대로 두면 `divefree`와 같은
	//    반쪽 수정이 된다 — 내려가려다 벽에 부딪혀 에너지만 잃는다. **둘 다 낮춘다.**
	//  규정상 고도 300m 즉시 패배. 상대는 800m 하한으로 403m까지 갔다(여유 103m).
	// ============ v40: 조준점 하한을 **상대 고도에 따라** 낮춘다 (채택) ============
	//  [문제] v32는 하한 1500m + ClimbOut 1800m이라 **매 판 1800m 벽에 걸렸다**
	//    (jh2전 15판 실측: 우리 최저고도 중앙 1797m / 최소 1780m).
	//    DECO_AltitudeCheck는 ReactiveFallback의 첫 분기라, 상대가 그 아래로 내려가면
	//    트리가 통째로 ClimbOut으로 넘어가 **추격이 중단된다.**
	//    상대(팀원 cf49f0e)는 최저 403m까지 쓴다 — 우리는 기동 공간 1000m를 버리고 있었다.
	//  [원리] 고도를 내주는 것은 **상대를 따라갈 때만** 이득이다. 상대가 위에 있으면
	//    내려갈 이유가 없다. 그래서 무조건이 아니라 **상대 고도에 연동**한다.
	//  [기각한 중간안] 무조건 800m(`lowfloor`)는 jh2를 4승11패->11승3패로 뒤집었지만
	//    kwon이 11승->8승 퇴행했다. kwon은 1500m 아래로 안 내려가는데(최저 1490m)
	//    우리만 1000m 더 내려가(중앙 5963->5006m) 준 데미지가 36% 줄었다.
	//  [실측 성과] 10상대 150판: 101승34무15패 +51.66 -> **102승42무6패 +68.14**
	//    jh2 4승11패 -> **12승2패**, ACE 14승1패 -> 15승0패, 우리 고도이탈 0건.
	//    Syllabus PASS 0->1(첫 PASS). jh2 최대기여시드 11%로 분산 아님.
	//  ⚠ XML의 `DECO_AltitudeCheck MinAlt`도 1800 -> 1000으로 **같이** 낮춰야 한다.
	//    하한만 낮추고 벽을 두면 내려가려다 부딪혀 에너지만 잃는다(`divefree` 기각 사유).
	double __follow = TargetLocation.Z - 300.0;      // 상대보다 300m 아래까지 따라간다
	double AIM_FLOOR = (__follow < 800.0) ? 800.0 : __follow;
	if (AIM_FLOOR > 1500.0) AIM_FLOOR = 1500.0;      // v32 하한보다 위로는 올리지 않는다
	if (Ablation::sel("v40floor")) AIM_FLOOR = 1500.0;          // 절제용: v32로 원복
	if (Ablation::sel("lowfloor")) AIM_FLOOR = 800.0;
	// (`lowfloor2` 태그는 위 기본 동작으로 승격됐다. 별도 분기 제거)
	if (predicted.Z < AIM_FLOOR) predicted.Z = AIM_FLOOR;   // v18: 3500 -> 1500
	// v22c: LeadPredict 내부 고도 안전망은 제거. 고도<1800이면 ClimbOut이 최우선으로
	//  잡아 LeadPredict가 실행조차 안 되므로(트리 구조) 여기 안전망은 죽은 코드였다.
	//  고도 안전은 DECO_AltitudeCheck(예측형) + Task_ClimbOut(풀스로틀) = 트리 레벨에서 처리.

	// ===== [실험 J] 개전 30초 생존 — 사격해 교란 (기본 OFF, Ablation 게이트) =====
	// 사전등록: experiments/match_conditions/PREREG_p1survival_2026-08-13.md
	// [문제] v42의 남은 실점이 **전부** 개전 22~29초의 7초 창에 몰려 있다.
	//   OBFM_RED 30판 실측: P1(0~100s) 받은 6.853 / P2 0.000 / P3 0.000.
	//   피격 565틱 전부 t<100s, 시각 중앙 25초, 거리 348m, 우리 ATA 168도(상대가 6시).
	//   그 구간에서 우리가 버는 건 0.475뿐 = **공격성을 생존과 맞바꾸는 비용이 사실상 0**.
	// [가설] 사격해를 깨는 것과 싸움을 포기하는 것은 다르다.
	//   P1 사격 요건은 |ATA| <= 1.0도로 극히 좁다. 비행경로에 작은 면외 성분만 줘도
	//   상대 추적 루프가 그 1도를 못 맞춘다. **기수는 계속 싸움 안에 둔다.**
	// [왜 Evade와 다른가] Evade는 MyRight 브레이크로 **진행 방향 자체**를 바꿔 등을 내줬고
	//   v41에서 제거가 이득이었다. 여기서는 조준점에 **주기적 면외 성분만** 더한다.
	//   게이트가 풀리면 즉시 원복 — 상태를 남기지 않는다(v33 설계와 동일).
	// [이미 기각된 것 — 반복하지 않는다] lag pursuit(v33/v33b: 뒤를 겨누면 ATA<=1도를
	//   영원히 못 만든다, ACE 13승->2승), Evade 게이트 축소(A2: 더 나쁜 순간으로 미룸),
	//   접근속도 상한(v39), dt 수정(orbit/full). **공통점: 전부 싸움을 포기하는 방향이었다.**
	{
		// 에피소드 경과 시간. RunningTime은 생성자 값에 고정돼 작동하지 않으므로
		// 위치점프 기반 경계(needThrReset)와 자체 추정 틱간격(tickDt)으로 만든다.
		static long long epTick[2] = { 0, 0 };
		if (needThrReset[__ti]) epTick[__ti] = 0;
		epTick[__ti]++;
		double dtJ   = (tickDt[__ti] > 1e-6) ? tickDt[__ti] : (1.0 / 60.0);
		double tSecJ = (double)epTick[__ti] * dtJ;

		double ampJ = 0.0, perJ = 2.0;
		if      (Ablation::sel("j1")) { ampJ = 150.0; perJ = 2.0; }
		else if (Ablation::sel("j2")) { ampJ = 300.0; perJ = 2.0; }
		else if (Ablation::sel("j3")) { ampJ = 150.0; perJ = 1.0; }

		// 게이트: 상대가 우리 뒤(ATA>120도) + 교전거리 + 개전 초반에만.
		if (ampJ > 0.0 && ataDeg > 120.0 && dist < 900.0 && tSecJ < 45.0)
		{
			Vector3 upJ = (*BB)->MyUpVector; upJ.normalize();
			double  ph  = 6.283185307179586 * tSecJ / perJ;
			predicted   = predicted + upJ * (ampJ * std::sin(ph));
			DUTY_jink[__ti]++;
		}
		DUTY_jtick[__ti]++;
	}
	// ==========================================================================

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
		// ※ v37(스로틀 하한을 거리별로 0.15/0.35/0.55) = **기각**. 되돌렸다.
		//   [실측] 하한을 0.15까지 풀었는데 거리 프로필이 소수점까지 동일했고
		//     kwon전 dealt는 10.9943 -> 10.9942로 사실상 무변화.
		//   [원인] 스로틀 계통 계측 결과 **실제 최저값이 0.545~0.66**이라
		//     0.55 하한에 애초에 닿지 않았다. 하한은 병목이 아니었다.
		if (u < 0.55) u = 0.55;

		// ★ v38: 코너속도 감속의 **거리 게이트를 제거**한다(아래 needTurn).
		//   진짜 병목은 하한이 아니라 **원거리 풀스로틀**이다.
		target = (float)u;
	}
	(void)tgtBank;

	// ============ v23: 전술적 코너속도 (기수를 돌려야 하는 순간에만 감속) ============
	// [실측 근거] 속도별 지속 선회율: 240~270m/s에서 27deg/s, 420~450m/s에서 7deg/s (4배).
	//   그런데 우리 교전속도 중앙값이 422m/s = 코너속도의 1.7배 -> 선회율이 최대치의 1/4.
	// [Syllabus S5 증거] 에너지 우세(1500m 위 + 고속)로 시작해도 사격 0틱, 최소ATA 45~52deg.
	//   고도 우위가 "속도"로 바뀌는데 이미 과속이라 기수를 못 돌림 = 우위가 오히려 독.
	// [S2/S4 증거] 최소ATA 0.0~0.2deg 도달(조준 가능)인데 사격틱 1.5~15.5 = 스치고 지나감.
	//   각속도 과다로 조준점에 "머물지" 못하는 것.
	// [과거 실패(v4/v9~v12)와의 결정적 차이] 그들은 "항상 감속"이라 직선 추격에서 뒤처져 실패.
	//   v23은 (a)교전거리 (b)기수를 크게 돌려야 함 (c)과속 상태 — 3조건이 동시에 참일 때만
	//   감속하고, 정렬되는 즉시 풀스로틀로 복귀한다. 직선 추격 국면은 건드리지 않는다.
	// ★ v36(260 -> 287) = **기각**. 되돌렸다. 재시도 금지.
	//  [측정] tools_diag/corner_speed.py — 뱅크82 수평선회 50초 유지, 총 각속도 기준:
	//    0.65 -> 220m/s, 11.0deg/s, 반경 1144m (반경 최소)
	//    0.80 -> 287m/s, 12.8deg/s, 반경 1281m (**선회율 최대**)
	//    1.00 -> 329m/s, 11.0deg/s, 반경 1710m
	//  [결과] 6상대 15시드에서 **5상대가 소수점까지 동일**하고 onecircle만 퇴행
	//    (1승12무2패 -> 0승11무4패). 합계 승 58->57, 패 3->5.
	//  [왜 틀렸나] 측정은 뱅크82를 50초 유지한(침하율 97m/s) **이상적 조건**이다.
	//    실전에서 그 자세를 유지하는 일이 없으므로 '287이 선회율 최적'은 그 기동에서만 참이다.
	//    측정 자체는 옳았으나 **적용 대상이 틀렸다.**
	//  [부수 발견] 5상대에서 결과가 완전 동일 = 이 코너속도 로직은 **onecircle 상대로만 발동**한다.
	//    needTurn 조건(dist<2500 && ata>12 && spd>CORNER+30 && !beingChased)이
	//    다른 상대에겐 거의 성립하지 않는다. '코너속도를 지킨다'고 믿었지만 실제론 거의 놀고 있다.
	const double CORNER = 260.0;
	// (myFwdT / losT / ataDeg 는 함수 상단에서 계산 — v27 리드 게이트와 공용)

	// v23b: 방어 상황에서는 절대 감속하지 않는다 (에너지 보존).
	//  [실측] v23에서 조준은 극적으로 개선(최소ATA 113->0.8, 51.8->0.3)됐으나
	//    S3(방어) 피격 2.5->18, S4(에너지열세) 피격 6.5->51.5로 악화.
	//    뒤를 물린 채 느려지면 그냥 표적이 된다. 코너속도는 "공세용 회전 자산"이지
	//    방어용이 아니다. 적 기수가 나를 향하면(적ATA 작음) 에너지를 지킨다.
	Vector3 tgtToMe = MyLocation - TargetLocation;
	double t2mLen = tgtToMe.length(); if (t2mLen < 1.0) t2mLen = 1.0;
	tgtToMe = tgtToMe / t2mLen;
	double enemyAtaDeg = std::acos(std::max(-1.0, std::min(1.0, TgtFwd.dot(tgtToMe)))) * 57.2957795;
	bool beingChased = (enemyAtaDeg < 35.0) && (dist < 2500.0);   // 적이 나를 겨누는 중

	// ※ v38(코너속도의 dist<2500 게이트 제거) = **기각**. 되돌렸다.
	//   [실측] 스로틀이 0.998 -> 0.965로만 내려갔고, 직진 상대전 dealt 1.0073 -> **0.0000**.
	//     15시드 합계 58승->57승, 순이득 +30.07 -> +27.42. sync는 3승->1승.
	//   [왜 안 통했나] 게이트를 없애도 **`ataDeg > 12.0` 조건**이 남는다.
	//     직선 추격 중에는 상대를 똑바로 겨누고 있어 ATA가 작으므로
	//     **가속하는 동안에는 감속이 안 걸리고, 돌아야 할 때는 이미 500m/s**다.
	//   [남은 진단] '원거리 풀스로틀이 문제'라는 관찰 자체는 유효하다(실측:
	//     직진 상대전 스로틀 0.98~0.99, 속도 496m/s, 선회반경 28km, 10초에 5.7km 이탈).
	//     다만 **코너속도 로직으로는 못 잡는다** — 그건 '이미 크게 벗어났을 때'용이고,
	//     필요한 건 '벗어나기 전에 속도를 관리하는 것'이다. 별도 기제가 필요하다.
	// [절제 A7] v23b 코너속도. v36에서 "5상대가 소수점까지 동일" = onecircle 상대로만
	//   발동한다는 게 드러났다. 실제로 짐을 지고 있는지 확인한다.
	bool needTurn = !Ablation::off("v23corner")
	                && (dist < 2500.0) && (ataDeg > 12.0)
	                && (mySpd > CORNER + 30.0) && !beingChased;
	float stepUse = 0.008f;                 // 기본 변화율(부드럽게)
	float targetBeforeCorner = target;      // 코너속도 적용 전 값(추적용)
	if (needTurn) DUTY_corner[__ti]++;
	if (needTurn)
	{
		// 코너속도까지 적극 감속. 남은 초과속도에 비례해 스로틀을 내린다(연속).
		double over = (mySpd - CORNER) / 200.0;   // 0.0~1.0+
		if (over > 1.0) over = 1.0;
		double u = 1.0 - over * 0.85;             // 초과 클수록 0.15까지
		if (u < 0.15) u = 0.15;
		if ((float)u < target) { target = (float)u; DUTY_capp[__ti]++; }  // 기존 목표보다 낮을 때만
		stepUse = 0.040f;                          // 전술 기동이므로 빠르게(10Hz에서 0.4/s)
	}
	// ==============================================================================

	// ★ 2026-08-06 스로틀 계통 추적: 명령이 어느 단계에서 사라지는지 본다.
	//  [계기] 스로틀을 세 번 건드렸는데 세 번 다 궤적이 소수점까지 동일했다:
	//    v36 CORNER 260->287 (5상대 동일) / v37 하한 0.55->0.15 (거리 프로필 완전 동일)
	//    -> 우리가 믿는 스로틀 제어가 실제로는 작동하지 않고 있다.
	//  [방법] 상수를 바꿔 결과를 보는 대신, **각 단계의 값을 직접 기록**한다.
	static double THR_dvT[2]={0,0}, THR_u[2]={0,0}, THR_after[2]={0,0}, THR_final[2]={0,0};
	static long long THR_n[2]={0,0};
	static double THR_min[2]={9,9}, THR_max[2]={0,0};
	THR_n[__ti]++;
	THR_dvT[__ti]  += dvTarget > 900.0 ? 999.0 : dvTarget;
	THR_u[__ti]    += targetBeforeCorner;   // 코너속도 적용 **전** 목표
	THR_after[__ti]+= target;               // 코너속도 적용 **후** 목표

	static float lastThr[2] = { 1.0f, 1.0f };
	if (needThrReset[__ti]) { lastThr[__ti] = 1.0f; needThrReset[__ti] = false; }
	float cur = lastThr[__ti];
	// 재가속은 항상 빠르게(에너지 회복이 늦으면 감속이 독이 된다 — 과거 실패의 교훈)
	float stepUp = (stepUse > 0.008f) ? stepUse : 0.030f;
	if (target > cur) { cur += stepUp;  if (cur > target) cur = target; }
	else              { cur -= stepUse; if (cur < target) cur = target; }
	// v33: 관통 임박(lag pursuit)이면 폐쇄율을 죽인다. 조준점만 뒤로 옮겨선 부족하다 —
	//  속도가 그대로면 결국 지나친다. 램프를 타지 않고 즉시 적용하되 상태(lastThr)에는
	//  남겨 조건 해제 시 위 로직이 정상적으로 램프업으로 복귀하게 한다.
	if (lagActive && cur > 0.30f) cur = 0.30f;
	// v45 standoff: 폐쇄율만 낮춘다. v33(0.30)보다 훨씬 약하게 잡는다 — 상대를 놓치면
	//  교전 자체가 성립하지 않아 v33처럼 "위치를 사고 사격을 파는" 실패로 간다.
	//  0.55는 감속은 되되 추격은 유지되는 값으로 잡았고, 배치 결과로 재조정한다.
	if (standoffActive && cur > 0.55f) cur = 0.55f;
	if (standoffActive) DUTY_standoff[__ti]++;
	lastThr[__ti] = cur;
	(*BB)->Throttle = cur;
	THR_final[__ti] += cur;
	if (cur < THR_min[__ti]) THR_min[__ti] = cur;
	if (cur > THR_max[__ti]) THR_max[__ti] = cur;
	if (THR_n[__ti] % 600 == 0)
	{
		double n = (double)THR_n[__ti];
		std::cerr << "[THR] team=" << (*BB)->Team
			<< " dvTarget평균=" << (THR_dvT[__ti]/n)
			<< " 코너전목표=" << (THR_u[__ti]/n)
			<< " 코너후목표=" << (THR_after[__ti]/n)
			<< " 실제스로틀평균=" << (THR_final[__ti]/n)
			<< " 최저=" << THR_min[__ti] << " 최고=" << THR_max[__ti]
			<< std::endl;
	}

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 60 == 0)
		std::cerr << "[ACTIVE] [" << (((*BB)->Team == BLUE) ? "BLUE" : "RED")
			<< "] LeadPredict dist=" << dist << " dV=" << speedMargin << " thr=" << cur
			<< " om=" << omegaNow << " lt=" << leadTime << std::endl;

	// ── DUTY 요약: 10초(600틱)마다 각 기능의 발동률을 낸다 ──
	if (DUTY_tick[__ti] % 600 == 0)
	{
		double n = (double)DUTY_tick[__ti];
		std::cerr << "[DUTY] team=" << (*BB)->Team << " ticks=" << DUTY_tick[__ti]
			<< " v27종말조준=" << (100.0*DUTY_lead[__ti]/n) << "%"
			<< " v21뱅크예측=" << (100.0*DUTY_bank[__ti]/n) << "%"
			<< " v17궤도조건=" << (100.0*DUTY_orbit[__ti]/n) << "%"
			<< " v17슬롯적용=" << (100.0*DUTY_slot[__ti]/n) << "%"
			<< " 상승클램프=" << (100.0*DUTY_clmpU[__ti]/n) << "%"
			<< " 강하클램프=" << (100.0*DUTY_clmpD[__ti]/n) << "%"
			<< " v23b조건=" << (100.0*DUTY_corner[__ti]/n) << "%"
			<< " v23b실제적용=" << (100.0*DUTY_capp[__ti]/n) << "%"
			// [실험 J] 게이트 발동률. 상수만 보고 판정하지 않기 위해 실제 적용 틱을 센다.
			<< " J교란적용=" << (100.0*DUTY_jink[__ti]/n) << "%"
			<< std::endl;
	}

	return NodeStatus::SUCCESS;
}
