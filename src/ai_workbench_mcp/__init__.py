"""Goose-compatible MCP integration package for AI Workbench."""

from .contracts import SCHEMA_VERSION, WorkbenchResponse, error_envelope, response_envelope
from .core import (
    analyze_runs,
    model_selection_file_response,
    model_selection_response,
    quality_gate_file_response,
    quality_gate_response,
    run_analysis_file_response,
    run_analysis_response,
    quality_gate,
    select_model,
    validate_run,
    validation_file_response,
    validation_response,
)

__all__ = [
    "analyze_runs",
    "SCHEMA_VERSION",
    "WorkbenchResponse",
    "error_envelope",
    "model_selection_file_response",
    "model_selection_response",
    "quality_gate",
    "quality_gate_file_response",
    "quality_gate_response",
    "response_envelope",
    "run_analysis_file_response",
    "run_analysis_response",
    "select_model",
    "validate_run",
    "validation_file_response",
    "validation_response",
]
