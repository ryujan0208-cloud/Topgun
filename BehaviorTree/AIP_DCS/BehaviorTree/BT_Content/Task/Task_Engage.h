#pragma once
// Continuous blend of GetTail (tail-chase) and Lead/Pure (direct aim).
// Previously the tree hard-switched between GetTail and Lead/Pure at AA=60 deg,
// causing the aim point (VP) to jump discontinuously at that boundary.
// This task treats AA as a continuous value and smoothly blends LeadPoint and
// TailPoint (smoothstep) to remove that discontinuity. 2026-07-03.
#include "../../behaviortree_cpp_v3\action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../Functions.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_Engage : public SyncActionNode
	{
	private:
		static constexpr double TailStandoff = 500.0;
		static constexpr double AA_BlendLow = 30.0;   // AA<=30: fully LeadPoint (direct aim)
		static constexpr double AA_BlendHigh = 90.0;  // AA>=90: fully TailPoint (tail chase)

	public:

		Task_Engage(const std::string& name, const NodeConfiguration& config) : SyncActionNode(name, config)
		{
		}

		~Task_Engage()
		{

		}

		static PortsList providedPorts();

		NodeStatus tick() override;
	};
}
