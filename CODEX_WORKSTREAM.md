# Codex state-policy workstream

## Isolation

- Stable base: `770d7a0` (`v32`, 9 opponents x 15 seeds, 135 matches).
- Branch: `codex/state-policy-lab`.
- This worktree is owned by Codex. The original `.topgun` worktree and `main`
  branch are owned by Claude/user work in progress.
- Do not merge, rebase, cherry-pick, or overwrite `main` without explicit user
  approval.
- Existing logs and opponent artifacts in the original worktree are read-only
  inputs. New generated outputs stay in this worktree or a temporary directory.

## Collaboration contract

1. Exchange work through commit hashes and short experiment reports, never by
   editing the other agent's working directory.
2. Every report identifies the baseline artifact, rule version, opponent,
   seeds, command, and log stamp.
3. Aircraft-source changes and analysis-tool changes are separate commits.
4. A proposal is eligible for integration only after its mechanism, per-seed
   result, largest-seed-excluded result, and full-regression result are known.
5. Rejected work remains on this branch with the reason recorded.

## First research track

Build a data-driven local-policy laboratory without changing the active v32
aircraft:

1. Convert paired Tacview CSV tracks into compact relative-state snapshots.
2. Attach multi-horizon future labels (dealt, taken, net damage and geometry).
3. Identify pivotal/failure states and reproducible state clusters.
4. Add counterfactual replay only after episode and native-policy state can be
   reproduced reliably.
5. Permit a future v32 override only in well-supported states with a measured
   value margin and a safe v32 fallback.

The first milestone is an analysis dataset, not a new combat version.
