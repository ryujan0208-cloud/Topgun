# CODEX CV02 randomized corpus and action telemetry - 2026-08-08

## Status

Research-only. No submission BT, production DLL, or Rule XML was changed.
All global VP override candidates remain rejected.

This directory is a compact, tracked index over raw cases retained below
the ignored `artifacts/state_policy/forks/` tree.

## Corpus

`baseline_manifest.csv` contains 16 genuinely distinct randomized starts:

- ACE: 8 starts, net HP range -0.010130 to +0.171094;
- SEARCH: 5 starts, net HP range +0.021427 to +0.497543;
- AIP_kwon: 3 starts, net HP range 0 to +1.000278.

All 16 ownship/target track-hash pairs are unique.

`baseline_events.csv` contains 56 HP-damage events, regenerated from raw
tracks with signed body-frame LOS azimuth, elevation, their rates, and the
lift-vector relation. ACE has 34 dealt and 2 taken events. SEARCH has 13
dealt events; Kwon has 7. SEARCH and Kwon remain under-sampled: their
largest single start contributes about 50% of total dealt HP.

## Predeclared fork decision

The 37 matched-prefix outcomes all pass exact pre-fork identity. A candidate
must improve net HP at 3, 5, and 10 seconds and at fight end. Final score alone
is not evidence because a short override can redirect the later trajectory.

Only three rows pass all four horizons; none generalizes across an opponent
holdout or several genuinely distinct starts.

The passing rows are two `pure` forks on one fixed ACE trajectory and one
`up 500 m` fork of only one-second duration on randomized ACE seed 1. The
latter fails at adjacent durations and offsets, so it is a timing resonance,
not a stable state rule. Median 5/10-second net delta is negative for every
candidate family. Global `pure`, `lead`, `up`, and `down` are rejected.

## Why state-only thresholds are still insufficient

The successful fixed-start `pure` scene at 178.60 s and the failed randomized
seed-2 scene at 192.78 s have nearly identical ownship LOS geometry:

| Scene | ATA | LOS az | LOS el | az rate | el rate |
|---|---:|---:|---:|---:|---:|
| fixed success | 38.86 | -3.93 | 38.69 | +2.78 | -10.92 |
| seed-2 failure | 39.19 | -4.20 | 39.00 | +2.38 | -10.74 |

The cases were replayed with identical DLL and Rule hashes while recording
the native BT VP and requested VP at each real 10 Hz update. In the success
case, `pure` initially requested about 6 m above the BT VP. In the failure
case it requested about 73 m below the BT VP, growing to about 94 m below.
It also reduced median rudder from 0.778 to 0.567 and removed the baseline
0.007045 HP shot.

Therefore the next policy representation should be a residual decision over
the current BT intent, not an absolute state-to-maneuver lookup. Candidate
triggers must include the proposed action difference (BT VP versus candidate
VP), recent command history, vertical/energy state, floor margin, and phase.
No threshold may be fitted until it survives held-out starts and opponents.

The telemetry recorder is observational: it wraps the existing provider
outside the native BT and before the unchanged 6-tick command hold. Production
DLL behavior is untouched.

The archived lab DLL and Rule are byte-identical to CV01. Their unchanged C++
and binding sources remain in the CV01 archive; CV02 snapshots only the tools
and tests changed for this milestone.

## Compact artifact hashes

- `baseline_manifest.csv`: `F108190A0AC92D7466BA8CA505E79C8407A0BC5EEABBDC7BBEFB12E2E4B75BFB`
- `baseline_events.csv`: `3D49215A5CE649BE420E680D5400107F7C3ED10593D12DB3A94AF5EC9F83A24A`
- `fork_outcomes.csv`: `1345EFFCA0558FA9A3C85C7C4AB892DF11BC26297AC8D49CBE9F1876C1CAAD9C`
- `candidate_summary.csv`: `A8F50396DA9A58C7773F84DCCE3E94084302D8225EBDFAF354ACFDD202653915`
- `action_telemetry_comparison.csv`: `B12C936906758E6A6D42011AC36E4BDD24339C75A509DC427428C3F4E77CF824`
