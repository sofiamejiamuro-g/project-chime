# Project CHIME 🔔
### **C**onversational **H**armonization for **I**VR & **M**essaging **E**valuations
*Unified Voice & Chat Simulation and Zero-Context Manual QA Harmonizer for Google Customer Engagement Suite (CXAS) & cxas-scrapi.*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Zero External Excel Dependencies](https://img.shields.io/badge/Excel-Native%20OpenXML-green.svg)]()
[![cxas-scrapi Compliant](https://img.shields.io/badge/Evals-cxas--scrapi%20Native-blue.svg)](https://github.com/GoogleCloudPlatform/cxas-scrapi)
[![Omnichannel](https://img.shields.io/badge/Modality-Voice%20IVR%20%2B%20Digital%20Chat-orange.svg)]()

---

## 📌 Executive Overview

Customer Experience Agent Studio (CXAS) sub-agents serve customers across two primary channels: **spoken voice over telephone lines (IVR)** and **digital messaging in web/mobile chat widgets**. As conversational sub-agents undergo daily prompt revisions, tool changes, and callback rewiring, testing faces three critical bottlenecks:

1. **Dual-Channel Code-to-QA Drift**: When instructions or callbacks change, static test matrices rot, requiring 2 to 3 days per release cycle to rewrite.
2. **The Blind Dialing & Chat Session Bottleneck**: Voice testers dialing live IVR lines lack matching caller CLIs and postcodes; Chat testers lack user session payloads, causing a **35%–40% false-failure rate** during UAT.
3. **Fragmented Channel Silos**: Telephony IVR and digital chat are tested in disconnected silos without verifying identical business rules and compliance guardrails.

**Project CHIME** is an autonomous, dual-target testing harmonizer fully compatible with **`cxas-scrapi`**. By introspecting sub-agent instructions, OpenAPI tools, runtime callbacks, and baseline client goldens, Project CHIME simultaneously synthesizes:
* 🤖 **Native `cxas-scrapi` SimulationEvals (`evals/simulations/*.yaml`)**: Goal-oriented LLM user simulations ready for execution via `cxas evals run`.
* 🎯 **Native `cxas-scrapi` Platform Goldens (`evals/goldens/*.yaml`)**: Deterministic turn-by-turn evaluation suites.
* 📋 **Multi-tab Zero-Context Manual QA Excel Workbooks (`evals/manual_qa/*.xlsx`)**: Complete turn-by-turn mock dialogues and pre-hydrated customer test credentials (Caller CLI phone, Postcode, Password, and Active Holdings).
* 📝 **Decisions & Changes Audit Reports (`evals/reports/*_Decisions_Report.md`)**: Full architectural rationale for HLV/LLV verification levels, 5-pillar guardrails, detected tool diffs, and priority tiers (`P0`, `P1`, `P2`).

---

## 🏛 4-Stage Omnichannel Architecture

```
[PRD, Codebase & Baseline Goldens] ──▶ [Stage 1: Dual Ingestion (Voice & Chat)]
                                                 │
                                                 ▼
                                       [Stage 2: Tool & Callback Introspection]
                                                 │
                                                 ▼
                                       [Stage 3: Tier Harmonization & Self-Healing]
                                                 │
                     ┌───────────────────────────┴───────────────────────────┐
                     ▼                                                       ▼
   [Engine A: Headless cxas-scrapi]                        [Engine B: Zero-Context Manual QA]
   - Native evals/simulations/*.yaml                       - Dedicated Voice IVR & Digital Chat tabs
   - Native evals/goldens/*.yaml                           - Turn-by-turn mock dialogues (no guesswork)
   - Decisions Audit Report (Markdown)                     - Hydrated Caller CLI, Postcode, Holdings & Pwd
```

### Mathematical Tier Harmonization
* **Sanity Suite (12 per journey)**: 5 Happy Paths (`P0`) + 1 Silence Fallback (`P2`) + 1 Live Escalation (`P0`: `escalate_to_human`) + 5 Hard Guardrails (`P0`/`P1`: `GR01` PCI-DSS DTMF/masking, `GR02` Competitor, `GR03` Prompt Injection, `GR04` Profanity, `GR05` Domain Grounding).
* **Regression Suite (26 per journey)**: 10 Multi-Turn Journeys (`P1`) + 5 Consecutive Fallbacks (`P2`) + 1 Live Escalation (`P0`) + 10 Guardrails (`P0`/`P1`).

---

## ⚡ Quickstart & Installation

Project CHIME has **zero external Excel dependencies**—all `.xlsx` workbooks are generated using Python standard library OpenXML streaming.

### 1. Install as a Python Package
```bash
# Clone the repository
git clone https://github.com/GoogleCloudPlatform/cxas-scrapi.git # or project-chime
cd project-chime

# Install locally in editable mode
pip install -e .
```

### 2. Run Single-Command Test Synchronization
```bash
# Generate Sanity test suites with Banking domain profile
chime --suite sanity --all --profile banking --app-dir /path/to/cxas_app

# Ingest client baseline goldens and harmonize Regression test suite with custom profile
chime --suite regression --all \
  --goldens /path/to/golden_evals \
  --profile travel \
  --accounts-file ./configs/passengers.json \
  --app-dir /path/to/cxas_app

# Run with custom domain schema definition
chime --suite sanity --subagent techsetup --generate-goldens \
  --hydration-config ./configs/healthcare_profile.yaml \
  --accounts-file ./configs/patients.yaml \
  --app-dir /path/to/cxas_app
```

### 3. Run Headless Automated Evals with `cxas-scrapi`
```bash
cxas evals run --eval-file ./evals/simulations/sanity_simulations_techsetup.yaml
```

---

## 🔐 Schema-Driven Data Hydration (`chime/core/hydrator.py`)

Project CHIME features a **100% customizable, schema-driven data hydration engine** that eliminates tester guesswork during live telephony IVR calls and digital chat sessions.

### 1. Built-in Industry Profiles (`--profile`)
Specify a domain profile to automatically adapt verification turns, summary cards, telephony DNIS/DTMF, and mock tools:
* `--profile telecom` (Default): CLI phone, postcode, broadband line status, router diagnostics.
* `--profile banking`: Account number, SSN last 4, DOB, PIN, balances, KYC status.
* `--profile travel`: PNR / booking reference, passenger name, flight number, seat assignment, passport last 4.
* `--profile retail`: Order ID, customer email, courier, tracking code, delivery status.
* `--profile generic`: Flexible account ID, user ID, status, and credentials.

### 2. Arbitrary Customer Schemas (`--accounts-file`)
Customers can pass any arbitrary JSON or YAML test pool without dropping custom fields. All domain keys are dynamically mapped to `session_parameters` for `cxas-scrapi`:

```yaml
accounts:
  - patient_id: "MED-99412"
    mrn_number: "MRN-008129"
    patient_name: "Eleanor Vance"
    insurance_policy: "BlueCross-Optima-99"
    primary_physician: "Dr. Sarah Adams"
    tags: ["healthcare", "cardiology"]
```

### 3. Custom Domain Profiles (`--hydration-config`)
Create a custom YAML/JSON profile defining summary templates, verification rules, channel defaults, and mock tool catalogs:

```yaml
domain: healthcare
display_label: "Hospital Patient Care"
primary_identifiers: [patient_id, mrn_number]
summary_template: "Patient: {patient_name} | MRN: {mrn_number} | Ins: {insurance_policy}"
verification:
  llv: [patient_name, dob]
  hlv: [mrn_number, ssn_last_4]
channel_defaults:
  voice: { dnis: "+18005559090" }
  chat: { platform: "mychart_portal" }
```

---

## 👥 Authors & Attribution
* **Sofia Mejia** (`sofiamejiamuro@google.com`) — Conversational AI Engineer, GECX Delivery Team.
* **GECX Ignite**: The CXAS Innovation Challenge (Hackathon 2026).
