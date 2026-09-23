# Vireo Audio — Support Tickets (Set C)

### 1. What did you build, and what business outcome does it move? State the number and the money.

I built a reproducible refund-analysis tool that reconciles the support-ticket export and produces monthly, refund-reason, team, and agent views.

From **12,238 source rows**, it produces **11,600 canonical tickets and 2,340 canonical refunds worth ₹67.10 lakh**.

It also identifies **879 GW-OTHER refunds above the ₹500 goodwill cap, totaling ₹28.72 lakh, for review**.

The business outcome is a cleaner, reconciled baseline showing where refund money is going and which cases need operational or policy review.

---

### 2. What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)?

There are **no paid API or model calls** in the current implementation.

* One run: **₹0** in paid inference/API costs
* Monthly volume: 650 tickets/week × 4 weeks = **2,600 tickets/month**
* Paid AI cost: 2,600 × ₹0 = **₹0/month**

The AI uses **Qwen3 8B locally through Ollama**, so there is no per-ticket API charge.

Production infrastructure, electricity, and hardware costs were not measured.

---

### 3. How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.

I added **9 automated tests**, and the final test run passed **9/9**.

The tests cover refund totals, refund reasons, valid amounts, policy-review counts, monthly reconciliation, agent reconciliation, unique ticket IDs, and required columns.

The canonical refund total is **₹6,709,932**, and both monthly and agent totals reconcile exactly to this amount with a **₹0 difference**.

The AI classifier was separately smoke-tested on **10 tickets**. All **10/10 returned valid structured responses with 0 technical failures**.

I am not claiming an AI accuracy percentage because the recorded refund reason is not independently verified ground truth. The AI can get ambiguous or context-dependent refund reasons wrong, so it is used only as advisory QC.

---

### 4. Did you change, narrow, or push back on the client's ask? What, when, and why?

Yes.

I narrowed the LLM's role to **ticket-text understanding and quality-control assistance**.

Financial aggregation, duplicate handling, currency normalization, monthly totals, agent totals, and policy checks are deterministic Python/Pandas calculations because financial numbers need to be reproducible and auditable.

I also reconciled the two source systems before producing the financial view because the export contained migration duplicates and a 100× legacy/helpdesk monetary-unit difference.

I did not turn the results into agent misconduct or fraud rankings because the policy states that Returns Desk owns most refund processing by design.

---

### 5. What is wrong with what you are handing us? Be specific.

Known limitations are:

* `refund_processed_at` is not available, so **`created_at` is used as the refund-month proxy**.
* The raw `refund_amount_inr` field contains mixed monetary units; financial reporting must use **`refund_amount_normalized`**.
* Some order links require fallback customer + SKU matching, with **145 cases remaining ambiguous**.
* There are **166 refund + replacement cases** requiring human review; they are not automatically invalid.
* There are **110 refunds above listed unit retail**, which may require pricing, quantity, linkage, or exception review.
* The AI was only smoke-tested on 10 tickets; a larger human-labeled evaluation has not been completed.
* The Streamlit app has a non-blocking deprecation warning for `use_container_width`.

---

### 6. What did you deliberately leave out, and why?

I deliberately left out:

* Automated refund approval or blocking
* Fraud detection
* Agent misconduct scoring
* Agent performance ranking
* Refund forecasting
* Production deployment
* Automated savings/recovery estimates
* A large-scale AI accuracy benchmark

These require additional data, stronger ground truth, or production infrastructure.

I focused on the core business need: establishing a reliable refund baseline, showing **who is handling refunds and for what reasons**, and identifying cases for review.

I also did not claim flagged amounts as recoverable savings because the data does not establish that.

---

### 7. Anything you built or found that nobody asked for?

Yes.

I added a policy and data-quality review layer:

* **879 GW-OTHER refunds above ₹500** — ₹28.72 lakh
* **166 refund + replacement cases** — ₹5.74 lakh
* **145 ambiguous order matches**
* **110 refunds above listed unit retail** — ₹7.58 lakh

I also found that **638 ticket IDs appear across the helpdesk and legacy systems**. Comparable records showed the legacy monetary value was consistently **100× the helpdesk value**, which required normalization before reporting.

These are review queues, not confirmed policy violations.

---

### 8. What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away.

I used:

* **ChatGPT** for coding assistance, debugging, prompt design, documentation, and workflow structure.
* **Ollama + Qwen3 8B** for local refund-reason classification.
* **nomic-embed-text** for local embedding experimentation.
* **Python/Pandas** for deterministic data processing and reconciliation.
* **Streamlit** for the application.
* **pytest** for automated validation.

AI was most useful for implementation, debugging, prompt design, and the advisory classifier.

During testing, Qwen sometimes produced thinking text around the JSON response. I changed the implementation to use **`/no_think` and robust JSON extraction**.

I also discarded the idea of using the LLM for financial aggregation and kept all financial calculations deterministic.

I did not claim a 100-ticket AI accuracy test. I reviewed 100 validation rows for analysis, but the AI classifier itself was smoke-tested on 10 tickets.

**Screen recording:** 
https://drive.google.com/file/d/1JCMQg7TBDVNIrApshQbjHF_7tPyniuz5/view?usp=sharing

---

### 9. Your Public Google Drive Link
https://drive.google.com/drive/folders/16GQX54uiLJiSRrv2lTqDG3pnEnt4pQ-W?usp=sharing

---

### 10. Someone picks this up on Monday and you are unreachable. The three things they need to know.

**1. Run the pipeline and tests:**

```text
python build_canonical.py
python monthly_analysis.py
python agent_analysis.py
python policy_audit.py
pytest -q
```

**2. Use the correct financial field:**

Use `refund_amount_normalized` for financial reporting. Do not aggregate the raw mixed-unit `refund_amount_inr` field.

**3. Treat proxies and review flags correctly:**

`created_at` is the refund-month proxy because `refund_processed_at` is unavailable. Policy flags and AI classifications are review aids, not automatic conclusions.

---

### 11. Honest hours spent. One number.

**5 hours**


