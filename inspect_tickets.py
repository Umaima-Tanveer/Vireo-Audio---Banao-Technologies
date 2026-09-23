import pandas as pd

tickets = pd.read_csv("tickets.csv")

print("ROWS:", len(tickets))
print("UNIQUE TICKETS:", tickets["ticket_id"].nunique())

print("\nDUPLICATE TICKET IDS:")
print(
    tickets[tickets["ticket_id"].duplicated(keep=False)]
    .sort_values("ticket_id")
    [["ticket_id", "source_system", "refund_amount_inr",
      "refund_reason_code", "replacement_issued"]]
    .to_string(index=False)
)

print("\nSOURCE SYSTEM:")
print(tickets["source_system"].value_counts(dropna=False))

print("\nREFUND ROWS:")
refunds = tickets[tickets["refund_amount_inr"].notna()]
print("Rows with refund:", len(refunds))
print("Refund amount sum:", refunds["refund_amount_inr"].sum())

print("\nREASON CODES:")
print(tickets["refund_reason_code"].value_counts(dropna=False))

print("\nREFUND + REPLACEMENT:")
print(
    (
        tickets["refund_amount_inr"].notna()
        & (tickets["replacement_issued"] == "Y")
    ).sum()
)