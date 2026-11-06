---
name: chime
description: >-
  Project CHIME: Conversational Harmonization for IVR & Messaging Evaluations for CXAS & cxas-scrapi.
  Automates continuous synchronization and generation of native cxas-scrapi SimulationEvals (evals/simulations/*.yaml),
  Platform Goldens (evals/goldens/*.yaml), Decisions & Changes Audit Reports, and zero-context multi-tab Manual QA Spreadsheet Suites (.xlsx / Google Sheets)
  across Sanity and Regression tiers for both Voice IVR and Digital Chat. Ingests client baseline goldens or dynamically synthesizes
  missing compositions, hydrates test rows with customer credentials, and generates turn-by-turn mock dialogues.
---

# Project CHIME: Unified Voice IVR & Chat Evaluation Harmonizer

Project CHIME establishes an automated, omnichannel testing pipeline for Google Customer Engagement Suite (CES / CXAS) and the open-source **`cxas-scrapi`** development ecosystem. It connects sub-agent codebase configurations (prompts, OpenAPI tools, runtime callbacks, and business rules) to simultaneously generate:

1. **Native `cxas-scrapi` SimulationEvals (`evals/simulations/*.yaml`)**: Ready for immediate execution with `cxas evals run` or CI/CD pipelines.
2. **Native `cxas-scrapi` Platform Goldens (`evals/goldens/*.yaml`)**: Turn-by-turn deterministic evaluation suites with snapshot versioning (`v1_baseline`, `v2`, and cryptographic `history_<subagent>.json` ledger).
3. **Decisions & Changes Audit Reports (`evals/reports/*_Decisions_Report.md`)**: Full architectural rationale for verification levels (HLV/LLV), 5-pillar guardrails, detected tool diffs, and priority distributions.
4. **Zero-Context Manual QA Spreadsheet Workbooks (`evals/manual_qa/*.xlsx`)**: Dedicated per-channel tabs (Voice IVR & Digital Chat) with turn-by-turn mock dialogues, pass/fail logging, and pre-hydrated customer test credentials (CLI phone, postcode, password, holdings). Zero external dependencies (pure Python standard library OpenXML streaming, natively importable into Google Sheets).

---

## 🏆 Key Enterprise Values & Capabilities

* **Zero-Context Human QA**: Testers never have to guess test accounts, search for active order numbers, or invent spoken dialogue turns. Every test row has exact turn-by-turn utterances and pre-hydrated test credentials.
* **100% Cross-Customer & Multi-Vertical**: Decoupled from any single client schema. Includes built-in profiles for **Telecom**, **Banking**, **Travel / Airlines**, **Retail / E-Commerce**, and **Generic**, with full support for custom YAML/JSON manifests.
* **Elimination of Credential Guesswork**: Eliminates manual credential lookups and downstream mock lookup failures by pairing tests with real, verified accounts.
* **Code-to-QA Drift Immunity**: Self-heals stale goldens whenever sub-agent tools or authentication callbacks change in code.

---

## 🚀 CLI Commands

### 1. Generate Sanity Suite (All Sub-Agents)
Generates 12 test cases per sub-agent (5 Happy Paths, 1 Fallback, 1 Escalation, 5 Guardrails) with P0/P2 priorities. Runs against `./sample_cxas_app` or any CXAS application:
```bash
# Out-of-the-box run using the included sample app
chime --suite sanity --all --app-dir ./sample_cxas_app

# Or against a custom application with a specific domain profile
chime --suite sanity --all --profile banking --app-dir ./cxas_app
```

### 2. Ingest Customer Baseline Goldens & Harmonize Regression Suite
Ingests client goldens from an existing YAML or Spreadsheet matrix, fills missing slots with synthesized guardrails/fallbacks, and hydrates test accounts:
```bash
chime --suite regression --all \
  --profile travel \
  --goldens ./evals/goldens \
  --accounts-file ./configs/passengers.yaml \
  --app-dir ./cxas_app
```

### 3. Generate with Custom Schema Configuration
Use `--hydration-config` to define arbitrary domain profiles (Healthcare, Logistics, etc.) or `--profile` for built-in industry domains (`telecom`, `banking`, `travel`, `retail`, `generic`):
```bash
chime --suite sanity --subagent techsetup --generate-goldens \
  --hydration-config ./configs/healthcare_profile.yaml \
  --accounts-file ./configs/patients.json \
  --app-dir ./cxas_app
```

### 4. Fetch Test Accounts Live from REST API
Retrieve pre-provisioned test accounts directly from a customer API endpoint:
```bash
chime --suite sanity --all \
  --accounts-api https://tdm.staging.customer.com/v1/accounts \
  --accounts-api-token "eyJhGciOiJIUzI1NiIsInR5cCI6..." \
  --app-dir ./cxas_app
```

### 5. Execute Generated Simulations in `cxas-scrapi`
```bash
cxas evals run --eval-file ./evals/simulations/sanity_simulations_techsetup.yaml
```

---

## 💬 Natural Language Prompt Triggers
When working with an AI coding assistant in Jetski or Gemini CLI, you can invoke Project CHIME naturally:
- *"Run Project CHIME to generate the sanity suite for all subagents with cxas-scrapi compliance."*
- *"Ingest our existing goldens from evals/goldens and synchronize the regression suite for techsetup using accounts.json."*
- *"Generate the manual QA spreadsheet workbook and decisions audit report for the billing subagent with hydrated customer credentials."*
- *"Synchronize the banking subagent with the banking profile and export both simulation and platform goldens."*

---

## 🏛 4-Stage Omnichannel Pipeline

```
[PRD & Sub-Agent Codebase] ──▶ [Stage 1: Dual Ingestion (Voice & Chat)]
(instruction.txt, *.json)                │
                                         ▼
                               [Stage 2: Tool & Callback Introspection]
                               (tools, before/after callbacks)
                                         │
                                         ▼
                               [Stage 3: Tier Harmonization & Self-Healing]
                               (P0/P1/P2 priorities, multi-turn dialogues)
                                         │
             ┌───────────────────────────┴───────────────────────────┐
             ▼                                                       ▼
   [Engine A: Headless cxas-scrapi]                        [Engine B: Zero-Context Manual QA]
   - Native evals/simulations/*.yaml                       - Dedicated Voice IVR & Digital Chat tabs
   - Native evals/goldens/*.yaml                           - Turn-by-turn mock dialogues (no guesswork)
   - Decisions Audit Report (Markdown)                     - Hydrated Caller CLI, Postcode, Holdings & Pwd
```

### Mathematical Tier Distribution
- **Sanity Suite (12 per journey)**: 5 Happy Paths (`P0`) + 1 Silence Fallback (`P2`) + 1 Live Escalation (`P0`) + 5 Hard Guardrails (`P0`: PCI-DSS, Prompt Injection; `P1`: Competitor, Profanity, Grounding).
- **Regression Suite (26 per journey)**: 10 Multi-Turn Journeys (`P1`) + 5 Consecutive Fallbacks (`P2`) + 1 Live Escalation (`P0`) + 10 Guardrails (`P0`/`P1`).

### The 5 Enterprise Security & Guardrail Pillars
1. **`GR01_PCI_DSS`**: Strict DTMF keypad masking and payment card number rejection.
2. **`GR02_COMPETITOR`**: Brand protection and polite deflection of competitor promotion baits.
3. **`GR03_PROMPT_INJECTION`**: Immune defense against system prompt overrides and instructions hijacking.
4. **`GR04_PROFANITY_SAFETY`**: De-escalation protocols and respectful response enforcement during customer hostility.
5. **`GR05_DOMAIN_GROUNDING`**: Anti-hallucination guardrail preventing out-of-domain conversational drifting.
