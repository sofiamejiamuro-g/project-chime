"""Golden Versioning & Historical Ledger Engine for Project CHIME and cxas-scrapi."""

import datetime
import json
import os
import shutil
import yaml
from typing import Dict, Any, List, Optional
from chime.generators.scrapi_yaml import export_scrapi_goldens_suite


class GoldenVersionManager:
    """Manages immutable snapshots, history ledgers, and change tracking for Goldens."""

    def __init__(self, goldens_base_dir: str):
        self.goldens_base_dir = goldens_base_dir
        self.versions_dir = os.path.join(goldens_base_dir, "versions")
        os.makedirs(self.versions_dir, exist_ok=True)

    def _get_history_file(self, subagent_key: str) -> str:
        return os.path.join(self.versions_dir, f"history_{subagent_key}.json")

    def load_history(self, subagent_key: str) -> Dict[str, Any]:
        h_file = self._get_history_file(subagent_key)
        if os.path.exists(h_file):
            try:
                with open(h_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "subagent": subagent_key,
            "created_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "versions": []
        }

    def record_version(
        self,
        subagent_key: str,
        baseline_cases: List[Dict[str, Any]],
        reconciled_cases: List[Dict[str, Any]],
        reconciliation_notes: List[str],
        agent_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Saves baseline snapshot (v1) and reconciled version snapshot (vN) with history ledger."""
        history = self.load_history(subagent_key)
        existing_versions = history.get("versions", [])
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        iso_timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

        cb_info = agent_meta.get("codebase_info", {})
        active_tools = cb_info.get("tools", [])
        active_callbacks = cb_info.get("callbacks", [])

        # 1. If v1 (baseline) does not exist yet, save it first
        if not any(v.get("version") == "v1" for v in existing_versions):
            v1_dir = os.path.join(self.versions_dir, "v1_baseline")
            os.makedirs(v1_dir, exist_ok=True)
            v1_path = os.path.join(v1_dir, f"golden_{subagent_key}.yaml")

            # If baseline cases were provided, export them; otherwise note it was synthesized
            if baseline_cases:
                export_scrapi_goldens_suite(v1_path, subagent_key, baseline_cases)
                v1_desc = "Initial customer baseline golden ingested"
            else:
                export_scrapi_goldens_suite(v1_path, subagent_key, reconciled_cases)
                v1_desc = "Initial synthetic baseline golden created"

            v1_record = {
                "version": "v1",
                "tag": "baseline",
                "type": "initial_baseline",
                "timestamp": iso_timestamp,
                "file_path": os.path.relpath(v1_path, self.goldens_base_dir),
                "total_cases": len(baseline_cases) if baseline_cases else len(reconciled_cases),
                "agent_tools": active_tools,
                "agent_callbacks": active_callbacks,
                "changes": [v1_desc]
            }
            existing_versions.append(v1_record)

        # 2. Record new reconciled version (v2, v3, ...)
        ver_num = f"v{len(existing_versions) + 1}"
        vn_dir_name = f"{ver_num}_{timestamp_str}"
        vn_dir = os.path.join(self.versions_dir, vn_dir_name)
        os.makedirs(vn_dir, exist_ok=True)
        vn_path = os.path.join(vn_dir, f"golden_{subagent_key}.yaml")

        export_scrapi_goldens_suite(vn_path, subagent_key, reconciled_cases)

        # 3. Update the primary active golden in evals/goldens/ (latest symlink/copy)
        active_golden_path = os.path.join(self.goldens_base_dir, f"golden_{subagent_key}.yaml")
        shutil.copy2(vn_path, active_golden_path)

        vn_record = {
            "version": ver_num,
            "tag": vn_dir_name,
            "type": "reconciled_with_agent",
            "timestamp": iso_timestamp,
            "file_path": os.path.relpath(vn_path, self.goldens_base_dir),
            "active_path": os.path.relpath(active_golden_path, self.goldens_base_dir),
            "total_cases": len(reconciled_cases),
            "agent_tools": active_tools,
            "agent_callbacks": active_callbacks,
            "changes": reconciliation_notes or ["Auto-healed and reconciled with latest agent codebase"]
        }
        existing_versions.append(vn_record)
        history["versions"] = existing_versions
        history["latest_version"] = ver_num
        history["last_updated"] = iso_timestamp

        # Save history ledger
        with open(self._get_history_file(subagent_key), "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        return {
            "current_version": ver_num,
            "baseline_version": "v1",
            "history_file": self._get_history_file(subagent_key),
            "version_path": vn_path,
            "active_path": active_golden_path,
            "all_versions": existing_versions
        }
