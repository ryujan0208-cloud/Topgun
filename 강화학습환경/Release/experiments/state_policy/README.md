# State-policy laboratory

This experiment asks a narrower question than "which global constant is
better?":

> Given a reproducible combat state, which short maneuver produces the best
> downstream tournament value, and how confident are we that the result
> generalizes beyond the source opponent?

## Stage 1: observational dataset

`tools_diag/state_dataset.py` converts paired ownship/target track CSVs into
relative-state rows with future labels. It does not claim causal action value;
it establishes the state representation and finds important scenes.

Example:

```powershell
$py = "C:\Users\TFX5470H\anaconda3\envs\aip\python.exe"
& $py tools_diag/state_dataset.py `
  --logdir ".\artifacts\logs" `
  --stamp 2026_8_7_16_33_58 `
  --output artifacts/state_policy/2026_8_7_16_33_58.csv
```

The output contains:

- geometry: range, ATA for both aircraft, relative heading, altitude delta;
- dynamics: speed, closure, vertical rate, turn rate, energy-height delta;
- context: phase, health and altitude margin;
- labels at 2/5/10/20 seconds: dealt, taken, net damage and future geometry.

`tools_diag/state_report.py` performs the same conversion in memory and reports
the p10/p50/p90 state distribution for windows preceding future dealt or taken
damage:

```powershell
& $py tools_diag/state_report.py `
  --logdir ".\artifacts\logs" `
  --stamp 2026_8_4_17_4_41 `
  --label v32-onecircle `
  --horizon 10
```

Counts from overlapping future windows are exposure density, not independent
firing-event counts.

## Stage 2: independent damage events

`tools_diag/damage_events.py` groups adjacent health-loss ticks into one burst
and records the exact source stamp, episode, damage-row index, pre-damage anchor,
and states 2/5/10 seconds before the event:

```powershell
& $py tools_diag/damage_events.py `
  --logdir ".\artifacts\logs" `
  --stamp 2026_8_4_17_4_41 `
  --label v32-onecircle `
  --output artifacts/state_policy/2026_8_4_17_4_41_events.csv

& $py tools_diag/damage_event_report.py `
  --input artifacts/state_policy/2026_8_4_17_4_41_events.csv
```

The default burst gap is 0.5 seconds and is configurable with
`--merge-gap-s`. A candidate result should be checked across reasonable gap
values so that an arbitrary grouping threshold does not create the conclusion.

## Stage 3: matched-prefix VP fork

`prefix_fork.py` uses the lab-only `StepWithVPOverride` DLL export. Before the
fork the normal v32 path runs unchanged. Inside the window, the BT still ticks,
its throttle remains active, the candidate replaces only VP, the 75-degree
off-boresight safety clamp still applies, and the stateful controller advances
once per 10 Hz update.

```powershell
& $py experiments/state_policy/prefix_fork.py `
  --candidate baseline --seed 0 --opponent ACE

& $py experiments/state_policy/prefix_fork.py `
  --candidate pure --fork-start 152.75 --fork-duration 3 `
  --seed 0 --opponent ACE

& $py tools_diag/prefix_compare.py `
  --logdir artifacts/logs `
  --baseline-stamp BASELINE_STAMP `
  --candidate-stamp CANDIDATE_STAMP `
  --fork-start 152.75
```

The baseline lab DLL must first reproduce the ordinary v32 track exactly. The
comparison must then report `pre_fork_equal=True` for both aircraft. A fork that
fails either check is invalid regardless of its score.

Available candidate VPs are deliberately small and interpretable: current
target position (`pure`), constant-velocity prediction (`lead`), and fixed
vertical offsets (`up` / `down`). They are experimental actions, not BT rules.

## Interpretation boundary

These labels describe what happened under the policy that generated the log.
They must not be interpreted as "action A caused value X". Causal comparison
requires replaying the same prefix with cloned simulator/controller/BT state and
changing only the candidate maneuver.

## Planned safety rule

A learned or tabulated override will eventually be allowed only when:

- the state has adequate data support;
- the alternative has a clear value margin over v32;
- the worst-case result does not violate altitude/crash constraints; and
- the same direction survives opponent and seed holdouts.

Otherwise the policy returns to unchanged v32 behavior.

## Archived campaigns

- `runs/CV01/README.md`: 20 exact-prefix action forks across fixed and
  randomized ACE starts, including the failed predeclared seed-2 prediction.
- `runs/CV01/fork_outcomes.csv`: state/action outcomes at 3/5/10/20-second
  horizons plus final net HP.
