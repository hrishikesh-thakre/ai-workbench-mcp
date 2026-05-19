from __future__ import annotations

from pathlib import Path

from .config_loader import load_simple_yaml
from .context_scout import WORKBENCH_ROOT


POLICY_PACKS_PATH = WORKBENCH_ROOT / "configs" / "policy_packs.yaml"
VALIDATION_PROFILES_PATH = WORKBENCH_ROOT / "configs" / "validation_profiles.yaml"
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

    validation_profile = str(pack_data.get("validation_profile", "")).strip()
    if not validation_profile:
        raise ValueError(f"Policy pack {pack_name} must declare a validation_profile.")

    normalized: dict[str, object] = {
        "name": pack_name,
        "version": version,
        "validation_profile": validation_profile,
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


def _validation_profiles_path_for(config_path: Path) -> Path:
    sibling_path = config_path.with_name("validation_profiles.yaml")
    if sibling_path.exists():
        return sibling_path
    return VALIDATION_PROFILES_PATH


def _policy_pack_name_from_profile(profile_data: object) -> str:
    if not isinstance(profile_data, dict):
        return ""
    policy_pack = profile_data.get("policy_pack")
    if isinstance(policy_pack, str):
        return policy_pack.strip()
    if isinstance(policy_pack, dict):
        return str(policy_pack.get("name", "")).strip()
    return ""


def validate_policy_pack_profile_mappings(
    catalog: dict[str, dict[str, object]],
    *,
    validation_profiles_path: Path,
) -> None:
    raw_profiles = load_simple_yaml(validation_profiles_path)
    profiles_data = _as_mapping(raw_profiles.get("profiles"), label="profiles")

    mapped_profiles: dict[str, str] = {}
    for pack_name, pack_data in catalog.items():
        validation_profile = str(pack_data.get("validation_profile", "")).strip()
        if validation_profile not in profiles_data:
            raise ValueError(
                f"Policy pack {pack_name} maps to unknown validation profile: {validation_profile}"
            )
        previous_pack = mapped_profiles.get(validation_profile)
        if previous_pack is not None:
            raise ValueError(
                "Policy packs must not share a validation profile without an explicit "
                f"mapping design. {previous_pack} and {pack_name} both map to {validation_profile}."
            )
        mapped_profiles[validation_profile] = pack_name

    for profile_name, profile_data in profiles_data.items():
        pack_name = _policy_pack_name_from_profile(profile_data)
        if pack_name not in catalog:
            continue
        mapped_profile = str(catalog[pack_name].get("validation_profile", "")).strip()
        if mapped_profile != profile_name:
            raise ValueError(
                f"Validation profile {profile_name} references policy pack {pack_name}, "
                f"but the catalog maps that pack to {mapped_profile}."
            )


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
    validate_policy_pack_profile_mappings(
        catalog,
        validation_profiles_path=_validation_profiles_path_for(config_path),
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
