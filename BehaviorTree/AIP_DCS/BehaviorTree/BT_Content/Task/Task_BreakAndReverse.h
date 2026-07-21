#pragma once
#include "../../behaviortree_cpp_v3/action_node.h"
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../../Geometry/Vector3.h"
#include "../BlackBoard/CPPBlackBoard.h"

using namespace BT;

namespace Action
{
	class Task_BreakAndReverse : public StatefulActionNode
	{
	private:
		enum class Phase { BREAK, REVERSE };
		Phase  _phase;
		int    _breakTicks;
		float  _prevDistance;
		float  _breakStartDistance;
		static const int BREAK_DURATION = 90;  // ~1.5s at 60Hz
		static const int BREAK_TIMEOUT  = 300; // ~5s at 60Hz, hard safety valve

	public:
		Task_BreakAndReverse(const std::string& name, const NodeConfiguration& config)
			: StatefulActionNode(name, config),
			  _phase(Phase::BREAK), _breakTicks(0), _prevDistance(-1.0f), _breakStartDistance(-1.0f) {}

		~Task_BreakAndReverse() {}

		static PortsList providedPorts();

		NodeStatus onStart()   override;
		NodeStatus onRunning() override;
		void       onHalted()  override;
	};
}
