"""Compatibility facade for Workbench core MCP operations.

The public import surface stays here while implementation details live under
``ai_workbench_mcp._core``.
"""

from __future__ import annotations

import subprocess as subprocess

from .contracts import JsonObject as JsonObject
from .contracts import error_envelope as error_envelope
from .contracts import response_envelope as response_envelope
from .tools import context_scout as context_scout_tool
from .tools import model_handoff as model_handoff_tool
from .tools import model_select as model_select_tool
from .tools import policy_packs as policy_packs_tool
from .tools import policy_pack_select as policy_pack_select_tool
from .tools import quality_loop as quality_loop_tool
from .tools import run_analyze as run_analyze_tool
from .tools import run_log as run_log_tool
from .tools import validate_run as validate_run_tool
from ._core.common import (
    ALLOWED_EXECUTION_HOSTS,
    ALLOWED_RECORD_MODEL_OUTPUT_STATUSES,
    ALLOWED_RISKS,
    ALLOWED_RUN_STATUSES,
    WORKBENCH_ROOT,
    append_optional,
    confidence,
    has_jsonl_decision,
    jsonl_entries,
    optional_text,
    read_json_artifact,
    require_choice,
    run_tool,
    workbench_path,
    write_json,
)
from ._core.lifecycle import final_prompt_text, open_run, record_execution, selected_model_summary
from ._core.operations import analyze_runs, quality_gate, select_model, select_policy_pack, validate_run
from ._core.policy_selection import (
    AUTO_POLICY_SELECTION_MIN_CONFIDENCE,
    MUTATING_TASK_TYPES,
    auto_policy_selection_not_selected,
    automatic_policy_selection,
    manual_policy_selection,
    policy_pack_for_profile,
    policy_selection_base,
    policy_selection_metadata,
    run_policy_pack_selection,
)
from ._core.responses import (
    model_selection_file_response,
    model_selection_response,
    open_run_response,
    policy_pack_selection_response,
    quality_gate_file_response,
    quality_gate_response,
    record_execution_response,
    run_analysis_file_response,
    run_analysis_response,
    validation_file_response,
    validation_response,
)


_append_optional = append_optional
_workbench_path = workbench_path
_require_choice = require_choice
_jsonl_entries = jsonl_entries
_has_jsonl_decision = has_jsonl_decision
_write_json = write_json
_optional_text = optional_text
_confidence = confidence
_policy_pack_for_profile = policy_pack_for_profile
_policy_selection_base = policy_selection_base
_manual_policy_selection = manual_policy_selection
_auto_policy_selection_not_selected = auto_policy_selection_not_selected
_automatic_policy_selection = automatic_policy_selection
_run_policy_pack_selection = run_policy_pack_selection
_policy_selection_metadata = policy_selection_metadata
_final_prompt_text = final_prompt_text
_selected_model_summary = selected_model_summary


__all__ = [
    "ALLOWED_EXECUTION_HOSTS",
    "ALLOWED_RECORD_MODEL_OUTPUT_STATUSES",
    "ALLOWED_RISKS",
    "ALLOWED_RUN_STATUSES",
    "AUTO_POLICY_SELECTION_MIN_CONFIDENCE",
    "MUTATING_TASK_TYPES",
    "WORKBENCH_ROOT",
    "JsonObject",
    "analyze_runs",
    "context_scout_tool",
    "model_handoff_tool",
    "model_selection_file_response",
    "model_selection_response",
    "model_select_tool",
    "open_run",
    "open_run_response",
    "policy_pack_select_tool",
    "policy_pack_selection_response",
    "policy_packs_tool",
    "quality_gate",
    "quality_gate_file_response",
    "quality_gate_response",
    "quality_loop_tool",
    "read_json_artifact",
    "record_execution",
    "record_execution_response",
    "run_analyze_tool",
    "run_analysis_file_response",
    "run_analysis_response",
    "run_tool",
    "run_log_tool",
    "select_model",
    "select_policy_pack",
    "validate_run",
    "validate_run_tool",
    "validation_file_response",
    "validation_response",
]
