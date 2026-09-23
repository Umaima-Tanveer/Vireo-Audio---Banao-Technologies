# Vireo Audio — Refund Reconciliation

## Board-Pack Summary | Jan 2025 – Jun 2026

### Executive finding

The support export contains **2,340 canonical refund tickets totaling ₹67.10 lakh** after reconciliation.

The raw export contains 2,465 refund rows totaling approximately **₹23.01 crore**. The difference is driven by two documented data-quality issues: legacy Freshdesk monetary values are stored in a different native unit and must be normalized, and 638 ticket IDs appear in both the current helpdesk and legacy export. For duplicate refund pairs, legacy amounts matched the current helpdesk amounts exactly after dividing the legacy value by 100.

The resulting canonical ledger contains **11,600 unique tickets**, including **2,340 refunds**, and reconciles exactly across the monthly and agent-level reports.

### Where the money goes

| Refund reason |   Refunds |          Amount |
| ------------- | --------: | --------------: |
| GW-OTHER      |       991 |     ₹29.07 lakh |
| RETURN-QC-OK  |       452 |     ₹11.81 lakh |
| DUP-PAYMENT   |       321 |      ₹8.85 lakh |
| CANCEL        |       222 |      ₹6.13 lakh |
| DOA-REPL      |       147 |      ₹4.71 lakh |
| WTY-BUYBACK   |        89 |      ₹2.89 lakh |
| PRICE-ADJ     |        71 |      ₹2.07 lakh |
| LOST-TRANSIT  |        47 |      ₹1.57 lakh |
| **Total**     | **2,340** | **₹67.10 lakh** |

`GW-OTHER` represents approximately 43% of refund value. This should be treated as an exposure category for review rather than automatically as an inappropriate refund, because CX leadership previously changed frontline guidance toward reducing customer friction.

### Agent / team view

Returns Desk processed the largest share of refunds by design because it owns return and refund processing. Billing's refunds are predominantly associated with duplicate/failed payment cases. Tier 2 warranty agents are also kept separate from Tier 1 volume comparisons because the support policy explicitly defines different work and measurement expectations.

The report therefore uses **refund count, refund value and reason mix as operational indicators**, not as misconduct rankings.

### Policy and data-quality exceptions

* **879 GW-OTHER refunds exceed ₹500**, representing ₹28.72 lakh. These require checking for the required Team Lead approval; approval evidence is not present in the export.
* **166 tickets contain both refund and replacement flags**, representing ₹5.74 lakh of refund value. These conflict with the policy's "never both" rule and should be reviewed.
* **145 fallback order matches are ambiguous** because customer + SKU identifies more than one possible order.
* **110 refunds exceed the listed unit retail price**, representing ₹7.58 lakh. These are review flags only; order quantity and other order-level factors must be checked before treating them as exceptions.

### Recommended Monday actions

1. **Finance:** adopt the canonical reconciliation logic and confirm it against the Finance-side ledger before the board pack.
2. **Support Ops:** review high-value `GW-OTHER` refunds and the 166 refund-plus-replacement cases, with approval evidence where applicable.
3. **Helpdesk Admin:** fix the reporting pipeline so legacy monetary units and migration duplicates cannot enter the financial report without normalization/deduplication.

### Confidence and limitations

The financial aggregation is deterministic and reconciles to ₹0 difference across monthly, agent and reason-level totals. The AI component uses local Qwen3 8B as a targeted text-classification/QC layer; it is not used to calculate financial totals or silently overwrite recorded reason codes. A 10-ticket smoke test produced 10/10 successful structured responses with zero technical failures. A larger human-labeled model evaluation was intentionally not run within the assignment time budget.
