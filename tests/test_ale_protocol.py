from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AleProtocolContractTests(unittest.TestCase):
    def test_authoritative_files_exist(self) -> None:
        for relative in (
            "docs/agentic_loop_engineering.md",
            "PROJECT_STATE.yaml",
            "CURRENT_ROUTE.md",
            "CODEX_WORKFLOW.md",
            "docs/history/CURRENT_ROUTE_FULL_HISTORY.md",
            "docs/ale_ta_1_manual_acceptance.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_protocol_defines_three_mutually_exclusive_modes(self) -> None:
        text = (ROOT / "docs/agentic_loop_engineering.md").read_text(encoding="utf-8")
        for term in (
            "ALE v1.5.0",
            "three mutually exclusive execution modes",
            "Micro Fix Loop",
            "Deterministic Fast Loop",
            "Full ALE",
            "Automated verification does not equal human acceptance.",
            "maximum of three minimal self-repair rounds",
        ):
            self.assertIn(term, text)

    def test_state_is_json_compatible_yaml_for_teaching_assist(self) -> None:
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["project"], "TeachingAssist")
        self.assertEqual(state["ale_protocol_version"], "1.5.0")
        self.assertEqual(
            state["git"]["baseline_commit"],
            "4ed88a90a07ff44383be17ade63eb4e677e053df",
        )
        self.assertEqual(
            state["git"]["authorized_work_branch"],
            "main",
        )
        self.assertTrue(state["git"]["merge_main_allowed"])
        self.assertTrue(state["git"]["push_origin_main_allowed"])

    def test_route_is_compact_and_points_to_machine_authority(self) -> None:
        text = (ROOT / "CURRENT_ROUTE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 140)
        self.assertIn("PROJECT_STATE.yaml", text)
        self.assertIn("single machine authority", text)
        self.assertIn("真实机房试点", text)

    def test_source_project_business_terms_are_not_imported(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "docs/agentic_loop_engineering.md",
                "PROJECT_STATE.yaml",
                "CURRENT_ROUTE.md",
                "CODEX_WORKFLOW.md",
            )
        )
        for forbidden in ("P23.R3", "P24", "candidate report", "CNC-01"):
            self.assertNotIn(forbidden, combined)

    def test_agents_contains_only_compact_ale_entry(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("docs/agentic_loop_engineering.md", text)
        self.assertIn("PROJECT_STATE.yaml", text)
        self.assertIn("CURRENT_ROUTE.md", text)
        self.assertLess(text.count("Micro Fix Loop"), 2)

    def test_accepted_outcome_records_user_authorized_main_integration(self) -> None:
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["control_plane"]["status"], "accepted_closed")
        self.assertEqual(state["control_plane"]["manual_acceptance"], "accepted")
        self.assertFalse(state["control_plane"]["bootstrap_in_place_allowed"])
        self.assertFalse(state["git"]["push_work_branch_allowed"])
        self.assertTrue(state["git"]["merge_main_allowed"])
        self.assertTrue(state["git"]["push_origin_main_allowed"])
        self.assertFalse(
            state["verification"]["automated_tests_equal_human_acceptance"]
        )

        parallel = state["parallel_work"]
        self.assertTrue(parallel["present_in_authorized_branch"])
        self.assertFalse(parallel["included_in_ale_acceptance"])
        self.assertTrue(parallel["main_integration_authorized"])

        package = (ROOT / "docs/ale_ta_1_manual_acceptance.md").read_text(
            encoding="utf-8"
        )
        for term in (
            "status: accepted_closed",
            "manual_acceptance: accepted",
            "b4c1958 / 891e225 / 8a6cd2c",
            "main integration authorized",
            "Automated verification does not equal human acceptance.",
        ):
            self.assertIn(term, package)


if __name__ == "__main__":
    unittest.main()
