"""Sub-Agent Codebase & Baseline Matrix Introspector."""

import datetime
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
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
            if os.path.exists(inst_file) or os.path.exists(json_file):
                # Clean key and display label
                key = entry.lower().replace("-", "_").replace(" ", "_")
                label = entry.replace("_", " ").title()
                prefix = "".join([w[0].upper() for w in entry.split("_") if w])[:4] or "SUB"
                
                discovered[label] = {
                    "key": key,
                    "alias": [key, entry.lower(), entry.replace("_", "")],
                    "agent_dir": entry,
                    "tag": key,
                    "domain_label": label,
                    "prefix": prefix,
                    "app_tags": [],
                    "default_ver": "HLV" if any(w in key for w in ["verif", "account", "billing", "move"]) else "NA",
                    "default_kb": ("kb" in key or "knowledge" in key)
                }
    return discovered


def inspect_subagent_codebase(agents_dir: str, agent_folder: str) -> Dict[str, Any]:
    """Extract metadata from the subagent's current codebase folder."""
    info = {
        "agent_folder": agent_folder,
        "exists": False,
        "instruction_lines": 0,
        "instruction_chars": 0,
        "last_modified": "N/A",
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
            info["instruction_lines"] = len(content.splitlines())
        mtime = os.path.getmtime(inst_path)
        info["last_modified"] = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    # Look for agent JSON definition
    json_candidates = [
        os.path.join(agent_path, f"{agent_folder}.json"),
        os.path.join(agent_path, "agent.json")
    ]
    for j_path in json_candidates:
        if os.path.exists(j_path):
            try:
                with open(j_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    info["tools"] = [t.split("/")[-1] for t in data.get("tools", [])]
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
    wb_tree = ET.fromstring(z.read('xl/workbook.xml'))
    wb_rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    rels_map = {
        r.attrib['Id']: r.attrib['Target']
        for r in wb_rels.findall('ns:Relationship', RELS_NS)
    }

    target_path = None
    for s in wb_tree.findall('.//ns:sheet', NS):
        if s.attrib['name'].strip().lower() == sheet_name.strip().lower():
            rid = s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target = rels_map[rid]
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
                    val = sst[int(v.text)] if t == 's' else v.text
            row_cells[col_letter] = val.strip()
        rows.append(row_cells)
    return rows


def parse_test_cases_generic(rows: List[Dict[str, str]], is_10_col_suite: bool = False) -> List[Dict[str, Any]]:
    """Parse test cases from either multi-turn baseline format or 10-column suite format."""
    if not rows:
        return []

    header = rows[0]
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
                "utterance": r.get('H', ''),
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
                "utterance": r.get('H', r.get('F', '')),
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
