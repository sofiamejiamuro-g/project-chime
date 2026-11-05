"""Basic smoke test for Project CHIME."""

import os
import unittest
import zipfile
from chime.core.hydrator import AccountHydrator
from chime.core.harmonizer import harmonize_subagent_tier
from chime.generators.openxml_excel import generate_manual_qa_excel_suite, QA_HEADERS
from chime.generators.scrapi_yaml import export_scrapi_simulation_suite

class TestChimeCore(unittest.TestCase):
    def setUp(self):
        self.hydrator = AccountHydrator()
        self.subagent_meta = {
            "key": "test_agent",
            "domain_label": "Test Service",
            "prefix": "TST",
            "agent_dir": "test_agent",
            "default_ver": "HLV",
            "default_kb": False
        }

    def test_hydrator_account_lookup(self):
        acc = self.hydrator.get_account_for_test("techsetup", "Happy Path", auth_required=True)
        self.assertIn("cli_phone", acc)
        self.assertIn("postcode", acc)
        self.assertIn("formatted_summary", acc)

    def test_tier_harmonization_sanity(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        self.assertEqual(len(cases), 12)
        self.assertEqual(cases[0]["journey"], "Test Service")

    def test_openxml_excel_generation(self):
        cases = harmonize_subagent_tier("sanity", [], self.subagent_meta, self.hydrator)
        rows = [QA_HEADERS]
        for c in cases:
            rows.append([c["id"], c["journey"], c["name"], c["scenario_type"], c["priority"], c["test_account"], c["primary_app_tag"], c["verification_required"], c["kb_trigger_eligible"], c["expected_agents_path"], c["initial_utterance"], c["simulated_conversation"], c["expected_tools_flow"], c["pass_criteria"], "", ""])
        
        test_out = "/tmp/test_chime_workbook.xlsx"
        generate_manual_qa_excel_suite(test_out, "sanity", "Test App", "2026-11-05", {"Test Service": rows})
        
        self.assertTrue(os.path.exists(test_out))
        with zipfile.ZipFile(test_out, "r") as z:
            self.assertIn("xl/workbook.xml", z.namelist())
        os.remove(test_out)

if __name__ == "__main__":
    unittest.main()
