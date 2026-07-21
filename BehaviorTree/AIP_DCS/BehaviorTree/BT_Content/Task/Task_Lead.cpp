#include "Task_Lead.h"
#include <iostream>

PortsList Action::Task_Lead::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Lead::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TargetForward = (*BB)->TargetForwardVector;

	TargetForward.normalize();
	Vector3 TargetVelocity = TargetForward * (double)(*BB)->TargetSpeed_MS;

	double Distance = MyLocation.distance(TargetLocation);
	double MySpeed = (*BB)->MySpeed_MS;
	if (MySpeed < 1.0)
	{
		MySpeed = 1.0;
	}

	double InterceptTime = Distance / MySpeed;
	// 너무 먼 거리/저속 상황에서 리드포인트가 과도하게 튀는 것을 방지
	// (2026-07-10 시도, 원복됨: 캡을 8.0->2.0으로 줄였더니 [LEAD_DIAG] 텔레메트리
	// 기준 Task_Lead 자체의 리드각오프셋은 크게 개선됐으나(median 134도->17도),
	// WEZ 진입 후 Task_Pure의 실제 ATA는 거의 그대로였고(mean 115.7도, 3785개 중
	// 3도 이하 0건 여전) 20시드 배치에서 Rule_Trinity에 패배가 1건 재발(0->1)해서
	// 즉시 원복함.
	// (2026-07-12 재시도, 다시 원복됨: 2026-07-11 AA 부호반전 버그 수정판 위에서
	// 캡 2.0을 재검증. Rule_Trinity 패배 재발은 없었으나(-77.73->-76.78, 사실상
	// 동일) Rule_BFMSelect가 -88.54->-108.13으로 뚜렷하게 악화(20시드, 패배는
	// 0/0/20 유지). 순이익 없음으로 판단해 8.0으로 재원복. 결론: AA 버그와
	// 무관하게 Task_Lead의 리드 계산은 병목이 아님이 재확인됨.
	// [[session-2026-07-11-aip-dogfight-aa-bug]], [[session-2026-07-12]] 참고.)
	if (InterceptTime > 8.0)
	{
		InterceptTime = 8.0;
	}

	// 강하각 클램프 pursuit: VP.Z를 자기 고도로 고정(flat)하면 컨트롤러가 절대 못 내려오므로
	// 타겟 고도를 따라가되 급강하/급상승은 각도로 제한한다.
	// 상승(회복 여유 충분)은 관대하게(~26.5도), 강하는 보수적으로(~11도) 비대칭 클램프.
	// 롤 비대칭 버그 수정 후 강하가 너무 효율적이 되어 회복 여유 없이 MinAlt를 뚫고 추락하는
	// 사고가 발생해서, 강하 쪽만 좁히고 바닥도 ClimbOut 트리거(3000m)보다 위로 올려둔다.
	Vector3 LeadPoint = TargetLocation + TargetVelocity * InterceptTime;
	double climbSlope = Distance * 0.5;
	double diveSlope = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (LeadPoint.Z < minZ) LeadPoint.Z = minZ;
	if (LeadPoint.Z > maxZ) LeadPoint.Z = maxZ;
	if (LeadPoint.Z < 3500.0) LeadPoint.Z = 3500.0;

	(*BB)->VP_Cartesian = LeadPoint;

	// 2026-07-09: Task_Pure에서 검증된 속도차 기반 스로틀 제어(속도차>20m/s ->
	// throttle 0.7)를 이 원거리 접근 태스크에도 적용해봤으나, 20시드 배치에서
	// mean -99.06 -> -115.05로 뚜렷한 악화(패배 재발은 없었음) 확인되어 원복함.
	// 결론: 폐쇄율 관리는 WEZ 근접 단계(Task_Pure)에서만 유효하고, 원거리
	// 접근 단계에서 미리 감속하는 건 오히려 접근 자체의 에너지/시간을 낭비해서
	// 손해 -- Task_Pure만 스로틀을 건드리고 Task_Lead는 항상 최대 유지가 맞음.
	// [[session-2026-07-09-aip-dogfight-ata-vs-aa]] 후속5/6 참고.

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] Lead Z=" << MyLocation.Z << " VPZ=" << LeadPoint.Z << std::endl;

	// 2026-07-10 진단: 914m WEZ 경계 부근에서 Task_Lead의 리드 오프셋이 Task_Pure로의
	// 전환 시 얼마나 큰 VP 불연속을 만드는지 확인. Distance<1500일 때만 30틱마다 출력.
	if (Distance < 1500.0)
	{
		double leadOffsetMag = (TargetVelocity * InterceptTime).length();
		Vector3 LeadDir = LeadPoint - MyLocation;
		Vector3 TargetDir = TargetLocation - MyLocation;
		LeadDir.normalize();
		TargetDir.normalize();
		double leadAngleOffsetDeg = LeadDir.angleBetween(TargetDir) * 57.2958;

		static int __diagCount[2] = { 0, 0 };
		if (++__diagCount[__t] % 30 == 0)
		{
			std::cerr << "[LEAD_DIAG] team=" << (*BB)->Team
				<< " dist=" << Distance
				<< " interceptT=" << InterceptTime
				<< " leadOffsetMag=" << leadOffsetMag
				<< " leadAngleOffsetDeg=" << leadAngleOffsetDeg
				<< std::endl;
		}
	}

	return NodeStatus::SUCCESS;
}
