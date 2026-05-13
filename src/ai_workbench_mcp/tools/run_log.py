from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append a machine-readable entry to a run_log.jsonl file."
    )
    parser.add_argument("--run-id", required=True, help="Unique run identifier.")
    parser.add_argument("--task", required=True, help="Task summary for the log entry.")
    parser.add_argument("--decision", required=True, help="Current decision or outcome for the run.")
    parser.add_argument(
        "--status",
        choices=["started", "in_progress", "completed", "blocked"],
        default="started",
        help="Run status to record.",
    )
    parser.add_argument("--prompt", help="Approved prompt used for the run.")
    parser.add_argument("--model-tier", help="Selected model tier, if known.")
    parser.add_argument("--model", help="Selected provider/model identifier, if known.")
    parser.add_argument("--validation", help="Validation result or summary for the run.")
    parser.add_argument("--first-pass-outcome", help="Phase 2 first-pass outcome, if known.")
    parser.add_argument("--final-outcome", help="Phase 2 final outcome, if known.")
    parser.add_argument("--quality-loop-status", help="Phase 2 quality-loop status, if known.")
    parser.add_argument("--authoritative-validation", help="Authoritative validation report artifact path.")
    parser.add_argument("--follow-up", help="Next action or unresolved follow-up.")
    parser.add_argument(
        "--context-docs",
        nargs="*",
        default=[],
        help="Optional list of context docs used for the run.",
    )
    parser.add_argument(
        "--files-touched",
        nargs="*",
        default=[],
        help="Optional list of files changed during the run.",
    )
    parser.add_argument(
        "--artifacts",
        nargs="*",
        default=[],
        help="Optional list of artifact paths associated with the run state.",
    )
    parser.add_argument("--out", required=True, help="Path for run_log.jsonl output.")
    return parser


def append_jsonl(file_path: Path, payload: dict[str, object]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def run_log_payload(args: argparse.Namespace) -> dict[str, object]:
    out_path = Path(args.out)

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "run_id": args.run_id,
        "task": args.task,
        "prompt": args.prompt,
        "model_tier": args.model_tier,
        "model": args.model,
        "decision": args.decision,
        "status": args.status,
        "validation": args.validation,
        "first_pass_outcome": args.first_pass_outcome,
        "final_outcome": args.final_outcome,
        "quality_loop_status": args.quality_loop_status,
        "authoritative_validation": args.authoritative_validation,
        "follow_up": args.follow_up,
        "context_docs": args.context_docs,
        "files_touched": args.files_touched,
        "artifacts": args.artifacts,
    }
    append_jsonl(out_path, payload)
    return {**payload, "out": str(out_path)}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = run_log_payload(args)

    print(f"run_id={payload['run_id']}")
    print(f"status={payload['status']}")
    print(f"out={payload['out']}")
    print(f"decision={payload['decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
