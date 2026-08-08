# CODEX CV04 transient BT-residual experiment - 2026-08-08

## Status before results

Research-only. No production BT or Rule XML will change in this experiment.
CV03 independently reproduced a short-horizon benefit from a 10 m downward
residual during a high-climb aiming scene, but a three-second hold produced a
negative final delta. CV04 tests the predeclared explanation that the useful
correction is transient and the later held residual causes the regression.

## Frozen selection and intervention

Use untouched ACE randomized seeds 12 through 15, in ascending seed and time
order. Select the first baseline dealt event satisfying the unchanged CV03 E5
filter: two seconds of history, range 800--1300 m, own ATA 25--55 deg,
absolute LOS azimuth at most 12 deg, LOS elevation 25--55 deg, event damage at
least 0.01 HP, and own vertical speed at least 80 m/s. If none matches, report
insufficient support; do not relax the filter.

At the selected event compare `bt_down` and `bt_up`, each a 10 m vertical
residual held for exactly 1.0 s. The opposite sign remains a symmetry control;
the baseline remains the matched-prefix reference. No other duration, offset,
or trigger is inspected on the selected start.

## Predeclared decision rule

The transient hypothesis passes this start only if down is strictly positive
and greater than up at 3, 5, and 10 seconds, and its final net-HP delta is
non-negative. Every prefix must be byte-identical before the fork. A failure
rejects the one-second candidate without duration tuning on the same scene.

Even a pass is only one held-start mechanism check. It does not authorize a
combat-BT change. Adoption would still require a state-defined trigger tested
over at least 15 starts and the heterogeneous opponent suite, with per-seed
results, leave-largest-contributor-out totals, and the Syllabus gate.

## Result and decision

Seeds 12--14 had no event matching the frozen filter. The first match was ACE
random seed 15 at fork 155.7666 s, two seconds before a 0.014367 HP dealt
event. Its state was range 923.03 m, ATA 25.16 deg, LOS azimuth -2.69 deg,
LOS elevation 25.02 deg, and own vertical speed 141.98 m/s.

Both candidates applied exactly ten 10 Hz residual updates and passed the
matched-prefix check. Down was better than up, but down was -0.000003998 HP at
3/5/10/20 s and -0.000100062 HP at fight end. Up was -0.000436753 HP locally
and -0.000499823 HP at fight end.

Reject the one-second candidate. The relative sign ranking reproduced, but
the required positive local value and non-negative final value both failed.
The three-second regression therefore cannot be explained only by excessive
hold duration. Do not tune another duration or offset on seed 15.

During analysis an ad-hoc query initially used nonexistent descriptive LOS
column names. Schema inspection caught the mistake before any result was
accepted or committed; the filter was rerun with `own_los_az_deg` and
`own_los_el_deg`. This motivates replacing shell predicates with a checked,
parameterized selector and keeping its output as the compact scan artifact.

## Provenance and validation

- residual lab DLL: `DA8403DB6C598883FCBB51F0250A22AFFB68EE59BE0B687D18B880ED13EFAE5A`;
- Rule XML: `1760A7E3EA9A50D38243F276983FCD393F5ED2067AB5FD7344ED2FCA8AC153E3`;
- `baseline_scan.csv`: `D1E3D4E6A1F0FF9AB301A212AE60645255BFB536E8D0086554DA858A22198689`;
- `transient_outcomes.csv`: `97A9F8A3659BC81A28EF111DBDA961A8384641AFF15D3A1B1AEA06AA702A7FC2`.

The checked selector reproduced exactly one match and selected seed 15. Ruff
passed, all 28 diagnostic tests passed, and `f16_init.xml` remained valid
after every baseline and fork batch.
