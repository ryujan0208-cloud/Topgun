#include "Task_Engage.h"
#include <algorithm>
#include <iostream>

PortsList Action::Task_Engage::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

NodeStatus Action::Task_Engage::tick()
{
	Optional<CPPBlackBoard*> BB = getInput<CPPBlackBoard*>("BB");

	Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
	Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
	Vector3 TargetForward  = (*BB)->TargetForwardVector;
	TargetForward.normalize();

	double Distance = MyLocation.distance(TargetLocation);
	double MySpeed = (*BB)->MySpeed_MS;
	if (MySpeed < 1.0)
	{
		MySpeed = 1.0;
	}

	// LeadPoint: same formula as Task_Lead/Task_Pure (lead shot point)
	Vector3 TargetVelocity = TargetForward * (double)(*BB)->TargetSpeed_MS;
	double InterceptTime = Distance / MySpeed;
	if (InterceptTime > 8.0) InterceptTime = 8.0;
	Vector3 LeadPoint = TargetLocation + TargetVelocity * InterceptTime;

	// TailPoint: same formula as Task_GetTail (aim at target's 6 o'clock)
	Vector3 TailPoint = TargetLocation - TargetForward * TailStandoff;

	// Blend by Aspect Angle (AA): AA<=30 -> pure LeadPoint, AA>=90 -> pure TailPoint,
	// smoothstep in between so the aim point never jumps at a hard boundary.
	double MyAA_deg = (double)(*BB)->MyAspectAngle_Degree;
	double w = (MyAA_deg - AA_BlendLow) / (AA_BlendHigh - AA_BlendLow);
	if (w < 0.0) w = 0.0;
	if (w > 1.0) w = 1.0;
	w = w * w * (3.0 - 2.0 * w); // smoothstep

	Vector3 VP = LeadPoint * (1.0 - w) + TailPoint * w;

	// Altitude clamp pursuit, same policy as the other tasks: generous climb
	// allowance (~26.5 deg), conservative dive allowance (~11 deg), floor above
	// the ClimbOut trigger altitude (3000m) to keep recovery margin.
	double climbSlope = Distance * 0.5;
	double diveSlope = Distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (VP.Z < minZ) VP.Z = minZ;
	if (VP.Z > maxZ) VP.Z = maxZ;
	if (VP.Z < 3500.0) VP.Z = 3500.0;

	(*BB)->VP_Cartesian = VP;

	static int __dbg[2] = { 0, 0 };
	int __t = ((*BB)->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] Engage AA=" << MyAA_deg << " w=" << w << " Dist=" << Distance << " Z=" << MyLocation.Z << std::endl;

	return NodeStatus::SUCCESS;
}
