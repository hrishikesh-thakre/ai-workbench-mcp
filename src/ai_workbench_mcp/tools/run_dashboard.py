from __future__ import annotations

import html
import os
from pathlib import Path

from .run_cost_time import as_dict, as_int, format_duration_ms, format_usd, selected_model_parts
from .run_evidence import latest_tier
from .run_metrics import (
    accepted_by_validation_and_gate,
    failure_reasons,
    public_outcome_bucket,
    quality_gate_outcome,
    recipe_for,
)


def html_escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def html_attr(value: object) -> str:
    return html.escape(str(value), quote=True)


def relative_artifact_href(out_dir: Path, artifact_path: Path) -> str:
    try:
        relative = os.path.relpath(artifact_path, start=out_dir)
    except ValueError:
        relative = artifact_path.name
    return Path(relative).as_posix()


def html_table(headers: list[str], rows: list[list[object]]) -> str:
    rendered = [
        "<table>",
        "<thead><tr>" + "".join(f"<th>{html_escape(header)}</th>" for header in headers) + "</tr></thead>",
        "<tbody>",
    ]
    if rows:
        for row in rows:
            rendered.append("<tr>" + "".join(f"<td>{html_escape(cell)}</td>" for cell in row) + "</tr>")
    else:
        rendered.append(f"<tr><td colspan=\"{len(headers)}\">No evidence found.</td></tr>")
    rendered.extend(["</tbody>", "</table>"])
    return "\n".join(rendered)


def html_mapping_table(title: str, mapping: object, headers: tuple[str, str] = ("Name", "Count")) -> str:
    rows: list[list[object]] = []
    for key, value in as_dict(mapping).items():
        rows.append([key, value])
    return "\n".join([f"<h3>{html_escape(title)}</h3>", html_table([headers[0], headers[1]], rows)])


def html_breakdown_table(title: str, mapping: object) -> str:
    rows: list[list[object]] = []
    for key, data in as_dict(mapping).items():
        data = as_dict(data)
        rows.append(
            [
                key,
                data.get("accepted", 0),
                data.get("review_required", data.get("needs_review", 0)),
                data.get("failed", 0),
                data.get("other", 0),
                data.get("total", 0),
                data.get("acceptance_rate", 0.0),
                data.get("review_rate", ""),
                data.get("failure_rate", ""),
            ]
        )
    return "\n".join(
        [
            f"<h3>{html_escape(title)}</h3>",
            html_table(
                [
                    "Name",
                    "Accepted",
                    "Review Required",
                    "Failed",
                    "Other",
                    "Total",
                    "Acceptance Rate",
                    "Review Rate",
                    "Failure Rate",
                ],
                rows,
            ),
        ]
    )


def html_artifact_links(out_dir: Path, run_dir: Path) -> str:
    artifact_names = [
        "task_metadata.json",
        "final_prompt.md",
        "model_selection.json",
        "model_output.md",
        "validation_report.json",
        "revision_decision.json",
        "run_log.jsonl",
    ]
    links: list[str] = []
    for artifact_name in artifact_names:
        artifact_path = run_dir / artifact_name
        if artifact_path.exists():
            href = html_attr(relative_artifact_href(out_dir, artifact_path))
            label = html_escape(artifact_name)
            links.append(f"<a href=\"{href}\">{label}</a>")
    return " ".join(links) if links else "No standard artifacts found."


def html_status_badge(outcome: str) -> str:
    class_name = {
        "accepted": "accepted",
        "review_required": "review",
        "failed": "failed",
    }.get(outcome, "other")
    return f"<span class=\"status-badge {class_name}\">{html_escape(outcome)}</span>"


def html_cell_stack(lines: list[tuple[str, object]]) -> str:
    rendered_lines = []
    for label, value in lines:
        rendered_lines.append(
            "<span>"
            f"<span class=\"cell-label\">{html_escape(label)}</span>"
            f"{html_escape(value)}"
            "</span>"
        )
    return "<div class=\"cell-stack\">" + "".join(rendered_lines) + "</div>"


def run_failure_reason_text(report: dict[str, object], decision: dict[str, object]) -> str:
    if accepted_by_validation_and_gate(report, decision):
        return "None recorded"
    reasons = failure_reasons(report, decision)
    if not reasons:
        return "unknown"
    rendered = reasons[:4]
    if len(reasons) > 4:
        rendered.append(f"+{len(reasons) - 4} more")
    return ", ".join(rendered)


def run_cost_time_lines(cost_time: dict[str, object]) -> list[tuple[str, object]]:
    return [
        (
            "Tokens",
            f"{as_int(cost_time.get('total_tokens')):,}"
            if cost_time.get("has_token_data") is True and as_int(cost_time.get("total_tokens")) is not None
            else "not recorded",
        ),
        ("Cost", format_usd(cost_time.get("estimated_cost_usd"), cost_time.get("has_cost_data") is True)),
        (
            "Provider time",
            format_duration_ms(cost_time.get("provider_duration_ms"), cost_time.get("has_provider_time_data") is True),
        ),
        (
            "Validation time",
            format_duration_ms(
                cost_time.get("validation_duration_ms"),
                cost_time.get("has_validation_time_data") is True,
            ),
        ),
    ]


def html_run_rows(runs: list[dict[str, object]], out_dir: Path) -> str:
    rows: list[str] = [
        "<table>",
        (
            "<thead><tr>"
            "<th>Run</th><th>Outcome</th><th>Agent / Model</th><th>Policy</th>"
            "<th>Failure Reasons</th><th>Cost / Time</th><th>Evidence Links</th>"
            "</tr></thead>"
        ),
        "<tbody>",
    ]
    if not runs:
        rows.append("<tr><td colspan=\"7\">No run folders were scanned.</td></tr>")
    for run in runs:
        logs = run.get("logs", [])
        logs = logs if isinstance(logs, list) else []
        report = as_dict(run.get("report"))
        decision = as_dict(run.get("decision"))
        selection = as_dict(run.get("selection"))
        metadata = as_dict(run.get("metadata"))
        cost_time = as_dict(run.get("cost_time"))
        recipe = recipe_for(metadata, selection, report, logs)
        profile = str(report.get("profile", "unknown"))
        selected_tier = latest_tier(logs, selection)
        risk = str(selection.get("risk", "unknown"))
        complexity = str(selection.get("complexity_band", "unknown"))
        provider, model = selected_model_parts(selection, cost_time)
        outcome = public_outcome_bucket(report, decision)
        run_dir = Path(str(run.get("path", "")))
        cells = [
            html_cell_stack(
                [
                    ("Run ID", run.get("run_id", "unknown")),
                    ("Task", run.get("task_type", "unknown")),
                    ("Recipe", recipe),
                ]
            ),
            html_status_badge(outcome),
            html_cell_stack(
                [
                    ("Host", run.get("execution_host", "goose")),
                    ("Source", run.get("response_source", "unknown")),
                    ("Provider", provider),
                    ("Model", model),
                    ("Tier", selected_tier),
                ]
            ),
            html_cell_stack(
                [
                    ("Profile", profile),
                    ("Gate", quality_gate_outcome(decision)),
                    ("Risk", risk),
                    ("Complexity", complexity),
                ]
            ),
            html_escape(run_failure_reason_text(report, decision)),
            html_cell_stack(run_cost_time_lines(cost_time)),
            html_artifact_links(out_dir, run_dir),
        ]
        rows.append(
            f"<tr data-outcome=\"{html_attr(outcome)}\">"
            + "".join(f"<td>{cell}</td>" for cell in cells)
            + "</tr>"
        )
    rows.extend(["</tbody>", "</table>"])
    return "\n".join(rows)


def html_routing_candidates(candidates: object) -> str:
    rows: list[list[object]] = []
    for key, data in as_dict(candidates).items():
        data = as_dict(data)
        reasons = as_dict(data.get("top_failure_reasons"))
        reason_text = ", ".join(f"{reason}={count}" for reason, count in reasons.items())
        rows.append(
            [
                key,
                data.get("recipe", "unknown"),
                data.get("validation_profile", "unknown"),
                data.get("selected_tier", "unknown"),
                data.get("risk", "unknown"),
                data.get("complexity_band", "unknown"),
                data.get("total", 0),
                data.get("acceptance_rate", 0.0),
                data.get("review_rate", 0.0),
                data.get("failure_rate", 0.0),
                reason_text,
            ]
        )
    return html_table(
        [
            "Candidate Key",
            "Recipe",
            "Profile",
            "Tier",
            "Risk",
            "Complexity",
            "Total",
            "Acceptance Rate",
            "Review Rate",
            "Failure Rate",
            "Top Failure Reasons",
        ],
        rows,
    )


def write_dashboard(metrics: dict[str, object], runs: list[dict[str, object]], out_dir: Path) -> Path:
    dashboard_path = out_dir / "run_dashboard.html"
    outcome_counts = as_dict(metrics.get("outcome_counts"))
    cost_tracking = as_dict(metrics.get("cost_tracking"))
    time_tracking = as_dict(metrics.get("time_tracking"))
    cost_note = (
        "No provider cost evidence was found. Empty or zero cost fields do not mean execution was free."
        if not cost_tracking.get("runs_with_cost_data")
        else "Provider cost evidence was found in model_call_metadata.json artifacts."
    )
    outcome_breakdown = as_dict(metrics.get("outcome_breakdown"))

    html_text = "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "<title>Workbench Evidence Dashboard</title>",
            "<style>",
            (
                ":root{--bg:#f6f7f9;--surface:#ffffff;--ink:#111827;--muted:#5b6472;--line:#d9dee7;"
                "--soft:#eef1f5;--accepted:#15803d;--review:#b45309;--failed:#b91c1c;--other:#475569;--link:#075985;}"
                "*{box-sizing:border-box;}body{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;"
                "margin:0;background:var(--bg);color:var(--ink);line-height:1.45;}main{max-width:1320px;margin:0 auto;padding:30px 20px 48px;}"
                "section{margin-top:28px;}h1{font-size:32px;line-height:1.15;margin:0 0 8px;font-weight:750;}h2{font-size:22px;line-height:1.25;margin:0 0 12px;}"
                "h3{font-size:15px;margin:20px 0 8px;}.muted{color:var(--muted);max-width:900px;}.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));}"
                ".metric{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 14px 13px;min-height:92px;}"
                ".metric span{display:block;color:var(--muted);font-size:12px;font-weight:700;text-transform:uppercase;}.metric strong{display:block;font-size:28px;line-height:1.1;margin-top:10px;}"
                ".metric.accepted{border-top:4px solid var(--accepted);}.metric.review{border-top:4px solid var(--review);}.metric.failed{border-top:4px solid var(--failed);}"
                "table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--line);border-radius:8px;overflow:hidden;}"
                "th,td{padding:10px 12px;border-top:1px solid #e7eaf0;text-align:left;vertical-align:top;font-size:13px;}td{min-width:120px;}"
                "th{background:var(--soft);font-size:11px;text-transform:uppercase;font-weight:750;color:#374151;}tbody tr:hover{background:#fbfcfd;}"
                "tr[data-outcome=accepted]{border-left:4px solid var(--accepted);}tr[data-outcome=review_required]{border-left:4px solid var(--review);}tr[data-outcome=failed]{border-left:4px solid var(--failed);}"
                "a{color:var(--link);text-decoration:none;margin-right:8px;white-space:nowrap;}a:hover{text-decoration:underline;}"
                ".note{background:var(--surface);border-left:4px solid var(--other);padding:12px 14px;border-radius:0 8px 8px 0;}"
                ".status-badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 9px;font-size:12px;font-weight:750;text-transform:capitalize;white-space:nowrap;}"
                ".status-badge.accepted{background:#dcfce7;color:#166534;}.status-badge.review{background:#fef3c7;color:#92400e;}.status-badge.failed{background:#fee2e2;color:#991b1b;}"
                ".status-badge.other{background:#e2e8f0;color:#334155;}.cell-stack{display:grid;gap:3px;min-width:180px;}.cell-stack>span{display:block;}"
                ".cell-label{display:inline-block;min-width:86px;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;}"
                "code{background:#e5e7eb;border-radius:5px;padding:1px 5px;}@media(max-width:720px){main{padding:22px 12px 36px;}h1{font-size:26px;}th,td{font-size:12px;padding:8px;}table{display:block;overflow-x:auto;}}"
            ),
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<h1>Workbench Evidence Dashboard</h1>",
            (
                f"<p class=\"muted\">Generated from run evidence at "
                f"<code>{html_escape(metrics.get('generated_at', 'unknown'))}</code>. "
                "This static report links to evidence artifacts but does not embed model outputs or provider logs.</p>"
            ),
            "<section class=\"grid\" aria-label=\"Outcome metrics\">",
            f"<div class=\"metric\"><span>Evidence Scope</span><strong>{html_escape(metrics.get('evidence_scope', 'all'))}</strong></div>",
            f"<div class=\"metric\"><span>Runs Total</span><strong>{html_escape(metrics.get('runs_total', 0))}</strong></div>",
            f"<div class=\"metric\"><span>Excluded Runs</span><strong>{html_escape(metrics.get('excluded_runs_total', 0))}</strong></div>",
            f"<div class=\"metric accepted\"><span>Accepted</span><strong>{html_escape(outcome_counts.get('accepted', 0))}</strong></div>",
            f"<div class=\"metric review\"><span>Review Required</span><strong>{html_escape(outcome_counts.get('review_required', 0))}</strong></div>",
            f"<div class=\"metric failed\"><span>Failed</span><strong>{html_escape(outcome_counts.get('failed', 0))}</strong></div>",
            f"<div class=\"metric\"><span>Acceptance Rate</span><strong>{html_escape(metrics.get('acceptance_rate', 0.0))}</strong></div>",
            f"<div class=\"metric\"><span>Average Confidence</span><strong>{html_escape(metrics.get('average_confidence', 0.0))}</strong></div>",
            "</section>",
            "<section>",
            "<h2>Outcome Buckets</h2>",
            html_mapping_table("Public Outcome Counts", metrics.get("outcome_counts")),
            html_mapping_table("Quality Gate Outcomes", metrics.get("quality_gate_outcomes")),
            html_mapping_table("Failure Reasons", metrics.get("failure_reasons")),
            "</section>",
            "<section>",
            "<h2>Breakdowns</h2>",
            html_breakdown_table("By Recipe", as_dict(outcome_breakdown.get("by_recipe"))),
            html_breakdown_table("By Execution Host", as_dict(outcome_breakdown.get("by_execution_host"))),
            html_breakdown_table("By Response Source", as_dict(outcome_breakdown.get("by_response_source"))),
            html_breakdown_table("By Validation Profile", as_dict(outcome_breakdown.get("by_validation_profile"))),
            html_breakdown_table("By Selected Tier", as_dict(outcome_breakdown.get("by_selected_tier"))),
            html_breakdown_table("By Quality Gate Outcome", as_dict(outcome_breakdown.get("by_quality_gate_outcome"))),
            "</section>",
            "<section>",
            "<h2>Routing Feedback Candidates</h2>",
            html_routing_candidates(metrics.get("routing_feedback_candidates")),
            "</section>",
            "<section>",
            "<h2>Cost And Time Evidence</h2>",
            f"<p class=\"note\">{html_escape(cost_note)}</p>",
            html_mapping_table("Cost Tracking", cost_tracking),
            html_mapping_table("Time Tracking", time_tracking),
            "</section>",
            "<section>",
            "<h2>Run Evidence</h2>",
            "<p class=\"muted\">Links are relative references to standard evidence artifacts; artifact contents are not embedded.</p>",
            html_run_rows(runs, out_dir),
            "</section>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    dashboard_path.write_text(html_text + "\n", encoding="utf-8")
    return dashboard_path

