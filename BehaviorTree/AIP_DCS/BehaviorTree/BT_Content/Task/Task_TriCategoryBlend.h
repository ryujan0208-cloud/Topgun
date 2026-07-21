#pragma once
// Continuous blend of 3 top-level behavior categories: Survival, Evasion, Attack.
// Each category produces a unit direction (from MyLocation) and a continuous weight
// in [0,1] every tick; the final VP_Cartesian is a weighted blend of the 3 directions
// placed at a common radius. This replaces the discrete ReactiveFallback priority list
// (Rule_Trinity.xml) with a single leaf node so there is no hard branch switching.
// This is an ADDITIVE experiment: Rule_Trinity.xml / its DLL behavior are untouched;
// this node is only wired into Rule_Trinity_TriBlend.xml. 2026-07-05.
//
// NOTE: keep all comments in this file in English. A prior new Task file with Korean
// comments failed to compile ("AA": undeclared identifier) due to an encoding issue
// when the compiler read the file as CP949 instead of UTF-8.
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_TriCategoryBlend : public SyncActionNode
	{
	private:
		// Survival: floor matches existing DECO_AltitudeCheck MinAlt=3000; ceiling is new
		// (no ceiling exists anywhere else in the system today). Planes spawn around
		// 7000m and healthy engagements range roughly 3500-9000m, so the ceiling must
		// sit above that whole band -- it should only catch the runaway-climb anomaly
		// (observed reaching 9000-11000m+) not normal high-altitude maneuvering.
		static constexpr double FLOOR_ALT = 3000.0;
		static constexpr double FLOOR_RAMP = 500.0;
		static constexpr double CEIL_ALT = 9500.0;
		static constexpr double CEIL_RAMP = 500.0;
		// Floor can still reach full weight (a low-altitude crash is catastrophic and
		// must fully override). Ceiling is capped well below 1.0: a full-weight ceiling
		// response was observed causing a large-amplitude climb/dive oscillation
		// (~5500-14600m, ~140s period) because Controller_CY cannot command an active
		// nose-down pitch -- it can only reach a lower altitude via an inverted roll+pull,
		// which tends to overshoot back into a climb once it rolls upright again. Capping
		// the ceiling's influence keeps some Attack pull-toward-target active at all times
		// so the aircraft never gets fully committed to that overshoot-prone maneuver.
		static constexpr double CEIL_MAX_WEIGHT = 0.4;

		// Evasion: angle/range ramps centered on the existing proven DECO_TailThreatCheck
		// thresholds (150 deg) and the 3000m range gate that prevents endless flee-away.
		static constexpr double THREAT_ANGLE = 150.0;
		static constexpr double ANGLE_RAMP = 15.0;
		static constexpr double EVADE_RANGE = 3000.0;
		static constexpr double DIST_RAMP = 300.0;

		// BreakAndReverse FSM, ported from Task_BreakAndReverse (same thresholds).
		enum class BRPhase { BREAK, REVERSE };
		bool    _brActive = false;
		BRPhase _brPhase = BRPhase::BREAK;
		int     _brTicks = 0;
		float   _brStartDistance = -1.0f;
		static const int BR_BREAK_DURATION = 90;
		static const int BR_BREAK_TIMEOUT = 300;
		static constexpr double BR_TRIGGER_DIST = 900.0;
		static constexpr double BR_TRIGGER_ANGLE = 140.0;
		static constexpr double BR_EXIT_ANGLE = 90.0;

		// Attack: same constants as Task_Engage's Lead/Tail AA blend.
		static constexpr double AA_LOW = 30.0;
		static constexpr double AA_HIGH = 90.0;
		static constexpr double TAIL_STANDOFF = 500.0;

		// Snap-to-Attack: when already in the WEZ with a good aspect angle, force the
		// Ceiling contribution to zero so Attack gets undiluted precision aim. Added
		// after measuring that damage requires ATA<=1 deg, and any Ceiling weight above
		// zero was enough to keep own_ata from ever reaching that threshold during a
		// real merge (observed merges happening above CEIL_ALT, where Ceiling was
		// permanently capped at CEIL_MAX_WEIGHT, capping Attack at 1-CEIL_MAX_WEIGHT).
		// Floor safety and Evasion are NOT overridden by this -- only Ceiling is, since
		// Ceiling (wasted altitude) is far less costly to override than crashing or
		// missing a real rear threat.
		static constexpr double SNAP_DIST = 914.4;    // WEZ_MAX
		static constexpr double SNAP_DIST_RAMP = 100.0;
		static constexpr double SNAP_AA = 20.0;
		static constexpr double SNAP_AA_RAMP = 10.0;

		// Shared placement radius for the final blended VP.
		static constexpr double COMMON_RADIUS = 3000.0;

		Vector3 ComputeSurvival(class CPPBlackBoard* BB, double& outFloorWeight, double& outCeilingWeight) const;
		Vector3 ComputeEvasion(class CPPBlackBoard* BB, double& outWeight);
		Vector3 ComputeAttack(class CPPBlackBoard* BB) const;

	public:

		Task_TriCategoryBlend(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_TriCategoryBlend()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
