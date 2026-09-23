# Vireo Audio — Support Ticket Refund Review

> **Submission Resources**
>
> 🎥 **Screen Recording:**
> https://drive.google.com/file/d/1JCMQg7TBDVNIrApshQbjHF_7tPyniuz5/view?usp=sharing
>
> 📁 **Public Google Drive Submission Folder:**
> https://drive.google.com/drive/folders/16GQX54uiLJiSRrv2lTqDG3pnEnt4pQ-W?usp=sharing

An AI-assisted support-ticket analysis tool for Vireo Audio. The tool reconciles a messy helpdesk export, produces finance-ready refund reporting, flags records requiring policy review, and provides an optional local LLM assistant for ticket-text quality control.

## 1. Business Objective

Finance needs a reliable monthly view of:

* refund value by month
* refund reason code
* refund-handling agent/team
* records that may require policy review

The source export contains migrated records from two systems with different monetary units and duplicate ticket IDs.

This tool converts the **12,238-row source export** into a reconciled dataset containing:

* **11,600 unique canonical tickets**
* **2,340 canonical refund tickets**
* **₹6,709,932 total canonical refund value**
* **₹2,867.49 average refund**

It also identifies **879 GW-OTHER refunds above the ₹500 goodwill-credit cap**, representing **₹2,871,632**, for review. These are review flags, not confirmed policy violations or confirmed savings.

---

## 2. What the Tool Does

The pipeline has four main stages:

### 1. Reconciliation

* identifies duplicate ticket IDs across helpdesk and legacy systems
* normalizes legacy monetary values
* creates one canonical record per ticket

### 2. Deterministic Financial Analysis

* monthly refund totals
* refund reason totals
* agent/team totals
* reconciliation checks

### 3. Policy Review

* GW-OTHER refunds above ₹500
* refund + replacement combinations
* ambiguous order matching
* refunds above listed unit retail

### 4. AI-Assisted Ticket Review

* local Qwen3 8B model through Ollama
* classifies ticket text against the existing refund reason codes
* provides confidence and evidence
* does not calculate financial values
* does not replace the recorded refund reason used for reporting

---

## 3. Important Data Reconciliation

The export contains records from both the current helpdesk and a legacy system.

### Duplicate Handling

There are **638 ticket IDs appearing across both source systems**, involving 1,276 rows.

For duplicated ticket IDs:

* the current helpdesk record is retained
* the legacy duplicate is removed from the canonical dataset

Legacy-only records are retained after monetary normalization.

### Monetary Normalization

The legacy system stores monetary values in a different native unit. A comparison of duplicate records showed that the legacy monetary values were exactly 100× the corresponding helpdesk values for the comparable refund pairs.

Therefore:

```text
legacy amount / 100 = INR amount
```

The normalized value is stored in:

```text
refund_amount_normalized
```

**Do not use `refund_amount_inr` for financial reporting**, because that field contains the original mixed-unit export values.

The canonical refund total used throughout the application is:

```text
₹6,709,932
```

or:

```text
₹67.10 lakh
```

The raw mixed-unit export total is not directly comparable across source systems and is therefore not used for financial reporting.

---

## 4. Dataset

The project uses the supplied:

```text
tickets.csv
agents.csv
orders.csv
customers.csv
products.csv
support-policy.pdf
email-thread.txt
README.txt
```

The main ticket export contains:

```text
12,238 rows
21 columns
```

The final canonical dataset contains:

```text
11,600 unique tickets
2,340 refund tickets
```

Because the source data does not contain `refund_processed_at`, the application's monthly refund analysis uses `created_at` as the refund-month proxy.

---

## 5. Project Structure

```text
Vireo Audio/

├── app.py
├── README.md
├── requirements.txt

├── tickets.csv
├── agents.csv
├── orders.csv
├── customers.csv
├── products.csv

├── build_canonical.py
├── reconcile_refunds.py
├── monthly_analysis.py
├── agent_analysis.py
├── policy_audit.py
├── inspect_data.py
├── inspect_tickets.py
├── inspect_agents.py

├── canonical_tickets.csv
├── canonical_refunds.csv
├── monthly_refunds.csv
├── monthly_reason_refunds.csv
├── agent_refunds.csv
├── agent_reason_refunds.csv
├── team_refunds.csv
├── refund_policy_audit.csv

├── prompts/
│   └── refund_classifier.txt

├── src/
│   ├── analysis.py
│   ├── classify.py
│   ├── report.py
│   └── validation.py

└── tests/
    └── test_analysis.py
```

Generated CSV outputs are included so the reviewer can inspect the analysis, while the pipeline scripts remain the source of truth for regeneration.

---

## 6. Requirements

### Python

Python 3.11+ is recommended.

The project was developed and tested with:

```text
Python 3.14.5
```

### Python Packages

Install the dependencies with:

```bash
pip install -r requirements.txt
```

---

## 7. Run the Analysis Pipeline

From the project directory:

```bash
python build_canonical.py
python monthly_analysis.py
python agent_analysis.py
python policy_audit.py
```

The scripts generate or update the canonical and analysis CSV files.

### Expected Key Results

After running the pipeline:

```text
Canonical tickets:       11,600
Refund tickets:            2,340
Refund value:          ₹6,709,932
Average refund:          ₹2,867.49
```

The monthly totals should reconcile to:

```text
₹6,709,932
```

The agent totals should also reconcile to:

```text
₹6,709,932
```

---

## 8. Run the Tests

Run:

```bash
pytest -q
```

The current test suite contains **9 automated tests** covering:

* canonical refund count and uniqueness
* reason-code totals
* valid refund amounts
* GW-OTHER review count/value
* refund + replacement count/value
* monthly reconciliation
* agent reconciliation
* required columns

Current result:

```text
9 passed
```

---

## 9. Run the Streamlit Application

Start the application with:

```bash
streamlit run app.py
```

The application provides:

### Executive Summary

Finance-level totals and reconciliation status.

### Monthly

Monthly refund count and value using `created_at` as the refund-month proxy.

### Reasons

Refund count and value by recorded reason code.

### Agents & Teams

Operational refund totals by agent and team.

Agent totals are intended as operational indicators, not misconduct rankings. Returns Desk owns refund processing by design, and Tier 2 should not be compared with Tier 1 using raw volume.

### Review Queue

Records requiring additional human review:

* GW-OTHER above ₹500
* refund + replacement
* ambiguous order matches
* refund above listed unit retail

These are review flags and do not by themselves establish policy violations.

### AI Assistant

A local LLM can review the text of a refund ticket and provide:

```json
{
  "reason_code": "DUP-PAYMENT",
  "confidence": 0.95,
  "evidence": "...",
  "needs_review": false
}
```

The AI output is advisory only.

---

## 10. Local AI Setup

The AI assistant uses:

```text
Ollama
Qwen3 8B
```

The development environment used:

```text
Ollama 0.30.8
Qwen3 8B
nomic-embed-text
MacBook Air M4, 16 GB
```

Install Ollama separately and make sure the model is available:

```bash
ollama pull qwen3:8b
```

The application communicates with the local Ollama HTTP API.

No paid model/API calls are required for the prototype.

If Ollama is unavailable, the deterministic financial analysis and reporting pipeline remain independent of the LLM.

---

## 11. AI Validation

The classifier was smoke-tested on **10 refund tickets**.

Result:

```text
10/10 structured responses
0 technical failures
```

The test also compared the model's suggested reason with the recorded reason code.

Those comparisons are **not reported as model accuracy**, because the recorded reason code has not been established as a human-verified ground-truth label.

A larger human-labeled evaluation is future work.

The AI assistant is therefore positioned as:

```text
Advisory text quality control
```

rather than:

```text
Financial calculation
```

or:

```text
Automated refund approval
```

---

## 12. Policy Review Findings

The current dataset produces the following review queues:

| Review Flag                 | Records | Refund Value |
| --------------------------- | ------: | -----------: |
| GW-OTHER > ₹500             |     879 |   ₹2,871,632 |
| Refund + replacement        |     166 |     ₹574,191 |
| Ambiguous order matches     |     145 |            — |
| Refund > listed unit retail |     110 |     ₹757,530 |

These records require human review against the order, quantity, approval context, and applicable policy.

They should not automatically be treated as fraud, misconduct, or confirmed policy breaches.

---

## 13. Important Limitations

### Refund Date

The source export does not contain `refund_processed_at`.

Therefore:

```text
created_at = refund-month proxy
```

This should be replaced with the actual refund-processing timestamp if it becomes available.

### Policy Flags

The review queue identifies records that warrant investigation.

A flag does not prove that the underlying refund was incorrect.

For example, a refund above listed unit retail may be legitimate when multiple units or other order-level circumstances are involved.

### AI Evaluation

The current AI validation is a 10-ticket technical smoke test.

A larger human-labeled benchmark is not included in this time-boxed prototype.

### Production Deployment

The prototype uses local Ollama inference. Production hosting, monitoring, authentication, model governance, and infrastructure costs have not been estimated.

---

## 14. Deliberately Out of Scope

The following were intentionally not implemented:

* automated refund approval
* automated financial decisions using the LLM
* refund forecasting
* agent misconduct scoring
* predictive fraud detection
* a large human-labeled AI benchmark
* production deployment infrastructure

These were excluded because the assignment is time-boxed and the available data does not justify making automated financial or personnel decisions from the prototype.

---

## 15. Business Outcome

The measurable outcome of the prototype is data reliability and review visibility.

It transforms:

```text
12,238 source rows
        ↓
11,600 canonical tickets
        ↓
2,340 refund tickets
        ↓
₹67.10 lakh reconciled refund value
```

Finance can then view refund value by:

```text
month
reason code
agent
team
```

and investigate a defined review queue rather than relying on the mixed-unit raw export.

---

## 16. AI Disclosure

AI tools used during development included:

* **ChatGPT** for coding assistance, debugging, analysis design, documentation, and prompt development
* **Ollama** for local model serving
* **Qwen3 8B** for ticket-text classification
* **`nomic-embed-text`** was available in the local environment for experimentation

The final financial calculations are deterministic Python/Pandas calculations.

The LLM is not used to calculate refund totals.

### Changed or Discarded Approaches

During development:

* LLM thinking output was adjusted using `/no_think` to make structured output more reliable.
* JSON extraction was made more robust after initial model responses included additional text.
* The LLM was deliberately kept out of financial aggregation.
* The recorded reason code remains the reporting source of truth.
* A larger AI accuracy claim was not made because a human-labeled benchmark was not completed.

---

## 17. Cost

The prototype uses local inference through Ollama.

Therefore:

```text
Paid API calls per run:   ₹0
Paid API calls per month: ₹0
```

At approximately 650 tickets/week:

```text
650 × 4 ≈ 2,600 tickets/month
```

No paid per-ticket LLM API cost is incurred by this local prototype.

Electricity, local hardware depreciation, production hosting, monitoring, and future infrastructure costs are not included because they were not measured.

---

## 18. Recommended Run Order for Handoff

For a fresh data refresh:

```bash
python build_canonical.py
python monthly_analysis.py
python agent_analysis.py
python policy_audit.py
pytest -q
streamlit run app.py
```

### Three Important Handoff Notes

1. **Use `refund_amount_normalized` for financial reporting.**

   `refund_amount_inr` contains the original mixed-unit export values.

2. **Use `created_at` only as the refund-month proxy** until a real `refund_processed_at` field is available.

3. **Treat policy flags and AI outputs as review aids**, not automated decisions.

---

## 19. Final Verification

The current implementation has been verified with:

```text
Canonical refund tickets: 2,340
Canonical refund value:   ₹6,709,932
Monthly reconciliation:   PASS
Agent reconciliation:     PASS
Automated tests:          9/9 PASS
AI smoke test:            10/10 structured responses
```

The application is intended as a finance-review prototype that makes the source data reproducible, auditable, and easier to investigate.

# Vireo-Audio---Banao-Technologies
