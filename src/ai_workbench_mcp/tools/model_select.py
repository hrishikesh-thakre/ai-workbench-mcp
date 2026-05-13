from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from types import SimpleNamespace

from .config_loader import load_simple_yaml
from .context_scout import WORKBENCH_ROOT, load_project_config, relative_path, resolve_cli_path


@dataclass
class ModelTier:
    name: str
    provider: str
    model: str
    use_for: list[str]
    fallback_models: list[str]
    parameters: dict[str, object]


@dataclass
class ModelRegistryLoad:
    registry: dict[str, ModelTier]
    source: dict[str, object]


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
class RoutingFeedbackPolicy:
    min_runs: int
    strong_acceptance_rate: float
    high_review_rate: float
    high_failure_rate: float


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

MODEL_REGISTRY_PATH = WORKBENCH_ROOT / "configs" / "model_registry.yaml"
LOCAL_MODEL_REGISTRY_PATH = WORKBENCH_ROOT / "configs" / "model_registry.local.yaml"


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
    parser.add_argument("--recipe", help="Optional Goose recipe filename for routing feedback matching.")
    parser.add_argument("--validation-profile", help="Optional validation profile for routing feedback matching.")
    parser.add_argument(
        "--routing-feedback-path",
        help="Optional run_metrics.json or routing_feedback_candidates JSON file from workbench_analyze_runs.",
    )
    parser.add_argument("--out", required=True, help="Path for model_selection.json output.")
    return parser


def validate_routing_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.complexity_score is not None and not 1 <= args.complexity_score <= 25:
        parser.error("--complexity-score must be between 1 and 25.")
    if args.test_complexity_level is not None and not 1 <= args.test_complexity_level <= 8:
        parser.error("--test-complexity-level must be between 1 and 8.")


def safe_relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def recursive_merge(base: object, override: object) -> object:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = recursive_merge(merged[key], value) if key in merged else value
        return merged
    return override


def load_model_registry_data(
    *,
    base_path: Path | None = None,
    local_override_path: Path | None = None,
    registry_root: Path | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    resolved_base = (base_path or MODEL_REGISTRY_PATH).resolve()
    resolved_local = (local_override_path or LOCAL_MODEL_REGISTRY_PATH).resolve()
    root = (registry_root or WORKBENCH_ROOT).resolve()

    base_data = load_simple_yaml(resolved_base)
    local_override_loaded = resolved_local.exists()
    if local_override_loaded:
        override_data = load_simple_yaml(resolved_local)
        merged_data = recursive_merge(base_data, override_data)
    else:
        merged_data = base_data

    if not isinstance(merged_data, dict):
        raise ValueError("model registry must parse to a top-level mapping.")

    source: dict[str, object] = {
        "base_registry_path": safe_relative_path(resolved_base, root),
        "local_override_loaded": local_override_loaded,
    }
    if local_override_loaded:
        source["local_override_path"] = safe_relative_path(resolved_local, root)
    return merged_data, source


def require_string_field(payload: dict[str, object], field_name: str, tier_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"model registry tier '{tier_name}' must define a non-empty {field_name}.")
    return value


def require_use_for(payload: dict[str, object], tier_name: str) -> list[str]:
    value = payload.get("use_for")
    if not isinstance(value, list) or not value:
        raise ValueError(f"model registry tier '{tier_name}' must define a non-empty use_for list.")
    use_for = [str(item) for item in value if item is not None]
    if not use_for:
        raise ValueError(f"model registry tier '{tier_name}' must define a non-empty use_for list.")
    return use_for


def model_registry_from_data(raw_data: dict[str, object]) -> dict[str, ModelTier]:
    models = raw_data.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("model registry must define a non-empty top-level models mapping.")

    tiers: dict[str, ModelTier] = {}
    for name, payload in models.items():
        if not isinstance(payload, dict):
            raise ValueError(f"model registry tier '{name}' must be a mapping.")
        tier_name = str(name)
        fallback_models_value = payload.get("fallback_models", [])
        if fallback_models_value is None:
            fallback_models = []
        elif isinstance(fallback_models_value, list):
            fallback_models = fallback_models_value
        else:
            raise ValueError(f"model registry tier '{tier_name}' fallback_models must be a list when present.")
        parameters_value = payload.get("parameters", {})
        if parameters_value is None:
            parameters = {}
        elif isinstance(parameters_value, dict):
            parameters = parameters_value
        else:
            raise ValueError(f"model registry tier '{tier_name}' parameters must be a mapping when present.")
        tiers[str(name)] = ModelTier(
            name=tier_name,
            provider=require_string_field(payload, "provider", tier_name),
            model=require_string_field(payload, "model", tier_name),
            use_for=require_use_for(payload, tier_name),
            fallback_models=[str(item) for item in fallback_models if item is not None],
            parameters=parameters,
        )
    return tiers


def load_model_registry_with_source(
    *,
    base_path: Path | None = None,
    local_override_path: Path | None = None,
    registry_root: Path | None = None,
) -> ModelRegistryLoad:
    raw_data, source = load_model_registry_data(
        base_path=base_path,
        local_override_path=local_override_path,
        registry_root=registry_root,
    )
    return ModelRegistryLoad(registry=model_registry_from_data(raw_data), source=source)


def load_model_registry(
    *,
    base_path: Path | None = None,
    local_override_path: Path | None = None,
    registry_root: Path | None = None,
) -> dict[str, ModelTier]:
    return load_model_registry_with_source(
        base_path=base_path,
        local_override_path=local_override_path,
        registry_root=registry_root,
    ).registry


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


def validate_selector_references(policy: SelectorPolicy, registry: dict[str, ModelTier]) -> None:
    missing: dict[str, set[str]] = {
        "default_model": set(),
        "rules": set(),
        "fallback_keys": set(),
        "fallback_values": set(),
    }

    if policy.default_model not in registry:
        missing["default_model"].add(policy.default_model)
    for rule in policy.rules:
        if rule.select not in registry:
            missing["rules"].add(rule.select)
    for source_tier, fallback_tiers in policy.fallbacks.items():
        if source_tier not in registry:
            missing["fallback_keys"].add(source_tier)
        for fallback_tier in fallback_tiers:
            if fallback_tier not in registry:
                missing["fallback_values"].add(fallback_tier)

    details = [
        f"{scope}={','.join(sorted(values))}"
        for scope, values in missing.items()
        if values
    ]
    if details:
        raise ValueError(f"model selector references undefined model tier(s): {'; '.join(details)}")


def load_routing_feedback_policy() -> RoutingFeedbackPolicy:
    config_path = WORKBENCH_ROOT / "configs" / "routing_feedback_policy.yaml"
    raw_data = load_simple_yaml(config_path) if config_path.exists() else {}
    return RoutingFeedbackPolicy(
        min_runs=int(raw_data.get("min_runs", 5)),
        strong_acceptance_rate=float(raw_data.get("strong_acceptance_rate", 0.8)),
        high_review_rate=float(raw_data.get("high_review_rate", 0.5)),
        high_failure_rate=float(raw_data.get("high_failure_rate", 0.35)),
    )


def routing_feedback_policy_payload(policy: RoutingFeedbackPolicy) -> dict[str, object]:
    return {
        "min_runs": policy.min_runs,
        "strong_acceptance_rate": policy.strong_acceptance_rate,
        "high_review_rate": policy.high_review_rate,
        "high_failure_rate": policy.high_failure_rate,
    }


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


def safe_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return default


def safe_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def routing_candidate_key(
    *,
    recipe: str | None,
    validation_profile: str | None,
    selected_tier: str | None,
    risk: str | None,
    complexity: str | None,
) -> str:
    return "|".join(
        [
            recipe or "unknown",
            validation_profile or "unknown",
            selected_tier or "unknown",
            risk or "unknown",
            complexity or "unknown",
        ]
    )


def routing_feedback_base(
    *,
    status: str,
    candidate_key: str,
    policy: RoutingFeedbackPolicy,
    recommendation: str,
    reason: str,
    source_path: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": status,
        "candidate_key": candidate_key,
        "candidate": None,
        "policy": routing_feedback_policy_payload(policy),
        "recommendation": recommendation,
        "reason": reason,
    }
    if source_path is not None:
        payload["source_path"] = source_path
    return payload


def normalize_failure_reasons(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {str(key): safe_int(count) for key, count in value.items()}


def normalize_candidate(key: str, value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    required_fields = {"total", "acceptance_rate", "review_rate", "failure_rate"}
    if not required_fields.issubset(value):
        return None
    parts = (key.split("|") + ["unknown"] * 5)[:5]
    recipe, profile, tier, risk, complexity = parts
    top_failure_reasons = value.get("top_failure_reasons", {})
    if top_failure_reasons is not None and not isinstance(top_failure_reasons, dict):
        return None
    return {
        "recipe": str(value.get("recipe") or recipe),
        "validation_profile": str(value.get("validation_profile") or profile),
        "selected_tier": str(value.get("selected_tier") or tier),
        "risk": str(value.get("risk") or risk),
        "complexity_band": str(value.get("complexity_band") or complexity),
        "accepted": safe_int(value.get("accepted")),
        "review_required": safe_int(value.get("review_required")),
        "failed": safe_int(value.get("failed")),
        "other": safe_int(value.get("other")),
        "total": safe_int(value.get("total")),
        "acceptance_rate": round(safe_float(value.get("acceptance_rate")), 2),
        "review_rate": round(safe_float(value.get("review_rate")), 2),
        "failure_rate": round(safe_float(value.get("failure_rate")), 2),
        "top_failure_reasons": normalize_failure_reasons(top_failure_reasons),
    }


def extract_routing_feedback_candidates(payload: object) -> dict[str, dict[str, object]] | None:
    if not isinstance(payload, dict):
        return None
    raw_candidates = payload.get("routing_feedback_candidates") if "routing_feedback_candidates" in payload else payload
    if not isinstance(raw_candidates, dict):
        return None

    candidates: dict[str, dict[str, object]] = {}
    for key, value in raw_candidates.items():
        if not isinstance(key, str):
            return None
        normalized = normalize_candidate(key, value)
        if normalized is None:
            return None
        candidates[key] = normalized
    return candidates


def aggregate_related_candidates(
    *,
    candidates: dict[str, dict[str, object]],
    recipe: str | None,
    validation_profile: str | None,
    risk: str | None,
    complexity: str | None,
    selected_tier: str,
) -> tuple[dict[str, object] | None, list[str]]:
    related: list[tuple[str, dict[str, object]]] = []
    for key, candidate in candidates.items():
        if (
            candidate.get("recipe") == (recipe or "unknown")
            and candidate.get("validation_profile") == (validation_profile or "unknown")
            and candidate.get("risk") == (risk or "unknown")
            and candidate.get("complexity_band") == (complexity or "unknown")
        ):
            related.append((key, candidate))
    if not related:
        return None, []

    accepted = sum(safe_int(candidate.get("accepted")) for _key, candidate in related)
    review_required = sum(safe_int(candidate.get("review_required")) for _key, candidate in related)
    failed = sum(safe_int(candidate.get("failed")) for _key, candidate in related)
    other = sum(safe_int(candidate.get("other")) for _key, candidate in related)
    total = accepted + review_required + failed + other
    failure_reasons: dict[str, int] = {}
    for _key, candidate in related:
        for reason, count in normalize_failure_reasons(candidate.get("top_failure_reasons")).items():
            failure_reasons[reason] = failure_reasons.get(reason, 0) + count

    return (
        {
            "recipe": recipe or "unknown",
            "validation_profile": validation_profile or "unknown",
            "selected_tier": selected_tier,
            "risk": risk or "unknown",
            "complexity_band": complexity or "unknown",
            "accepted": accepted,
            "review_required": review_required,
            "failed": failed,
            "other": other,
            "total": total,
            "acceptance_rate": round(accepted / max(1, total), 2),
            "review_rate": round(review_required / max(1, total), 2),
            "failure_rate": round(failed / max(1, total), 2),
            "top_failure_reasons": dict(sorted(failure_reasons.items(), key=lambda item: item[1], reverse=True)[:5]),
            "related_candidate_keys": [key for key, _candidate in related],
        },
        [key for key, _candidate in related],
    )


def advisory_recommendation(
    *,
    candidate: dict[str, object],
    selected_tier: str,
    policy: RoutingFeedbackPolicy,
) -> tuple[str, str]:
    acceptance_rate = safe_float(candidate.get("acceptance_rate"))
    review_rate = safe_float(candidate.get("review_rate"))
    failure_rate = safe_float(candidate.get("failure_rate"))
    if review_rate >= policy.high_review_rate or failure_rate >= policy.high_failure_rate:
        if selected_tier == "frontier":
            return (
                "require_human_review",
                "Historical feedback shows high review or failure pressure even on the frontier tier.",
            )
        return (
            "consider_escalation",
            "Historical feedback shows high review or failure pressure for this route bucket.",
        )
    if acceptance_rate >= policy.strong_acceptance_rate:
        return (
            "prefer_current_tier",
            "Historical feedback supports the current tier for this route bucket.",
        )
    return (
        "no_change",
        "Historical feedback is sufficient but does not cross an advisory threshold.",
    )


def evaluate_routing_feedback(
    *,
    args: argparse.Namespace,
    project_root: Path,
    selected_tier: str,
    policy: RoutingFeedbackPolicy,
) -> dict[str, object]:
    recipe = getattr(args, "recipe", None)
    validation_profile = getattr(args, "validation_profile", None)
    complexity = complexity_band(getattr(args, "complexity_score", None))
    candidate_key = routing_candidate_key(
        recipe=recipe,
        validation_profile=validation_profile,
        selected_tier=selected_tier,
        risk=getattr(args, "risk", None),
        complexity=complexity,
    )
    path_text = getattr(args, "routing_feedback_path", None)
    if not path_text:
        return routing_feedback_base(
            status="not_provided",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="no_change",
            reason="No routing feedback path was provided.",
        )

    feedback_path = resolve_cli_path(str(path_text), project_root)
    source_path = relative_path(feedback_path, project_root)
    if not feedback_path.exists():
        return routing_feedback_base(
            status="source_missing",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="no_change",
            reason="Routing feedback source was not found; deterministic selection was used.",
            source_path=source_path,
        )

    try:
        payload = json.loads(feedback_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return routing_feedback_base(
            status="source_invalid",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="no_change",
            reason="Routing feedback source could not be parsed as valid JSON.",
            source_path=source_path,
        )

    candidates = extract_routing_feedback_candidates(payload)
    if candidates is None:
        return routing_feedback_base(
            status="source_invalid",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="no_change",
            reason="Routing feedback source does not contain valid routing_feedback_candidates.",
            source_path=source_path,
        )
    if not candidates:
        return routing_feedback_base(
            status="no_candidates",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="collect_more_evidence",
            reason="Routing feedback source did not contain any candidates.",
            source_path=source_path,
        )

    candidate = candidates.get(candidate_key)
    if candidate is None:
        related_candidate, related_keys = aggregate_related_candidates(
            candidates=candidates,
            recipe=recipe,
            validation_profile=validation_profile,
            risk=getattr(args, "risk", None),
            complexity=complexity,
            selected_tier=selected_tier,
        )
        if related_candidate is not None and safe_int(related_candidate.get("total")) < policy.min_runs:
            result = routing_feedback_base(
                status="insufficient_evidence",
                candidate_key=candidate_key,
                policy=policy,
                recommendation="collect_more_evidence",
                reason="Related routing feedback exists, but not enough evidence exists for a tier-specific advisory.",
                source_path=source_path,
            )
            result["candidate"] = related_candidate
            result["related_candidate_keys"] = related_keys
            return result
        return routing_feedback_base(
            status="no_match",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="collect_more_evidence",
            reason="No routing feedback candidate matched this route bucket.",
            source_path=source_path,
        )

    if safe_int(candidate.get("total")) < policy.min_runs:
        result = routing_feedback_base(
            status="insufficient_evidence",
            candidate_key=candidate_key,
            policy=policy,
            recommendation="collect_more_evidence",
            reason="Matched routing feedback has fewer runs than the configured minimum.",
            source_path=source_path,
        )
        result["candidate"] = candidate
        return result

    recommendation, reason = advisory_recommendation(
        candidate=candidate,
        selected_tier=selected_tier,
        policy=policy,
    )
    result = routing_feedback_base(
        status="advisory",
        candidate_key=candidate_key,
        policy=policy,
        recommendation=recommendation,
        reason=reason,
        source_path=source_path,
    )
    result["candidate"] = candidate
    return result


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
    routing_feedback: dict[str, object] | None = None,
    registry_source: dict[str, object] | None = None,
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
        "recipe": getattr(args, "recipe", None),
        "validation_profile": getattr(args, "validation_profile", None),
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
        "model_registry": registry_source
        or {
            "base_registry_path": "configs/model_registry.yaml",
            "local_override_loaded": False,
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
        "routing_feedback": routing_feedback
        or routing_feedback_base(
            status="not_provided",
            candidate_key=routing_candidate_key(
                recipe=getattr(args, "recipe", None),
                validation_profile=getattr(args, "validation_profile", None),
                selected_tier=selected_tier,
                risk=getattr(args, "risk", None),
                complexity=complexity_band(getattr(args, "complexity_score", None)),
            ),
            policy=load_routing_feedback_policy(),
            recommendation="no_change",
            reason="No routing feedback path was provided.",
        ),
        "status": "selected",
    }


def select_model_payload(
    args: argparse.Namespace,
    *,
    registry_base_path: Path | None = None,
    registry_local_override_path: Path | None = None,
    registry_root: Path | None = None,
) -> dict[str, object]:
    project = load_project_config(args.project)
    output_path = resolve_cli_path(args.out, project.root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    registry_load = load_model_registry_with_source(
        base_path=registry_base_path,
        local_override_path=registry_local_override_path,
        registry_root=registry_root,
    )
    registry = registry_load.registry
    policy = load_selector_policy()
    validate_selector_references(policy, registry)
    feedback_policy = load_routing_feedback_policy()
    inferred_routing = infer_routing(args, project.root)
    routed_args = effective_args(args, inferred_routing)
    selected_tier, selection_reason, matched_rule = select_model(policy, routed_args)
    if selected_tier not in registry:
        raise ValueError(f"Selected model tier is not defined in model_registry.yaml: {selected_tier}")
    routing_feedback = evaluate_routing_feedback(
        args=routed_args,
        project_root=project.root,
        selected_tier=selected_tier,
        policy=feedback_policy,
    )

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
        routing_feedback=routing_feedback,
        registry_source=registry_load.source,
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
