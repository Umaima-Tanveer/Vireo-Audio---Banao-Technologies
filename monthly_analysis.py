import pandas as pd

print("=" * 80)
print("MONTHLY REFUND ANALYSIS")
print("=" * 80)

# ---------------------------------------------------------
# Load canonical refunds
# ---------------------------------------------------------

refunds = pd.read_csv("canonical_refunds.csv")

# Parse dates
refunds["created_at"] = pd.to_datetime(
    refunds["created_at"],
    errors="coerce"
)

# Create reporting month
refunds["month"] = refunds["created_at"].dt.to_period("M").astype(str)


# ---------------------------------------------------------
# 1. Overall monthly refunds
# ---------------------------------------------------------

monthly = (
    refunds
    .groupby("month")
    .agg(
        refund_count=("refund_amount_normalized", "size"),
        refund_amount_inr=("refund_amount_normalized", "sum")
    )
    .reset_index()
)

print("\nMONTHLY REFUNDS")
print("-" * 80)

print(
    monthly.to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)


# ---------------------------------------------------------
# 2. Monthly refunds by reason
# ---------------------------------------------------------

monthly_reason = (
    refunds
    .groupby(
        ["month", "refund_reason_code"]
    )
    .agg(
        refund_count=("refund_amount_normalized", "size"),
        refund_amount_inr=("refund_amount_normalized", "sum")
    )
    .reset_index()
    .sort_values(
        ["month", "refund_amount_inr"],
        ascending=[True, False]
    )
)

print("\nMONTHLY REFUNDS BY REASON")
print("-" * 80)

print(
    monthly_reason.to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)


# ---------------------------------------------------------
# 3. Save outputs
# ---------------------------------------------------------

monthly.to_csv(
    "monthly_refunds.csv",
    index=False
)

monthly_reason.to_csv(
    "monthly_reason_refunds.csv",
    index=False
)

print("\nSaved:")
print("  monthly_refunds.csv")
print("  monthly_reason_refunds.csv")


# ---------------------------------------------------------
# 4. Reconciliation check
# ---------------------------------------------------------

total_from_months = monthly["refund_amount_inr"].sum()
total_from_canonical = refunds["refund_amount_normalized"].sum()

print("\nRECONCILIATION")
print("-" * 80)

print(
    f"Canonical total: ₹{total_from_canonical:,.2f}"
)

print(
    f"Monthly total:   ₹{total_from_months:,.2f}"
)

print(
    "Difference:       "
    f"₹{total_from_canonical - total_from_months:,.2f}"
)

if abs(total_from_canonical - total_from_months) < 0.01:
    print("STATUS: PASS")
else:
    print("STATUS: FAIL")