---
name: chime
description: >-
  Project CHIME: Conversational Harmonization for IVR & Messaging Evaluations for CXAS & cxas-scrapi.
  Automates continuous synchronization and generation of native cxas-scrapi SimulationEvals (evals/simulations/*.yaml),
  Platform Goldens (evals/goldens/*.yaml), Decisions & Changes Audit Reports, and zero-context multi-tab Manual QA Suites (Excel .xlsx)
  across Sanity and Regression tiers for both Voice IVR and Digital Chat. Ingests client baseline goldens or dynamically synthesizes
  missing compositions, hydrates test rows with customer credentials, and generates turn-by-turn mock dialogues.
---

# Project CHIME: Unified Voice IVR & Chat Evaluation Harmonizer

Project CHIME establishes an automated, omnichannel testing pipeline for Google Customer Engagement Suite (CES / CXAS) and the open-source **`cxas-scrapi`** development ecosystem. It connects sub-agent codebase configurations (prompts, OpenAPI tools, runtime callbacks, and business rules) to simultaneously generate:

1. **Native `cxas-scrapi` SimulationEvals (`evals/simulations/*.yaml`)**: Ready for immediate execution with `cxas evals run` or CI/CD pipelines.
2. **Native `cxas-scrapi` Platform Goldens (`evals/goldens/*.yaml`)**: Turn-by-turn deterministic evaluation suites.
3. **Decisions & Changes Audit Reports (`evals/reports/*_Decisions_Report.md`)**: Full rationale for verification levels (HLV/LLV), 5-pillar guardrails, detected tool changes, and priority distributions.
4. **Zero-Context Manual QA Excel Workbooks (`evals/manual_qa/*.xlsx`)**: Dedicated per-journey tabs with turn-by-turn mock dialogues, pass/fail logging, and pre-hydrated customer test credentials (CLI phone, postcode, password, holdings).

---

## 🚀 CLI Commands

### 1. Generate Sanity Suite (All Sub-Agents)
Generates 12 test cases per sub-agent (5 Happy Paths, 1 Fallback, 1 Escalation, 5 Guardrails) with P0/P2 priorities:
```bash
chime --suite sanity --all --app-dir ./cxas_app
```

### 2. Ingest Customer Baseline Goldens & Harmonize Regression Suite
Ingests client goldens from an existing YAML or Excel matrix, fills missing slots with synthesized guardrails/fallbacks, and hydrates test accounts:
```bash
chime --suite regression --all \
  --profile banking \
  --goldens ./evals/goldens \
  --accounts-file ./configs/accounts.example.json \
  --app-dir ./cxas_app
```

### 3. Generate with Custom Schema Configuration
Use `--hydration-config` to define arbitrary domain profiles (Healthcare, Logistics, etc.) or `--profile` for built-in industry domains (`telecom`, `banking`, `travel`, `retail`, `generic`):
```bash
chime --suite sanity --subagent techsetup --generate-goldens \
  --profile travel \
  --app-dir ./cxas_app
```

### 4. Execute Generated Simulations in `cxas-scrapi`
```bash
cxas evals run --eval-file ./evals/simulations/sanity_simulations_techsetup.yaml
```

---

## 💬 Natural Language Prompt Triggers
When working with an AI coding assistant in Jetski or Gemini CLI, you can invoke Project CHIME naturally:
- *"Run Project CHIME to generate the sanity suite for all subagents with cxas-scrapi compliance."*
- *"Ingest our existing goldens from evals/goldens and synchronize the regression suite for techsetup using accounts.json."*
- *"Generate the manual QA Excel workbook and decisions audit report for the billing subagent with hydrated customer credentials."*

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
