---
name: chime
description: >-
  Project CHIME: Conversational Harmonization for IVR & Messaging Evaluations.
  Automates continuous synchronization and generation of CXAS SCRAPI SimulationEvals
  and zero-context multi-tab Manual QA Suites (Excel & CSV) across Sanity and Regression
  tiers for both Voice (Telephony / IVR) and Digital Chat. Ingests sub-agent prompts,
  tools, and callbacks, dynamically synthesizes missing compositions (fallbacks, escalations,
  5-pillar guardrails), and hydrates test rows with real customer credentials.
---

# Project CHIME: Unified Voice IVR & Chat Simulation Engine

Project CHIME establishes an automated, omnichannel testing pipeline for Google Customer Engagement Suite (CES / CXAS) conversational applications. It connects sub-agent codebase configurations (prompts, OpenAPI tools, runtime callbacks, and business rules) to simultaneously generate:
1. **Automated Headless SCRAPI YAML Suites** (`.sim.yaml`) for CI/CD regression gating.
2. **Zero-Context Manual QA Excel Workbooks** (`.xlsx`) with dynamic pass/fail formulas and hydrated caller/user credentials.

---

## 🚀 CLI Commands

### 1. Generate Sanity Suite (All Sub-Agents)
Generates 12 test cases per sub-agent (5 Happy Paths, 1 Fallback, 1 Escalation, 5 Guardrails):
```bash
chime --suite sanity --all --app-dir ./cxas_app
```

### 2. Generate Regression Suite with Customer Test Accounts
Generates 26 test cases per sub-agent (10 Journeys, 5 Fallbacks, 1 Escalation, 10 Guardrails) hydrated with credentials:
```bash
chime --suite regression --all --accounts-file ./configs/accounts.json --app-dir ./cxas_app
```

### 3. Generate Suite for a Specific Sub-Agent
```bash
chime --suite sanity --subagent techsetup --app-dir ./cxas_app
```

---

## 💬 Natural Language Prompt Triggers
When working with an AI coding assistant in Jetski or Gemini CLI, you can invoke Project CHIME naturally:
- *"Run Project CHIME to generate the sanity suite for all subagents."*
- *"Synchronize the regression simulation suite and manual QA spreadsheet for the techsetup subagent using test_accounts.json."*
- *"Generate manual QA testing sheets for the billing subagent with hydrated caller phone numbers and postcodes."*

---

## 🏛 4-Stage Omnichannel Pipeline

```
[PRD & Sub-Agent Codebase] ──▶ [Stage 1: Dual Ingestion (Voice & Chat)]
                                         │
                                         ▼
                               [Stage 2: Tool & Callback Introspection]
                                         │
                                         ▼
                               [Stage 3: Tier Harmonization & Self-Healing]
                                         │
             ┌───────────────────────────┴───────────────────────────┐
             ▼                                                       ▼
   [Engine A: Headless SCRAPI]                             [Engine B: Zero-Context Manual QA]
   - Strongly-typed .sim.yaml                              - Dedicated Voice IVR & Digital Chat tabs
   - Speech & chat turn assertions                         - Hydrated Caller CLI, Postcode & Chat IDs
   - Tool mocks & AppTag validation                        - Dynamic pass/fail formulas & HTML reports
```

### Tier Mathematical Distribution
- **Sanity Suite (12 per journey)**: 5 Happy Paths + 1 Silence Fallback + 1 Live Escalation + 5 Hard Guardrails (`GR01` PCI-DSS, `GR02` Competitor, `GR03` Prompt Injection, `GR04` Profanity, `GR05` Domain Grounding).
- **Regression Suite (26 per journey)**: 10 Multi-Turn Journeys + 5 Consecutive Fallbacks + 1 Live Escalation + 10 Guardrails.
