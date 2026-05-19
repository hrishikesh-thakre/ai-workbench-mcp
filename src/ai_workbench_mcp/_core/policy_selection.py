"""Policy-pack selection helpers used while opening a run."""

from __future__ import annotations

from ai_workbench_mcp.contracts import JsonObject
from ai_workbench_mcp.tools import policy_packs as policy_packs_tool
from ai_workbench_mcp.tools import policy_pack_select as policy_pack_select_tool
from ai_workbench_mcp.tools import validate_run as validate_run_tool

from .common import confidence, optional_text


AUTO_POLICY_SELECTION_MIN_CONFIDENCE = 0.7
MUTATING_TASK_TYPES = {"implementation", "bug investigation", "test development", "general investigation"}


def policy_pack_for_profile(
    catalog: dict[str, dict[str, object]],
    validation_profile: str,
) -> str | None:
    for pack_name, pack_data in catalog.items():
        if str(pack_data.get("validation_profile", "")).strip() == validation_profile:
            return pack_name
    return None


def policy_selection_base(
    *,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject:
    return {
        "schema_version": 1,
        "operation": "workbench_select_policy_pack",
        "artifact": "policy_pack_selection",
        "selection_attempted": True,
        "auto_select_policy_pack": auto_select_policy_pack,
        "requested_policy_pack": policy_pack,
        "requested_validation_profile": validation_profile,
    }


def manual_policy_selection(
    *,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject:
    base = policy_selection_base(
        auto_select_policy_pack=auto_select_policy_pack,
        policy_pack=policy_pack,
        validation_profile=validation_profile,
    )
    try:
        catalog = policy_packs_tool.load_policy_pack_catalog()
        selected_pack: str | None = None
        selected_profile: str | None = None

        if policy_pack is not None:
            pack_data = catalog.get(policy_pack)
            if pack_data is None:
                raise ValueError(f"Unknown policy pack: {policy_pack}")
            selected_pack = policy_pack
            selected_profile = str(pack_data.get("validation_profile", "")).strip() or None
            if selected_profile is None:
                raise ValueError(f"Policy pack {policy_pack} does not map to a validation profile.")

        if validation_profile is not None:
            profile = validate_run_tool.load_validation_profile(validation_profile)
            selected_profile = profile.name
            profile_pack = policy_pack_for_profile(catalog, profile.name)
            profile_policy_pack = profile.policy_pack if isinstance(profile.policy_pack, dict) else {}
            profile_pack = optional_text(profile_policy_pack.get("name")) or profile_pack
            if policy_pack is not None and selected_pack is not None:
                mapped_profile = str(catalog[selected_pack].get("validation_profile", "")).strip()
                if mapped_profile != profile.name:
                    raise ValueError(
                        "Conflicting policy_pack and validation_profile: "
                        f"{policy_pack} maps to {mapped_profile}, but validation_profile={profile.name}."
                    )
            selected_pack = profile_pack or selected_pack

        if selected_profile is None:
            raise ValueError("Manual policy-pack selection did not resolve a validation profile.")

        validate_run_tool.load_validation_profile(selected_profile)
        mode = "manual_validation_profile" if validation_profile is not None else "manual_policy_pack"
        if validation_profile is not None and policy_pack is not None:
            reason = "Explicit validation_profile was used; explicit policy_pack mapped to the same profile."
        elif validation_profile is not None:
            reason = "Explicit validation_profile was used."
        else:
            reason = "Explicit policy_pack was mapped through the catalog to its validation profile."
        return {
            **base,
            "status": "selected",
            "ok": True,
            "blocking": False,
            "policy_pack": selected_pack,
            "validation_profile": selected_profile,
            "recommended_policy_pack": selected_pack,
            "recommended_validation_profile": selected_profile,
            "profile_selection_mode": mode,
            "policy_pack_selection_mode": mode,
            "confidence": 1.0,
            "reason": reason,
            "matched_signals": [],
            "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
        }
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "ok": False,
            "blocking": True,
            "policy_pack": None,
            "validation_profile": validation_profile,
            "recommended_policy_pack": None,
            "recommended_validation_profile": validation_profile,
            "profile_selection_mode": "manual_error",
            "policy_pack_selection_mode": "manual_error",
            "confidence": 0.0,
            "reason": str(exc),
            "matched_signals": [],
            "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
        }


def auto_policy_selection_not_selected(base: JsonObject, reason: str) -> JsonObject:
    return {
        **base,
        "status": "not_selected",
        "ok": False,
        "blocking": False,
        "policy_pack": None,
        "validation_profile": None,
        "recommended_policy_pack": None,
        "recommended_validation_profile": None,
        "profile_selection_mode": "auto_advisory",
        "policy_pack_selection_mode": "auto_advisory",
        "confidence": 0.0,
        "reason": reason,
        "matched_signals": [],
        "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
    }


def automatic_policy_selection(
    *,
    task: str,
    task_type: str,
    prompt: str,
    risk: str,
    changed_files: list[str] | None,
) -> JsonObject:
    base = policy_selection_base(
        auto_select_policy_pack=True,
        policy_pack=None,
        validation_profile=None,
    )
    try:
        selector_payload = policy_pack_select_tool.select_policy_pack_payload(
            task_text=task,
            task_type=task_type,
            changed_files=changed_files or [],
            prompt=prompt,
            risk=risk,
        )
    except Exception as exc:
        return auto_policy_selection_not_selected(base, f"Automatic policy-pack selection failed: {exc}")

    status = str(selector_payload.get("status") or "")
    ok = bool(selector_payload.get("ok", status == "selected"))
    selected_pack = optional_text(selector_payload.get("recommended_policy_pack"))
    selected_profile = optional_text(selector_payload.get("recommended_validation_profile"))
    if not ok or status != "selected" or selected_pack is None or selected_profile is None:
        return auto_policy_selection_not_selected(
            base,
            "Automatic policy-pack selection did not return a usable policy pack and validation profile.",
        )

    selected_confidence = confidence(selector_payload.get("confidence"), 0.0)
    if selected_confidence < AUTO_POLICY_SELECTION_MIN_CONFIDENCE:
        return auto_policy_selection_not_selected(
            base,
            "Automatic policy-pack selection confidence "
            f"{selected_confidence:.2f} is below the required {AUTO_POLICY_SELECTION_MIN_CONFIDENCE:.2f}; "
            "pass validation_profile or policy_pack explicitly.",
        )

    if not changed_files and selected_pack != "docs_only" and task_type in MUTATING_TASK_TYPES:
        return auto_policy_selection_not_selected(
            base,
            "Changed files are required before automatic policy-pack selection can choose a "
            f"mutating validation profile for task_type={task_type}.",
        )

    try:
        catalog = policy_packs_tool.load_policy_pack_catalog()
        pack_data = catalog.get(selected_pack)
        if pack_data is None:
            raise ValueError(f"recommended policy pack is not in the catalog: {selected_pack}")
        mapped_profile = str(pack_data.get("validation_profile", "")).strip()
        if mapped_profile != selected_profile:
            raise ValueError(
                f"recommended policy pack {selected_pack} maps to {mapped_profile}, "
                f"not {selected_profile}"
            )
        validate_run_tool.load_validation_profile(selected_profile)
    except Exception as exc:
        return auto_policy_selection_not_selected(
            base,
            f"Automatic policy-pack selection was not usable: {exc}",
        )

    mode = str(selector_payload.get("profile_selection_mode") or "auto_advisory")
    return {
        **base,
        **selector_payload,
        "operation": "workbench_select_policy_pack",
        "artifact": "policy_pack_selection",
        "selection_attempted": True,
        "auto_select_policy_pack": True,
        "requested_policy_pack": None,
        "requested_validation_profile": None,
        "status": "selected",
        "ok": True,
        "blocking": False,
        "policy_pack": selected_pack,
        "validation_profile": selected_profile,
        "profile_selection_mode": mode,
        "policy_pack_selection_mode": mode,
        "confidence": selected_confidence,
    }


def run_policy_pack_selection(
    *,
    task: str,
    task_type: str,
    prompt: str,
    risk: str,
    changed_files: list[str] | None,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject | None:
    requested_pack = optional_text(policy_pack)
    requested_profile = optional_text(validation_profile)
    if requested_pack is None and requested_profile is None and not auto_select_policy_pack:
        return None
    if requested_pack is not None or requested_profile is not None:
        return manual_policy_selection(
            auto_select_policy_pack=auto_select_policy_pack,
            policy_pack=requested_pack,
            validation_profile=requested_profile,
        )
    return automatic_policy_selection(
        task=task,
        task_type=task_type,
        prompt=prompt,
        risk=risk,
        changed_files=changed_files,
    )


def policy_selection_metadata(selection: JsonObject | None) -> JsonObject:
    if not selection or selection.get("status") != "selected":
        return {}
    validation_profile = optional_text(selection.get("validation_profile"))
    if validation_profile is None:
        return {}
    mode = optional_text(selection.get("policy_pack_selection_mode")) or optional_text(
        selection.get("profile_selection_mode")
    )
    return {
        "policy_pack": optional_text(selection.get("policy_pack")),
        "validation_profile": validation_profile,
        "policy_pack_selection_mode": mode,
        "policy_pack_selection_confidence": confidence(selection.get("confidence"), 0.0),
    }

