from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

TICKETS_FILE = BASE_DIR / "canonical_tickets.csv"
OUTPUT_FILE = BASE_DIR / "outputs" / "validation_sample.csv"


REASONS = [
    "GW-OTHER",
    "RETURN-QC-OK",
    "DUP-PAYMENT",
    "CANCEL",
    "DOA-REPL",
    "WTY-BUYBACK",
    "PRICE-ADJ",
    "LOST-TRANSIT",
]


def main():

    print("=" * 80)
    print("VIREO AUDIO — CREATE 100-TICKET VALIDATION SAMPLE")
    print("=" * 80)

    df = pd.read_csv(TICKETS_FILE)

    # Refund tickets only.
    refund_mask = pd.to_numeric(
        df["refund_amount_inr"],
        errors="coerce"
    ).fillna(0) > 0

    refunds = df[refund_mask].copy()

    print(f"Total refund tickets: {len(refunds)}")

    # Show full reason distribution.
    counts = (
        refunds["refund_reason_code"]
        .value_counts()
        .reindex(REASONS)
        .fillna(0)
        .astype(int)
    )

    print("\nFull refund distribution:")
    print(counts.to_string())

    # ---------------------------------------------------------
    # Allocate approximately proportional sample sizes.
    # Minimum 5 tickets per reason where possible.
    # ---------------------------------------------------------

    allocation = {}

    for reason in REASONS:
        available = counts[reason]

        if available >= 5:
            allocation[reason] = 5
        else:
            allocation[reason] = int(available)

    allocated = sum(allocation.values())
    remaining = 100 - allocated

    # Distribute remaining slots proportionally among reasons
    # that still have enough tickets available.
    while remaining > 0:

        candidates = []

        for reason in REASONS:

            available = counts[reason]

            if allocation[reason] < available:
                candidates.append(reason)

        if not candidates:
            break

        # Give next slot to the reason with the largest
        # remaining population relative to its current allocation.
        reason = max(
            candidates,
            key=lambda r: counts[r] - allocation[r]
        )

        allocation[reason] += 1
        remaining -= 1

    print("\nValidation allocation:")

    for reason in REASONS:
        print(
            f"{reason:18s}: "
            f"{allocation[reason]}"
        )

    print(
        f"\nTotal allocated: "
        f"{sum(allocation.values())}"
    )

    # ---------------------------------------------------------
    # Sample tickets.
    # ---------------------------------------------------------

    parts = []

    for reason in REASONS:

        group = refunds[
            refunds["refund_reason_code"] == reason
        ]

        n = allocation[reason]

        if n == 0:
            continue

        sampled = group.sample(
            n=n,
            random_state=42
        )

        parts.append(sampled)

    validation = pd.concat(
        parts,
        ignore_index=True
    )

    # Shuffle final sample.
    validation = validation.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # Columns needed for human review and AI classification.
    # ---------------------------------------------------------

    output_columns = [
        "ticket_id",
        "recorded_reason_code",
        "refund_amount_inr",
        "refund_reason_code",
        "customer_message",
        "agent_notes",
        "category",
        "assigned_team",
        "agent_id",
    ]

    # The source column is called refund_reason_code.
    validation["recorded_reason_code"] = (
        validation["refund_reason_code"]
    )

    validation = validation[
        [
            "ticket_id",
            "recorded_reason_code",
            "refund_amount_inr",
            "customer_message",
            "agent_notes",
            "category",
            "assigned_team",
            "agent_id",
        ]
    ]

    # Human review columns.
    validation["human_label"] = ""
    validation["human_notes"] = ""
    validation["reviewer"] = ""

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    validation.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8"
    )

    print()
    print("=" * 80)
    print("VALIDATION SAMPLE CREATED")
    print("=" * 80)

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows: {len(validation)}")

    print("\nActual sample distribution:")
    print(
        validation["recorded_reason_code"]
        .value_counts()
        .to_string()
    )


if __name__ == "__main__":
    main()