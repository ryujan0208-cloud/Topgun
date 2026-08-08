# CODEX CV03 BT-intent residual experiment - 2026-08-08

## Status

Research-only. The normal `Step` path of the residual lab DLL produced
byte-identical 200-second ownship and target tracks versus the CV02 lab DLL.
No production policy or Rule XML is changed.

## E1 predeclared prediction

Scene: ACE randomized seed 2, fork 192.78 s, duration 3 s, vertical residual
50 m. CV02 showed that failed `pure` was equivalent to requesting 73--94 m
below the native BT VP and removed the baseline 0.007045 HP shot.

- `bt_down`: predict negative local net delta at 3/5/10 s.
- `bt_up`: predict non-negative local net delta at 3/5/10 s.
- Final score is diagnostic only and cannot reverse the local decision.

This one paired scene can test the mechanism sign, not justify a BT trigger.

## E1 result and E2 predeclared prediction

Both E1 candidates were locally negative: down 50 m lost 0.007045 HP and up
50 m lost 0.002691 HP at every 3/5/10-second horizon. Direction ordering was
correct, but the predicted non-negative up result failed. This suggests the
native BT VP is already near a local aiming optimum in this shot window.

E2 repeats the same matched prefix at plus/minus 10 m. Before viewing results:

- both deltas are predicted non-positive;
- each absolute loss must be no larger than its same-sign 50 m loss;
- down is predicted no better than up.

## E2 result and E3 cross-scene prediction

E2 down 10 m was -0.000845 HP, but up 10 m was +0.000400 HP at all local
horizons. The predicted scale ordering and down-below-up ordering held; the
prediction that both signs were non-positive failed. The local response is
nonlinear: a small positive residual helped, while plus 50 m hurt.

Do not optimize more offsets on that same scene. E3 instead checks the fixed
ACE scene at 178.60 s, where successful `pure` initially lay about 6 m above
the BT VP. Before E3 results:

- `bt_up` 10 m is predicted non-negative at 3/5/10 s;
- `bt_down` 10 m is predicted no better than `bt_up`;
- neither result is a trigger-adoption sample because both scenes were used
  to formulate the residual hypothesis.

## E3 result and E4 held-start prediction

At fixed 178.60 s, down 10 m was +0.000669 HP through 10 s while up 10 m
was -0.001603 HP. Both E3 sign predictions failed. Down later reversed to
-0.000724 HP at 20 s/fight end, so it is not a candidate rule.

The two development scenes suggest an exploratory sign feature: high ownship
climb rate favored down; low climb rate favored up. E4 freezes the following
selection from CV02 before running residual forks:

- common filter: ACE dealt event, 2 s pre-event history, range 800--1300 m,
  ATA 25--55 deg, absolute LOS azimuth <=12 deg, LOS elevation 25--55 deg,
  baseline event damage >=0.01 HP;
- high-climb case: first unused seed/time with own vertical speed >=80 m/s,
  yielding random seed 3 at 146.0833 s;
- low-climb case: first later unused seed/time with own vertical speed from
  0 through 40 m/s, yielding random seed 4 at 154.8 s.

For each case, compare `bt_up` and `bt_down` at 10 m for 3 s. Predictions:

- seed 3 high-climb: down is non-negative locally and better than up;
- seed 4 low-climb: up is non-negative locally and better than down;
- success requires the ordering at 3/5/10 s; final score remains diagnostic.

Failure rejects this one-feature sign model. Success would only justify more
held-start tests, not policy adoption.

## E4 result and E5 unseen-seed gate

High-climb seed 3 passed the local ordering/value prediction: down was
+0.001295 HP and up was -0.004625 HP through 10 s. Low-climb seed 4 preserved
the ranking (up -0.001479 versus down -0.002303) but failed the required
non-negative up value. The low-climb up action is rejected.

Final score again contradicted local evidence: the harmful seed-3 up ended
+0.001284 and the worse seed-4 down ended +0.002949. Those are trajectory
effects, not action-value evidence.

E5 tests only the provisional high-climb down ranking on untouched ACE random
seeds 9--15. Scan seeds in ascending order and time in ascending order using
the frozen E4 common filter, event damage >=0.01 HP, and own vertical speed
>=80 m/s. Stop at the first matching event without viewing any fork outcome.

At that event run down/up 10 m for 3 s. E5 passes only if down is strictly
positive and greater than up at 3/5/10 s, with non-negative final delta. If no
event matches, report insufficient support rather than relaxing the filter.
One pass remains research evidence only; adoption still requires the full
15-start/opponent gate.

## E5 result and decision

Seeds 9 and 10 had no matching event; the filter was not relaxed. The first
match was seed 11 at 163.8666 s: baseline event 0.014451 HP, own vertical speed
95.37 m/s, range 806.27 m, and ATA 31.09 deg.

Down 10 m beat up 10 m at every local horizon: +0.006505 versus -0.005103 HP.
This independently reproduced the high-climb short-horizon ranking. However,
down ended -0.026546 HP and up ended -0.039332 HP. The required non-negative
final delta failed.

Reject the current 3-second vertical-residual candidate. High climb may be a
useful feature for ranking a brief aiming correction, but it is not an
eligibility trigger and does not justify changing the combat BT. Do not tune
duration on seed 11 after seeing this result; any transient-residual study must
be predeclared on new starts.

## Build and provenance

- residual lab DLL SHA-256: `DA8403DB6C598883FCBB51F0250A22AFFB68EE59BE0B687D18B880ED13EFAE5A`;
- Rule SHA-256: `1760A7E3EA9A50D38243F276983FCD393F5ED2067AB5FD7344ED2FCA8AC153E3`;
- exports: `Step`, `StepWithVPOverride`, and `StepWithVPResidual`;
- normal-path ownship track: `DF61EDD0F14DC13B36A18FF3E1B8FBC594DB2F371F0EE77EC572C456B6075D8E`;
- normal-path target track: `C027AE5C0CC30620D4CB3ABEF443532F22AD9446AE0E63DB4BF8F8AA1DFBC664`.

Both normal-path hashes are byte-identical to the CV02 lab DLL baseline.

Compact artifact hashes:

- `residual_outcomes.csv`: `431692CA80C4E521659E88883F06CB89CB2E7F12FE62469CA980A2A106D27EE7`;
- `e5_baseline_scan.csv`: `D138A1C274B76A15FBBE59934820F0F57A518E2FB21924C6B2A39959762DC6CF`.

Raw paired tracks, action telemetry, manifests, stdout, and stderr remain under
the ignored `artifacts/state_policy/forks/CV021...CV027` directories.

## Validation

- Visual Studio Release x64 build succeeded; emitted warnings were pre-existing
  code-page/narrowing warnings, with no compile or link error.
- `dumpbin` confirmed all three Step exports.
- A 10-update smoke fork recorded requested VP minus BT VP as exactly +50 m.
- Legacy CV02 DLL loads with residual export absent; CV03 DLL loads with it
  present.
- Ruff passed and all 25 diagnostic unit tests passed.
- `aircraft/f16/f16_init.xml` remained valid after every batch.
