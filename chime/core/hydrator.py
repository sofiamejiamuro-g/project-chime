"""Schema-Driven Omnichannel Data Hydration Engine for CXAS & Project CHIME."""

import csv
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
import yaml
import zipfile
from typing import Dict, Any, List, Optional
from chime.profiles import load_profile, list_available_profiles


def _load_from_spreadsheet(path: str) -> List[Dict[str, Any]]:
    """Loads accounts from an OpenXML spreadsheet (.xlsx / Google Sheets export)."""
    if not zipfile.is_zipfile(path):
        return []

    try:
        with zipfile.ZipFile(path, 'r') as z:
            sst = []
            if 'xl/sharedStrings.xml' in z.namelist():
                s_tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
                for si in s_tree.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                    text = "".join(t.text for t in si.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text)
                    sst.append(text)

            target_path = None
            for name in z.namelist():
                if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                    target_path = name
                    break

            if not target_path:
                return []

            sheet_tree = ET.fromstring(z.read(target_path))
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

            rows_data = []
            for r in sheet_tree.findall('.//ns:row', ns):
                row_dict = {}
                for c in r.findall('ns:c', ns):
                    ref = c.attrib.get('r', '')
                    col_match = re.match(r'([A-Z]+)', ref)
                    if not col_match:
                        continue
                    col_letter = col_match.group(1)
                    t = c.attrib.get('t')
                    val = ''
                    if t == 'inlineStr':
                        is_elem = c.find('ns:is', ns)
                        if is_elem is not None and is_elem.find('ns:t', ns) is not None:
                            val = is_elem.find('ns:t', ns).text or ''
                    else:
                        v = c.find('ns:v', ns)
                        if v is not None and v.text:
                            try:
                                val = sst[int(v.text)] if t == 's' else v.text
                            except Exception:
                                val = v.text
                    row_dict[col_letter] = val.strip()
                if row_dict:
                    rows_data.append(row_dict)

            if not rows_data or len(rows_data) < 2:
                return []

            header_row = rows_data[0]
            col_to_key = {}
            for col_letter, header_val in header_row.items():
                if header_val:
                    clean_k = re.sub(r'[^a-zA-Z0-9_]+', '_', header_val.strip().lower()).strip('_')
                    col_to_key[col_letter] = clean_k

            accounts = []
            for row_dict in rows_data[1:]:
                acc = {}
                for col_letter, key_name in col_to_key.items():
                    acc[key_name] = row_dict.get(col_letter, "")

                if "tags" in acc and isinstance(acc["tags"], str) and acc["tags"]:
                    acc["tags"] = [t.strip() for t in acc["tags"].split(",") if t.strip()]
                if "products" in acc and isinstance(acc["products"], str) and acc["products"]:
                    acc["products"] = [p.strip() for p in acc["products"].split(",") if p.strip()]

                if any(v for k, v in acc.items() if k):
                    accounts.append(acc)

            return accounts
    except Exception as e:
        print(f"Notice: Failed to read spreadsheet '{path}': {e}")
        return []


def _load_from_csv(path: str, delimiter: str = ',') -> List[Dict[str, Any]]:
    """Loads accounts from a CSV or TSV file."""
    accounts = []
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for r in reader:
                clean_row = {}
                for k, v in r.items():
                    if k is not None:
                        clean_k = re.sub(r'[^a-zA-Z0-9_]+', '_', k.strip().lower()).strip('_')
                        clean_row[clean_k] = v.strip() if isinstance(v, str) else v
                if "tags" in clean_row and isinstance(clean_row["tags"], str) and clean_row["tags"]:
                    clean_row["tags"] = [t.strip() for t in clean_row["tags"].split(",") if t.strip()]
                if "products" in clean_row and isinstance(clean_row["products"], str) and clean_row["products"]:
                    clean_row["products"] = [p.strip() for p in clean_row["products"].split(",") if p.strip()]
                if clean_row:
                    accounts.append(clean_row)
    except Exception as e:
        print(f"Notice: Failed to read delimited document '{path}': {e}")
    return accounts


class AccountHydrator:
    """Schema-driven customer account provider & omnichannel credential hydrator."""

    def __init__(
        self,
        accounts_path: Optional[str] = None,
        profile_name: Optional[str] = None,
        hydration_config_path: Optional[str] = None,
        accounts_source: str = "auto",
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        api_headers: Optional[Dict[str, str]] = None
    ):
        self.accounts_source = accounts_source.lower().strip() if accounts_source else "auto"
        self.api_url = api_url
        self.api_token = api_token
        self.api_headers = api_headers or {}
        self.accounts_path = accounts_path
        self.resolved_source = "profile"

        # 1. Load domain profile / hydration config
        if hydration_config_path and os.path.exists(hydration_config_path):
            self.profile = load_profile(hydration_config_path)
        else:
            self.profile = load_profile(profile_name)

        self.domain = self.profile.get("domain", "generic")
        self.summary_template = self.profile.get("summary_template", "")
        self.primary_identifiers = self.profile.get("primary_identifiers", ["account_id"])
        self.verification_rules = self.profile.get("verification", {})
        self.channel_defaults = self.profile.get("channel_defaults", {})
        self.mock_tools_catalog = self.profile.get("mock_tools", {})

        # 2. Retrieve account pool based on accounts_source and inputs
        self.accounts: List[Dict[str, Any]] = []

        # Mode A: Explicit profile
        if self.accounts_source == "profile":
            self.accounts = self.profile.get("sample_accounts", [])
            self.resolved_source = f"profile ({self.domain})"

        # Mode B: Explicit API or Auto with api_url provided
        elif self.accounts_source == "api" or (self.accounts_source == "auto" and self.api_url):
            if not self.api_url:
                raise ValueError("Accounts source set to 'api' but no --accounts-api URL was provided.")
            try:
                self.accounts = self.fetch_accounts_from_api(self.api_url, self.api_token, self.api_headers)
                self.resolved_source = f"API ({self.api_url})"
            except Exception as e:
                print(f"Notice: Failed to fetch accounts from API '{self.api_url}': {e}.")
                if self.accounts_source == "api":
                    raise
                if self.accounts_path and os.path.exists(self.accounts_path):
                    self.load_accounts(self.accounts_path)
                    self.resolved_source = f"document fallback ({self.accounts_path})"
                else:
                    self.accounts = self.profile.get("sample_accounts", [])
                    self.resolved_source = f"profile fallback ({self.domain})"

        # Mode C: Explicit File or Auto with accounts_path provided
        elif self.accounts_source == "file" or (self.accounts_source == "auto" and self.accounts_path):
            if not self.accounts_path or not os.path.exists(self.accounts_path):
                if self.accounts_source == "file":
                    raise FileNotFoundError(f"Accounts source set to 'file' but '{self.accounts_path}' was not found.")
                else:
                    self.accounts = self.profile.get("sample_accounts", [])
                    self.resolved_source = f"profile ({self.domain})"
            else:
                self.load_accounts(self.accounts_path)
                self.resolved_source = f"document ({self.accounts_path})"

        # Mode D: Fallback to profile
        else:
            self.accounts = self.profile.get("sample_accounts", [])
            self.resolved_source = f"profile ({self.domain})"

        if not self.accounts:
            fallback_profile = load_profile("telecom")
            self.accounts = fallback_profile.get("sample_accounts", [])
            self.resolved_source = "profile fallback (telecom)"

    def fetch_accounts_from_api(
        self,
        api_url: str,
        api_token: Optional[str] = None,
        api_headers: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Fetches live/mock test accounts dynamically from a customer REST API endpoint."""
        req_headers = {
            "User-Agent": "Project-CHIME-Hydrator/1.0",
            "Accept": "application/json"
        }
        if api_token:
            req_headers["Authorization"] = f"Bearer {api_token}"
        if api_headers:
            req_headers.update(api_headers)

        req = urllib.request.Request(api_url, headers=req_headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_body = resp.read().decode("utf-8")
            data = json.loads(raw_body)

        parsed_accounts: List[Dict[str, Any]] = []
        if isinstance(data, list):
            parsed_accounts = data
        elif isinstance(data, dict):
            if "accounts" in data and isinstance(data["accounts"], list):
                parsed_accounts = data["accounts"]
            elif "data" in data and isinstance(data["data"], list):
                parsed_accounts = data["data"]
            elif "results" in data and isinstance(data["results"], list):
                parsed_accounts = data["results"]
            else:
                parsed_accounts = [data]

        return parsed_accounts

    def load_accounts(self, path: str):
        """Loads accounts from JSON, YAML, CSV, TSV, or OpenXML Spreadsheet (.xlsx)."""
        clean_path = path.strip()
        lower_path = clean_path.lower()
        try:
            # 1. OpenXML Spreadsheet (.xlsx / Google Sheets download)
            if lower_path.endswith(".xlsx"):
                data = _load_from_spreadsheet(clean_path)
                if data:
                    self.accounts = data
                    return

            # 2. Delimited CSV / TSV
            elif lower_path.endswith(".csv") or lower_path.endswith(".tsv"):
                delim = "\t" if lower_path.endswith(".tsv") else ","
                data = _load_from_csv(clean_path, delimiter=delim)
                if data:
                    self.accounts = data
                    return

            # 3. YAML
            elif lower_path.endswith(".yaml") or lower_path.endswith(".yml"):
                with open(clean_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)

            # 4. JSON
            else:
                with open(clean_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

            if isinstance(data, list):
                self.accounts = data
            elif isinstance(data, dict):
                if "accounts" in data and isinstance(data["accounts"], list):
                    self.accounts = data["accounts"]
                elif "data" in data and isinstance(data["data"], list):
                    self.accounts = data["data"]
                else:
                    flattened = []
                    for k, v in data.items():
                        if isinstance(v, dict):
                            entry = dict(v)
                            entry.setdefault("account_id", k)
                            entry.setdefault("tags", [k.lower()])
                            flattened.append(entry)
                    self.accounts = flattened if flattened else self.profile.get("sample_accounts", [])
        except Exception as e:
            print(f"Notice: Could not parse accounts document '{clean_path}': {e}. Using domain profile sample pool.")
            self.accounts = self.profile.get("sample_accounts", [])

    def get_account_for_test(
        self,
        subagent_key: str,
        category: str = "",
        auth_required: bool = True
    ) -> Dict[str, Any]:
        """Finds, adapts, and hydrates the best matching test account for any subagent scenario."""
        if not auth_required:
            return {
                "account_id": "N/A (Unauthenticated / Public)",
                "chat_user_id": "anonymous_visitor",
                "formatted_summary": "Unauthenticated Visitor (No Account Required)",
                "verification_dialogue_turn": "I am an unauthenticated visitor inquiring about public information.",
                "channel_context": {
                    "voice": {"ani": "anonymous", "dnis": self.channel_defaults.get("voice", {}).get("dnis", "+18005550100")},
                    "chat": {"session_type": "guest", "jwt": "none"}
                },
                "mock_tools": {}
            }

        target_key = subagent_key.lower().strip()
        cat_key = category.lower().strip()

        # 1. Match by tags
        for acc in self.accounts:
            tags = [str(t).lower() for t in acc.get("tags", [])]
            if target_key in tags or cat_key in tags:
                return self._format_account(acc)

        # 2. Match by key substring in any field value
        for acc in self.accounts:
            for val in acc.values():
                if isinstance(val, str) and target_key in val.lower():
                    return self._format_account(acc)

        # 3. Fallback to hash round-robin across account pool
        idx = hash(target_key + cat_key) % len(self.accounts)
        return self._format_account(self.accounts[idx])

    def _format_account(self, raw_acc: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamically hydrates and formats an account supporting arbitrary customer schemas."""
        acc = dict(raw_acc)

        # Auto-ensure account_id
        if "account_id" not in acc:
            candidate_id_fields = self.primary_identifiers + ["id", "customer_id", "order_id", "pnr", "patient_id"] + [
                k for k in acc.keys() if k.endswith("_id") or k.endswith("_number")
            ]
            for id_field in candidate_id_fields:
                if id_field in acc and acc[id_field]:
                    acc["account_id"] = str(acc[id_field])
                    break
            else:
                acc["account_id"] = "ACC-001"

        # Format summary string
        summary = self._render_summary(acc)
        acc["formatted_summary"] = summary

        # Build dynamic dialogue turn for verification
        acc["verification_dialogue_turn"] = self._render_verification_turn(acc)

        # Build omnichannel context
        acc["channel_context"] = self._render_channel_context(acc)

        # Hydrate dynamic mock tool responses
        acc["mock_tools"] = self._render_mock_tools(acc)

        return acc

    def _render_summary(self, acc: Dict[str, Any]) -> str:
        """Renders summary string using template or intelligent auto-selection of non-empty keys."""
        # 1. Template-based formatting if template present and matches keys in acc
        if self.summary_template:
            tokens = re.findall(r"\{([a-zA-Z0-9_]+)\}", self.summary_template)
            specific_tokens = [t for t in tokens if t != "account_id"]
            matched_tokens = [t for t in specific_tokens if t in acc and acc[t]]

            if matched_tokens or (not specific_tokens and "account_id" in acc):
                try:
                    mapping = {}
                    for t in tokens:
                        val = acc.get(t, "")
                        if isinstance(val, list):
                            mapping[t] = ", ".join(str(x) for x in val)
                        else:
                            mapping[t] = str(val) if val else "N/A"
                    return self.summary_template.format(**mapping)
                except Exception:
                    pass

        # 2. Intelligent auto-formatting from available prominent keys
        ignore_keys = {"tags", "mock_tools", "channel_context", "formatted_summary", "verification_dialogue_turn"}
        parts = []
        for k in self.primary_identifiers:
            if k in acc and acc[k]:
                parts.append(f"{k.replace('_', ' ').title()}: {acc[k]}")

        for k, v in acc.items():
            if k not in ignore_keys and k not in self.primary_identifiers and v is not None and str(v).strip():
                if len(parts) >= 5:
                    break
                val_str = ", ".join(str(x) for x in v) if isinstance(v, list) else str(v)
                parts.append(f"{k.replace('_', ' ').title()}: {val_str}")

        return " | ".join(parts) if parts else f"Account ID: {acc.get('account_id', 'ACC-001')}"

    def _render_verification_turn(self, acc: Dict[str, Any]) -> str:
        """Constructs an authentic verification dialogue utterance matching the customer's schema."""
        # Extract verification fields from profile rules or account
        hlv_fields = self.verification_rules.get("hlv", [])
        llv_fields = self.verification_rules.get("llv", [])

        # Priority 1: Banking
        if "account_number" in acc and ("ssn_last_4" in acc or "dob" in acc):
            acc_num = acc.get("account_number") or acc.get("account_id")
            dob = acc.get("dob", "")
            ssn = acc.get("ssn_last_4", "")
            phrase = f"Sure, my account number is {acc_num}"
            if dob:
                phrase += f" and my date of birth is {dob}"
            if ssn:
                phrase += f", with SSN ending in {ssn}"
            return phrase + "."

        # Priority 2: Travel / Airlines
        if "pnr" in acc or "booking_reference" in acc:
            pnr = acc.get("pnr") or acc.get("booking_reference")
            last_name = acc.get("last_name", "Smith")
            phrase = f"Sure, my booking reference is {pnr} and my last name is {last_name}"
            if "flight_number" in acc:
                phrase += f" for flight {acc['flight_number']}"
            return phrase + "."

        # Priority 3: Retail / E-commerce
        if "order_id" in acc or "order_number" in acc:
            order = acc.get("order_id") or acc.get("order_number")
            email = acc.get("customer_email") or acc.get("email", "")
            phrase = f"Sure, my order number is {order}"
            if email:
                phrase += f" and my email is {email}"
            return phrase + "."

        # Priority 4: Telecom
        cli = acc.get("cli_phone") or acc.get("telephone_number") or acc.get("phone_number")
        postcode = acc.get("postcode") or acc.get("billing_zip") or acc.get("postal_code")
        if cli and postcode:
            return f"Sure, my phone number is {cli} and my postcode is {postcode}."
        elif cli:
            return f"Sure, my registered phone number is {cli}."

        # Generic fallback
        acc_id = acc.get("account_id") or "ACC-001"
        pwd = acc.get("security_password") or acc.get("one_time_passcode")
        if pwd:
            return f"Sure, my account ID is {acc_id} and my security pass is {pwd}."
        elif "patient_id" in acc or "mrn_number" in acc:
            p_id = acc.get("patient_id") or acc.get("mrn_number")
            name = acc.get("patient_name") or acc.get("name", "")
            return f"Sure, my patient ID is {p_id}" + (f" and my name is {name}." if name else ".")
        else:
            for id_k in ["customer_id", "member_id", "user_id", "id"]:
                if id_k in acc and acc[id_k]:
                    return f"Sure, my {id_k.replace('_', ' ')} is {acc[id_k]}."
            return f"Sure, my account ID is {acc_id}."

    def _render_channel_context(self, acc: Dict[str, Any]) -> Dict[str, Any]:
        """Renders voice telephony and digital chat context parameters."""
        voice_defaults = self.channel_defaults.get("voice", {})
        chat_defaults = self.channel_defaults.get("chat", {})

        cli = acc.get("cli_phone") or acc.get("phone_number") or acc.get("telephone_number") or "07700900123"
        dnis = voice_defaults.get("dnis", "+18005550199")
        dtmf = acc.get("security_pin") or acc.get("dtmf_card") or voice_defaults.get("dtmf_pin") or "4111222233334444"

        user_id = acc.get("chat_user_id") or acc.get("customer_id") or acc.get("account_id") or "usr_001"
        platform = chat_defaults.get("platform", "web_chat")

        return {
            "voice": {
                "ani": str(cli),
                "dnis": str(dnis),
                "dtmf_input": str(dtmf)
            },
            "chat": {
                "user_id": str(user_id),
                "platform": str(platform),
                "jwt": f"chime_jwt_{acc.get('account_id', '001')}",
                "session_type": "authenticated"
            }
        }

    def _render_mock_tools(self, acc: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves mock tool payloads combining profile templates and account variables."""
        merged = dict(self.mock_tools_catalog)
        if "mock_tools" in acc and isinstance(acc["mock_tools"], dict):
            merged.update(acc["mock_tools"])

        # Substitute variable placeholders like {flight_number} or {available_balance}
        resolved = {}
        for tool_name, payload in merged.items():
            if isinstance(payload, dict):
                res_tool = {}
                for k, v in payload.items():
                    if isinstance(v, str) and "{" in v and "}" in v:
                        tokens = re.findall(r"\{([a-zA-Z0-9_]+)\}", v)
                        res_val = v
                        for t in tokens:
                            res_val = res_val.replace(f"{{{t}}}", str(acc.get(t, "N/A")))
                        res_tool[k] = res_val
                    else:
                        res_tool[k] = v
                resolved[tool_name] = res_tool
            else:
                resolved[tool_name] = payload

        return resolved
