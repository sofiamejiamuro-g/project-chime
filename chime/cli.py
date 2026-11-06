"""Project CHIME CLI Entrypoint: Unified Voice IVR & Chat Simulation Engine for CXAS."""

import argparse
import datetime
import os
import sys
from typing import Dict, Any, List

from chime.core.hydrator import AccountHydrator
from chime.core.introspector import (
    discover_subagents,
    inspect_subagent_codebase,
    load_goldens_for_subagent
)
from chime.core.harmonizer import harmonize_subagent_tier
from chime.core.versioning import GoldenVersionManager
from chime.generators.scrapi_yaml import export_scrapi_simulation_suite, export_scrapi_goldens_suite
from chime.generators.openxml_excel import (
    generate_manual_qa_excel_suite,
    build_overview_rows,
    QA_HEADERS
)
from chime.generators.decisions_report import generate_decisions_report


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
    parser.add_argument("--goldens", default=None,
                        help="Path to baseline customer goldens file (.yaml/.xlsx) or directory")
    parser.add_argument("--generate-goldens", action="store_true",
                        help="Also generate deterministic Platform Goldens YAML files (evals/goldens/)")
    parser.add_argument("--output-dir", default="evals",
                        help="Root output directory for generated suites (default: ./evals)")
    parser.add_argument("--app-title", default="Conversational AI Concierge",
                        help="Application title for reports and workbooks")
    parser.add_argument("--profile", default=None,
                        help="Domain profile for data hydration: 'telecom', 'banking', 'travel', 'retail', 'generic'")
    parser.add_argument("--hydration-config", default=None,
                        help="Path to custom domain profile / hydration configuration JSON/YAML")
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
        subagents = {
            "Customer Support": {
                "key": "customer_support",
                "alias": ["support", "customer_support"],
                "agent_dir": "support",
                "tag": "customer_support",
                "domain_label": "Customer Support",
                "prefix": "SUP",
                "default_ver": "HLV",
                "default_kb": False,
                "codebase_info": {
                    "tools": ["lookup_account", "check_status"],
                    "callbacks": ["beforeAgentCallbacks:auth_validator"],
                    "instruction_lines": 45,
                    "instruction_chars": 1820,
                    "last_modified": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                }
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
    print(f"Domain Profile:     {args.profile or 'Auto / Telecom'}")
    if args.hydration_config:
        print(f"Hydration Config:   {args.hydration_config}")
    print(f"Accounts Pool:      {args.accounts_file or 'Default Synthetic Pool'}")
    print(f"Goldens Source:     {args.goldens or 'None (Autonomous Dynamic Synthesis)'}")
    print(f"Output Directory:   {args.output_dir}\n")

    # 4. Initialize hydrator
    hydrator = AccountHydrator(
        accounts_path=args.accounts_file,
        profile_name=args.profile,
        hydration_config_path=args.hydration_config
    )

    # 5. Process targets and generate suites
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    yaml_dir = os.path.join(args.output_dir, "simulations")
    goldens_dir = os.path.join(args.output_dir, "goldens")
    manual_dir = os.path.join(args.output_dir, "manual_qa")
    reports_dir = os.path.join(args.output_dir, "reports")

    os.makedirs(yaml_dir, exist_ok=True)
    os.makedirs(manual_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    if args.generate_goldens:
        os.makedirs(goldens_dir, exist_ok=True)

    sheets_dict: Dict[str, List[List[str]]] = {}
    all_rows: List[List[str]] = []
    all_harmonized_cases: List[Dict[str, Any]] = []
    subagent_summaries: List[Dict[str, Any]] = []
    version_summaries: List[Dict[str, Any]] = []

    # Ensure goldens directory is always ready for versioning
    os.makedirs(goldens_dir, exist_ok=True)

    for label, meta in targets:
        s_key = meta["key"]
        print(f"Processing journey: {label} ({s_key})...")
        
        # Load baseline goldens if provided
        raw_goldens = load_goldens_for_subagent(args.goldens, s_key, label)
        if raw_goldens:
            print(f"   • Ingested {len(raw_goldens)} baseline golden case(s) from '{args.goldens}'")

        # Harmonize & auto-heal test cases against latest agent
        harmonized_cases = harmonize_subagent_tier(
            suite_tier=args.suite,
            raw_test_cases=raw_goldens,
            subagent_meta=meta,
            hydrator=hydrator
        )

        all_harmonized_cases.extend(harmonized_cases)

        # Collect reconciliation notes for audit log
        reconciliation_notes = []
        for tc in harmonized_cases:
            for note in tc.get("reconciliation_notes", []):
                if note not in reconciliation_notes:
                    reconciliation_notes.append(note)

        # Record Golden version snapshot and update history ledger
        version_mgr = GoldenVersionManager(goldens_dir)
        v_info = version_mgr.record_version(
            subagent_key=s_key,
            baseline_cases=raw_goldens,
            reconciled_cases=harmonized_cases,
            reconciliation_notes=reconciliation_notes,
            agent_meta=meta
        )
        v_info["subagent"] = s_key
        version_summaries.append(v_info)
        print(f"   • Version Snapshot: {v_info['current_version']} (Baseline: {v_info['baseline_version']})")

        # Export native cxas-scrapi Simulation YAML (evals/simulations/*.yaml)
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

    # 8. Generate Decisions & Changes Audit Report with Versioning History
    decisions_report_path = os.path.join(reports_dir, f"{tier_name}_Decisions_Report.md")
    generate_decisions_report(
        output_report_path=decisions_report_path,
        suite_tier=args.suite,
        app_title=args.app_title,
        timestamp=timestamp,
        subagents_meta=subagent_summaries,
        all_test_cases=all_harmonized_cases,
        goldens_source=args.goldens or "",
        version_summaries=version_summaries
    )

    print(f"\n✅ Synchronization Complete!")
    print(f"   • Total Test Cases:      {len(all_rows)}")
    print(f"   • Automated Simulations: {yaml_dir}/")
    print(f"   • Platform Goldens:      {goldens_dir}/ (Active & Version History)")
    print(f"   • Manual QA Spreadsheet: {excel_path} (Google Sheets / OpenXML)")
    print(f"   • Decisions Report:      {decisions_report_path}\n")


if __name__ == "__main__":
    main()
