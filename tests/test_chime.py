"""Unit tests for Project CHIME and cxas-scrapi compatibility."""

import os
import unittest
import yaml
import zipfile
from chime.core.hydrator import AccountHydrator
from chime.core.harmonizer import harmonize_subagent_tier, build_multi_turn_dialogue
from chime.core.versioning import GoldenVersionManager
from chime.core.introspector import load_golden_cases_from_yaml, load_goldens_for_subagent
from chime.generators.openxml_excel import generate_manual_qa_excel_suite, QA_HEADERS
from chime.generators.scrapi_yaml import export_scrapi_simulation_suite, export_scrapi_goldens_suite
from chime.generators.decisions_report import generate_decisions_report


class TestChimeCore(unittest.TestCase):
    def setUp(self):
        self.hydrator = AccountHydrator()
        self.subagent_meta = {
            "key": "techsetup",
            "domain_label": "Broadband Tech Setup",
            "prefix": "TECH",
            "agent_dir": "techsetup",
            "default_ver": "HLV",
            "default_kb": False,
            "codebase_info": {
                "tools": ["diagnose_line", "reboot_router"],
                "callbacks": ["beforeAgentCallbacks:validate_account"],
                "instruction_lines": 35,
                "instruction_chars": 1500,
                "last_modified": "2026-11-06 00:00"
            }
        }

    def test_hydrator_account_lookup(self):
        acc = self.hydrator.get_account_for_test("techsetup", "Happy Path", auth_required=True)
        self.assertIn("cli_phone", acc)
        self.assertIn("postcode", acc)
        self.assertIn("formatted_summary", acc)
        self.assertIn("one_time_passcode", acc)
        self.assertIn("channel_context", acc)
        self.assertIn("voice", acc["channel_context"])
        self.assertIn("chat", acc["channel_context"])

    def test_tier_harmonization_sanity_counts_and_priorities(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        self.assertEqual(len(cases), 12)
        self.assertEqual(cases[0]["journey"], "Broadband Tech Setup")
        # In Sanity, blockers are P0
        self.assertEqual(cases[0]["priority"], "P0")

    def test_tier_harmonization_regression_counts(self):
        cases = harmonize_subagent_tier("regression", [], self.subagent_meta, self.hydrator)
        self.assertEqual(len(cases), 26)
        # Checks that P0, P1, and P2 priorities are present in regression suite
        priorities = set(c["priority"] for c in cases)
        self.assertIn("P0", priorities)
        self.assertIn("P1", priorities)
        self.assertIn("P2", priorities)

    def test_multi_turn_dialogue_generation(self):
        account = self.hydrator.get_account_for_test("techsetup", "Happy Path", auth_required=True)
        dialogue = build_multi_turn_dialogue(
            scenario_type="Happy Path",
            domain_label="Broadband Tech Setup",
            subagent_key="techsetup",
            account_data=account,
            initial_utt="My internet is running very slow."
        )
        self.assertGreaterEqual(len(dialogue), 3)
        # Check that user provides hydrated phone and postcode in turn 2
        user_turn_2 = dialogue[1]["user"]
        self.assertIn(account["cli_phone"], user_turn_2)
        self.assertIn(account["postcode"], user_turn_2)

    def test_cxas_scrapi_simulation_yaml_schema(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        test_yaml = "/tmp/test_cxas_scrapi_sim.yaml"
        export_scrapi_simulation_suite(test_yaml, "techsetup", "sanity", cases)

        self.assertTrue(os.path.exists(test_yaml))
        with open(test_yaml, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # cxas-scrapi expects top-level 'evals' key
        self.assertIn("evals", data)
        self.assertEqual(len(data["evals"]), 12)

        first_eval = data["evals"][0]
        self.assertIn("name", first_eval)
        self.assertIn("tags", first_eval)
        self.assertIn("steps", first_eval)
        self.assertIn("expectations", first_eval)
        self.assertIn("session_parameters", first_eval)

        step = first_eval["steps"][0]
        self.assertIn("goal", step)
        self.assertIn("success_criteria", step)
        self.assertIn("response_guide", step)

        os.remove(test_yaml)

    def test_cxas_scrapi_golden_yaml_schema(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        test_gld = "/tmp/test_cxas_scrapi_gld.yaml"
        export_scrapi_goldens_suite(test_gld, "techsetup", cases)

        self.assertTrue(os.path.exists(test_gld))
        with open(test_gld, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("conversations", data)
        self.assertEqual(len(data["conversations"]), 12)
        first_conv = data["conversations"][0]
        self.assertIn("conversation", first_conv)
        self.assertIn("turns", first_conv)
        self.assertIn("expectations", first_conv)
        self.assertIn("tags", first_conv)

        os.remove(test_gld)

    def test_decisions_report_generation(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        test_report = "/tmp/test_decisions_report.md"
        generate_decisions_report(
            output_report_path=test_report,
            suite_tier="sanity",
            app_title="CXAS Telecom Concierge",
            timestamp="2026-11-06 00:00:00",
            subagents_meta=[self.subagent_meta],
            all_test_cases=cases
        )

        self.assertTrue(os.path.exists(test_report))
        with open(test_report, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Project CHIME · Decisions & Changes Audit Report", content)
        self.assertIn("P0 (Critical / Blocker)", content)
        self.assertIn("5-Pillar Guardrails", content)
        self.assertIn("Zero-Context Credential Hydration", content)

        os.remove(test_report)

    def test_golden_version_manager(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        base_dir = "/tmp/test_chime_versions_goldens"
        if os.path.exists(base_dir):
            import shutil
            shutil.rmtree(base_dir)

        mgr = GoldenVersionManager(base_dir)
        # 1. Record first run (creates v1 baseline and v2 reconciled)
        info1 = mgr.record_version(
            subagent_key="techsetup",
            baseline_cases=cases[:3],
            reconciled_cases=cases,
            reconciliation_notes=["Initial reconciliation"],
            agent_meta=self.subagent_meta
        )
        self.assertEqual(info1["current_version"], "v2")
        self.assertEqual(info1["baseline_version"], "v1")
        
        # Verify files exist on disk
        v1_path = os.path.join(base_dir, "versions", "v1_baseline", "golden_techsetup.yaml")
        history_path = os.path.join(base_dir, "versions", "history_techsetup.json")
        active_path = os.path.join(base_dir, "golden_techsetup.yaml")

        self.assertTrue(os.path.exists(v1_path))
        self.assertTrue(os.path.exists(history_path))
        self.assertTrue(os.path.exists(active_path))

        # 2. Record subsequent update (creates v3)
        info2 = mgr.record_version(
            subagent_key="techsetup",
            baseline_cases=cases[:3],
            reconciled_cases=cases,
            reconciliation_notes=["Added new tool reboot_router"],
            agent_meta=self.subagent_meta
        )
        self.assertEqual(info2["current_version"], "v3")

        import shutil
        shutil.rmtree(base_dir)

    def test_openxml_excel_generation(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        rows = [QA_HEADERS]
        for c in cases:
            rows.append([
                c["id"], c["journey"], c["name"], c["scenario_type"], c["priority"],
                c["test_account"], c["primary_app_tag"], c["verification_required"],
                c["kb_trigger_eligible"], c["expected_agents_path"], c["initial_utterance"],
                c["simulated_conversation"], c["expected_tools_flow"], c["pass_criteria"],
                "", ""
            ])
        
        test_out = "/tmp/test_chime_workbook.xlsx"
        generate_manual_qa_excel_suite(test_out, "sanity", "Test App", "2026-11-06", {"Broadband Tech Setup": rows})
        
        self.assertTrue(os.path.exists(test_out))
        with zipfile.ZipFile(test_out, "r") as z:
            self.assertIn("xl/workbook.xml", z.namelist())
            self.assertIn("xl/sharedStrings.xml", z.namelist())
        os.remove(test_out)


if __name__ == "__main__":
    unittest.main()
