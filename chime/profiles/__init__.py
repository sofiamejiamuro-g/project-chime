"""Domain Profiles & Schema Definitions for Project CHIME."""

import json
import os
import yaml
from typing import Dict, Any, List, Optional

PROFILES_DIR = os.path.dirname(os.path.abspath(__file__))


def list_available_profiles() -> List[str]:
    """Lists built-in industry domain profiles."""
    profiles = []
    if os.path.exists(PROFILES_DIR):
        for f in sorted(os.listdir(PROFILES_DIR)):
            if f.endswith(".json") and not f.startswith("__"):
                profiles.append(f[:-5])
    return profiles


def load_profile(name_or_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads a domain profile schema by name ('telecom', 'banking', etc.) or file path."""
    if not name_or_path:
        name_or_path = "telecom"

    # 1. Direct file path check
    if os.path.exists(name_or_path) and os.path.isfile(name_or_path):
        try:
            with open(name_or_path, "r", encoding="utf-8") as f:
                if name_or_path.endswith(".yaml") or name_or_path.endswith(".yml"):
                    return yaml.safe_load(f)
                return json.load(f)
        except Exception as e:
            print(f"Notice: Failed to load custom profile from '{name_or_path}': {e}. Falling back to telecom.")

    # 2. Built-in profile check
    clean_name = name_or_path.lower().strip()
    profile_file = os.path.join(PROFILES_DIR, f"{clean_name}.json")
    if os.path.exists(profile_file):
        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Notice: Failed to load built-in profile '{clean_name}': {e}")

    # Fallback to generic or telecom
    fallback = os.path.join(PROFILES_DIR, "telecom.json")
    if os.path.exists(fallback):
        with open(fallback, "r", encoding="utf-8") as f:
            return json.load(f)

    return {"domain": "generic", "primary_identifiers": ["account_id"], "verification": {}}
