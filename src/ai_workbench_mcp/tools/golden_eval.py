from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


JsonObject = dict[str, Any]

REQUIRED_ARTIFACTS = {
    "task_metadata.json",
    "final_prompt.md",
    "model_selection.json",
    "model_output.md",
    "validation_report.json",
    "revision_decision.json",
    "run_log.jsonl",
}
EXPECTED_FIELDS = {
    "recipe",
    "validation_profile",
    "prompt",
    "final_status",
    "overall_status",
    "sign_off_ready",
}
PRIVATE_PATTERNS = [
    re.compile(r"(?<![A-Za-z])[A-Za-z]:\\"),
    re.compile(r"(?<![A-Za-z])[A-Za-z]:/(?!/)"),
    re.compile(r"\bC:/Users\b", flags=re.IGNORECASE),
    re.compile(r"\bD:/ai-workbench\b", flags=re.IGNORECASE),
    re.compile(r"\bD:\\ai-workbench\b", flags=re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\s*[:=]", flags=re.IGNORECASE),
    re.compile(r"\btoken\s*=", flags=re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
]


class GoldenEvalError(ValueError):
    pass


class MissingSourceRunError(FileNotFoundError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Score Workbench evidence folders against sanitized golden cases.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--case", help="Single golden case JSON file.")
    source.add_argument("--cases-dir", help="Directory of golden case JSON files.")
    parser.add_argument("--run-dir", help="Run evidence folder. In batch mode, overrides source-runs-dir/source_run_id for every case.")
    parser.add_argument(
        "--source-runs-dir",
        default="examples/sample-runs",
        help="Base directory used to resolve source-runs-dir/<source_run_id> when --run-dir is not provided.",
    )
    parser.add_argument("--out-dir", default="runs/golden_eval", help="Output directory for eval reports.")
    return parser


def read_json(path: Path) -> JsonObject:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: JsonObject) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def private_string(value: str) -> bool:
    return any(pattern.search(value) for pattern in PRIVATE_PATTERNS)


def walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        results: list[str] = []
        for item in value:
            results.extend(walk_strings(item))
        return results
    if isinstance(value, dict):
        results = []
        for item in value.values():
            results.extend(walk_strings(item))
        return results
    return []


def require_string(case: JsonObject, key: str) -> str:
    value = case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GoldenEvalError(f"invalid_case_schema:missing_{key}")
    return value


def require_string_list(case: JsonObject, key: str) -> list[str]:
    value = case.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise GoldenEvalError(f"invalid_case_schema:{key}")
    return [str(item) for item in value]


def validate_simple_id(value: str, field: str) -> None:
    if any(marker in value for marker in ("/", "\\", ":", "..")):
        raise GoldenEvalError(f"invalid_case_schema:{field}")


def validate_artifact_name(value: str) -> None:
    artifact = Path(value)
    if artifact.is_absolute() or ".." in artifact.parts or artifact.as_posix() != value:
        raise GoldenEvalError(f"invalid_case_schema:required_artifacts")
    if value not in REQUIRED_ARTIFACTS:
        raise GoldenEvalError(f"invalid_case_schema:required_artifacts")


def validate_case(case: JsonObject) -> JsonObject:
    if case.get("schema_version") != 1:
        raise GoldenEvalError("invalid_case_schema:schema_version")

    for key in ("case_id", "source_run_id", "case_type", "difficulty", "risk"):
        validate_simple_id(require_string(case, key), key)

    expected = case.get("expected")
    if not isinstance(expected, dict):
        raise GoldenEvalError("invalid_case_schema:expected")
    missing_expected = EXPECTED_FIELDS - set(expected)
    if missing_expected:
        raise GoldenEvalError(f"invalid_case_schema:expected.{sorted(missing_expected)[0]}")
    for key in EXPECTED_FIELDS - {"sign_off_ready"}:
        if not isinstance(expected.get(key), str) or not str(expected.get(key)).strip():
            raise GoldenEvalError(f"invalid_case_schema:expected.{key}")
    if not isinstance(expected.get("sign_off_ready"), bool):
        raise GoldenEvalError("invalid_case_schema:expected.sign_off_ready")

    required_artifacts = require_string_list(case, "required_artifacts")
    if not required_artifacts:
        raise GoldenEvalError("invalid_case_schema:required_artifacts")
    for artifact_name in required_artifacts:
        validate_artifact_name(artifact_name)

    for key in ("required_output_terms", "forbidden_output_terms"):
        for term in require_string_list(case, key):
            if len(term) > 80:
                raise GoldenEvalError(f"invalid_case_schema:{key}")

    for value in walk_strings(case):
        if private_string(value):
            raise GoldenEvalError("invalid_case_schema:private_value")

    return case


def load_case(path: Path) -> JsonObject:
    try:
        return validate_case(read_json(path))
    except json.JSONDecodeError as exc:
        raise GoldenEvalError(f"invalid_case_json:{path}") from exc


def load_optional_json(path: Path) -> JsonObject:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {}


def first_present(*values: object) -> object:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def expected_actuals(run_dir: Path) -> dict[str, object]:
    metadata = load_optional_json(run_dir / "task_metadata.json")
    selection = load_optional_json(run_dir / "model_selection.json")
    report = load_optional_json(run_dir / "validation_report.json")
    decision = load_optional_json(run_dir / "revision_decision.json")
    return {
        "recipe": first_present(metadata.get("recipe"), selection.get("recipe"), report.get("recipe")),
        "validation_profile": report.get("profile"),
        "prompt": first_present(metadata.get("prompt"), selection.get("prompt")),
        "final_status": decision.get("final_status"),
        "overall_status": report.get("overall_status"),
        "sign_off_ready": report.get("sign_off_ready"),
    }


def add_failure(failure_modes: list[str], failure_mode: str) -> None:
    if failure_mode not in failure_modes:
        failure_modes.append(failure_mode)


def score_case(case: JsonObject, run_dir: Path) -> JsonObject:
    failure_modes: list[str] = []
    total_checks = 0
    passed_checks = 0

    required_artifacts = [str(item) for item in case["required_artifacts"]]
    for artifact_name in required_artifacts:
        total_checks += 1
        if (run_dir / artifact_name).is_file():
            passed_checks += 1
        else:
            add_failure(failure_modes, f"missing_artifact:{artifact_name}")

    expected = case["expected"]
    actuals = expected_actuals(run_dir)
    for field in sorted(EXPECTED_FIELDS):
        total_checks += 1
        if actuals.get(field) == expected.get(field):
            passed_checks += 1
        else:
            add_failure(failure_modes, f"metadata_mismatch:{field}")

    total_checks += 1
    if actuals.get("overall_status") == "passed" and actuals.get("sign_off_ready") is True:
        passed_checks += 1
    else:
        add_failure(failure_modes, "validation_not_passed")

    total_checks += 1
    if actuals.get("final_status") == "accepted":
        passed_checks += 1
    else:
        add_failure(failure_modes, "quality_gate_not_accepted")

    model_output = ""
    output_path = run_dir / "model_output.md"
    if output_path.exists():
        model_output = output_path.read_text(encoding="utf-8", errors="replace")
    normalized_output = model_output.lower()

    for term in case.get("required_output_terms", []):
        total_checks += 1
        if str(term).lower() in normalized_output:
            passed_checks += 1
        else:
            add_failure(failure_modes, f"missing_output_term:{term}")

    for term in case.get("forbidden_output_terms", []):
        total_checks += 1
        if str(term).lower() in normalized_output:
            add_failure(failure_modes, f"forbidden_output_term:{term}")
        else:
            passed_checks += 1

    passed = not failure_modes
    score = round(passed_checks / max(1, total_checks), 2)
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "provider": "workbench",
        "model": "golden-case-harness",
        "case_name": case["case_id"],
        "case_type": case["case_type"],
        "difficulty": case["difficulty"],
        "risk": case["risk"],
        "label": "accepted_baseline",
        "source_run_id": case["source_run_id"],
        "passed": passed,
        "overall_score": score,
        "failure_modes": failure_modes,
        "checks_total": total_checks,
        "checks_passed": passed_checks,
        "checks_failed": total_checks - passed_checks,
    }


def metadata_for(case: JsonObject, score_report: JsonObject) -> JsonObject:
    return {
        "schema_version": 1,
        "generated_at": score_report["generated_at"],
        "status": "completed",
        "provider": "workbench",
        "model": "golden-case-harness",
        "tier": "deterministic_tool",
        "case_id": case["case_id"],
        "case_name": case["case_id"],
        "source_run_id": case["source_run_id"],
        "case_type": case["case_type"],
        "difficulty": case["difficulty"],
        "risk": case["risk"],
        "label": "accepted_baseline",
    }


def resolve_run_dir(case: JsonObject, args: argparse.Namespace) -> Path:
    if args.run_dir:
        return Path(args.run_dir)
    return Path(args.source_runs_dir) / str(case["source_run_id"])


def evaluate_case(case_path: Path, run_dir: Path, out_dir: Path) -> JsonObject:
    case = load_case(case_path)
    if not run_dir.is_dir():
        raise MissingSourceRunError(f"missing_source_run={run_dir}")
    score_report = score_case(case, run_dir)
    metadata = metadata_for(case, score_report)
    write_json(out_dir / "model_eval_metadata.json", metadata)
    write_json(out_dir / "score_report.json", score_report)
    return score_report


def case_paths(args: argparse.Namespace) -> tuple[list[Path], bool]:
    if args.case:
        return [Path(args.case)], False
    cases_dir = Path(args.cases_dir)
    if not cases_dir.is_dir():
        raise GoldenEvalError(f"cases_dir_missing={cases_dir}")
    return sorted(path for path in cases_dir.glob("*.json") if path.is_file()), True


def run_payload(args: argparse.Namespace) -> JsonObject:
    paths, batch = case_paths(args)
    out_root = Path(args.out_dir)
    results: list[JsonObject] = []

    for case_path in paths:
        case = load_case(case_path)
        run_dir = resolve_run_dir(case, args)
        if not run_dir.is_dir():
            raise MissingSourceRunError(f"missing_source_run={run_dir}")
        case_out_dir = out_root / str(case["case_id"]) if batch else out_root
        score_report = score_case(case, run_dir)
        write_json(case_out_dir / "model_eval_metadata.json", metadata_for(case, score_report))
        write_json(case_out_dir / "score_report.json", score_report)
        results.append(
            {
                "case_id": case["case_id"],
                "source_run_id": case["source_run_id"],
                "passed": score_report["passed"],
                "score_report": str(case_out_dir / "score_report.json"),
            }
        )

    return {
        "cases_total": len(results),
        "cases_passed": sum(1 for result in results if result["passed"]),
        "cases_failed": sum(1 for result in results if not result["passed"]),
        "results": results,
        "out_dir": str(out_root),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = run_payload(args)
    except GoldenEvalError as exc:
        print(str(exc))
        return 2
    except MissingSourceRunError as exc:
        print(str(exc))
        return 3

    print(f"out_dir={payload['out_dir']}")
    print(f"cases_total={payload['cases_total']}")
    print(f"cases_passed={payload['cases_passed']}")
    print(f"cases_failed={payload['cases_failed']}")
    for result in payload["results"]:
        print(f"score_report={result['score_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
