#include "Task_LoopAttack.h"
#include <cmath>
#include <algorithm>
#include <iostream>

using namespace BT_Geometry;

PortsList Action::Task_LoopAttack::providedPorts()
{
    return { InputPort<CPPBlackBoard*>("BB") };
}

NodeStatus Action::Task_LoopAttack::onStart()
{
    auto BB = getInput<CPPBlackBoard*>("BB");

    Vector3 MyLoc  = (*BB)->MyLocation_Cartesian;
    Vector3 TgtLoc = (*BB)->TargetLocaion_Cartesian;
    Vector3 MyFwd  = (*BB)->MyForwardVector;

    double dist = MyLoc.distance(TgtLoc);

    // 거리 800~1800m, 고도 3000m 이상일 때만 루프 공격 진입
    if (dist < 800.0 || dist > 1800.0 || MyLoc.Z < 3000.0)
        return NodeStatus::FAILURE;

    // 적이 전방 70° 이내일 때만 (공격 포지션)
    Vector3 los = TgtLoc - MyLoc;
    los.normalize();
    double dot = std::max(-1.0, std::min(1.0, MyFwd.dot(los)));
    float ata = (float)(std::acos(dot) * 57.2958f);
    if (ata > 70.0f)
        return NodeStatus::FAILURE;

    _phase    = Phase::PULLUP;
    _ticks    = 0;
    _startAlt = (float)MyLoc.Z;
    return NodeStatus::RUNNING;
}

NodeStatus Action::Task_LoopAttack::onRunning()
{
    auto BB = getInput<CPPBlackBoard*>("BB");

    Vector3 MyLocation     = (*BB)->MyLocation_Cartesian;
    Vector3 TargetLocation = (*BB)->TargetLocaion_Cartesian;
    float   upZ            = (float)(*BB)->MyUpVector.Z;

    _ticks++;

    // Safety exits
    if (_ticks > 540)          return NodeStatus::SUCCESS; // 9s hard limit
    if (MyLocation.Z < 1400.0f) return NodeStatus::SUCCESS; // altitude floor

    if (_phase == Phase::PULLUP)
    {
        // VP를 시작 고도 기준 고정값으로 설정 (동적 갱신 시 무한 상승 방지)
        Vector3 VP = MyLocation;
        VP.Z = _startAlt + 6000.0f;
        (*BB)->VP_Cartesian = VP;

        static int __dbg1[2] = { 0, 0 };
        int __t1 = ((*BB)->Team == BLUE) ? 0 : 1;
        if (++__dbg1[__t1] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] LoopAttack-PULLUP Z=" << MyLocation.Z << std::endl;

        // Inverted AND at least 2s of pullup AND climbed 300m
        if (upZ < -0.3f && _ticks >= PULLUP_MIN_TICKS
            && MyLocation.Z > _startAlt + 300.0f)
        {
            _phase = Phase::DIVE;
        }
    }
    else // DIVE: aim nose at Red below
    {
        // VP = Red's position. Since Red is below and ahead (inverted):
        // LOS < 90 -> normal law -> pull back -> nose toward ground -> toward Red
        (*BB)->VP_Cartesian = TargetLocation;

        static int __dbg2[2] = { 0, 0 };
        int __t2 = ((*BB)->Team == BLUE) ? 0 : 1;
        if (++__dbg2[__t2] % 30 == 0) std::cerr << "[ACTIVE] [" << ((*BB)->Team == BLUE ? "BLUE" : "RED") << "] LoopAttack-DIVE Z=" << MyLocation.Z << std::endl;

        // Exit: loop complete (back upright, below start alt)
        if (upZ > 0.7f && MyLocation.Z < _startAlt - 200.0f)
            return NodeStatus::SUCCESS;

        // Collision avoidance
        float dist = (float)MyLocation.distance(TargetLocation);
        if (dist < 200.0f)
            return NodeStatus::SUCCESS;
    }

    return NodeStatus::RUNNING;
}

void Action::Task_LoopAttack::onHalted()
{
    _phase    = Phase::PULLUP;
    _ticks    = 0;
    _startAlt = 0.0f;
}
