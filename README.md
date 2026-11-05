# Project CHIME 🔔
### **C**onversational **H**armonization for **I**VR & **M**essaging **E**valuations
*Unified Voice & Chat Simulation and Zero-Context Manual QA Harmonizer for Google Customer Engagement Suite (CXAS).*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Zero External Excel Dependencies](https://img.shields.io/badge/Excel-Native%20OpenXML-green.svg)]()
[![Omnichannel](https://img.shields.io/badge/Modality-Voice%20IVR%20%2B%20Digital%20Chat-orange.svg)]()

---

## 📌 Executive Overview

Customer Experience Agent Studio (CXAS) sub-agents serve customers across two primary channels: **spoken voice over telephone lines (IVR)** and **digital messaging in web/mobile chat widgets**. As conversational sub-agents undergo daily prompt revisions, tool changes, and callback rewiring, testing faces three critical bottlenecks:

1. **Dual-Channel Code-to-QA Drift**: When instructions or callbacks change, static test matrices rot, requiring 2 to 3 days per release cycle to rewrite.
2. **The Blind Dialing & Chat Session Bottleneck**: Voice testers dialing live IVR lines lack matching caller CLIs and postcodes; Chat testers lack user session payloads, causing a **35%–40% false-failure rate** during UAT.
3. **Fragmented Channel Silos**: Telephony IVR and digital chat are tested in disconnected silos without verifying identical business rules and compliance guardrails.

**Project CHIME** is an autonomous, dual-target testing harmonizer. By introspecting sub-agent instructions, OpenAPI tools, runtime callbacks, and channel-specific business rules, Project CHIME simultaneously synthesizes:
* 🤖 **Strongly-typed SCRAPI SimulationEvals (`.sim.yaml`)** for automated CI/CD regression gating.
* 📋 **Multi-tab Zero-Context Manual QA Excel Workbooks (`.xlsx`)** with dynamic formulas and real/mock customer test credentials (Caller CLI phone, Postcode, Password, and Active Holdings).

---

## 🏛 4-Stage Omnichannel Architecture

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

### Mathematical Tier Harmonization
* **Sanity Suite (12 per journey)**: 5 Happy Paths + 1 Silence Fallback + 1 Live Escalation (`escalate_to_human`) + 5 Hard Guardrails (`GR01` PCI-DSS DTMF/masking, `GR02` Competitor, `GR03` Prompt Injection, `GR04` Profanity, `GR05` Domain Grounding).
* **Regression Suite (26 per journey)**: 10 Multi-Turn Journeys + 5 Consecutive Fallbacks + 1 Live Escalation + 10 Guardrails.

---

## ⚡ Quickstart & Installation

Project CHIME has **zero external Excel dependencies**—all `.xlsx` workbooks are generated using Python standard library OpenXML streaming.

### 1. Install as a Python Package
```bash
# Clone the repository
git clone https://github.com/your-org/project-chime.git
cd project-chime

# Install locally
pip install -e .
```

### 2. Run Single-Command Test Synchronization
```bash
# Generate Sanity test suites for all subagents in any CXAS app
chime --suite sanity --all --app-dir /path/to/cxas_app

# Generate Regression test suites with customer test account hydration
chime --suite regression --all --accounts-file ./configs/accounts.example.json --app-dir /path/to/cxas_app

# Target a specific subagent
chime --suite sanity --subagent techsetup --app-dir /path/to/cxas_app
```

---

## 🔐 Customer Test Account Manifest (`accounts.json`)

To eliminate tester guesswork during live telephony IVR calls and chat sessions, provide a JSON manifest:

```json
{
  "accounts": [
    {
      "account_id": "ACC-TEL-001",
      "cli_phone": "+14155552671",
      "postcode": "94105",
      "security_password": "TelecomSecure123!",
      "chat_user_id": "usr_tel_001",
      "products": ["Gigabit Fiber Broadband", "Digital Stream Box"],
      "billing_status": "Current",
      "tags": ["techsetup", "broadband", "voice_ivr", "chat"]
    }
  ]
}
```

---

## 🌍 Client-Agnostic Portability

Project CHIME is completely decoupled from any single customer codebase:
* **Telecom**: Tests line diagnostics, router reboot prompts, and DTMF card payments.
* **Banking**: Tests balance inquiries, fraud alerts, and high-level verification (HLV).
* **Retail**: Tests order tracking, delivery rescheduling, and returns.

---

## 👥 Authors & Attribution
* **Sofia Mejia** (`sofiamejiamuro@google.com`) — Conversational AI Engineer, GECX Delivery Team.
* **GECX Ignite**: The CXAS Innovation Challenge (Hackathon 2026).
