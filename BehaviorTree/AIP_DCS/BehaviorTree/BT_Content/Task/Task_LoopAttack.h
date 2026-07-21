#pragma once
#include "../../behaviortree_cpp_v3/bt_factory.h"
#include "../../behaviortree_cpp_v3/action_node.h"
#include "../BlackBoard/CPPBlackBoard.h"
#include "../../../Geometry/Vector3.h"

using namespace BT;

namespace Action {

    class Task_LoopAttack : public StatefulActionNode {
    private:
        enum class Phase { PULLUP, DIVE };
        Phase _phase;
        int   _ticks;
        float _startAlt;
        static const int PULLUP_MIN_TICKS = 120; // 2s minimum pullup

    public:
        Task_LoopAttack(const std::string& name, const NodeConfiguration& config)
            : StatefulActionNode(name, config),
              _phase(Phase::PULLUP), _ticks(0), _startAlt(0.0f) {}

        static PortsList providedPorts();
        NodeStatus onStart()   override;
        NodeStatus onRunning() override;
        void       onHalted()  override;
    };

} // namespace Action
