import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from model_select import (
    build_model_selection,
    complexity_band,
    effective_args,
    infer_routing,
    load_model_registry,
    load_selector_policy,
    select_model,
)


def selector_args(
    *,
    task_type: str = "implement",
    risk: str = "medium",
    validation_strength: str = "medium",
    prompt: str = "implement_request_change_request",
    complexity_score: int | None = None,
    test_complexity_level: int | None = None,
    instruction_following: str = "normal",
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
    )


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
        registry = load_model_registry()
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


if __name__ == "__main__":
    unittest.main()
