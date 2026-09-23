import pandas as pd

print("=" * 80)
print("BUILDING CANONICAL REFUND DATASET")
print("=" * 80)

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

tickets = pd.read_csv("tickets.csv")

print("\nRaw rows:", len(tickets))
print("Unique ticket IDs:", tickets["ticket_id"].nunique())


# ---------------------------------------------------------
# Normalize legacy monetary values
# ---------------------------------------------------------

tickets["refund_amount_normalized"] = tickets["refund_amount_inr"]

legacy_mask = tickets["source_system"].eq("legacy_fd")

tickets.loc[
    legacy_mask,
    "refund_amount_normalized"
] = (
    tickets.loc[legacy_mask, "refund_amount_inr"] / 100
)


# ---------------------------------------------------------
# Identify duplicate ticket IDs
# ---------------------------------------------------------

ticket_source_count = (
    tickets
    .groupby("ticket_id")["source_system"]
    .nunique()
)

duplicated_across_systems = ticket_source_count[
    ticket_source_count > 1
].index

print(
    "\nTicket IDs duplicated across systems:",
    len(duplicated_across_systems)
)


# ---------------------------------------------------------
# Canonical selection
#
# Rule:
# - If ticket exists in helpdesk -> use helpdesk
# - Otherwise -> use legacy_fd
# ---------------------------------------------------------

tickets["canonical"] = True

legacy_duplicate_mask = (
    tickets["source_system"].eq("legacy_fd")
    & tickets["ticket_id"].isin(duplicated_across_systems)
)

tickets.loc[
    legacy_duplicate_mask,
    "canonical"
] = False

canonical = tickets[
    tickets["canonical"]
].copy()


# ---------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------

print("\nCanonical rows:", len(canonical))
print(
    "Canonical unique ticket IDs:",
    canonical["ticket_id"].nunique()
)

print(
    "Duplicate canonical ticket IDs:",
    canonical["ticket_id"].duplicated().sum()
)


# ---------------------------------------------------------
# Refund totals
# ---------------------------------------------------------

refunds = canonical[
    canonical["refund_amount_normalized"].notna()
].copy()

print("\nCANONICAL REFUNDS")
print("-" * 80)

print("Refund rows:", len(refunds))

print(
    "Refund total: ₹{:,.2f}".format(
        refunds["refund_amount_normalized"].sum()
    )
)

print(
    "Average refund: ₹{:,.2f}".format(
        refunds["refund_amount_normalized"].mean()
    )
)

print(
    "Median refund: ₹{:,.2f}".format(
        refunds["refund_amount_normalized"].median()
    )
)


# ---------------------------------------------------------
# Refund totals by source after canonicalization
# ---------------------------------------------------------

print("\nCANONICAL REFUNDS BY ORIGINAL SOURCE")

source_summary = (
    refunds
    .groupby("source_system")
    .agg(
        refund_rows=("refund_amount_normalized", "size"),
        refund_total=("refund_amount_normalized", "sum")
    )
)

print(source_summary.to_string())


# ---------------------------------------------------------
# Reason totals
# ---------------------------------------------------------

print("\nCANONICAL REFUNDS BY REASON")

reason_summary = (
    refunds
    .groupby("refund_reason_code")
    .agg(
        refund_rows=("refund_amount_normalized", "size"),
        refund_total=("refund_amount_normalized", "sum")
    )
    .sort_values("refund_total", ascending=False)
)

print(reason_summary.to_string())


# ---------------------------------------------------------
# Save canonical dataset
# ---------------------------------------------------------

canonical.to_csv(
    "canonical_tickets.csv",
    index=False
)

refunds.to_csv(
    "canonical_refunds.csv",
    index=False
)

print("\nSaved:")
print("  canonical_tickets.csv")
print("  canonical_refunds.csv")


print("\n" + "=" * 80)
print("DONE")
print("=" * 80)