"""Test Account Provider & Credential Hydration Engine for Voice IVR and Chat."""

import json
import os
import yaml
from typing import Dict, Any, List, Optional


DEFAULT_SYNTHETIC_ACCOUNTS = [
    {
        "account_id": "ACC-UK-0841",
        "cli_phone": "07700900123",
        "postcode": "SW1A 1AA",
        "security_password": "BlueStar77!",
        "chat_user_id": "usr_voice_chat_841",
        "products": ["Broadband Ultrafast", "Digital TV"],
        "billing_status": "Current",
        "line_status": "Degraded / Flashing Orange",
        "tags": ["techsetup", "broadband", "voice_ivr", "chat"]
    },
    {
        "account_id": "ACC-UK-0952",
        "cli_phone": "07700900456",
        "postcode": "EC1A 1BB",
        "security_password": "SafeRiver99!",
        "chat_user_id": "usr_voice_chat_952",
        "products": ["Fiber Broadband", "Streaming Pass"],
        "billing_status": "Overdue £45.00",
        "line_status": "Healthy / Operational",
        "tags": ["billing", "billing_complaints", "voice_ivr", "chat"]
    },
    {
        "account_id": "ACC-UK-1023",
        "cli_phone": "07700900789",
        "postcode": "M1 1AA",
        "security_password": "Summit2026*",
        "chat_user_id": "usr_voice_chat_1023",
        "products": ["Home Move Package", "Smart Home Hub"],
        "billing_status": "Current",
        "line_status": "Pending Relocation",
        "tags": ["homemove", "relocation", "voice_ivr", "chat"]
    },
    {
        "account_id": "ACC-UK-2045",
        "cli_phone": "07700900321",
        "postcode": "G1 1AA",
        "security_password": "NovaShield12!",
        "chat_user_id": "usr_voice_chat_2045",
        "products": ["Complete Family Bundle"],
        "billing_status": "Pending Cancellation",
        "line_status": "Active",
        "tags": ["cancellations", "downgrades", "retention", "voice_ivr", "chat"]
    }
]


class AccountHydrator:
    """Manages customer account credentials and hydrates test case rows."""

    def __init__(self, accounts_path: Optional[str] = None):
        self.accounts: List[Dict[str, Any]] = []
        if accounts_path and os.path.exists(accounts_path):
            self.load_accounts(accounts_path)
        else:
            self.accounts = DEFAULT_SYNTHETIC_ACCOUNTS

    def load_accounts(self, path: str):
        """Loads accounts from a JSON or YAML file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.endswith(".yaml") or path.endswith(".yml"):
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            if isinstance(data, list):
                self.accounts = data
            elif isinstance(data, dict):
                if "accounts" in data and isinstance(data["accounts"], list):
                    self.accounts = data["accounts"]
                else:
                    # Flatten dictionary of named profiles
                    flattened = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            entry = dict(v)
                            entry.setdefault("account_id", k)
                            entry.setdefault("cli_phone", entry.get("MOBILE_NUMBER") or entry.get("telephone_number", "07700900000"))
                            entry.setdefault("postcode", entry.get("POSTCODE", "SW1A 1AA"))
                            entry.setdefault("security_password", entry.get("PASSWORD", "P@ssword1"))
                            entry.setdefault("products", [entry.get("PRODUCT_FAMILY", "Standard Service")])
                            entry.setdefault("tags", [k.lower()])
                            flattened.append(entry)
                    self.accounts = flattened if flattened else DEFAULT_SYNTHETIC_ACCOUNTS
        except Exception as e:
            print(f"Notice: Could not parse accounts file '{path}': {e}. Using synthetic account pool.")
            self.accounts = DEFAULT_SYNTHETIC_ACCOUNTS

    def get_account_for_test(self, subagent_key: str, category: str = "", auth_required: bool = True) -> Dict[str, Any]:
        """Finds or synthesizes the best matching test account for a specific sub-agent scenario."""
        if not auth_required:
            return {
                "account_id": "N/A (Unauthenticated / Public)",
                "cli_phone": "N/A",
                "postcode": "N/A",
                "security_password": "N/A",
                "chat_user_id": "anonymous_visitor",
                "products": [],
                "formatted_summary": "Unauthenticated Visitor (No Account Required)"
            }

        target_key = subagent_key.lower().strip()
        cat_key = category.lower().strip()

        # 1. Exact tag match
        for acc in self.accounts:
            tags = [t.lower() for t in acc.get("tags", [])]
            if target_key in tags or cat_key in tags:
                return self._format_account(acc)

        # 2. Fallback to index-based round-robin
        idx = hash(target_key + cat_key) % len(self.accounts)
        return self._format_account(self.accounts[idx])

    def _format_account(self, acc: Dict[str, Any]) -> Dict[str, Any]:
        cli = acc.get("cli_phone") or acc.get("telephone_number") or acc.get("MOBILE_NUMBER", "07700900123")
        postcode = acc.get("postcode") or acc.get("POSTCODE", "SW1A 1AA")
        pwd = acc.get("security_password") or acc.get("password") or acc.get("PASSWORD", "VerifiedPass123!")
        prods = acc.get("products") or acc.get("PRODUCT_FAMILY") or ["Connected Service"]
        if isinstance(prods, list):
            prods_str = ", ".join(prods)
        else:
            prods_str = str(prods)

        summary = f"CLI: {cli} | Postcode: {postcode} | Pwd: {pwd} | Holdings: [{prods_str}]"
        
        result = dict(acc)
        result["cli_phone"] = cli
        result["postcode"] = postcode
        result["security_password"] = pwd
        result["formatted_summary"] = summary
        return result
