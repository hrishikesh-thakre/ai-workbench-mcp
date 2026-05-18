from __future__ import annotations

from pathlib import Path

from .config_loader import load_simple_yaml
from .context_scout import WORKBENCH_ROOT


POLICY_PACKS_PATH = WORKBENCH_ROOT / "configs" / "policy_packs.yaml"
PRODUCT_POLICY_PACK_NAMES = (
    "docs_only",
    "low_risk_bug_fix",
    "test_fix",
    "api_contract_change",
    "security_privacy_sensitive",
)

REQUIRED_LIST_FIELDS = (
    "allowed_files",
    "required_tests",
    "required_evidence",
    "review_triggers",
    "blocker_rules",
)
REQUIRED_REASON_CODE_KEYS = (
    "accepted",
    "required_test_missing",
    "required_test_failed",
    "required_tests_passed",
)


def _as_mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a mapping.")
    return value


def _string_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list.")
    items = [str(item).strip() for item in value if str(item).strip()]
    if not items:
        raise ValueError(f"{label} must not be empty.")
    return items


def normalize_policy_pack(
    pack_name: str,
    pack_data: dict[str, object],
    *,
    source: str,
) -> dict[str, object]:
    configured_name = str(pack_data.get("name", pack_name)).strip()
    if configured_name != pack_name:
        raise ValueError(f"Policy pack {pack_name} declares mismatched name {configured_name}.")

    version = str(pack_data.get("version", "")).strip()
    if not version:
        raise ValueError(f"Policy pack {pack_name} must declare a version.")

    normalized: dict[str, object] = {
        "name": pack_name,
        "version": version,
        "source": source,
    }

    for field in REQUIRED_LIST_FIELDS:
        normalized[field] = _string_list(
            pack_data.get(field),
            label=f"Policy pack {pack_name}.{field}",
        )

    reason_codes = _as_mapping(
        pack_data.get("reason_codes"),
        label=f"Policy pack {pack_name}.reason_codes",
    )
    normalized_reason_codes: dict[str, str] = {}
    for key in REQUIRED_REASON_CODE_KEYS:
        code = str(reason_codes.get(key, "")).strip()
        if not code:
            raise ValueError(f"Policy pack {pack_name}.reason_codes.{key} must not be empty.")
        normalized_reason_codes[key] = code
    normalized["reason_codes"] = normalized_reason_codes
    return normalized


def load_policy_pack_catalog(config_path: Path = POLICY_PACKS_PATH) -> dict[str, dict[str, object]]:
    raw_data = load_simple_yaml(config_path)
    packs_data = _as_mapping(raw_data.get("policy_packs"), label="policy_packs")
    configured_names = set(packs_data)
    expected_names = set(PRODUCT_POLICY_PACK_NAMES)
    if configured_names != expected_names:
        expected = ", ".join(PRODUCT_POLICY_PACK_NAMES)
        actual = ", ".join(sorted(configured_names)) or "none"
        raise ValueError(
            "First-class policy-pack catalog must define exactly "
            f"{expected}. Found: {actual}."
        )

    catalog: dict[str, dict[str, object]] = {}
    for pack_name in PRODUCT_POLICY_PACK_NAMES:
        pack_data = _as_mapping(packs_data.get(pack_name), label=f"policy_packs.{pack_name}")
        try:
            source = config_path.relative_to(WORKBENCH_ROOT).as_posix()
        except ValueError:
            source = config_path.as_posix()
        catalog[pack_name] = normalize_policy_pack(
            pack_name,
            pack_data,
            source=source,
        )
    return catalog


def resolve_policy_pack_reference(
    profile_name: str,
    profile_data: dict[str, object],
    catalog: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    raw_policy_pack = profile_data.get("policy_pack")
    if not raw_policy_pack:
        return {}

    catalog = catalog or load_policy_pack_catalog()
    if isinstance(raw_policy_pack, str):
        pack_name = raw_policy_pack.strip()
        if pack_name in catalog:
            return dict(catalog[pack_name])
        raise ValueError(f"Validation profile {profile_name} references unknown policy pack: {pack_name}")

    if not isinstance(raw_policy_pack, dict):
        raise ValueError(f"Validation profile {profile_name} policy_pack must be a string or mapping.")

    pack_name = str(raw_policy_pack.get("name", "")).strip()
    if pack_name in catalog:
        return dict(catalog[pack_name])

    if all(field in raw_policy_pack for field in (*REQUIRED_LIST_FIELDS, "reason_codes")):
        return normalize_policy_pack(
            pack_name or profile_name,
            raw_policy_pack,
            source="validation_profiles.yaml",
        )

    raise ValueError(f"Validation profile {profile_name} declares an incomplete policy_pack reference.")
