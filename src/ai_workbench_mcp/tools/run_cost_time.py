from __future__ import annotations

from pathlib import Path

from .config_loader import load_simple_yaml


def as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def explicit_duration_ms(payload: dict[str, object]) -> int | None:
    for field_name in ("duration_ms", "elapsed_ms", "latency_ms", "wall_time_ms"):
        value = as_float(payload.get(field_name))
        if value is not None and value >= 0:
            return int(round(value))
    for field_name in ("duration_seconds", "elapsed_seconds", "latency_seconds", "wall_time_seconds"):
        value = as_float(payload.get(field_name))
        if value is not None and value >= 0:
            return int(round(value * 1000))
    return None


def format_duration_ms(duration_ms: object, has_evidence: bool = True) -> str:
    value = as_int(duration_ms)
    if not has_evidence or value is None:
        return "not recorded"
    if value >= 1000:
        return f"{value / 1000:.2f}s"
    return f"{value}ms"


def format_usd(amount: object, has_evidence: bool = True) -> str:
    value = as_float(amount)
    if not has_evidence or value is None:
        return "not recorded"
    rendered = f"{value:.8f}".rstrip("0").rstrip(".")
    return f"${rendered or '0'}"


def selected_model_parts(selection: dict[str, object], cost_time: dict[str, object]) -> tuple[str, str]:
    selected_model = as_dict(selection.get("selected_model"))
    provider = selected_model.get("provider") or selection.get("provider")
    model = selected_model.get("model") or selection.get("model")
    if not provider:
        providers = as_dict(cost_time.get("providers"))
        provider = next(iter(providers), None)
    if not model:
        models = as_dict(cost_time.get("models"))
        model = next(iter(models), None)
    return (str(provider) if provider else "unknown", str(model) if model else "unknown")


def first_non_none(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def load_runtime_config() -> dict[str, object]:
    config_path = Path(__file__).resolve().parent.parent / "configs" / "litellm.yaml"
    if not config_path.exists():
        return {}
    return load_simple_yaml(config_path)


def model_pricing(runtime: dict[str, object], model: str) -> dict[str, object]:
    providers = as_dict(runtime.get("providers"))
    litellm = as_dict(providers.get("litellm"))
    pricing = as_dict(litellm.get("model_pricing_usd_per_1m"))
    return as_dict(pricing.get(model))


def usage_summary_from_metadata(metadata: dict[str, object]) -> dict[str, object]:
    existing = as_dict(metadata.get("usage_summary"))
    if existing:
        return existing

    attempts = metadata.get("attempts", [])
    for attempt in reversed(attempts) if isinstance(attempts, list) else []:
        attempt_dict = as_dict(attempt)
        if attempt_dict.get("status") != "completed":
            continue
        usage = as_dict(attempt_dict.get("usage"))
        if not usage:
            continue
        prompt_tokens = as_int(usage.get("prompt_tokens"))
        completion_tokens = as_int(usage.get("completion_tokens"))
        total_tokens = as_int(usage.get("total_tokens"))
        cached_input_tokens = as_int(
            first_non_none(
                as_int(usage.get("prompt_cache_hit_tokens")),
                as_int(usage.get("cache_read_input_tokens")),
                as_int(usage.get("cached_tokens")),
            )
        )
        if cached_input_tokens is not None and prompt_tokens is not None:
            cached_input_tokens = max(0, min(cached_input_tokens, prompt_tokens))
        uncached_input_tokens = (
            prompt_tokens - cached_input_tokens
            if prompt_tokens is not None and cached_input_tokens is not None
            else prompt_tokens
        )
        summary: dict[str, object] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        if cached_input_tokens is not None:
            summary["cached_input_tokens"] = cached_input_tokens
        if uncached_input_tokens is not None:
            summary["uncached_input_tokens"] = uncached_input_tokens
        return summary
    return {}


def duration_ms_from_metadata(metadata: dict[str, object]) -> int | None:
    direct_duration_ms = explicit_duration_ms(metadata)
    if direct_duration_ms is not None:
        return direct_duration_ms

    attempts = metadata.get("attempts", [])
    total_duration_ms = 0
    found_duration = False
    for attempt in attempts if isinstance(attempts, list) else []:
        attempt_duration_ms = explicit_duration_ms(as_dict(attempt))
        if attempt_duration_ms is None:
            continue
        total_duration_ms += attempt_duration_ms
        found_duration = True
    return total_duration_ms if found_duration else None


def validation_duration_ms(report: dict[str, object]) -> int | None:
    total_duration_ms = 0
    found_duration = False
    for command in report.get("commands_run", []) if isinstance(report.get("commands_run", []), list) else []:
        command_duration_ms = explicit_duration_ms(as_dict(command))
        if command_duration_ms is None:
            continue
        total_duration_ms += command_duration_ms
        found_duration = True
    return total_duration_ms if found_duration else None


def successful_attempt_model(metadata: dict[str, object]) -> str:
    attempts = metadata.get("attempts", [])
    for attempt in reversed(attempts) if isinstance(attempts, list) else []:
        attempt_dict = as_dict(attempt)
        if attempt_dict.get("status") == "completed" and attempt_dict.get("model"):
            return str(attempt_dict.get("model"))
    return str(metadata.get("model", ""))


def estimate_cost_from_metadata(metadata: dict[str, object], runtime: dict[str, object]) -> tuple[float | None, str | None]:
    direct_cost = as_float(metadata.get("estimated_cost_usd"))
    direct_source = metadata.get("pricing_source")
    if direct_cost is not None:
        return direct_cost, str(direct_source) if direct_source else None

    usage_summary = usage_summary_from_metadata(metadata)
    if not usage_summary:
        return None, None

    model = successful_attempt_model(metadata)
    pricing = model_pricing(runtime, model)
    input_rate = as_float(pricing.get("input_tokens"))
    cached_input_rate = as_float(pricing.get("cached_input_tokens"))
    output_rate = as_float(pricing.get("output_tokens"))
    if input_rate is None or cached_input_rate is None or output_rate is None:
        return None, None

    prompt_tokens = as_int(usage_summary.get("prompt_tokens"))
    completion_tokens = as_int(usage_summary.get("completion_tokens"))
    cached_input_tokens = as_int(usage_summary.get("cached_input_tokens")) or 0
    uncached_input_tokens = as_int(usage_summary.get("uncached_input_tokens"))
    if uncached_input_tokens is None and prompt_tokens is not None:
        uncached_input_tokens = max(0, prompt_tokens - cached_input_tokens)
    if uncached_input_tokens is None and completion_tokens is None:
        return None, None

    estimated_cost_usd = (
        ((uncached_input_tokens or 0) * input_rate)
        + (cached_input_tokens * cached_input_rate)
        + ((completion_tokens or 0) * output_rate)
    ) / 1_000_000
    return round(estimated_cost_usd, 8), str(pricing.get("source")) if pricing.get("source") else None

