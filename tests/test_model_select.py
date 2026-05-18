import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.tools.model_select import (
    SelectorPolicy,
    SelectorRule,
    build_model_selection,
    complexity_band,
    effective_args,
    infer_routing,
    load_model_registry,
    load_model_registry_with_source,
    load_routing_feedback_policy,
    load_selector_policy,
    select_model,
    select_model_payload,
    validate_selector_references,
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_REGISTRY = ROOT / "configs" / "model_registry.yaml"
MISSING_LOCAL_REGISTRY = ROOT / "configs" / "__missing_model_registry.local.yaml"


def selector_args(
    *,
    task_type: str = "implement",
    risk: str = "medium",
    validation_strength: str = "medium",
    prompt: str = "implement_request_change_request",
    complexity_score: int | None = None,
    test_complexity_level: int | None = None,
    instruction_following: str = "normal",
    recipe: str | None = None,
    validation_profile: str | None = None,
    routing_feedback_path: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        project="ai_workbench",
        task_type=task_type,
        risk=risk,
        validation_strength=validation_strength,
        prompt=prompt,
        complexity_score=complexity_score,
        test_complexity_level=test_complexity_level,
        instruction_following=instruction_following,
        task_text="",
        code_file=[],
        recipe=recipe,
        validation_profile=validation_profile,
        routing_feedback_path=routing_feedback_path,
    )


def candidate_payload(
    *,
    recipe: str = "workbench-engineering-acceptance.yaml",
    validation_profile: str = "low_risk_coding",
    selected_tier: str = "local_coding",
    risk: str = "medium",
    complexity_band: str = "moderate",
    accepted: int = 5,
    review_required: int = 0,
    failed: int = 0,
    top_failure_reasons: dict[str, int] | None = None,
) -> tuple[str, dict[str, object]]:
    total = accepted + review_required + failed
    key = "|".join([recipe, validation_profile, selected_tier, risk, complexity_band])
    return key, {
        "recipe": recipe,
        "validation_profile": validation_profile,
        "selected_tier": selected_tier,
        "risk": risk,
        "complexity_band": complexity_band,
        "accepted": accepted,
        "review_required": review_required,
        "failed": failed,
        "other": 0,
        "total": total,
        "acceptance_rate": round(accepted / max(1, total), 2),
        "review_rate": round(review_required / max(1, total), 2),
        "failure_rate": round(failed / max(1, total), 2),
        "top_failure_reasons": top_failure_reasons or {},
    }


def write_feedback(path: Path, candidates: dict[str, dict[str, object]]) -> None:
    path.write_text(json.dumps({"routing_feedback_candidates": candidates}), encoding="utf-8")


def select_model_payload_without_local(args: SimpleNamespace) -> dict[str, object]:
    return select_model_payload(args, registry_local_override_path=MISSING_LOCAL_REGISTRY)


class ModelSelectorRoutingTests(unittest.TestCase):
    def test_complexity_band_maps_scores_to_policy_ranges(self) -> None:
        self.assertEqual(complexity_band(8), "easy")
        self.assertEqual(complexity_band(13), "moderate")
        self.assertEqual(complexity_band(18), "hard")
        self.assertEqual(complexity_band(22), "very_hard")
        self.assertEqual(complexity_band(25), "nasty_hard")

    def test_very_hard_complexity_routes_to_frontier(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(risk="low", complexity_score=19),
        )

        self.assertEqual(tier, "frontier")
        self.assertEqual(matched_rule, "very_hard_frontier")

    def test_hard_complexity_routes_to_mid_cloud(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(risk="medium", complexity_score=14),
        )

        self.assertEqual(tier, "mid_cloud")
        self.assertEqual(matched_rule, "hard_work_mid_cloud")

    def test_strict_instruction_following_routes_to_mid_cloud(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(risk="low", complexity_score=10, instruction_following="strict"),
        )

        self.assertEqual(tier, "mid_cloud")
        self.assertEqual(matched_rule, "strict_instruction_mid_cloud")

    def test_weak_validation_overrides_strict_instruction_following(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(
                risk="low",
                validation_strength="weak",
                complexity_score=10,
                instruction_following="strict",
            ),
        )

        self.assertEqual(tier, "frontier")
        self.assertEqual(matched_rule, "weak_validation_escalate")

    def test_level_8_test_generation_routes_to_mid_cloud(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(task_type="test", risk="low", test_complexity_level=8),
        )

        self.assertEqual(tier, "mid_cloud")
        self.assertEqual(matched_rule, "characterization_tests_mid_cloud")

    def test_level_7_test_generation_routes_to_local_coding(self) -> None:
        tier, _reason, matched_rule = select_model(
            load_selector_policy(),
            selector_args(task_type="test", risk="medium", test_complexity_level=7),
        )

        self.assertEqual(tier, "local_coding")
        self.assertEqual(matched_rule, "local_test_generation")

    def test_model_selection_records_complexity_metadata(self) -> None:
        registry = load_model_registry(local_override_path=MISSING_LOCAL_REGISTRY)
        args = selector_args(risk="low", complexity_score=13, test_complexity_level=7)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "run1" / "model_selection.json"
            output_path.parent.mkdir()

            payload = build_model_selection(
                args=args,
                original_args=args,
                inferred_routing=infer_routing(args, Path(tmpdir)),
                project_root=Path(tmpdir),
                output_path=output_path,
                selected_tier="local_coding",
                selection_reason="test reason",
                matched_rule="easy_moderate_local_coding",
                tier=registry["local_coding"],
                fallbacks=["mid_cloud", "frontier"],
                registry=registry,
                manual_override=True,
            )

        self.assertEqual(payload["complexity_score"], 13)
        self.assertEqual(payload["complexity_band"], "moderate")
        self.assertEqual(payload["test_complexity_level"], 7)
        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(json.loads(json.dumps(payload))["selected_tier"], "local_coding")
        self.assertEqual(payload["execution_boundary"], "automatic_provider_execution_with_validation")
        self.assertEqual(payload["selected_model"]["provider"], "goose")
        self.assertEqual(payload["selected_model"]["model"], "unsloth/gemma-4-E4B-it-GGUF:Q4_K_M")
        self.assertIn("unsloth/gemma-4-E2B-it-GGUF:Q4_K_M", payload["selected_model"]["fallback_models"])
        self.assertEqual(payload["model_registry"]["base_registry_path"], "configs/model_registry.yaml")
        self.assertFalse(payload["model_registry"]["local_override_loaded"])
        self.assertNotIn("local_override_path", payload["model_registry"])
        self.assertEqual(payload["routing_feedback"]["status"], "not_provided")
        self.assertEqual(payload["routing_feedback"]["policy"], {
            "min_runs": 5,
            "strong_acceptance_rate": 0.8,
            "high_review_rate": 0.5,
            "high_failure_rate": 0.35,
        })

    def test_inferred_routing_fills_missing_complexity_without_overriding_explicit_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            code_path = Path(tmpdir) / "workflow.py"
            code_path.write_text(
                "\n".join(
                    [
                        "class Workflow:",
                        "    def apply(self, state, event):",
                        "        if event == 'commit':",
                        "            self.status = 'done'",
                        "        if event == 'rollback':",
                        "            self.status = 'open'",
                    ]
                ),
                encoding="utf-8",
            )
            args = selector_args(complexity_score=8)
            args.code_file = [str(code_path)]
            args.task_text = "Implement strict transactional workflow state handling."
            inferred = infer_routing(args, Path(tmpdir))

        self.assertIsNotNone(inferred.complexity_score)
        self.assertGreater(inferred.complexity_score, 8)
        routed_args = effective_args(args, inferred)
        self.assertEqual(routed_args.complexity_score, 8)

    def test_select_model_payload_writes_existing_artifact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                validation_strength="medium",
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload, written)
        self.assertEqual(payload["status"], "selected")
        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["matched_rule"], "easy_moderate_local_coding")
        self.assertEqual(payload["complexity_band"], "moderate")
        self.assertEqual(payload["selected_model"]["provider"], "goose")
        self.assertEqual(payload["routing_feedback"]["status"], "not_provided")

    def test_routing_feedback_policy_loads_conservative_defaults(self) -> None:
        policy = load_routing_feedback_policy()

        self.assertEqual(policy.min_runs, 5)
        self.assertEqual(policy.strong_acceptance_rate, 0.8)
        self.assertEqual(policy.high_review_rate, 0.5)
        self.assertEqual(policy.high_failure_rate, 0.35)

    def test_missing_routing_feedback_source_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(Path(tmpdir) / "missing.json"),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["routing_feedback"]["status"], "source_missing")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "no_change")

    def test_invalid_routing_feedback_source_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            feedback_path.write_text("{invalid", encoding="utf-8")
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["routing_feedback"]["status"], "source_invalid")

    def test_wrong_routing_feedback_schema_is_non_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            feedback_path.write_text(
                json.dumps({"routing_feedback_candidates": {"bad": {"total": 1}}}),
                encoding="utf-8",
            )
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "source_invalid")

    def test_no_matching_routing_feedback_candidate_collects_more_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(risk="low")
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "no_match")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "collect_more_evidence")

    def test_routing_feedback_below_minimum_runs_is_insufficient_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(accepted=1)
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "insufficient_evidence")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "collect_more_evidence")
        self.assertEqual(payload["routing_feedback"]["candidate"]["total"], 1)

    def test_related_sample_feedback_below_minimum_runs_is_insufficient_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(selected_tier="frontier", accepted=0, review_required=1)
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["routing_feedback"]["status"], "insufficient_evidence")
        self.assertEqual(payload["routing_feedback"]["candidate"]["related_candidate_keys"], [key])

    def test_docs_only_current_tier_policy_prefers_current_tier_without_mutating_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                risk="low",
                complexity_band="easy",
                accepted=6,
            )
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="low",
                complexity_score=8,
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "prefer_current_tier")
        self.assertIn("docs_only_current_tier_when_accepted", payload["routing_feedback"]["reason"])
        self.assertEqual(payload["routing_feedback"]["candidate_key"], key)

    def test_high_acceptance_non_policy_feedback_does_not_prefer_current_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(accepted=5)
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "no_change")
        self.assertIn("no bounded advisory policy", payload["routing_feedback"]["reason"])
        self.assertEqual(payload["routing_feedback"]["candidate_key"], key)

    def test_docs_only_policy_rejects_medium_risk_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                risk="medium",
                complexity_band="easy",
                accepted=6,
            )
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=8,
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "no_change")
        self.assertEqual(payload["routing_feedback"]["candidate_key"], key)

    def test_docs_only_policy_rejects_non_easy_complexity_bucket(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                risk="low",
                complexity_band="moderate",
                accepted=6,
            )
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="low",
                complexity_score=13,
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "no_change")
        self.assertEqual(payload["routing_feedback"]["candidate_key"], key)

    def test_fallback_scaffold_payload_never_counts_as_routing_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "pr_decision.json"
            feedback_path.write_text(
                json.dumps(
                    {
                        "evidence_source": "fallback_scaffold",
                        "outcome": "block",
                        "reason_codes": ["pr_gate.acceptance_evidence_missing"],
                    }
                ),
                encoding="utf-8",
            )
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="low",
                complexity_score=8,
                recipe="workbench-docs-only-acceptance.yaml",
                validation_profile="docs_only",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "source_invalid")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "no_change")

    def test_high_review_routing_feedback_suggests_escalation_for_non_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(
                accepted=2,
                review_required=3,
                top_failure_reasons={"command_failed:full_test_suite": 3},
            )
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="medium",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "consider_escalation")
        self.assertEqual(
            payload["routing_feedback"]["candidate"]["top_failure_reasons"]["command_failed:full_test_suite"],
            3,
        )

    def test_high_review_routing_feedback_requires_human_review_for_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            feedback_path = tmp_path / "run_metrics.json"
            key, candidate = candidate_payload(
                selected_tier="frontier",
                risk="high",
                accepted=2,
                review_required=3,
            )
            write_feedback(feedback_path, {key: candidate})
            output_path = tmp_path / "run1" / "model_selection.json"
            args = selector_args(
                risk="high",
                complexity_score=13,
                recipe="workbench-engineering-acceptance.yaml",
                validation_profile="low_risk_coding",
                routing_feedback_path=str(feedback_path),
            )
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload_without_local(args)

        self.assertEqual(payload["selected_tier"], "frontier")
        self.assertEqual(payload["routing_feedback"]["status"], "advisory")
        self.assertEqual(payload["routing_feedback"]["recommendation"], "require_human_review")

    def test_default_registry_loads_without_local_override(self) -> None:
        registry_load = load_model_registry_with_source(
            base_path=MODEL_REGISTRY,
            local_override_path=MISSING_LOCAL_REGISTRY,
            registry_root=ROOT,
        )

        self.assertFalse(registry_load.source["local_override_loaded"])
        self.assertEqual(registry_load.source["base_registry_path"], "configs/model_registry.yaml")
        self.assertNotIn("local_override_path", registry_load.source)
        self.assertEqual(registry_load.registry["local_coding"].provider, "goose")
        self.assertEqual(registry_load.registry["mid_cloud"].model, "deepseek/deepseek-v4-flash")

    def test_local_registry_override_replaces_one_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_path = tmp_path / "model_registry.yaml"
            local_path = tmp_path / "model_registry.local.yaml"
            base_path.write_text(MODEL_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
            local_path.write_text(
                "\n".join(
                    [
                        "models:",
                        "  local_coding:",
                        "    model: public-local-coder",
                    ]
                ),
                encoding="utf-8",
            )

            registry_load = load_model_registry_with_source(
                base_path=base_path,
                local_override_path=local_path,
                registry_root=tmp_path,
            )

        self.assertTrue(registry_load.source["local_override_loaded"])
        self.assertEqual(registry_load.source["base_registry_path"], "model_registry.yaml")
        self.assertEqual(registry_load.source["local_override_path"], "model_registry.local.yaml")
        self.assertEqual(registry_load.registry["local_coding"].provider, "goose")
        self.assertEqual(registry_load.registry["local_coding"].model, "public-local-coder")

    def test_local_registry_override_merges_nested_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_path = tmp_path / "model_registry.yaml"
            local_path = tmp_path / "model_registry.local.yaml"
            base_path.write_text(MODEL_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
            local_path.write_text(
                "\n".join(
                    [
                        "models:",
                        "  frontier:",
                        "    parameters:",
                        "      max_output_tokens: 16000",
                    ]
                ),
                encoding="utf-8",
            )

            registry = load_model_registry(
                base_path=base_path,
                local_override_path=local_path,
                registry_root=tmp_path,
            )

        self.assertEqual(registry["frontier"].parameters["reasoning_effort"], "xhigh")
        self.assertEqual(registry["frontier"].parameters["max_output_tokens"], 16000)

    def test_local_registry_override_replaces_fallback_models_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_path = tmp_path / "model_registry.yaml"
            local_path = tmp_path / "model_registry.local.yaml"
            base_path.write_text(MODEL_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
            local_path.write_text(
                "\n".join(
                    [
                        "models:",
                        "  local_coding:",
                        "    fallback_models:",
                        "      - public-fallback-coder",
                    ]
                ),
                encoding="utf-8",
            )

            registry = load_model_registry(
                base_path=base_path,
                local_override_path=local_path,
                registry_root=tmp_path,
            )

        self.assertEqual(registry["local_coding"].fallback_models, ["public-fallback-coder"])

    def test_invalid_registry_override_schema_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_path = tmp_path / "model_registry.yaml"
            local_path = tmp_path / "model_registry.local.yaml"
            base_path.write_text(MODEL_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
            local_path.write_text(
                "\n".join(
                    [
                        "models:",
                        "  local_coding:",
                        "    provider:",
                        "      invalid: true",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "local_coding.*provider"):
                load_model_registry(
                    base_path=base_path,
                    local_override_path=local_path,
                    registry_root=tmp_path,
                )

    def test_selector_reference_validation_covers_defaults_rules_and_fallbacks(self) -> None:
        registry = load_model_registry(local_override_path=MISSING_LOCAL_REGISTRY)
        validate_selector_references(load_selector_policy(), registry)

        broken_policy = SelectorPolicy(
            default_model="missing_default",
            manual_override=True,
            rules=[
                SelectorRule(
                    name="broken_rule",
                    conditions={"risk": "low"},
                    select="missing_rule_select",
                    reason="exercise selector reference validation",
                )
            ],
            fallbacks={"missing_fallback_key": ["missing_fallback_value"]},
        )

        with self.assertRaises(ValueError) as raised:
            validate_selector_references(broken_policy, registry)
        message = str(raised.exception)
        self.assertIn("default_model=missing_default", message)
        self.assertIn("rules=missing_rule_select", message)
        self.assertIn("fallback_keys=missing_fallback_key", message)
        self.assertIn("fallback_values=missing_fallback_value", message)

    def test_selector_uses_overridden_model_in_model_selection_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            base_path = tmp_path / "model_registry.yaml"
            local_path = tmp_path / "model_registry.local.yaml"
            output_path = tmp_path / "run1" / "model_selection.json"
            base_path.write_text(MODEL_REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
            local_path.write_text(
                "\n".join(
                    [
                        "models:",
                        "  local_coding:",
                        "    model: public-local-coder",
                    ]
                ),
                encoding="utf-8",
            )
            args = selector_args(risk="medium", complexity_score=13)
            args.project = "ai_workbench_mcp"
            args.out = str(output_path)

            payload = select_model_payload(
                args,
                registry_base_path=base_path,
                registry_local_override_path=local_path,
                registry_root=tmp_path,
            )
            written = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload, written)
        self.assertEqual(payload["selected_tier"], "local_coding")
        self.assertEqual(payload["selected_model"]["model"], "public-local-coder")
        self.assertEqual(payload["model_registry"]["base_registry_path"], "model_registry.yaml")
        self.assertTrue(payload["model_registry"]["local_override_loaded"])
        self.assertEqual(payload["model_registry"]["local_override_path"], "model_registry.local.yaml")
        self.assertNotIn(":", payload["model_registry"]["base_registry_path"])
        self.assertNotIn(":", payload["model_registry"]["local_override_path"])


if __name__ == "__main__":
    unittest.main()
