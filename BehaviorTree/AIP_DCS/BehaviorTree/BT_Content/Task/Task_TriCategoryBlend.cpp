#include "Task_TriCategoryBlend.h"
#include <algorithm>
#include <cmath>
#include <iostream>

namespace
{
	double Clamp01(double x)
	{
		return x < 0.0 ? 0.0 : (x > 1.0 ? 1.0 : x);
	}

	// 0 at/below lo, 1 at/above hi, smooth (and saturating, not asymptotic) in between.
	double Smoothstep01(double x, double lo, double hi)
	{
		double t = Clamp01((x - lo) / (hi - lo));
		return t * t * (3.0 - 2.0 * t);
	}

	BT_Geometry::Vector3 SafeNormalize(BT_Geometry::Vector3 v, const BT_Geometry::Vector3& fallback)
	{
		if (v.length() < 1e-6)
		{
			v = fallback;
		}
		v.normalize();
		return v;
	}
}

PortsList Action::Task_TriCategoryBlend::providedPorts()
{
	return {
			InputPort<CPPBlackBoard*>("BB")
	};
}

// Survival: reuses Task_ClimbOut's low-altitude recovery direction, mirrored for a new
// high-altitude ceiling response (there is no ceiling anywhere else in the system).
Vector3 Action::Task_TriCategoryBlend::ComputeSurvival(CPPBlackBoard* BB, double& outFloorWeight, double& outCeilingWeight) const
{
	Vector3 MyForward = BB->MyForwardVector;
	MyForward.normalize();
	Vector3 WorldUp(0.0, 0.0, 1.0);

	double myAlt = BB->MyLocation_Cartesian.Z;
	double wFloor = 1.0 - Smoothstep01(myAlt, FLOOR_ALT - FLOOR_RAMP, FLOOR_ALT + FLOOR_RAMP);
	double wCeiling = Smoothstep01(myAlt, CEIL_ALT - CEIL_RAMP, CEIL_ALT + CEIL_RAMP) * CEIL_MAX_WEIGHT;
	outFloorWeight = wFloor;
	outCeilingWeight = wCeiling;

	Vector3 LowAltDir = SafeNormalize(MyForward * 0.3 + WorldUp, MyForward);
	Vector3 HighAltDir = SafeNormalize(MyForward * 0.3 - WorldUp, MyForward);
	return SafeNormalize(LowAltDir * wFloor + HighAltDir * wCeiling, MyForward);
}

// Evasion: continuous rear-threat ramp (Task_Evade's break direction, gated by the same
// angle/range thresholds as DECO_TailThreatCheck) plus the ported Task_BreakAndReverse
// BREAK->REVERSE state machine for close-range threats. The state machine is preserved
// verbatim (not flattened into a formula) because its forced-exit timeout is what
// prevents getting stuck evading forever -- a pure per-tick continuous weight cannot
// express "how long have I already been breaking."
Vector3 Action::Task_TriCategoryBlend::ComputeEvasion(CPPBlackBoard* BB, double& outWeight)
{
	Vector3 MyLocation = BB->MyLocation_Cartesian;
	Vector3 TargetLocation = BB->TargetLocaion_Cartesian;
	Vector3 MyForward = BB->MyForwardVector;
	Vector3 MyRight = BB->MyRightVector;
	Vector3 TargetForward = BB->TargetForwardVector;
	MyForward.normalize();
	TargetForward.normalize();

	double distance = MyLocation.distance(TargetLocation);
	double angleDeg = (TargetLocation - MyLocation).angleBetween(MyForward) * 57.2958;

	double wAngle = Smoothstep01(angleDeg, THREAT_ANGLE - ANGLE_RAMP, THREAT_ANGLE + ANGLE_RAMP);
	double wDist = 1.0 - Smoothstep01(distance, EVADE_RANGE - DIST_RAMP, EVADE_RANGE + DIST_RAMP);
	double wRearThreat = wAngle * wDist;

	Vector3 LOSToTarget = SafeNormalize(TargetLocation - MyLocation, MyForward);
	double turnSign = (MyRight.dot(LOSToTarget) >= 0.0) ? 1.0 : -1.0;
	Vector3 EvadeBreakDirRaw = SafeNormalize(MyRight * turnSign, MyForward);

	// MyRight can point steeply up/down when the aircraft is banked hard, which the
	// original Task_Evade never clamps (it just does MyLocation + BreakDirection*3000).
	// In the discrete tree this rarely mattered because Evade only ever ran briefly
	// before a hard hand-off; here Evasion blends in more often and for longer, so an
	// unclamped near-vertical break direction was observed compounding into a sustained
	// climb the Attack category's near-level VP couldn't recover from afterward. Apply
	// the same distance-proportional climb/dive clamp every other Task already uses.
	Vector3 evadeCandidate = MyLocation + EvadeBreakDirRaw * COMMON_RADIUS;
	double climbSlope = distance * 0.5;
	double diveSlope = distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (evadeCandidate.Z < minZ) evadeCandidate.Z = minZ;
	if (evadeCandidate.Z > maxZ) evadeCandidate.Z = maxZ;
	if (evadeCandidate.Z < 3500.0) evadeCandidate.Z = 3500.0;
	Vector3 EvadeBreakDir = SafeNormalize(evadeCandidate - MyLocation, MyForward);

	if (!_brActive && distance <= BR_TRIGGER_DIST && angleDeg > BR_TRIGGER_ANGLE)
	{
		_brActive = true;
		_brPhase = BRPhase::BREAK;
		_brTicks = 0;
		_brStartDistance = (float)distance;
	}

	Vector3 evasionDir = EvadeBreakDir;
	if (_brActive)
	{
		if (_brPhase == BRPhase::BREAK)
		{
			_brTicks++;
			evasionDir = EvadeBreakDir;

			bool overshoot = ((float)distance > _brStartDistance + 30.0f);
			if ((overshoot && _brTicks >= BR_BREAK_DURATION) || _brTicks >= BR_BREAK_TIMEOUT)
			{
				_brPhase = BRPhase::REVERSE;
			}
		}
		else // REVERSE
		{
			Vector3 redSix = TargetLocation - TargetForward * 800.0;
			evasionDir = SafeNormalize(redSix - MyLocation, MyForward);

			if (angleDeg < BR_EXIT_ANGLE)
			{
				_brActive = false;
			}
		}
	}

	outWeight = Clamp01(_brActive ? 1.0 : wRearThreat);
	return evasionDir;
}

// Attack: verbatim reuse of Task_Engage's continuous Lead<->Tail AA blend.
Vector3 Action::Task_TriCategoryBlend::ComputeAttack(CPPBlackBoard* BB) const
{
	Vector3 MyLocation = BB->MyLocation_Cartesian;
	Vector3 TargetLocation = BB->TargetLocaion_Cartesian;
	Vector3 TargetForward = BB->TargetForwardVector;
	Vector3 MyForward = BB->MyForwardVector;
	TargetForward.normalize();
	MyForward.normalize();

	double distance = MyLocation.distance(TargetLocation);
	double mySpeed = (double)BB->MySpeed_MS;
	if (mySpeed < 1.0) mySpeed = 1.0;

	Vector3 targetVelocity = TargetForward * (double)BB->TargetSpeed_MS;
	double interceptTime = distance / mySpeed;
	if (interceptTime > 8.0) interceptTime = 8.0;
	Vector3 leadPoint = TargetLocation + targetVelocity * interceptTime;

	Vector3 tailPoint = TargetLocation - TargetForward * TAIL_STANDOFF;

	double myAA = (double)BB->MyAspectAngle_Degree;
	double wTail = Smoothstep01(myAA, AA_LOW, AA_HIGH);

	Vector3 attackPoint = leadPoint * (1.0 - wTail) + tailPoint * wTail;

	double climbSlope = distance * 0.5;
	double diveSlope = distance * 0.2;
	double minZ = MyLocation.Z - diveSlope;
	double maxZ = MyLocation.Z + climbSlope;
	if (attackPoint.Z < minZ) attackPoint.Z = minZ;
	if (attackPoint.Z > maxZ) attackPoint.Z = maxZ;
	if (attackPoint.Z < 3500.0) attackPoint.Z = 3500.0;

	return SafeNormalize(attackPoint - MyLocation, MyForward);
}

NodeStatus Action::Task_TriCategoryBlend::tick()
{
	Optional<CPPBlackBoard*> BBOpt = getInput<CPPBlackBoard*>("BB");
	CPPBlackBoard* BB = *BBOpt;

	Vector3 MyLocation = BB->MyLocation_Cartesian;
	Vector3 TargetLocation = BB->TargetLocaion_Cartesian;
	Vector3 MyForward = BB->MyForwardVector;
	MyForward.normalize();

	double wFloor = 0.0, wCeiling = 0.0;
	Vector3 survivalDir = ComputeSurvival(BB, wFloor, wCeiling);

	double aEvasion = 0.0;
	Vector3 evasionDir = ComputeEvasion(BB, aEvasion);

	Vector3 attackDir = ComputeAttack(BB);

	// Snap-to-Attack: a clean WEZ + low-AA shot overrides Ceiling only (never Floor
	// safety, never Evasion) so Attack gets undiluted precision aim right when it
	// matters most. See header comment for why this was necessary.
	double distance = MyLocation.distance(TargetLocation);
	double myAA = (double)BB->MyAspectAngle_Degree;
	double wSnapDist = 1.0 - Smoothstep01(distance, SNAP_DIST - SNAP_DIST_RAMP, SNAP_DIST + SNAP_DIST_RAMP);
	double wSnapAA = 1.0 - Smoothstep01(myAA, SNAP_AA - SNAP_AA_RAMP, SNAP_AA + SNAP_AA_RAMP);
	double wSnap = wSnapDist * wSnapAA * (1.0 - wFloor);
	wCeiling *= (1.0 - wSnap);

	double aSurvival = Clamp01(wFloor + wCeiling);

	// "Over" compositing, matching the old ReactiveFallback's priority order
	// (Survival > Evasion > Attack) so weights always sum to exactly 1 and a fully
	// active higher-priority category is never diluted by a lower one.
	double wSurvival = aSurvival;
	double wEvasion = aEvasion * (1.0 - aSurvival);
	double wAttack = (1.0 - aSurvival) * (1.0 - aEvasion);

	Vector3 blendedDir = SafeNormalize(
		survivalDir * wSurvival + evasionDir * wEvasion + attackDir * wAttack,
		MyForward);

	Vector3 VP = MyLocation + blendedDir * COMMON_RADIUS;
	if (VP.Z < 3500.0) VP.Z = 3500.0;
	BB->VP_Cartesian = VP;

	static int __dbg[2] = { 0, 0 };
	int __t = (BB->Team == BLUE) ? 0 : 1;
	if (++__dbg[__t] % 30 == 0)
	{
		std::cerr << "[ACTIVE] [" << (BB->Team == BLUE ? "BLUE" : "RED")
			<< "] TriBlend wS=" << wSurvival << " wE=" << wEvasion << " wA=" << wAttack
			<< " Z=" << MyLocation.Z << " VPZ=" << VP.Z << std::endl;
	}

	return NodeStatus::SUCCESS;
}
