# -*- coding: utf-8 -*-
"""Run and archive one matched-prefix VP fork case.

Raw tracks are kept below the ignored ``artifacts/state_policy`` tree.  Every
case writes a compact manifest containing the exact DLL, rule, Git revision,
arguments, score, replay stamp, file hashes, and (for candidates) the prefix
identity check against a baseline case.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools_diag"))

from prefix_compare import compare_tracks  # noqa: E402


ROLES = {
    "ownship": "ownship_(F-16)[Blue].csv",
    "target": "target_(F-16)[Red].csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def replay_files(logdir: Path, stamp: str) -> dict[str, Path]:
    return {
        "summary": logdir / f"{stamp}_summary.json",
        **{role: logdir / f"{stamp}_{suffix}" for role, suffix in ROLES.items()},
    }


def discover_new_stamp(logdir: Path, before: set[str]) -> str:
    after = {path.name for path in logdir.glob("*_summary.json")}
    created = sorted(after - before)
    if len(created) != 1:
        raise RuntimeError(
            f"expected exactly one new summary, found {len(created)}: {created}"
        )
    return created[0].removesuffix("_summary.json")


def git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def load_manifest(case_dir: Path) -> dict[str, object]:
    path = case_dir / "case_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"baseline manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument(
        "--candidate", choices=("baseline", "pure", "lead", "up", "down"), required=True
    )
    parser.add_argument("--fork-start", type=float, required=True)
    parser.add_argument("--fork-duration", type=float, default=3.0)
    parser.add_argument("--lead-time", type=float, default=2.0)
    parser.add_argument("--vertical-offset", type=float, default=500.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--opponent", default="ACE")
    parser.add_argument("--max-time", type=float, default=200.0)
    parser.add_argument("--ownship-dll", default="AIP_DCS_lab.dll")
    parser.add_argument("--rule-xml", default="Rule_forTraining.xml")
    parser.add_argument("--randomized-start", action="store_true")
    parser.add_argument("--baseline-case", type=Path)
    parser.add_argument(
        "--keep-logdir-copy",
        action="store_true",
        help="keep the redundant replay files in artifacts/logs after archiving",
    )
    parser.add_argument(
        "--archive-root", type=Path, default=Path("artifacts/state_policy/forks")
    )
    parser.add_argument("--logdir", type=Path, default=Path("artifacts/logs"))
    candidate_action = next(a for a in parser._actions if a.dest == "candidate")
    candidate_action.choices = (*candidate_action.choices, "bt_up", "bt_down")
    args = parser.parse_args()

    if args.candidate != "baseline" and args.baseline_case is None:
        parser.error("candidate cases require --baseline-case")
    if args.fork_start < 0.0 or args.fork_duration <= 0.0:
        parser.error("fork start must be non-negative and duration positive")

    logdir = (ROOT / args.logdir).resolve()
    archive_root = (ROOT / args.archive_root).resolve()
    case_dir = archive_root / args.campaign / args.case_id
    if case_dir.exists():
        raise FileExistsError(f"case archive already exists: {case_dir}")
    logdir.mkdir(parents=True, exist_ok=True)
    telemetry_path = logdir / f".telemetry_{args.campaign}_{args.case_id}.csv"
    if telemetry_path.exists():
        raise FileExistsError(f"stale telemetry file: {telemetry_path}")

    dll_path = (ROOT / args.ownship_dll).resolve()
    rule_path = (ROOT / args.rule_xml).resolve()
    if not dll_path.is_file() or not rule_path.is_file():
        raise FileNotFoundError(f"missing DLL or rule: {dll_path}, {rule_path}")

    before = {path.name for path in logdir.glob("*_summary.json")}
    command = [
        sys.executable,
        str(Path(__file__).with_name("prefix_fork.py")),
        "--candidate",
        args.candidate,
        "--fork-start",
        str(args.fork_start),
        "--fork-duration",
        str(args.fork_duration),
        "--lead-time",
        str(args.lead_time),
        "--vertical-offset",
        str(args.vertical_offset),
        "--seed",
        str(args.seed),
        "--opponent",
        args.opponent,
        "--max-time",
        str(args.max_time),
        "--ownship-dll",
        args.ownship_dll,
    ]
    command.extend(["--telemetry-out", str(telemetry_path)])
    if args.randomized_start:
        command.append("--randomized-start")
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        telemetry_path.unlink(missing_ok=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        return completed.returncode

    stamp = discover_new_stamp(logdir, before)
    sources = replay_files(logdir, stamp)
    sources["telemetry"] = telemetry_path
    missing = [str(path) for path in sources.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"incomplete replay set: {missing}")

    case_dir.mkdir(parents=True)
    archived: dict[str, Path] = {}
    for kind, source in sources.items():
        name = "action_telemetry.csv" if kind == "telemetry" else source.name
        destination = case_dir / name
        shutil.copy2(source, destination)
        archived[kind] = destination
    stdout_path = case_dir / "runtime_stdout.log"
    stderr_path = case_dir / "runtime_stderr.log"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    archived["stdout"] = stdout_path
    archived["stderr"] = stderr_path

    score = json.loads(archived["summary"].read_text(encoding="utf-8"))
    dealt = 1.0 - float(score["target_health"])
    taken = 1.0 - float(score["ownship_health"])
    prefix: dict[str, object] | None = None
    baseline_reference: dict[str, object] | None = None
    if args.baseline_case is not None:
        baseline_dir = args.baseline_case.resolve()
        baseline_manifest = load_manifest(baseline_dir)
        baseline_stamp = str(baseline_manifest["replay_stamp"])
        baseline_reference = {
            "case_dir": str(baseline_dir),
            "case_id": baseline_manifest["case_id"],
            "replay_stamp": baseline_stamp,
        }
        prefix = {}
        for role, suffix in ROLES.items():
            prefix[role] = compare_tracks(
                baseline_dir / f"{baseline_stamp}_{suffix}",
                archived[role],
                args.fork_start,
            )

    selected_output = [
        line
        for line in completed.stdout.splitlines()
        if line.startswith("[prefix_fork]") or line == "tacview log saved"
    ]
    for line in selected_output:
        print(line)
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "campaign": args.campaign,
        "case_id": args.case_id,
        "git_revision": git_revision(),
        "configuration": {
            "candidate": args.candidate,
            "fork_start_s": args.fork_start,
            "fork_duration_s": args.fork_duration,
            "lead_time_s": args.lead_time,
            "vertical_offset_m": args.vertical_offset,
            "seed": args.seed,
            "opponent": args.opponent,
            "max_time_s": args.max_time,
            "randomized_start": args.randomized_start,
            "ownship_dll": args.ownship_dll,
            "rule_xml": args.rule_xml,
        },
        "provenance": {
            "dll_sha256": sha256(dll_path),
            "rule_sha256": sha256(rule_path),
        },
        "replay_stamp": stamp,
        "score": {
            **score,
            "dealt_hp": dealt,
            "taken_hp": taken,
            "net_hp": dealt - taken,
        },
        "baseline": baseline_reference,
        "prefix_comparison": prefix,
        "files": {
            kind: {"name": path.name, "sha256": sha256(path)}
            for kind, path in archived.items()
        },
        "selected_output": selected_output,
    }
    manifest_path = case_dir / "case_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not args.keep_logdir_copy:
        for source in sources.values():
            source.unlink()
    prefix_ok = prefix is None or all(
        bool(report["pre_fork_equal"]) for report in prefix.values()
    )
    print(
        f"[fork_case] archive={case_dir} stamp={stamp} "
        f"net={dealt - taken:.6f} prefix_ok={prefix_ok}"
    )
    return 0 if prefix_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
