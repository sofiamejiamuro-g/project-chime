"""Project CHIME CLI Entrypoint: Unified Voice IVR & Chat Simulation Engine."""

import argparse
import datetime
import os
import sys
from typing import Dict, Any, List

from chime.core.hydrator import AccountHydrator
from chime.core.introspector import discover_subagents, inspect_subagent_codebase
from chime.core.harmonizer import harmonize_subagent_tier
from chime.generators.scrapi_yaml import export_scrapi_simulation_suite
from chime.generators.openxml_excel import (
    generate_manual_qa_excel_suite,
    build_overview_rows,
    QA_HEADERS
)


def main():
    parser = argparse.ArgumentParser(
        description="Project CHIME: Conversational Harmonization for IVR & Messaging Evaluations."
    )
    parser.add_argument("--suite", choices=["full", "regression", "sanity"], default="sanity",
                        help="Simulation tier: 'sanity' (12/journey), 'regression' (26/journey), 'full' (all)")
    parser.add_argument("--subagent", default=None,
                        help="Target specific subagent by key or name (e.g. techsetup, billing)")
    parser.add_argument("--all", action="store_true",
                        help="Synchronize all discovered subagents")
    parser.add_argument("--app-dir", default=None,
                        help="Root directory of the CXAS application (containing agents/ or sub-agents)")
    parser.add_argument("--agents-dir", default=None,
                        help="Direct path to subagent directories")
    parser.add_argument("--accounts-file", default=None,
                        help="Path to customer test account pool JSON/YAML (for Voice & Chat credential hydration)")
    parser.add_argument("--output-dir", default="evals",
                        help="Root output directory for generated suites (default: ./evals)")
    parser.add_argument("--app-title", default="Conversational AI Concierge",
                        help="Application title for reports and workbooks")
    args = parser.parse_args()

    if not args.subagent and not args.all:
        print("Error: Please specify --subagent <key> or --all to synchronize all journeys.")
        sys.exit(1)

    # 1. Resolve agents directory
    agents_dir = args.agents_dir
    if not agents_dir:
        candidates = [
            os.path.join(args.app_dir, "agents") if args.app_dir else None,
            os.path.join(args.app_dir, "AI_Concierge_CXAS_Agent", "agents") if args.app_dir else None,
            "cxas_app/AI_Concierge_CXAS_Agent/agents",
            "cxas_app/agents",
            "agents"
        ]
        for c in candidates:
            if c and os.path.exists(c):
                agents_dir = c
                break

    if not agents_dir or not os.path.exists(agents_dir):
        print(f"Notice: Agents directory not found at '{agents_dir}'. Running in standalone synthetic mode.")
        agents_dir = ""

    # 2. Discover subagents
    subagents = discover_subagents(agents_dir) if agents_dir else {}
    if not subagents:
        # Default fallback subagents if none discovered
        subagents = {
            "Customer Support": {
                "key": "customer_support",
                "alias": ["support", "customer_support"],
                "agent_dir": "support",
                "tag": "customer_support",
                "domain_label": "Customer Support",
                "prefix": "SUP",
                "default_ver": "HLV",
                "default_kb": False
            }
        }

    # 3. Filter targets
    if args.all:
        targets = list(subagents.items())
    else:
        req = args.subagent.lower().strip()
        targets = []
        for label, meta in subagents.items():
            if req == meta["key"] or req in meta.get("alias", []):
                targets.append((label, meta))
        if not targets:
            print(f"Error: Unknown subagent '{args.subagent}'. Available: {', '.join(m['key'] for m in subagents.values())}")
            sys.exit(1)

    print(f"\n🔔 Project CHIME · Unified Voice IVR & Chat Simulation Engine")
    print(f"============================================================")
    print(f"Tier:               {args.suite.upper()}")
    print(f"Synchronizing:      {len(targets)} subagent(s)")
    print(f"Agents Directory:   {agents_dir or 'Synthetic Spec'}")
    print(f"Accounts Pool:      {args.accounts_file or 'Default Synthetic Pool'}")
    print(f"Output Directory:   {args.output_dir}\n")

    # 4. Initialize hydrator
    hydrator = AccountHydrator(args.accounts_file)

    # 5. Process targets and generate suites
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yaml_dir = os.path.join(args.output_dir, "simulations")
    manual_dir = os.path.join(args.output_dir, "manual_qa")
    os.makedirs(yaml_dir, exist_ok=True)
    os.makedirs(manual_dir, exist_ok=True)

    sheets_dict: Dict[str, List[List[str]]] = {}
    all_rows: List[List[str]] = []
    subagent_summaries: List[Dict[str, Any]] = []

    for label, meta in targets:
        s_key = meta["key"]
        print(f"Processing journey: {label} ({s_key})...")
        
        # Harmonize test cases for this tier
        harmonized_cases = harmonize_subagent_tier(
            suite_tier=args.suite,
            raw_test_cases=[],  # Dynamic synthesis if no baseline provided
            subagent_meta=meta,
            hydrator=hydrator
        )

        # Export SCRAPI Simulation YAML
        yaml_filename = f"{args.suite}_simulations_{s_key}.yaml"
        yaml_path = os.path.join(yaml_dir, yaml_filename)
        export_scrapi_simulation_suite(yaml_path, s_key, args.suite, harmonized_cases)

        # Build sheet rows for Excel manual suite
        sheet_rows = [QA_HEADERS]
        for tc in harmonized_cases:
            row = [
                tc["id"],
                tc["journey"],
                tc["name"],
                tc["scenario_type"],
                tc["priority"],
                tc["test_account"],
                tc["primary_app_tag"],
                tc["verification_required"],
                tc["kb_trigger_eligible"],
                tc["expected_agents_path"],
                tc["initial_utterance"],
                tc["simulated_conversation"],
                tc["expected_tools_flow"],
                tc["pass_criteria"],
                "",  # Tester Status
                ""   # Tester Notes
            ]
            sheet_rows.append(row)
            all_rows.append(row)

        sheets_dict[label] = sheet_rows
        subagent_summaries.append(meta)

    # 6. Build Overview & Tester Instructions sheet
    overview_rows = build_overview_rows(
        suite_tier=args.suite,
        app_title=args.app_title,
        timestamp=timestamp,
        subagent_summaries=subagent_summaries,
        all_rows=all_rows
    )

    final_sheets = {"Overview & Instructions": overview_rows}
    final_sheets.update(sheets_dict)

    # 7. Generate multi-tab OpenXML Excel workbook
    tier_name = args.suite.capitalize()
    excel_filename = f"{tier_name}_Manual_QA_Suite.xlsx"
    excel_path = os.path.join(manual_dir, excel_filename)
    generate_manual_qa_excel_suite(
        output_xlsx_path=excel_path,
        suite_tier=args.suite,
        app_title=args.app_title,
        timestamp=timestamp,
        sheets_dict=final_sheets
    )

    print(f"\n✅ Synchronization Complete!")
    print(f"   • Total Test Cases: {len(all_rows)}")
    print(f"   • Automated YAMLs:  {yaml_dir}/")
    print(f"   • Manual QA Excel:  {excel_path}")


if __name__ == "__main__":
    main()
