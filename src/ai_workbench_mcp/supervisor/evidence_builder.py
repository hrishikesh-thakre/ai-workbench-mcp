from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..evidence_gate.acceptance_report import write_csv_report, write_report
from .daemon_state import utc_now
from ..evidence_gate.gate_engine import run_acceptance
from ..evidence_gate.types import Decision, Severity
from .validation_runner import CODE_CHANGE_TASK_TYPES, VALIDATION_MISSING, run_validation


DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value or "unknown").strip("-")
    return cleaned[:80] or "unknown"


def make_run_id(agent: str, session_id: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{_safe_id(agent)}-{_safe_id(session_id)}"


def _run_git(project_dir: str, args: list[str], timeout: int = 20) -> tuple[int | None, str, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except Exception as exc:
        return None, "", str(exc)


def _relative_evidence_prefix(project_dir: str, evidence_root: str) -> str:
    try:
        root = Path(project_dir).resolve()
        evidence = Path(evidence_root).resolve()
        rel = evidence.relative_to(root)
    except (OSError, ValueError):
        return ""
    return str(rel).replace("\\", "/").rstrip("/") + "/"


def _filter_evidence_status(status: str, project_dir: str, evidence_root: str) -> str:
    prefix = _relative_evidence_prefix(project_dir, evidence_root)
    if not prefix:
        return status
    kept: list[str] = []
    for line in status.splitlines():
        if len(line) < 4:
            kept.append(line)
            continue
        path = line[3:].strip().replace("\\", "/")
        if path == prefix.rstrip("/") or path.startswith(prefix):
            continue
        kept.append(line)
    return "\n".join(kept)


def _git_status(project_dir: str, evidence_root: str) -> str:
    code, stdout, stderr = _run_git(project_dir, ["status", "--short"])
    if code == 0:
        filtered = _filter_evidence_status(stdout, project_dir, evidence_root).strip()
        return filtered or "(clean)"
    return f"(unavailable)\n{stderr.strip()}".strip()


def _git_diff(project_dir: str) -> str:
    code, stdout, stderr = _run_git(project_dir, ["diff", "--"])
    if code == 0:
        return stdout if stdout.strip() else "(no diff)\n"
    return f"(diff unavailable)\n{stderr.strip()}\n"


def _git_changed_files(project_dir: str, evidence_root: str = "") -> list[str]:
    code, stdout, _stderr = _run_git(project_dir, ["diff", "--name-only", "--"])
    changed = [line.strip() for line in stdout.splitlines() if line.strip()] if code == 0 else []
    code_status, status, _stderr_status = _run_git(project_dir, ["status", "--short"])
    if code_status == 0:
        for line in status.splitlines():
            if not line.strip():
                continue
            path = line[3:].strip()
            if path and path not in changed:
                changed.append(path)
    prefix = _relative_evidence_prefix(project_dir, evidence_root) if evidence_root else ""
    if prefix:
        changed = [
            item for item in changed
            if item.replace("\\", "/") != prefix.rstrip("/")
            and not item.replace("\\", "/").startswith(prefix)
        ]
    return sorted(set(changed))


def _inventory(project_dir: str, evidence_root: str) -> dict[str, Any]:
    root = Path(project_dir).resolve()
    evidence_path = Path(evidence_root).resolve()
    files: list[dict[str, Any]] = []

    for current, dirs, filenames in os.walk(root):
        cur_path = Path(current)
        dirs[:] = [
            d for d in dirs
            if d not in DEFAULT_EXCLUDES
            and not str((cur_path / d).resolve()).startswith(str(evidence_path))
        ]
        for filename in filenames:
            path = cur_path / filename
            try:
                resolved = path.resolve()
                if str(resolved).startswith(str(evidence_path)):
                    continue
                rel = resolved.relative_to(root)
                stat = resolved.stat()
            except (OSError, ValueError):
                continue
            files.append({
                "path": str(rel).replace("\\", "/"),
                "size_bytes": stat.st_size,
            })

    files.sort(key=lambda item: item["path"])
    return {
        "schema": "ai-workbench.inventory.v1",
        "generated_at": utc_now(),
        "root": str(root),
        "total_files": len(files),
        "files": files,
        "excluded_dirs": sorted(DEFAULT_EXCLUDES),
    }


class EvidenceRunBuilder:
    def __init__(
        self,
        project_dir: str,
        evidence_root: str,
        task_type: str,
        agent: str,
        session_id: str,
        policy: str = "",
        run_id: str | None = None,
        run_path: str | None = None,
        late_snapshot: bool = False,
    ) -> None:
        self.project_dir = str(Path(project_dir).expanduser().resolve())
        self.evidence_root = str(Path(evidence_root).expanduser().resolve())
        self.task_type = task_type or "audit"
        self.agent = agent
        self.session_id = session_id or "unknown"
        self.policy = policy or ""
        self.run_id = run_id or make_run_id(agent, self.session_id)
        self.run_path = Path(run_path) if run_path else Path(self.evidence_root) / self.run_id
        self.late_snapshot = late_snapshot
        self.metadata_path = self.run_path / "metadata.json"

    @classmethod
    def create(
        cls,
        project_dir: str,
        evidence_root: str,
        task_type: str,
        agent: str,
        session_id: str,
        policy: str = "",
        late_snapshot: bool = False,
    ) -> "EvidenceRunBuilder":
        builder = cls(project_dir, evidence_root, task_type, agent, session_id, policy, late_snapshot=late_snapshot)
        builder.initialize()
        return builder

    @classmethod
    def from_existing(cls, run_path: str, project_dir: str, evidence_root: str, task_type: str, policy: str = "") -> "EvidenceRunBuilder":
        metadata_path = Path(run_path) / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.is_file():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                metadata = {}
        return cls(
            project_dir=project_dir,
            evidence_root=evidence_root,
            task_type=task_type,
            agent=metadata.get("agent", "unknown"),
            session_id=metadata.get("session_id", "unknown"),
            policy=policy or metadata.get("policy", ""),
            run_id=metadata.get("run_id") or Path(run_path).name,
            run_path=run_path,
            late_snapshot=bool(metadata.get("late_snapshot")),
        )

    def initialize(self) -> None:
        (self.run_path / "workspace").mkdir(parents=True, exist_ok=True)
        (self.run_path / "validation").mkdir(parents=True, exist_ok=True)
        (self.run_path / "artifacts").mkdir(parents=True, exist_ok=True)
        self._write_metadata({
            "schema": "ai-workbench.run.v1",
            "run_id": self.run_id,
            "agent": self.agent,
            "session_id": self.session_id,
            "project_dir": self.project_dir,
            "evidence_root": self.evidence_root,
            "task_type": self.task_type,
            "policy": self.policy,
            "created_at": utc_now(),
            "late_snapshot": self.late_snapshot,
            "status": "RUNNING",
            "finalized_at": "",
            "decision": "",
        })
        self.capture_git_status("before")
        self.write_base_documents()
        self.update_latest("RUNNING")

    def _read_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.is_file():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_metadata(self, updates: dict[str, Any]) -> dict[str, Any]:
        data = self._read_metadata()
        data.update(updates)
        data["updated_at"] = utc_now()
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return data

    def capture_git_status(self, phase: str) -> Path:
        target = self.run_path / "workspace" / f"git_status_{phase}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_git_status(self.project_dir, self.evidence_root), encoding="utf-8")
        return target

    def write_base_documents(self) -> None:
        brief = (
            "# Task Brief\n\n"
            f"Project directory: `{self.project_dir}`\n"
            f"Task type: `{self.task_type}`\n"
            f"Agent: `{self.agent}`\n"
            f"Session id: `{self.session_id}`\n\n"
            "Scope statement: daemon-supervised activity for this registered project directory.\n"
        )
        if self.late_snapshot:
            brief += "\nBaseline note: the daemon detected the session after activity had already started.\n"
        (self.run_path / "brief.md").write_text(brief, encoding="utf-8")

        plan = (
            "# Plan\n\n"
            "1. Capture workspace baseline and tool events for the registered project.\n"
            "2. Persist required evidence artifacts using the shared evidence builder.\n"
            "3. Run conservative validation when the task type requires code-change validation.\n"
            "4. Run Workbench acceptance checks and record the terminal decision.\n"
        )
        (self.run_path / "plan.md").write_text(plan, encoding="utf-8")

        self._write_risks([])
        audit_guard = (
            "Audit guard source: automated evidence supervisor daemon.\n"
            f"Agent: {self.agent}\n"
            f"Session id: {self.session_id}\n"
            f"late_snapshot: {str(self.late_snapshot).lower()}\n"
            "Status: running; final policy violations are evaluated at finalization.\n"
        )
        (self.run_path / "validation" / "audit_guard.txt").write_text(audit_guard, encoding="utf-8")

        for kind in ("test", "lint", "typecheck"):
            path = self.run_path / "validation" / f"{kind}_output.txt"
            if not path.exists():
                path.write_text(f"Validation not run yet for {kind}.\n", encoding="utf-8")
        (self.run_path / "validation_summary.md").write_text("Validation not finalized yet.\n", encoding="utf-8")
        (self.run_path / "commands.jsonl").touch()
        (self.run_path / "transcript.jsonl").touch()
        (self.run_path / "changed_files.txt").write_text("(not finalized)\n", encoding="utf-8")
        (self.run_path / "workspace" / "diff_summary.patch").write_text("(not finalized)\n", encoding="utf-8")
        self.write_artifacts([])
        self.write_workbench_setup_artifacts(status="running")

    def _write_risks(self, violations: list[dict[str, Any]]) -> None:
        lines = [
            "# Risks",
            "",
            "Confidence: 0.74",
            "Evidence is accepted only through deterministic gate checks and generated artifacts.",
            "Residual risk: daemon supervision can only cover events emitted by supported adapters.",
        ]
        if self.late_snapshot:
            lines.append("late_snapshot=true: the baseline may not represent a true pre-session state.")
        if violations:
            lines.append("Captured policy violations require review before acceptance.")
            for violation in violations[:20]:
                lines.append(f"- {violation.get('severity', 'unknown')}: {violation.get('message', violation.get('rule', 'policy violation'))}")
        (self.run_path / "risks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_artifacts(self, violations: list[dict[str, Any]]) -> None:
        inventory = _inventory(self.project_dir, self.evidence_root)
        (self.run_path / "artifacts" / "inventory.json").write_text(
            json.dumps(inventory, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        findings = {
            "schema": "ai-workbench.extracted_findings.v1",
            "generated_at": utc_now(),
            "agent": self.agent,
            "session_id": self.session_id,
            "event_count": self._event_count(),
            "violations": violations,
            "late_snapshot": self.late_snapshot,
            "changed_files": _git_changed_files(self.project_dir, self.evidence_root),
        }
        (self.run_path / "artifacts" / "extracted_findings.json").write_text(
            json.dumps(findings, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _event_count(self) -> int:
        path = self.run_path / "transcript.jsonl"
        if not path.is_file():
            return 0
        return sum(1 for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())

    def append_event(self, event: dict[str, Any]) -> None:
        self.run_path.mkdir(parents=True, exist_ok=True)
        event = dict(event)
        event.setdefault("timestamp", utc_now())
        event.setdefault("agent", self.agent)
        event.setdefault("session_id", self.session_id)
        event.setdefault("source", self.agent)
        event.setdefault("role", "tool")
        event.setdefault("type", "tool_result" if event.get("output") or event.get("content") else "hook_event")

        with (self.run_path / "transcript.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        command = event.get("command") or ""
        tool_input = event.get("tool_input") or {}
        if not command and isinstance(tool_input, dict):
            command = tool_input.get("command") or ""
        if command:
            entry = {
                "timestamp": event.get("timestamp"),
                "agent": self.agent,
                "session_id": self.session_id,
                "tool_name": event.get("tool_name", ""),
                "command": command,
                "event_id": event.get("event_id") or event.get("tool_use_id") or event.get("part_rowid"),
            }
            with (self.run_path / "commands.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _workbench_task_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "project": "supervised_project",
            "task": f"Supervisor-captured {self.task_type} session",
            "task_type": self.task_type,
            "risk": "medium",
            "execution_host": self.agent,
            "response_source": self.agent,
            "validation_profile": f"supervised_{self.task_type}",
            "supervisor": {
                "agent": self.agent,
                "session_id": self.session_id,
                "late_snapshot": self.late_snapshot,
                "project_dir": self.project_dir,
                "evidence_root": self.evidence_root,
            },
            "generated_at": utc_now(),
        }

    def write_workbench_setup_artifacts(self, status: str = "running") -> None:
        (self.run_path / "task_metadata.json").write_text(
            json.dumps(self._workbench_task_metadata(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        final_prompt = (
            "# AI Workbench Supervised Run\n\n"
            f"Project directory: `{self.project_dir}`\n"
            f"Task type: `{self.task_type}`\n"
            f"Execution host: `{self.agent}`\n"
            f"Session id: `{self.session_id}`\n"
            f"Late snapshot: `{str(self.late_snapshot).lower()}`\n\n"
            "The local supervisor captures evidence, then AI Workbench validation and quality-gate "
            "artifacts decide the acceptance outcome.\n"
        )
        (self.run_path / "final_prompt.md").write_text(final_prompt, encoding="utf-8")
        (self.run_path / "model_selection.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "selected_tier": "supervisor",
                    "selected_model": self.agent,
                    "runtime": "local-supervisor",
                    "reason": "Run was captured by the AI Workbench supervisor rather than model-routed by Workbench.",
                    "status": status,
                    "generated_at": utc_now(),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def _read_supporting_text(self, relative: str) -> str:
        path = self.run_path / relative
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="replace")

    def write_model_output(self, validation: dict[str, Any], violations: list[dict[str, Any]]) -> None:
        changed_files = self._read_supporting_text("changed_files.txt").strip()
        closeout = self._read_supporting_text("closeout.md").strip()
        risks = self._read_supporting_text("risks.md").strip()
        lines = [
            "# Supervisor Captured Output",
            "",
            "## Summary",
            "",
            f"- Run id: `{self.run_id}`",
            f"- Agent: `{self.agent}`",
            f"- Session id: `{self.session_id}`",
            f"- Events captured: `{self._event_count()}`",
            f"- Policy violations captured: `{len(violations)}`",
            f"- Validation status: `{validation.get('status', 'unknown')}`",
            "",
            "## Files touched",
            "",
            changed_files or "(not available)",
            "",
            "## Validation run",
            "",
            json.dumps(validation, indent=2, ensure_ascii=False),
            "",
            "## Risks / follow-ups",
            "",
            risks or "No risk artifact was captured.",
            "",
            "## Closeout",
            "",
            closeout or "No closeout artifact was captured.",
        ]
        (self.run_path / "model_output.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_run_log(self, decision: str, validation: dict[str, Any]) -> None:
        entries = [
            {
                "timestamp": utc_now(),
                "event": "supervisor_run_finalized",
                "run_id": self.run_id,
                "agent": self.agent,
                "session_id": self.session_id,
                "event_count": self._event_count(),
                "validation_status": validation.get("status", "unknown"),
                "decision": decision,
            }
        ]
        transcript_path = self.run_path / "transcript.jsonl"
        if transcript_path.is_file():
            for line in transcript_path.read_text(encoding="utf-8", errors="replace").splitlines()[:200]:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                entries.append(
                    {
                        "timestamp": event.get("timestamp") or utc_now(),
                        "event": "captured_tool_event",
                        "run_id": self.run_id,
                        "agent": event.get("agent", self.agent),
                        "session_id": event.get("session_id", self.session_id),
                        "tool_name": event.get("tool_name", ""),
                        "event_id": event.get("event_id", ""),
                    }
                )
        with (self.run_path / "run_log.jsonl").open("w", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def write_skipped_validation_outputs(self) -> dict[str, Any]:
        validation_dir = self.run_path / "validation"
        validation_dir.mkdir(parents=True, exist_ok=True)
        is_code_change = self.task_type in CODE_CHANGE_TASK_TYPES
        results: dict[str, Any] = {}

        for kind in ("test", "lint", "typecheck"):
            if is_code_change:
                status = "missing"
                output = (
                    f"{VALIDATION_MISSING}: validation step was skipped for a code-change task.\n"
                    "Acceptance for code-change task types must remain BLOCKED until validation evidence exists.\n"
                )
                skipped_reason = "validation step skipped"
            else:
                status = "not_required"
                output = (
                    f"Validation not required for task_type={self.task_type}.\n"
                    "No code-change validation command was run by the supervisor.\n"
                )
                skipped_reason = "not required for task type"
            (validation_dir / f"{kind}_output.txt").write_text(output, encoding="utf-8")
            results[kind] = {
                "status": status,
                "exit_code": None,
                "timed_out": False,
                "skipped_reason": skipped_reason,
                "command": None,
            }

        terminal_status = "blocked" if is_code_change else "passed"
        summary_lines = [
            "# Validation Summary",
            "",
            *[f"- {kind}: {results[kind]['status']}; command: `(none)`" for kind in ("test", "lint", "typecheck")],
            "",
            f"Overall validation status: {terminal_status}",
        ]
        (self.run_path / "validation_summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        return {
            "status": terminal_status,
            "commands_detected": {},
            "results": results,
            "skipped": True,
        }

    def _reason_sources_from_report(self, report: Any) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        for check in report.checks:
            if not check.issues:
                continue
            for issue in check.issues:
                if issue.severity == Severity.BLOCKER:
                    severity = "blocker"
                elif issue.severity == Severity.REJECT:
                    severity = "blocker"
                else:
                    severity = "review"
                sources.append(
                    {
                        "code": f"supervisor.{check.check_name}",
                        "status": check.status,
                        "severity": severity,
                        "source": "supervisor_evidence_gate",
                        "name": check.check_name,
                        "summary": issue.message,
                        "details": [issue.evidence] if issue.evidence else [],
                    }
                )
        return sources

    def write_workbench_acceptance_artifacts(self, report: Any, validation: dict[str, Any]) -> dict[str, str]:
        validation_status = str(validation.get("status", "unknown"))
        validation_blocks = validation_status in {"blocked", "failed", "timeout"}
        if validation_blocks:
            overall_status = "failed"
            sign_off_ready = False
            final_status = "revision_required"
            next_action = "provide_missing_or_corrected_validation"
        elif report.decision == Decision.ACCEPT:
            overall_status = "passed"
            sign_off_ready = True
            final_status = "accepted"
            next_action = "none"
        elif report.decision == Decision.ACCEPT_WITH_CONDITIONS:
            overall_status = "needs_review"
            sign_off_ready = False
            final_status = "review_required"
            next_action = "manual_review_handoff"
        else:
            overall_status = "failed"
            sign_off_ready = False
            final_status = "revision_required"
            next_action = "provide_missing_or_corrected_evidence"

        reason_sources = self._reason_sources_from_report(report)
        if validation_blocks:
            reason_sources.append(
                {
                    "code": f"supervisor.validation_{validation_status}",
                    "status": "failed",
                    "severity": "blocker",
                    "source": "supervisor_validation",
                    "name": "supervisor_validation",
                    "summary": f"Supervisor validation status is {validation_status}.",
                    "details": [],
                }
            )
        if self.late_snapshot:
            reason_sources.append(
                {
                    "code": "supervisor.late_snapshot",
                    "status": "needs_review",
                    "severity": "review",
                    "source": "supervisor",
                    "name": "late_snapshot",
                    "summary": "Supervisor baseline was captured after activity started.",
                    "details": [],
                }
            )
        reason_codes = sorted({str(source["code"]) for source in reason_sources})
        validation_report = {
            "schema_version": 1,
            "run_id": self.run_id,
            "project": "supervised_project",
            "profile": f"supervised_{self.task_type}",
            "generated_at": utc_now(),
            "commands_run": [],
            "commands_not_run": [],
            "artifact_checks": [
                {
                    "name": check.check_name,
                    "status": check.status,
                    "summary": f"{check.check_name}: {check.status}",
                    "details": [issue.message for issue in check.issues],
                    "reason_codes": [f"supervisor.{check.check_name}"] if check.issues else [],
                }
                for check in report.checks
            ],
            "review_checks": [],
            "missing_context_notes": {"needs_review": [], "info": []},
            "overall_status": overall_status,
            "sign_off_ready": sign_off_ready,
            "confidence": 0.85 if sign_off_ready else 0.65,
            "summary": {
                "checks_total": len(report.checks),
                "checks_failed": len(report.failed_checks),
                "checks_blocked": len(report.blocked_checks),
                "checks_needs_review": len(report.warning_checks),
                "supervisor_validation_status": validation.get("status", "unknown"),
            },
            "policy_pack": {
                "name": f"supervised_{self.task_type}",
                "version": "v0.8-alpha",
                "source": "supervisor_policy",
            },
            "profile_source": "supervisor",
            "reason_sources": reason_sources,
            "reason_codes": reason_codes,
            "supervisor": {
                "agent": self.agent,
                "session_id": self.session_id,
                "late_snapshot": self.late_snapshot,
                "acceptance_report_decision": report.decision.value,
                "acceptance_report_json": str(self.run_path / "acceptance_report_supporting.json"),
            },
        }
        (self.run_path / "validation_report.json").write_text(
            json.dumps(validation_report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        quality_reason_code = "quality_gate.accepted"
        quality_severity = "info"
        if final_status == "review_required":
            quality_reason_code = "quality_loop.supervisor_review_required"
            quality_severity = "review"
        elif final_status == "revision_required":
            quality_reason_code = "quality_loop.supervisor_revision_required"
            quality_severity = "blocker"

        revision_decision = {
            "schema_version": 1,
            "generated_at": utc_now(),
            "loop_type": "supervisor_gate",
            "required": final_status != "accepted",
            "reason": report.required_next_action,
            "next_action": next_action,
            "accepted_pass": 1 if final_status == "accepted" else 0,
            "final_status": final_status,
            "authoritative_model_output": "model_output.md",
            "authoritative_validation_report": "validation_report.json",
            "first_pass_artifacts": {
                "model_output": "model_output.md",
                "validation_report": "validation_report.json",
            },
            "second_pass_artifacts": {},
            "blocking_findings": [source["summary"] for source in reason_sources if source.get("severity") == "blocker"],
            "non_blocking_findings": [source["summary"] for source in reason_sources if source.get("severity") != "blocker"],
            "reason_sources": [
                {
                    "code": quality_reason_code,
                    "status": final_status,
                    "severity": quality_severity,
                    "source": "quality_loop",
                    "name": "supervisor_gate",
                    "summary": report.required_next_action,
                    "details": [],
                }
            ],
            "reason_codes": [quality_reason_code],
        }
        (self.run_path / "revision_decision.json").write_text(
            json.dumps(revision_decision, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if final_status == "accepted":
            public_outcome = "accept"
        elif final_status == "review_required":
            public_outcome = "needs_review"
        else:
            public_outcome = "block"
        return {
            "overall_status": overall_status,
            "final_status": final_status,
            "outcome": public_outcome,
            "next_action": next_action,
            "required_next_action": (
                "Provide missing or corrected validation evidence, then rerun the supervised Workbench gate."
                if validation_blocks
                else report.required_next_action
            ),
        }

    def _collect_violations(self) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []
        path = self.run_path / "transcript.jsonl"
        if not path.is_file():
            return violations
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for violation in event.get("violations") or []:
                    if isinstance(violation, dict):
                        violations.append(violation)
        return violations

    def finalize(
        self,
        policy_dir: str,
        validation_timeout: int = 120,
        run_validation_step: bool = True,
    ) -> dict[str, Any]:
        self.capture_git_status("after")
        (self.run_path / "workspace" / "diff_summary.patch").write_text(_git_diff(self.project_dir), encoding="utf-8")
        changed = _git_changed_files(self.project_dir, self.evidence_root)
        (self.run_path / "changed_files.txt").write_text(
            ("\n".join(changed) + "\n") if changed else "(no file changes detected)\n",
            encoding="utf-8",
        )

        violations = self._collect_violations()
        self._write_risks(violations)
        self.write_artifacts(violations)

        if run_validation_step:
            validation = run_validation(
                project_dir=self.project_dir,
                validation_dir=str(self.run_path / "validation"),
                task_type=self.task_type,
                timeout_seconds=validation_timeout,
            )
        else:
            validation = self.write_skipped_validation_outputs()

        audit_guard_status = "passed" if not violations else "failed"
        audit_guard = (
            "Audit guard source: automated evidence supervisor daemon.\n"
            f"Agent: {self.agent}\n"
            f"Session id: {self.session_id}\n"
            f"late_snapshot: {str(self.late_snapshot).lower()}\n"
            f"Captured policy violations: {len(violations)}\n"
            f"Validation status: {validation.get('status', 'unknown')}\n"
            f"Status: {audit_guard_status}\n"
        )
        (self.run_path / "validation" / "audit_guard.txt").write_text(audit_guard, encoding="utf-8")

        closeout = (
            "# Closeout\n\n"
            f"Run id: `{self.run_id}`\n"
            f"Agent: `{self.agent}`\n"
            f"Session id: `{self.session_id}`\n"
            f"Events captured: {self._event_count()}\n"
            f"Policy violations captured: {len(violations)}\n"
            f"Validation status: {validation.get('status', 'unknown')}\n"
            "Final decision is recorded in validation_report.json and revision_decision.json.\n"
        )
        (self.run_path / "closeout.md").write_text(closeout, encoding="utf-8")

        transcript_path = self.run_path / "transcript.jsonl"
        if not transcript_path.read_text(encoding="utf-8", errors="replace").strip():
            self.append_event({
                "type": "supervisor_event",
                "role": "tool",
                "tool_name": "ai-workbench-daemon",
                "content": "No tool events were captured before finalization.",
                "violations": [],
            })

        report = run_acceptance(
            repo_path=self.project_dir,
            evidence_path=str(self.run_path),
            transcript_path=str(transcript_path),
            policy_dir=policy_dir,
            policy_name=self.policy or None,
            task_type=self.task_type,
        )
        if self.late_snapshot and report.decision == Decision.ACCEPT:
            report.decision = Decision.ACCEPT_WITH_CONDITIONS
            report.required_next_action = (
                "Review late-snapshot run because the supervisor baseline was captured after activity started."
            )
        md_path, json_path = write_report(report, str(self.run_path))
        csv_path = write_csv_report(report, str(self.run_path))
        supporting_json = self.run_path / "acceptance_report_supporting.json"
        try:
            supporting_json.write_text(Path(json_path).read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
        self.write_workbench_setup_artifacts(status="finalized")
        self.write_model_output(validation, violations)
        workbench_status = self.write_workbench_acceptance_artifacts(report, validation)
        self.write_run_log(workbench_status["outcome"], validation)

        metadata = self._write_metadata({
            "status": workbench_status["outcome"],
            "decision": workbench_status["outcome"],
            "supporting_acceptance_decision": report.decision.value,
            "finalized_at": utc_now(),
            "required_next_action": workbench_status["required_next_action"],
            "acceptance_report_md": str(md_path),
            "acceptance_report_json": str(json_path),
            "acceptance_report_csv": str(csv_path),
            "validation": validation,
        })
        self.update_latest(workbench_status["outcome"], workbench_status["required_next_action"])
        return metadata

    def update_latest(self, status: str, next_action: str = "") -> None:
        root = Path(self.evidence_root)
        root.mkdir(parents=True, exist_ok=True)
        latest = {
            "schema": "ai-workbench.latest.v1",
            "updated_at": utc_now(),
            "run_id": self.run_id,
            "run_path": str(self.run_path),
            "project_dir": self.project_dir,
            "agent": self.agent,
            "session_id": self.session_id,
            "task_type": self.task_type,
            "status": status,
            "decision": status if status != "RUNNING" else "",
            "required_next_action": next_action,
            "late_snapshot": self.late_snapshot,
        }
        (root / "latest.json").write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
