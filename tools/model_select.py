from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from types import SimpleNamespace

from config_loader import load_simple_yaml
from context_scout import WORKBENCH_ROOT, load_project_config, relative_path, resolve_cli_path


@dataclass
class ModelTier:
    name: str
    provider: str
    model: str
    use_for: list[str]
    fallback_models: list[str]
    parameters: dict[str, object]


@dataclass
class SelectorRule:
    name: str
    conditions: dict[str, str]
    select: str
    reason: str


@dataclass
class SelectorPolicy:
    default_model: str
    manual_override: bool
    rules: list[SelectorRule]
    fallbacks: dict[str, list[str]]


@dataclass
class InferredRouting:
    complexity_score: int | None
    test_complexity_level: int | None
    detected_risk_keywords: list[str]
    explanation: str


TASK_TYPE_LABELS = {
    "implement": "implementation",
    "review": "review",
    "investigate": "investigation",
    "test": "test",
}


def complexity_band(score: int | None) -> str | None:
    if score is None:
        return None
    if score <= 8:
        return "easy"
    if score <= 13:
        return "moderate"
    if score <= 18:
        return "hard"
    if score <= 22:
        return "very_hard"
    return "nasty_hard"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select a model tier using the configured rule-based selector policy."
    )
    parser.add_argument("--project", required=True, help="Project key from configs/projects.yaml.")
    parser.add_argument("--task-type", required=True, help="Task type such as implement or review.")
    parser.add_argument("--risk", choices=["low", "medium", "high"], required=True)
    parser.add_argument(
        "--validation-strength",
        choices=["strong", "medium", "weak"],
        default="medium",
        help="How strong the planned validation coverage is.",
    )
    parser.add_argument("--prompt", help="Canonical approved prompt name.")
    parser.add_argument(
        "--complexity-score",
        type=int,
        help="Optional 1-25 coding difficulty score from the five-axis routing rubric.",
    )
    parser.add_argument(
        "--test-complexity-level",
        type=int,
        help="Optional 1-8 test-generation complexity level.",
    )
    parser.add_argument(
        "--instruction-following",
        choices=["normal", "strict"],
        default="normal",
        help="Use strict when exact output shape, rule following, or no-extra-text behavior is critical.",
    )
    parser.add_argument("--task-text", help="Optional raw task text for advisory routing inference.")
    parser.add_argument(
        "--code-file",
        nargs="*",
        default=[],
        help="Optional Python files to inspect for advisory complexity/test routing inference.",
    )
    parser.add_argument("--out", required=True, help="Path for model_selection.json output.")
    return parser


def validate_routing_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.complexity_score is not None and not 1 <= args.complexity_score <= 25:
        parser.error("--complexity-score must be between 1 and 25.")
    if args.test_complexity_level is not None and not 1 <= args.test_complexity_level <= 8:
        parser.error("--test-complexity-level must be between 1 and 8.")


def load_model_registry() -> dict[str, ModelTier]:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "model_registry.yaml")
    models = raw_data.get("models", {})
    tiers: dict[str, ModelTier] = {}
    for name, payload in models.items():
        if not isinstance(payload, dict):
            continue
        tiers[str(name)] = ModelTier(
            name=str(name),
            provider=str(payload.get("provider", "")),
            model=str(payload.get("model", "")),
            use_for=[str(item) for item in payload.get("use_for", []) if item is not None],
            fallback_models=[str(item) for item in payload.get("fallback_models", []) if item is not None],
            parameters=payload.get("parameters", {}) if isinstance(payload.get("parameters", {}), dict) else {},
        )
    return tiers


def load_selector_policy() -> SelectorPolicy:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "model_selector.yaml")
    rules: list[SelectorRule] = []
    for raw_rule in raw_data.get("rules", []):
        if not isinstance(raw_rule, dict):
            continue
        when = raw_rule.get("when", {})
        rules.append(
            SelectorRule(
                name=str(raw_rule.get("name", "")),
                conditions={
                    str(key): str(value)
                    for key, value in when.items()
                    if value is not None
                }
                if isinstance(when, dict)
                else {},
                select=str(raw_rule.get("select", "")),
                reason=str(raw_rule.get("reason", "")),
            )
        )

    return SelectorPolicy(
        default_model=str(raw_data.get("default_model", "")),
        manual_override=bool(raw_data.get("manual_override", False)),
        rules=rules,
        fallbacks={
            str(key): [str(item) for item in value]
            for key, value in raw_data.get("fallbacks", {}).items()
            if isinstance(value, list)
        },
    )


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def read_code_files(paths: list[str], project_root: Path) -> str:
    chunks: list[str] = []
    for path_text in paths:
        path = resolve_cli_path(path_text, project_root)
        if path.exists() and path.is_file() and path.suffix == ".py":
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n\n".join(chunks)


def detect_risk_keywords(text: str) -> list[str]:
    risk_terms = [
        "auth",
        "permission",
        "payment",
        "money",
        "transaction",
        "concurrency",
        "thread",
        "migration",
        "destructive",
        "delete",
        "data integrity",
        "security",
        "privacy",
    ]
    lowered = text.lower()
    return [term for term in risk_terms if term in lowered]


def ast_counts(code_text: str) -> dict[str, int | bool]:
    try:
        tree = ast.parse(code_text or "\n")
    except SyntaxError:
        return {"syntax_error": True}

    counts: dict[str, int | bool] = {
        "syntax_error": False,
        "functions": 0,
        "classes": 0,
        "ifs": 0,
        "loops": 0,
        "bool_ops": 0,
        "raises": 0,
        "tries": 0,
        "async_defs": 0,
        "self_attrs": 0,
        "calls": 0,
    }
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            counts["functions"] = int(counts["functions"]) + 1
            if isinstance(node, ast.AsyncFunctionDef):
                counts["async_defs"] = int(counts["async_defs"]) + 1
        elif isinstance(node, ast.ClassDef):
            counts["classes"] = int(counts["classes"]) + 1
        elif isinstance(node, ast.If):
            counts["ifs"] = int(counts["ifs"]) + 1
        elif isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            counts["loops"] = int(counts["loops"]) + 1
        elif isinstance(node, ast.BoolOp):
            counts["bool_ops"] = int(counts["bool_ops"]) + 1
        elif isinstance(node, ast.Raise):
            counts["raises"] = int(counts["raises"]) + 1
        elif isinstance(node, ast.Try):
            counts["tries"] = int(counts["tries"]) + 1
        elif isinstance(node, ast.Call):
            counts["calls"] = int(counts["calls"]) + 1
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            counts["self_attrs"] = int(counts["self_attrs"]) + 1
    return counts


def infer_complexity_score(code_text: str, task_text: str, risk_keywords: list[str]) -> int | None:
    if not code_text.strip() and not task_text.strip():
        return None
    counts = ast_counts(code_text)
    text = f"{task_text}\n{code_text}".lower()
    syntax_error = bool(counts.get("syntax_error", False))
    if syntax_error and not task_text.strip():
        return None

    algorithmic = 1
    algorithmic += 1 if int(counts.get("loops", 0)) else 0
    algorithmic += 1 if int(counts.get("bool_ops", 0)) >= 2 else 0
    algorithmic += 1 if any(term in text for term in ("cache", "scheduler", "graph", "interval", "transaction")) else 0
    algorithmic += 1 if any(term in text for term in ("refactor", "migrate", "optimize", "batch", "pipeline", "parsing")) else 0

    state = 1
    state += 1 if int(counts.get("classes", 0)) else 0
    state += 1 if int(counts.get("self_attrs", 0)) >= 2 else 0
    state += 1 if any(term in text for term in ("state", "workflow", "transaction", "nested", "concurrency")) else 0
    state += 1 if any(term in text for term in ("database", "session", "queue", "lock", "thread", "mutex")) else 0

    edge_cases = 1
    edge_cases += 1 if int(counts.get("ifs", 0)) >= 2 else 0
    edge_cases += 1 if int(counts.get("raises", 0)) or int(counts.get("tries", 0)) else 0
    edge_cases += 1 if any(term in text for term in ("edge", "invalid", "fallback", "boundary", "empty", "missing")) else 0
    edge_cases += 1 if any(term in text for term in ("backward compat", "deprecat", "multi-tenant", "race condition")) else 0

    spec_precision = 1
    spec_precision += 1 if any(term in text for term in ("must", "exact", "strict", "only", "preserve")) else 0
    spec_precision += 1 if len(re.findall(r"\b(rule|requirement|acceptance|invariant)\b", text)) >= 2 else 0
    spec_precision += 1 if int(counts.get("functions", 0)) + int(counts.get("classes", 0)) >= 4 else 0
    spec_precision += 1 if any(term in text for term in ("schema", "contract", "api", "interface", "protocol", "specification")) else 0

    verification = 1
    verification += 1 if int(counts.get("async_defs", 0)) else 0
    verification += 1 if risk_keywords else 0
    verification += 1 if any(term in text for term in ("migration", "auth", "transaction", "data integrity")) else 0
    verification += 1 if any(term in text for term in ("compliance", "audit", "regulation", "pii", "encrypt", "credential")) else 0

    # Prompt-name baseline boosts: the prompt name is included in task_text by infer_routing().
    prompt_boosts = {
        "security_privacy_risk_review": (0, 0, 0, 2, 2),
        "performance_latency_hotspot_audit": (1, 0, 1, 0, 0),
        "bug_root_cause_investigation": (0, 1, 1, 0, 0),
        "code_review_patch_risk_audit": (0, 0, 0, 1, 1),
        "data_acquisition_surface_audit": (0, 1, 0, 1, 1),
        "test_case_development_meaningful_coverage": (0, 0, 1, 0, 0),
        "navigation_page_title_ia_audit": (0, 0, 0, 1, 0),
        "ux_visual_accessibility_audit": (0, 0, 1, 1, 0),
    }
    for prompt_name, (alg, st, edge, spec, verif) in prompt_boosts.items():
        if prompt_name in text:
            algorithmic += alg
            state += st
            edge_cases += edge
            spec_precision += spec
            verification += verif
            break

    return clamp(algorithmic + state + edge_cases + spec_precision + verification, 1, 25)


def infer_test_complexity_level(code_text: str, task_text: str) -> int | None:
    if not code_text.strip() and not task_text.strip():
        return None
    counts = ast_counts(code_text)
    text = f"{task_text}\n{code_text}".lower()
    if any(term in text for term in ("characterization", "current behavior", "before refactoring", "legacy behavior")):
        return 8
    if int(counts.get("async_defs", 0)) or "async" in text:
        return 7
    if int(counts.get("tries", 0)) or int(counts.get("raises", 0)) or any(term in text for term in ("exception", "failure", "fallback")):
        return 6
    if int(counts.get("calls", 0)) >= 4 and any(term in text for term in ("mock", "api", "repo", "client", "logger")):
        return 5
    if int(counts.get("classes", 0)) or int(counts.get("self_attrs", 0)) >= 2 or "state" in text:
        return 4
    if int(counts.get("ifs", 0)) >= 3 or "validation" in text:
        return 3
    if int(counts.get("ifs", 0)) >= 1:
        return 2
    return 1


def infer_routing(args: argparse.Namespace, project_root: Path) -> InferredRouting:
    code_text = read_code_files(args.code_file, project_root)
    task_text = " ".join(part for part in [args.task_text or "", args.prompt or ""] if part)
    risk_keywords = detect_risk_keywords(f"{task_text}\n{code_text}")
    complexity_score = infer_complexity_score(code_text, task_text, risk_keywords)
    test_complexity_level = infer_test_complexity_level(code_text, task_text) if args.task_type == "test" else None
    explanation_parts = []
    if complexity_score is not None:
        explanation_parts.append(f"suggested complexity_score={complexity_score}")
    if test_complexity_level is not None:
        explanation_parts.append(f"suggested test_complexity_level={test_complexity_level}")
    if risk_keywords:
        explanation_parts.append(f"detected risk keywords: {', '.join(risk_keywords)}")
    if not explanation_parts:
        explanation_parts.append("no advisory routing signals detected")
    return InferredRouting(
        complexity_score=complexity_score,
        test_complexity_level=test_complexity_level,
        detected_risk_keywords=risk_keywords,
        explanation="; ".join(explanation_parts),
    )


def effective_args(args: argparse.Namespace, inferred: InferredRouting) -> argparse.Namespace:
    values = vars(args).copy()
    values["complexity_score"] = args.complexity_score if args.complexity_score is not None else inferred.complexity_score
    values["test_complexity_level"] = (
        args.test_complexity_level if args.test_complexity_level is not None else inferred.test_complexity_level
    )
    return SimpleNamespace(**values)


def condition_matches(key: str, expected: str, args: argparse.Namespace) -> bool:
    if key in {"complexity_min", "complexity_max"}:
        score = getattr(args, "complexity_score", None)
        if score is None:
            return False
        expected_score = int(expected)
        return score >= expected_score if key == "complexity_min" else score <= expected_score

    if key in {"test_complexity_min", "test_complexity_max"}:
        level = getattr(args, "test_complexity_level", None)
        if level is None:
            return False
        expected_level = int(expected)
        return level >= expected_level if key == "test_complexity_min" else level <= expected_level

    actual_map = {
        "risk": args.risk,
        "task_type": args.task_type,
        "validation_strength": args.validation_strength,
        "prompt": Path(args.prompt).stem if args.prompt else None,
        "complexity_band": complexity_band(getattr(args, "complexity_score", None)),
        "instruction_following": getattr(args, "instruction_following", "normal"),
    }
    actual_value = actual_map.get(key)
    if actual_value is None:
        return False
    if expected == "low_or_medium":
        return str(actual_value) in {"low", "medium"}
    return str(actual_value) == expected


def select_model(policy: SelectorPolicy, args: argparse.Namespace) -> tuple[str, str, str | None]:
    for rule in policy.rules:
        if all(condition_matches(key, value, args) for key, value in rule.conditions.items()):
            return rule.select, rule.reason, rule.name
    return policy.default_model, "No explicit rule matched; selected the configured default model tier.", None


def build_model_selection(
    args: argparse.Namespace,
    original_args: argparse.Namespace,
    inferred_routing: InferredRouting,
    project_root: Path,
    output_path: Path,
    selected_tier: str,
    selection_reason: str,
    matched_rule: str | None,
    tier: ModelTier,
    fallbacks: list[str],
    registry: dict[str, ModelTier],
    manual_override: bool,
) -> dict[str, object]:
    run_id = output_path.parent.name
    normalized_task_type = TASK_TYPE_LABELS.get(args.task_type, args.task_type)
    return {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": args.project,
        "task_type": normalized_task_type,
        "workflow_mode": args.task_type,
        "execution_boundary": "automatic_provider_execution_with_validation",
        "risk": args.risk,
        "validation_strength": args.validation_strength,
        "complexity_score": args.complexity_score,
        "complexity_band": complexity_band(args.complexity_score),
        "test_complexity_level": args.test_complexity_level,
        "instruction_following": args.instruction_following,
        "provided_routing_hints": {
            "complexity_score": original_args.complexity_score,
            "test_complexity_level": original_args.test_complexity_level,
            "instruction_following": original_args.instruction_following,
        },
        "inferred_routing_hints": {
            "complexity_score": inferred_routing.complexity_score,
            "complexity_band": complexity_band(inferred_routing.complexity_score),
            "test_complexity_level": inferred_routing.test_complexity_level,
            "detected_risk_keywords": inferred_routing.detected_risk_keywords,
            "explanation": inferred_routing.explanation,
        },
        "prompt": Path(args.prompt).stem if args.prompt else None,
        "selected_tier": selected_tier,
        "selected_model": {
            "provider": tier.provider,
            "model": tier.model,
            "fallback_models": tier.fallback_models,
            "parameters": tier.parameters,
            "use_for": tier.use_for,
        },
        "reason": selection_reason,
        "matched_rule": matched_rule,
        "manual_override_allowed": manual_override,
        "fallbacks": [
            {
                "tier": fallback,
                "provider": registry[fallback].provider if fallback in registry else None,
                "model": registry[fallback].model if fallback in registry else None,
                "fallback_models": registry[fallback].fallback_models if fallback in registry else [],
            }
            for fallback in fallbacks
        ],
        "output_path": relative_path(output_path, project_root),
        "status": "selected",
    }


def select_model_payload(args: argparse.Namespace) -> dict[str, object]:
    project = load_project_config(args.project)
    output_path = resolve_cli_path(args.out, project.root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    registry = load_model_registry()
    policy = load_selector_policy()
    inferred_routing = infer_routing(args, project.root)
    routed_args = effective_args(args, inferred_routing)
    selected_tier, selection_reason, matched_rule = select_model(policy, routed_args)
    if selected_tier not in registry:
        raise ValueError(f"Selected model tier is not defined in model_registry.yaml: {selected_tier}")

    model_selection = build_model_selection(
        args=routed_args,
        original_args=args,
        inferred_routing=inferred_routing,
        project_root=project.root,
        output_path=output_path,
        selected_tier=selected_tier,
        selection_reason=selection_reason,
        matched_rule=matched_rule,
        tier=registry[selected_tier],
        fallbacks=policy.fallbacks.get(selected_tier, []),
        registry=registry,
        manual_override=policy.manual_override,
    )
    output_path.write_text(json.dumps(model_selection, indent=2) + "\n", encoding="utf-8")
    return model_selection


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_routing_args(parser, args)

    project = load_project_config(args.project)
    output_path = resolve_cli_path(args.out, project.root)
    model_selection = select_model_payload(args)

    print(f"project={args.project}")
    print(f"task_type={args.task_type}")
    print(f"risk={args.risk}")
    print(f"selected_tier={model_selection['selected_tier']}")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
