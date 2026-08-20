#include "../Ablation.h"
#include "DECO_AltitudeCheck.h"
#include <cmath>

namespace Action
{
	PortsList DECO_AltitudeCheck::providedPorts()
	{
		return {
			InputPort<CPPBlackBoard*>("BB"),
			InputPort<std::string>("MinAlt")
		};
	}

	// Returns SUCCESS when altitude(m) < MinAlt -> triggers recovery
	NodeStatus DECO_AltitudeCheck::tick()
	{
		Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");
		Optional<std::string> MinAltStr = getInput<std::string>("MinAlt");

		float CurrentAlt = (float)(*BB)->MyLocation_Cartesian.Z;
		float InputMinAlt = std::stof(MinAltStr.value());

		// v22c: predictive altitude guard. A plain altitude line (1800) is too late
		//  in a steep dive (seed11: pitch -79deg, hit 1800 at pitch -88deg and lost
		//  1461m more to 300m floor). Trigger on predicted altitude 5s ahead using
		//  vertical speed. In level flight (zdot~0) this equals the old behavior, so
		//  no interference with engagement (one-directional safety).
		double pitchRad = (*BB)->MyRotation_EDegree.Pitch * 3.14159265358979 / 180.0;
		double zdot = (double)(*BB)->MySpeed_MS * std::sin(pitchRad);   // negative = descending
		// ★★ 2026-08-19 "divebait" — 예측 선행시간을 5.0s -> 1.5s로 줄인다(절제 플래그, 기본 꺼짐).
		//  [왜] 실효 하한 = MinAlt + (선행시간)x(하강률) 이다. 급하강일수록 실효 하한이 올라간다:
		//    250m/s 60도 강하  -> 700 + 1083 = 1783m
		//    300m/s 60도 강하  -> 700 + 1299 = 1999m  (yuno 하한 1800보다 **높다**)
		//  즉 "상대 고도하한을 착취하려고 급하강"하면 **우리가 먼저 기수를 채올린다.**
		//  선행시간을 1.5s로 줄이면 250m/s 60도에서 실효 하한이 1783 -> 1025m가 되어
		//  yuno(1800) / TW(3000)보다 확실히 아래로 갈 수 있다.
		//  [우리 하한이 전원 중 최저다] 우리 700 / jung·jh2 800 / yuno 1800 / TW 3000 (XML 실측).
		//  ⚠ 예측 항 자체는 없애지 않는다. v22c가 실제 추락(1800m에서 걸린 뒤 1461m 더 손실)
		//    때문에 넣은 것이다. 줄이되 남긴다. 그리고 절대 하한(예측 무시)을 함께 둔다.
		//  ⚠ 규정상 고도 300m 미만은 즉시 패배다. **추락 1건이라도 나면 즉시 기각.**
		double lookAhead = Ablation::sel("divebait") ? 1.5 : 5.0;
		double predAlt = (double)CurrentAlt + zdot * lookAhead;
		// divebait일 때의 절대 안전망: 예측을 무시하고 550m는 무조건 지킨다.
		if (Ablation::sel("divebait") && CurrentAlt < 550.0)
			return NodeStatus::SUCCESS;

		if (CurrentAlt < InputMinAlt || predAlt < (double)InputMinAlt)
		{
			return NodeStatus::SUCCESS;
		}
		else
		{
			return NodeStatus::FAILURE;
		}
	}
}
