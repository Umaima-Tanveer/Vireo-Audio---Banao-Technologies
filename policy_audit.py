import pandas as pd

print("=" * 90)
print("REFUND POLICY & DATA-QUALITY AUDIT")
print("=" * 90)

# -------------------------------------------------------------------
# Load data
# -------------------------------------------------------------------

refunds = pd.read_csv("canonical_refunds.csv")
tickets = pd.read_csv("canonical_tickets.csv")
orders = pd.read_csv("orders.csv")
products = pd.read_csv("products.csv")

# Ensure refunds contains all available metadata from tickets
if "assigned_team" not in refunds.columns and "assigned_team" in tickets.columns:
    ticket_teams = tickets[["ticket_id", "assigned_team"]].drop_duplicates("ticket_id")
    refunds = refunds.merge(ticket_teams, on="ticket_id", how="left")

refunds["created_at"] = pd.to_datetime(refunds["created_at"], errors="coerce")
refunds["resolved_at"] = pd.to_datetime(refunds["resolved_at"], errors="coerce")

orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
products["launch_date"] = pd.to_datetime(products["launch_date"], errors="coerce")

# -------------------------------------------------------------------
# 1. Basic refund sanity checks
# -------------------------------------------------------------------

print("\n1. REFUND DATA QUALITY")
print("-" * 90)

print("Refund rows:", len(refunds))
print(
    "Missing refund amount:",
    refunds["refund_amount_normalized"].isna().sum()
)
print(
    "Missing refund reason:",
    refunds["refund_reason_code"].isna().sum()
)

print(
    "Zero/negative refunds:",
    (refunds["refund_amount_normalized"] <= 0).sum()
)

print(
    "Refunds > ₹10,000:",
    (refunds["refund_amount_normalized"] > 10000).sum()
)

print(
    "Refunds > ₹50,000:",
    (refunds["refund_amount_normalized"] > 50000).sum()
)

# -------------------------------------------------------------------
# 2. Goodwill amount check
# -------------------------------------------------------------------

goodwill = refunds[
    refunds["refund_reason_code"] == "GW-OTHER"
].copy()

goodwill_over_cap = goodwill[
    goodwill["refund_amount_normalized"] > 500
].copy()

print("\n2. GOODWILL CAP CHECK")
print("-" * 90)

print("GW-OTHER refunds:", len(goodwill))
print(
    "GW-OTHER total:",
    f"₹{goodwill['refund_amount_normalized'].sum():,.2f}"
)

print(
    "GW-OTHER > ₹500:",
    len(goodwill_over_cap)
)

print(
    "Amount represented by GW-OTHER > ₹500:",
    f"₹{goodwill_over_cap['refund_amount_normalized'].sum():,.2f}"
)

if len(goodwill_over_cap) > 0:
    print("\nExamples:")
    print(
        goodwill_over_cap[
            [
                "ticket_id",
                "agent_id",
                "refund_amount_normalized",
                "refund_reason_code"
            ]
        ]
        .sort_values("refund_amount_normalized", ascending=False)
        .head(20)
        .to_string(index=False)
    )

# -------------------------------------------------------------------
# 3. Refund + replacement check
# -------------------------------------------------------------------

refund_replacement = refunds[
    refunds["replacement_issued"].astype(str).str.upper().isin(
        ["Y", "YES", "TRUE", "1"]
    )
].copy()

print("\n3. REFUND + REPLACEMENT CHECK")
print("-" * 90)

print("Refund + replacement tickets:", len(refund_replacement))

print(
    "Refund amount:",
    f"₹{refund_replacement['refund_amount_normalized'].sum():,.2f}"
)

if len(refund_replacement) > 0:
    print("\nBy reason:")
    print(
        refund_replacement
        .groupby("refund_reason_code")
        .agg(
            count=("ticket_id", "nunique"),
            refund_amount_inr=("refund_amount_normalized", "sum")
        )
        .sort_values("refund_amount_inr", ascending=False)
        .to_string(
            formatters={
                "refund_amount_inr": lambda x: f"₹{x:,.2f}"
            }
        )
    )

# -------------------------------------------------------------------
# 4. Order linkage
# -------------------------------------------------------------------

print("\n4. ORDER LINKAGE")
print("-" * 90)

# Direct order_id match
orders_by_id = orders.drop_duplicates("order_id").copy()

refunds["direct_order_match"] = refunds["order_id"].isin(
    orders_by_id["order_id"]
)

print(
    "Direct order_id matches:",
    refunds["direct_order_match"].sum()
)

print(
    "Missing/unmatched direct order_id:",
    (~refunds["direct_order_match"]).sum()
)

# Fallback customer_id + product_sku match
order_keys = (
    orders.groupby(["customer_id", "sku"])
    .size()
    .reset_index(name="order_match_count")
)

refunds = refunds.merge(
    order_keys,
    left_on=["customer_id", "product_sku"],
    right_on=["customer_id", "sku"],
    how="left"
)

fallback_only = (
    ~refunds["direct_order_match"]
    & refunds["order_match_count"].notna()
)

ambiguous_fallback = (
    ~refunds["direct_order_match"]
    & (refunds["order_match_count"] > 1)
)

unmatched = (
    ~refunds["direct_order_match"]
    & refunds["order_match_count"].isna()
)

print("Fallback customer + SKU matches:", fallback_only.sum())
print("Ambiguous fallback matches:", ambiguous_fallback.sum())
print("Completely unmatched:", unmatched.sum())

# -------------------------------------------------------------------
# 5. Refund amount vs product retail price
# -------------------------------------------------------------------

print("\n5. REFUND VS PRODUCT PRICE")
print("-" * 90)

product_lookup = products[
    [
        "sku",
        "product_name",
        "unit_cost_inr",
        "retail_price_inr"
    ]
].drop_duplicates("sku")

refunds = refunds.merge(
    product_lookup,
    left_on="product_sku",
    right_on="sku",
    how="left"
)

refunds["refund_above_retail"] = (
    refunds["refund_amount_normalized"]
    > refunds["retail_price_inr"]
)

above_retail = refunds[
    refunds["refund_above_retail"] == True
].copy()

print(
    "Refunds above listed retail price:",
    len(above_retail)
)

print(
    "Amount represented:",
    f"₹{above_retail['refund_amount_normalized'].sum():,.2f}"
)

if len(above_retail) > 0:
    print("\nLargest examples:")
    print(
        above_retail[
            [
                "ticket_id",
                "agent_id",
                "product_sku",
                "refund_amount_normalized",
                "retail_price_inr",
                "refund_reason_code"
            ]
        ]
        .sort_values("refund_amount_normalized", ascending=False)
        .head(20)
        .to_string(index=False)
    )

# -------------------------------------------------------------------
# 6. Team ownership check
# -------------------------------------------------------------------

print("\n6. TEAM / REASON PATTERNS")
print("-" * 90)

team_reason_cols = [
    "assigned_team",
    "refund_reason_code",
    "refund_amount_normalized"
]

missing_team_reason_cols = [
    c for c in team_reason_cols
    if c not in refunds.columns
]

if missing_team_reason_cols:
    print(
        "WARNING: Missing columns for team/reason analysis:",
        missing_team_reason_cols
    )
else:
    team_reason = (
        refunds
        .groupby(
            ["assigned_team", "refund_reason_code"],
            dropna=False
        )
        .agg(
            refund_count=("refund_amount_normalized", "size"),
            refund_total_inr=("refund_amount_normalized", "sum")
        )
        .reset_index()
        .sort_values(
            "refund_total_inr",
            ascending=False
        )
    )

    print(
        team_reason.to_string(
            index=False,
            formatters={
                "refund_total_inr": lambda x: f"₹{x:,.2f}"
            }
        )
    )

# -------------------------------------------------------------------
# 7. Save audit output
# -------------------------------------------------------------------

refunds.to_csv("refund_policy_audit.csv", index=False)

print("\n\nSaved:")
print("  refund_policy_audit.csv")

# -------------------------------------------------------------------
# 8. Summary
# -------------------------------------------------------------------

print("\n" + "=" * 90)
print("AUDIT SUMMARY")
print("=" * 90)

print(f"Total refund tickets: {len(refunds)}")
print(
    f"Total refund amount: "
    f"₹{refunds['refund_amount_normalized'].sum():,.2f}"
)
print(f"Goodwill > ₹500: {len(goodwill_over_cap)}")
print(f"Refund + replacement: {len(refund_replacement)}")
print(f"Refund > retail price: {len(above_retail)}")
print(f"Ambiguous order fallback: {ambiguous_fallback.sum()}")
print(f"Unmatched orders: {unmatched.sum()}")