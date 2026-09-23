import pandas as pd

tickets = pd.read_csv("tickets.csv")

print("=" * 80)
print("REFUND RECONCILIATION")
print("=" * 80)

# ---------------------------------------------------------
# 1. Basic duplicate analysis
# ---------------------------------------------------------

print("\n1. TICKET ID DUPLICATES")

duplicate_ids = (
    tickets["ticket_id"]
    .value_counts()
    .loc[lambda x: x > 1]
)

print("Number of ticket IDs appearing more than once:", len(duplicate_ids))
print("Total rows involved in duplicate IDs:", duplicate_ids.sum())

# Show examples
dup_tickets = tickets[
    tickets["ticket_id"].isin(duplicate_ids.index)
].copy()

print("\nSample duplicate tickets:")
print(
    dup_tickets[
        [
            "ticket_id",
            "source_system",
            "refund_amount_inr",
            "refund_reason_code",
            "replacement_issued",
        ]
    ]
    .sort_values(["ticket_id", "source_system"])
    .head(30)
    .to_string(index=False)
)


# ---------------------------------------------------------
# 2. How many duplicate IDs have both systems?
# ---------------------------------------------------------

print("\n2. DUPLICATES BY SOURCE SYSTEM")

duplicate_source = (
    dup_tickets
    .groupby("ticket_id")["source_system"]
    .agg(lambda x: sorted(set(x)))
)

both_systems = duplicate_source[
    duplicate_source.apply(
        lambda x: "helpdesk" in x and "legacy_fd" in x
    )
]

print("Duplicate IDs appearing in BOTH helpdesk and legacy_fd:",
      len(both_systems))


# ---------------------------------------------------------
# 3. Refund amounts by source
# ---------------------------------------------------------

print("\n3. RAW REFUND TOTAL BY SOURCE")

refunds = tickets[tickets["refund_amount_inr"].notna()].copy()

source_summary = (
    refunds
    .groupby("source_system")
    .agg(
        refund_rows=("refund_amount_inr", "size"),
        refund_total=("refund_amount_inr", "sum"),
        average_refund=("refund_amount_inr", "mean"),
        median_refund=("refund_amount_inr", "median"),
    )
)

print(source_summary.to_string())


# ---------------------------------------------------------
# 4. Duplicate refund comparisons
# ---------------------------------------------------------

print("\n4. DUPLICATE REFUND AMOUNT COMPARISON")

dup_refunds = (
    dup_tickets[
        dup_tickets["refund_amount_inr"].notna()
    ]
    .pivot_table(
        index="ticket_id",
        columns="source_system",
        values="refund_amount_inr",
        aggfunc="first"
    )
    .reset_index()
)

if "helpdesk" in dup_refunds.columns and "legacy_fd" in dup_refunds.columns:

    dup_refunds["ratio_legacy_to_helpdesk"] = (
        dup_refunds["legacy_fd"] /
        dup_refunds["helpdesk"]
    )

    print(
        dup_refunds[
            [
                "ticket_id",
                "helpdesk",
                "legacy_fd",
                "ratio_legacy_to_helpdesk",
            ]
        ]
        .dropna()
        .head(50)
        .to_string(index=False)
    )

    print("\nRatio statistics:")

    print(
        dup_refunds["ratio_legacy_to_helpdesk"]
        .dropna()
        .describe()
    )


# ---------------------------------------------------------
# 5. Test the possible x100 conversion
# ---------------------------------------------------------

print("\n5. TESTING LEGACY / 100")

if "helpdesk" in dup_refunds.columns and "legacy_fd" in dup_refunds.columns:

    comparable = dup_refunds.dropna(
        subset=["helpdesk", "legacy_fd"]
    ).copy()

    comparable["legacy_converted"] = (
        comparable["legacy_fd"] / 100
    )

    comparable["difference"] = (
        comparable["legacy_converted"] -
        comparable["helpdesk"]
    )

    comparable["exact_match"] = (
        comparable["difference"].abs() < 0.01
    )

    print(
        "Comparable duplicate refund pairs:",
        len(comparable)
    )

    print(
        "Exact matches after legacy / 100:",
        comparable["exact_match"].sum()
    )

    print(
        "Match percentage:",
        round(
            comparable["exact_match"].mean() * 100,
            2
        ),
            "%"
    )

    print("\nLargest mismatches:")

    print(
        comparable[
            [
                "ticket_id",
                "helpdesk",
                "legacy_fd",
                "legacy_converted",
                "difference",
            ]
        ]
        .sort_values(
            "difference",
            key=lambda x: x.abs(),
            ascending=False
        )
        .head(20)
        .to_string(index=False)
    )


# ---------------------------------------------------------
# 6. Refund rows with missing reason
# ---------------------------------------------------------

print("\n6. REFUNDS WITH MISSING REASON")

missing_reason = refunds[
    refunds["refund_reason_code"].isna()
]

print(
    "Refund rows with missing reason:",
    len(missing_reason)
)

print(
    "Amount involved:",
    missing_reason["refund_amount_inr"].sum()
)


# ---------------------------------------------------------
# 7. Refund + replacement
# ---------------------------------------------------------

print("\n7. REFUND + REPLACEMENT")

refund_replacement = refunds[
    refunds["replacement_issued"].eq("Y")
]

print(
    "Rows with both refund and replacement:",
    len(refund_replacement)
)

print(
    "Refund amount on those rows:",
    refund_replacement["refund_amount_inr"].sum()
)

print("\nReason codes for refund + replacement:")

print(
    refund_replacement["refund_reason_code"]
    .value_counts(dropna=False)
)


print("\n" + "=" * 80)
print("END")
print("=" * 80)