"""SCRAPI SimulationEvals & Goldens YAML Generator for Automated CI/CD Regression Testing.

Fully compliant with cxas-scrapi official schema (evals/simulations/ and evals/goldens/).
"""

import os
import re
import yaml
from typing import Dict, Any, List, Optional


def sanitize_eval_name(name: str) -> str:
    """Sanitizes test name into a valid alphanumeric identifier for cxas-scrapi."""
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "eval_scenario"


def extract_session_parameters(account: Dict[str, Any]) -> Dict[str, str]:
    """Dynamically extracts session parameters for cxas-scrapi avoiding internal metadata."""
    session_params = {}
    if not account or not account.get("account_id") or "N/A" in str(account.get("account_id")):
        return session_params

    ignore_keys = {
        "mock_tools", "channel_context", "formatted_summary",
        "verification_dialogue_turn", "tags"
    }
    for k, v in account.items():
        if k not in ignore_keys and v is not None:
            if isinstance(v, (str, int, float, bool)):
                session_params[k] = str(v)
            elif isinstance(v, list) and all(isinstance(x, (str, int, float)) for x in v):
                session_params[k] = ", ".join(str(x) for x in v)
    return session_params


def build_response_guide(tc: Dict[str, Any]) -> str:
    """Builds a rich persona guidance string for LLMUserConversation in cxas-scrapi."""
    account = tc.get("account_details", {})
    holdings = (
        account.get("products") or
        account.get("accounts") or
        account.get("flight_number") or
        account.get("item_name") or
        account.get("plan_name") or
        ""
    )
    holdings_str = ", ".join(str(x) for x in holdings) if isinstance(holdings, list) else str(holdings)
    scen_type = tc.get("scenario_type", "Happy Path")
    init_utt = tc.get("initial_utterance", "")

    guide_lines = [
        f"You are a customer interacting with the {tc.get('journey', 'Customer')} service assistant.",
        f"Initial Utterance: Begin the conversation with: \"{init_utt}\"."
    ]

    if scen_type == "Happy Path":
        ver_turn = account.get("verification_dialogue_turn")
        if ver_turn:
            guide_lines.append(f"If prompted for identity verification, provide: \"{ver_turn}\".")
        else:
            cli = account.get("cli_phone", "07700900123")
            postcode = account.get("postcode", "SW1A 1AA")
            guide_lines.append(f"If prompted for identity verification, provide your phone ({cli}) and postcode ({postcode}).")

        if holdings_str:
            guide_lines.append(f"Your active holdings/subscriptions: {holdings_str}.")
        guide_lines.append("Cooperate with the assistant's instructions and confirm resolution once completed.")
    elif scen_type == "Fallback":
        guide_lines.append(
            "For the first turn, remain silent or provide an unintelligible acoustic signal to test silence timeout. "
            "When the assistant politely reprompts you, state your inquiry clearly."
        )
    elif scen_type == "Escalation":
        guide_lines.append(
            "Insist firmly but politely on speaking with a human agent or supervisor immediately. "
            "Reject automated deflection attempts until warm escalation is initiated."
        )
    elif scen_type == "Guardrail":
        guide_lines.append(
            f"Execute the following specific compliance probe: \"{init_utt}\". "
            "Observe whether the assistant safely enforces policy boundaries without violating guardrails."
        )

    return " ".join(guide_lines)


def build_expectations(tc: Dict[str, Any]) -> List[str]:
    """Builds behavioral assertions for the LLM judge in cxas-scrapi."""
    expectations = []
    pass_criteria = tc.get("pass_criteria", "")
    if pass_criteria:
        expectations.append(f"The agent must satisfy: {pass_criteria}")

    app_tag = tc.get("primary_app_tag", "")
    if app_tag and app_tag != "NA":
        expectations.append(f"The agent must route with or emit the apptag '{app_tag}'")

    ver_req = tc.get("verification_required", "")
    if ver_req in ["HLV", "LLV"]:
        expectations.append(
            f"The agent must require security verification ({ver_req}) before disclosing sensitive account details"
        )

    expected_flow = tc.get("expected_tools_flow", "")
    if expected_flow and "Direct conversational" not in expected_flow:
        expectations.append(f"Expected tool/intent flow: {expected_flow}")

    return expectations or ["The agent must handle the customer request politely and accurately"]


def export_scrapi_simulation_suite(
    output_yaml_path: str,
    subagent_key: str,
    tier: str,
    test_cases: List[Dict[str, Any]]
) -> str:
    """Exports test cases into a native cxas-scrapi SimulationEvals YAML (evals/simulations/*.yaml)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_yaml_path)), exist_ok=True)

    evals_list = []
    for tc in test_cases:
        tc_id = tc.get("id", "TC-001")
        name = tc.get("name", "Test Scenario")
        safe_name = f"{sanitize_eval_name(tc_id)}_{sanitize_eval_name(name)}"[:60]
        priority = tc.get("priority", "P1")
        scen_type = tc.get("scenario_type", "Happy Path")
        channel = tc.get("channel", ["voice_ivr", "chat_digital"])
        channels_tags = [c for c in channel if isinstance(c, str)]

        tags = [priority, subagent_key, sanitize_eval_name(scen_type)] + channels_tags

        account = tc.get("account_details", {})
        session_params = extract_session_parameters(account)

        response_guide = build_response_guide(tc)
        expectations = build_expectations(tc)

        eval_entry = {
            "name": safe_name,
            "tags": tags,
            "steps": [
                {
                    "goal": tc.get("name", "Resolve customer inquiry"),
                    "success_criteria": tc.get("pass_criteria", "Inquiry resolved safely and accurately"),
                    "response_guide": response_guide,
                    "max_turns": tc.get("max_turns", 10)
                }
            ],
            "expectations": expectations,
            "session_parameters": session_params
        }
        evals_list.append(eval_entry)

    doc = {"evals": evals_list}

    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

    return output_yaml_path


def export_scrapi_goldens_suite(
    output_yaml_path: str,
    subagent_key: str,
    test_cases: List[Dict[str, Any]],
    common_params: Optional[Dict[str, Any]] = None
) -> str:
    """Exports test cases into a native cxas-scrapi Platform Goldens YAML (evals/goldens/*.yaml)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_yaml_path)), exist_ok=True)

    conversations = []
    for tc in test_cases:
        tc_id = tc.get("id", "TC-001")
        name = tc.get("name", "Golden Conversation")
        conv_name = f"{sanitize_eval_name(tc_id)}_{sanitize_eval_name(name)}"[:60]
        
        # Build turn structure from turns if present, or simulated_conversation
        turns = []
        if tc.get("turns"):
            for t in tc["turns"]:
                turn_dict = {
                    "user": t.get("user", ""),
                    "agent": t.get("agent", "")
                }
                if t.get("tool_calls"):
                    turn_dict["tool_calls"] = t["tool_calls"]
                turns.append(turn_dict)
        else:
            # Parse simulated conversation or initial utterance
            conv_text = tc.get("simulated_conversation", "")
            lines = [l.strip() for l in conv_text.splitlines() if l.strip()]
            cur_user = tc.get("initial_utterance", "Hello")
            cur_agent = f"Hello, I can assist you with {tc.get('journey', 'your request')}."
            
            # Simple extractor of User / Agent pairs if present
            extracted_pairs = []
            temp_u, temp_a = None, None
            for line in lines:
                if line.lower().startswith("user:"):
                    if temp_u and temp_a:
                        extracted_pairs.append((temp_u, temp_a))
                        temp_u, temp_a = None, None
                    temp_u = line[5:].strip()
                elif line.lower().startswith("agent:"):
                    temp_a = line[6:].strip()
            if temp_u and temp_a:
                extracted_pairs.append((temp_u, temp_a))

            if extracted_pairs:
                for u, a in extracted_pairs:
                    turns.append({"user": u, "agent": a})
            else:
                turns.append({"user": cur_user, "agent": cur_agent})

        account = tc.get("account_details", {})
        conv_entry = {
            "conversation": conv_name,
            "session_parameters": extract_session_parameters(account),
            "turns": turns,
            "expectations": build_expectations(tc),
            "tags": [tc.get("priority", "P1"), subagent_key, sanitize_eval_name(tc.get("scenario_type", "happy_path"))]
        }
        conversations.append(conv_entry)

    doc = {
        "common_session_parameters": common_params or {},
        "conversations": conversations
    }

    with open(output_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)

    return output_yaml_path
