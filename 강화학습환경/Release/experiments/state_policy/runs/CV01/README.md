# CODEX CV01 matched-prefix campaign — 2026-08-08

## Status

Research-only; no production BT rule was changed or proposed for adoption.
Twenty candidate forks passed exact pre-fork identity for both aircraft. Raw
tracks and per-case manifests are retained under the ignored
`artifacts/state_policy/forks/` tree. The compact state/action/outcome table is
`fork_outcomes.csv` (SHA-256
`CCFA7C408AAAEA0E13230BC807550A32D984C82CD0579B14626672F09EDAFFA9`).

All cases used:

- lab DLL SHA-256: `5AFE544793AAE631C99AB922F4A1B9066E3DBB9B511F60470F9390A0F5F1003D`;
- Rule XML SHA-256: `1760A7E3EA9A50D38243F276983FCD393F5ED2067AB5FD7344ED2FCA8AC153E3`;
- 10 Hz action emulation and 200-second fights.

## Fixed-start ACE, seed 0

The 45.25-second fork was selected two seconds before the only received-damage
event. None of the four candidates prevented that immediate hit. Their positive
final scores came from changing the later trajectory, so this scene is not
evidence for a defensive trigger.

At the two offensive forks, `pure` increased the local damage burst while
received damage stayed unchanged:

| Fork | Baseline burst | Pure burst | 3 s local net delta | Final net delta |
|---:|---:|---:|---:|---:|
| 152.75 s | 0.019833 | 0.034285 | +0.014452 | +0.014695 |
| 178.60 s | 0.008420 | 0.023111 | +0.014690 | +0.016823 |

These are two positive causal scenes on one trajectory, not independent
generalization samples.

## Seed audit and randomized starts

Changing `seed=0` to `seed=1` without enabling start randomization produced
byte-identical tracks:

- ownship: `DF61EDD0F14DC13B36A18FF3E1B8FBC594DB2F371F0EE77EC572C456B6075D8E`;
- target: `C027AE5C0CC30620D4CB3ABEF443532F22AD9446AE0E63DB4BF8F8AA1DFBC664`.

The seed number alone is therefore not an independent sample. The harness now
has an explicit `--randomized-start` switch that matches `rehearsal_10hz.py`'s
multi-seed ownship distribution.

Randomized seed 1 contradicted a global `pure` rule. At 161.43 seconds:

| Candidate | 3 s local net delta | 5 s local net delta | Final net delta |
|---|---:|---:|---:|
| pure | -0.009723 | -0.009723 | -0.010429 |
| lead | -0.009723 | -0.000825 | +0.014300 |
| up | -0.009723 | +0.038322 | +0.037615 |
| down | -0.009723 | -0.009723 | -0.010429 |

The `up` candidate delayed the shot beyond three seconds but increased the
event from 0.009723 to 0.048044 HP by five seconds. This is why evaluation must
use several fixed horizons rather than one arbitrary delay.

Randomized seed 2 was used as a predeclared prediction check. Its range, ATA,
closure, and altitude difference resembled the fixed-start `pure` success at
178.60 seconds, so `pure` was predicted to improve the burst. The prediction
failed: all four candidates removed the baseline 0.007045 HP event. The
baseline BT action was best among the tested actions.

The superficially similar seed-0/seed-2 states differed materially in vertical
motion and energy: own vertical speed 72.2 vs 20.7 m/s, target vertical speed
43.5 vs 8.0 m/s, and energy-height delta 21.2 vs 181.8 m. Even the current full
feature vector may omit decisive LOS-rate or maneuver-history state.

## Decision

1. Reject any global `pure`, `lead`, `up`, or `down` override.
2. Do not create a BT threshold from these 20 rows.
3. Retain the matched-prefix method and multi-horizon labels.
4. Next instrumentation priority is LOS azimuth/elevation rate, signed aspect,
   lift-vector relation, and current BT VP/action. After that, gather distinct
   randomized starts and opponent holdouts before fitting any state partition.

Adoption still requires 15 genuinely distinct starts, opponent holdouts,
net-HP and floor-safety checks, maximum-contribution removal, and a mechanism
that survives those checks.
