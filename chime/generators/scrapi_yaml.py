"""SCRAPI SimulationEvals YAML Generator for Automated CI/CD Regression Testing."""

import os
import yaml
from typing import Dict, Any, List


def export_scrapi_simulation_suite(output_yaml_path: str, subagent_key: str, tier: str, test_cases: List[Dict[str, Any]]) -> str:
    """Exports a list of normalized test case models into a strongly-typed SCRAPI SimulationEval YAML file."""
    os.makedirs(os.path.dirname(os.path.abspath(output_yaml_path)), exist_ok=True)

    simulations = []
    for tc in test_cases:
        tc_id = tc.get("id") or tc.get("test_case_id", "TC-001")
        name = tc.get("name", "Test Scenario")
        user_utt = tc.get("utterance") or tc.get("initial_utterance", "")
        app_tag = tc.get("app_tag") or tc.get("primary_app_tag", "")
        flow = tc.get("expected_flow", [])
        channel = tc.get("channel", ["voice_ivr", "chat_digital"])

        entry = {
            "test_case_id": tc_id,
            "name": name,
            "tier": tier,
            "subagent": subagent_key,
            "channel": channel,
            "conversation": [
                {
                    "turn": 1,
                    "user_utterance": user_utt,
                    "expectations": {
                        "agent_response_patterns": tc.get("expected_patterns", []),
                        "tool_calls": tc.get("tool_calls", []),
                        "apptags": [app_tag] if app_tag else []
                    }
                }
            ],
            "thresholds": {
                "semantic_similarity": 0.85,
                "tool_arguments_match": "strict"
            }
        }
        simulations.append(entry)

    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(simulations, f, default_flow_style=False, sort_keys=False)

    return output_yaml_path
