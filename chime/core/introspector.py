"""Sub-Agent Codebase & Baseline Matrix Introspector for CXAS and Project CHIME."""

import datetime
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
import yaml
from typing import Dict, Any, List, Optional, Tuple

NS = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
RELS_NS = {'ns': 'http://schemas.openxmlformats.org/package/2006/relationships'}


def discover_subagents(agents_dir: str) -> Dict[str, Dict[str, Any]]:
    """Autonomously discovers all subagents in the agents directory."""
    discovered = {}
    if not os.path.exists(agents_dir):
        return discovered

    for entry in sorted(os.listdir(agents_dir)):
        full_path = os.path.join(agents_dir, entry)
        if os.path.isdir(full_path):
            inst_file = os.path.join(full_path, "instruction.txt")
            json_file = os.path.join(full_path, f"{entry}.json")
            agent_json = os.path.join(full_path, "agent.json")
            if os.path.exists(inst_file) or os.path.exists(json_file) or os.path.exists(agent_json):
                key = entry.lower().replace("-", "_").replace(" ", "_")
                label = entry.replace("_", " ").title()
                prefix = "".join([w[0].upper() for w in entry.split("_") if w])[:4] or "SUB"
                
                codebase_info = inspect_subagent_codebase(agents_dir, entry)
                
                discovered[label] = {
                    "key": key,
                    "alias": [key, entry.lower(), entry.replace("_", "")],
                    "agent_dir": entry,
                    "tag": key,
                    "domain_label": label,
                    "prefix": prefix,
                    "app_tags": [f"intent_{key}"],
                    "default_ver": "HLV" if any(w in key for w in ["verif", "account", "billing", "move", "cancel"]) else "NA",
                    "default_kb": ("kb" in key or "knowledge" in key),
                    "codebase_info": codebase_info
                }
    return discovered


def inspect_subagent_codebase(agents_dir: str, agent_folder: str) -> Dict[str, Any]:
    """Extract metadata, instructions, tools, and callbacks from subagent folder."""
    info = {
        "agent_folder": agent_folder,
        "exists": False,
        "instruction_lines": 0,
        "instruction_chars": 0,
        "last_modified": "N/A",
        "instruction_preview": "",
        "callbacks": [],
        "tools": []
    }
    agent_path = os.path.join(agents_dir, agent_folder)
    if not os.path.exists(agent_path):
        return info

    info["exists"] = True
    inst_path = os.path.join(agent_path, "instruction.txt")
    if os.path.exists(inst_path):
        with open(inst_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            info["instruction_chars"] = len(content)
            lines = content.splitlines()
            info["instruction_lines"] = len(lines)
            info["instruction_preview"] = " ".join([l.strip() for l in lines[:3] if l.strip()])[:200]
        mtime = os.path.getmtime(inst_path)
        info["last_modified"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    # Look for agent JSON definitions
    json_candidates = [
        os.path.join(agent_path, f"{agent_folder}.json"),
        os.path.join(agent_path, "agent.json")
    ]
    for j_path in json_candidates:
        if os.path.exists(j_path):
            try:
                with open(j_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tools_raw = data.get("tools", [])
                    info["tools"] = [t.split("/")[-1] for t in tools_raw]
                    for cb_type in ["beforeAgentCallbacks", "beforeModelCallbacks", "afterModelCallbacks", "afterToolCallbacks"]:
                        for cb in data.get(cb_type, []):
                            info["callbacks"].append(f"{cb_type}:{cb.split('/')[-1]}")
            except Exception:
                pass
            break

    return info


def load_shared_strings(z: zipfile.ZipFile) -> List[str]:
    """Parse shared strings XML table from Excel archive."""
    if 'xl/sharedStrings.xml' not in z.namelist():
        return []
    tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
    strings = []
    for si in tree.findall('ns:si', NS):
        text = ''.join([t.text or '' for t in si.findall('.//ns:t', NS)])
        strings.append(text)
    return strings


def extract_sheet_cell_grid(z: zipfile.ZipFile, sheet_name: str, sst: List[str]) -> List[Dict[str, str]]:
    """Extract cell grid from sheet XML."""
    if 'xl/workbook.xml' not in z.namelist() or 'xl/_rels/workbook.xml.rels' not in z.namelist():
        return []

    wb_tree = ET.fromstring(z.read('xl/workbook.xml'))
    wb_rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rels_map = {
        r.attrib['Id']: r.attrib['Target']
        for r in wb_rels.findall('ns:Relationship', RELS_NS)
    }

    target_path = None
    for s in wb_tree.findall('.//ns:sheet', NS):
        if sheet_name is None or s.attrib['name'].strip().lower() == sheet_name.strip().lower():
            rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = rels_map.get(rid, "")
            target_path = 'xl/' + target if not target.startswith('xl/') else target
            break

    if not target_path or target_path not in z.namelist():
        return []

    s_tree = ET.fromstring(z.read(target_path))
    rows = []
    for r in s_tree.findall('.//ns:row', NS):
        row_cells = {}
        for c in r.findall('ns:c', NS):
            ref = c.attrib.get('r', '')
            col_match = re.match(r'([A-Z]+)', ref)
            if not col_match:
                continue
            col_letter = col_match.group(1)
            t = c.attrib.get('t')
            val = ''
            if t == 'inlineStr':
                is_elem = c.find('ns:is', NS)
                if is_elem is not None and is_elem.find('ns:t', NS) is not None:
                    val = is_elem.find('ns:t', NS).text or ''
            else:
                v = c.find('ns:v', NS)
                if v is not None and v.text:
                    try:
                        val = sst[int(v.text)] if t == 's' else v.text
                    except Exception:
                        val = v.text
            row_cells[col_letter] = val.strip()
        rows.append(row_cells)
    return rows


def parse_test_cases_generic(rows: List[Dict[str, str]], is_10_col_suite: bool = False) -> List[Dict[str, Any]]:
    """Parse test cases from either multi-turn baseline format or 10/16-column suite format."""
    if not rows:
        return []

    header = rows[0]
    
    # 16-column CHIME QA format check
    if 'test case id' in header.get('A', '').lower() and 'full simulated conversation' in str(header.values()).lower():
        test_cases = []
        for r in rows[1:]:
            t_id = r.get('A', '').strip()
            if not t_id or t_id.lower().startswith('test case id'):
                continue
            test_cases.append({
                "id": t_id,
                "journey": r.get('B', ''),
                "name": r.get('C', t_id),
                "scenario_type": r.get('D', 'Happy Path'),
                "priority": r.get('E', 'P1'),
                "test_account": r.get('F', ''),
                "primary_app_tag": r.get('G', ''),
                "verification_required": r.get('H', 'HLV'),
                "kb_trigger_eligible": r.get('I', 'No'),
                "expected_agents_path": r.get('J', ''),
                "initial_utterance": r.get('K', ''),
                "simulated_conversation": r.get('L', ''),
                "expected_tools_flow": r.get('M', ''),
                "pass_criteria": r.get('N', '')
            })
        return test_cases

    # 10-column suite format check
    if is_10_col_suite or ('scenario description' in header.get('G', '').lower() or 'sample user utterance' in header.get('H', '').lower()):
        test_cases = []
        for r in rows[1:]:
            t_id = r.get('A', '').strip()
            if not t_id or t_id.lower().startswith('test case id'):
                continue
            test_cases.append({
                "id": t_id,
                "name": r.get('B', ''),
                "scenario_type": r.get('C', 'Happy Path'),
                "priority": r.get('D', 'P1'),
                "channel": ["voice_ivr", "chat_digital"],
                "test_account": r.get('E', ''),
                "primary_app_tag": r.get('F', ''),
                "description": r.get('G', ''),
                "initial_utterance": r.get('H', ''),
                "expected_response": r.get('I', ''),
                "pass_criteria": r.get('J', '')
            })
        return test_cases

    # Legacy baseline multi-turn parser fallback
    test_cases = []
    current_tc = None
    for r in rows[1:]:
        t_id = r.get('A', '').strip()
        if t_id and t_id.lower() != 'test case id':
            if current_tc:
                test_cases.append(current_tc)
            current_tc = {
                "id": t_id,
                "name": r.get('B', t_id),
                "scenario_type": r.get('C', 'Happy Path'),
                "priority": r.get('D', 'P1'),
                "channel": ["voice_ivr", "chat_digital"],
                "initial_utterance": r.get('H', r.get('F', '')),
                "turns": []
            }
        if current_tc and r.get('H'):
            current_tc["turns"].append({
                "user": r.get('H', ''),
                "agent": r.get('I', '')
            })
    if current_tc:
        test_cases.append(current_tc)

    return test_cases


def load_golden_cases_from_yaml(yaml_path: str) -> List[Dict[str, Any]]:
    """Loads golden or simulation test cases from a native cxas-scrapi YAML file."""
    if not os.path.exists(yaml_path):
        return []

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Notice: Failed to load YAML from {yaml_path}: {e}")
        return []

    if not isinstance(data, dict):
        return []

    cases = []
    
    # Format 1: Platform Goldens (conversations: [...])
    if "conversations" in data and isinstance(data["conversations"], list):
        common_params = data.get("common_session_parameters", {})
        for idx, conv in enumerate(data["conversations"], 1):
            c_name = conv.get("conversation", f"golden_scenario_{idx}")
            turns = conv.get("turns", [])
            init_utt = turns[0].get("user", "") if turns else ""
            
            # Format dialogue transcript
            dialogue_lines = []
            for t in turns:
                if "user" in t:
                    dialogue_lines.append(f"User: {t['user']}")
                if "agent" in t:
                    dialogue_lines.append(f"Agent: {t['agent']}")
            
            expectations = conv.get("expectations", [])
            pass_crit = "; ".join(expectations) if expectations else "Agent behaves according to golden transcript."
            tags = conv.get("tags", [])
            priority = "P0" if "P0" in tags else ("P1" if "P1" in tags else "P2")

            cases.append({
                "id": f"GLD-{idx:03d}",
                "name": c_name.replace("_", " ").title(),
                "scenario_type": "Golden / Baseline",
                "priority": priority,
                "initial_utterance": init_utt,
                "turns": turns,
                "simulated_conversation": "\n".join(dialogue_lines),
                "pass_criteria": pass_crit,
                "tags": tags,
                "session_parameters": conv.get("session_parameters") or common_params
            })
        return cases

    # Format 2: SimulationEvals (evals: [...])
    if "evals" in data and isinstance(data["evals"], list):
        for idx, ev in enumerate(data["evals"], 1):
            e_name = ev.get("name", f"simulation_scenario_{idx}")
            steps = ev.get("steps", [])
            first_step = steps[0] if steps else {}
            
            goal = first_step.get("goal", e_name)
            success_crit = first_step.get("success_criteria", "")
            response_guide = first_step.get("response_guide", "")
            expectations = ev.get("expectations", [])
            pass_crit = success_crit or ("; ".join(expectations) if expectations else goal)
            tags = ev.get("tags", [])
            priority = "P0" if "P0" in tags else ("P1" if "P1" in tags else "P2")

            cases.append({
                "id": f"SIM-{idx:03d}",
                "name": e_name.replace("_", " ").title(),
                "scenario_type": "Simulation / Golden",
                "priority": priority,
                "initial_utterance": goal,
                "simulated_conversation": f"User Guide: {response_guide}\nExpected Outcome: {pass_crit}",
                "pass_criteria": pass_crit,
                "tags": tags,
                "session_parameters": ev.get("session_parameters", {})
            })
        return cases

    return cases


def load_golden_cases_from_excel(xlsx_path: str, target_sheet: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads golden test cases from an Excel workbook (.xlsx)."""
    if not os.path.exists(xlsx_path):
        return []

    try:
        with zipfile.ZipFile(xlsx_path, "r") as z:
            sst = load_shared_strings(z)
            wb_tree = ET.fromstring(z.read("xl/workbook.xml"))
            
            # Find candidate sheet
            chosen_sheet = None
            all_sheet_names = []
            for s in wb_tree.findall(".//ns:sheet", NS):
                s_name = s.attrib.get("name", "")
                all_sheet_names.append(s_name)
                if target_sheet and s_name.strip().lower() == target_sheet.strip().lower():
                    chosen_sheet = s_name
                    break

            if not chosen_sheet:
                # Prefer non-overview sheet
                for name in all_sheet_names:
                    if "overview" not in name.lower() and "instruction" not in name.lower():
                        chosen_sheet = name
                        break
            if not chosen_sheet and all_sheet_names:
                chosen_sheet = all_sheet_names[0]

            if not chosen_sheet:
                return []

            rows = extract_sheet_cell_grid(z, chosen_sheet, sst)
            return parse_test_cases_generic(rows)
    except Exception as e:
        print(f"Notice: Failed to load golden test cases from Excel {xlsx_path}: {e}")
        return []


def load_goldens_for_subagent(goldens_source: Optional[str], subagent_key: str, subagent_label: str = "") -> List[Dict[str, Any]]:
    """Discovers and parses baseline goldens for a specific subagent."""
    if not goldens_source or not os.path.exists(goldens_source):
        return []

    # If single file
    if os.path.isfile(goldens_source):
        if goldens_source.endswith(".xlsx"):
            return load_golden_cases_from_excel(goldens_source, target_sheet=subagent_label or subagent_key)
        elif goldens_source.endswith(".yaml") or goldens_source.endswith(".yml"):
            return load_golden_cases_from_yaml(goldens_source)

    # If directory (e.g. evals/goldens/ or evals/simulations/)
    if os.path.isdir(goldens_source):
        candidates = []
        for root, _, files in os.walk(goldens_source):
            for f in files:
                f_lower = f.lower()
                if subagent_key in f_lower or subagent_label.lower().replace(" ", "_") in f_lower or "golden" in f_lower or "sim" in f_lower:
                    full_p = os.path.join(root, f)
                    if f.endswith(".yaml") or f.endswith(".yml"):
                        cases = load_golden_cases_from_yaml(full_p)
                        if cases:
                            candidates.extend(cases)
                    elif f.endswith(".xlsx"):
                        cases = load_golden_cases_from_excel(full_p, target_sheet=subagent_label or subagent_key)
                        if cases:
                            candidates.extend(cases)
        return candidates

    return []
