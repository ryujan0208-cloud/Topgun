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
  --logdir "C:\Users\TFX5470H\Desktop\.topgun\강화학습환경\Release\artifacts\logs" `
  --stamp 2026_8_7_16_33_58 `
  --output artifacts/state_policy/2026_8_7_16_33_58.csv
```

The output contains:

- geometry: range, ATA for both aircraft, relative heading, altitude delta;
- dynamics: speed, closure, vertical rate, turn rate, energy-height delta;
- context: phase, health and altitude margin;
- labels at 2/5/10/20 seconds: dealt, taken, net damage and future geometry.

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
