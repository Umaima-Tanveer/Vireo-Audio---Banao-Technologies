import pandas as pd

print("=" * 90)
print("AGENT REFUND ANALYSIS")
print("=" * 90)

# -------------------------------------------------------------------
# 1. Load data
# -------------------------------------------------------------------

refunds = pd.read_csv("canonical_refunds.csv")
tickets = pd.read_csv("canonical_tickets.csv")
agents = pd.read_csv("agents.csv")

# Clean dates
refunds["created_at"] = pd.to_datetime(refunds["created_at"], errors="coerce")
tickets["created_at"] = pd.to_datetime(tickets["created_at"], errors="coerce")

# -------------------------------------------------------------------
# 2. Basic ticket / refund counts
# -------------------------------------------------------------------

# Total attended tickets by agent
ticket_counts = (
    tickets
    .groupby("agent_id")
    .agg(
        attended_tickets=("ticket_id", "nunique")
    )
    .reset_index()
)

# Refund metrics by agent
agent_refunds = (
    refunds
    .groupby("agent_id")
    .agg(
        refund_count=("ticket_id", "nunique"),
        refund_amount_inr=("refund_amount_normalized", "sum"),
        average_refund_inr=("refund_amount_normalized", "mean")
    )
    .reset_index()
)

# -------------------------------------------------------------------
# 3. Join agent roster
# -------------------------------------------------------------------

agent_report = (
    agents
    .merge(ticket_counts, on="agent_id", how="left")
    .merge(agent_refunds, on="agent_id", how="left")
)

# Fill agents with no refunds
for col in ["refund_count", "refund_amount_inr", "average_refund_inr"]:
    agent_report[col] = agent_report[col].fillna(0)

agent_report["attended_tickets"] = agent_report["attended_tickets"].fillna(0)

# -------------------------------------------------------------------
# 4. Derived metrics
# -------------------------------------------------------------------

agent_report["refund_rate_pct"] = (
    agent_report["refund_count"]
    / agent_report["attended_tickets"]
    * 100
).fillna(0)

agent_report["refund_amount_per_ticket_inr"] = (
    agent_report["refund_amount_inr"]
    / agent_report["attended_tickets"]
).fillna(0)

# Round metrics
agent_report["refund_amount_inr"] = agent_report["refund_amount_inr"].round(2)
agent_report["average_refund_inr"] = agent_report["average_refund_inr"].round(2)
agent_report["refund_rate_pct"] = agent_report["refund_rate_pct"].round(2)
agent_report["refund_amount_per_ticket_inr"] = (
    agent_report["refund_amount_per_ticket_inr"].round(2)
)

# -------------------------------------------------------------------
# 5. Print overall agent report
# -------------------------------------------------------------------

display_columns = [
    "agent_id",
    "name",
    "team",
    "tier",
    "attended_tickets",
    "refund_count",
    "refund_amount_inr",
    "average_refund_inr",
    "refund_rate_pct",
    "refund_amount_per_ticket_inr"
]

print("\nAGENT REFUND SUMMARY")
print("-" * 90)

print(
    agent_report[
        display_columns
    ]
    .sort_values("refund_amount_inr", ascending=False)
    .to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}",
            "average_refund_inr": lambda x: f"₹{x:,.2f}",
            "refund_rate_pct": lambda x: f"{x:.2f}%",
            "refund_amount_per_ticket_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)

# -------------------------------------------------------------------
# 6. Team-level summary
# -------------------------------------------------------------------

team_summary = (
    agent_report
    .groupby(["team", "tier"])
    .agg(
        agents=("agent_id", "nunique"),
        attended_tickets=("attended_tickets", "sum"),
        refund_count=("refund_count", "sum"),
        refund_amount_inr=("refund_amount_inr", "sum")
    )
    .reset_index()
)

team_summary["refund_rate_pct"] = (
    team_summary["refund_count"]
    / team_summary["attended_tickets"]
    * 100
).fillna(0)

team_summary["average_refund_inr"] = (
    team_summary["refund_amount_inr"]
    / team_summary["refund_count"]
).fillna(0)

team_summary["refund_amount_per_ticket_inr"] = (
    team_summary["refund_amount_inr"]
    / team_summary["attended_tickets"]
).fillna(0)

print("\n\nTEAM SUMMARY")
print("-" * 90)

print(
    team_summary.to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}",
            "average_refund_inr": lambda x: f"₹{x:,.2f}",
            "refund_rate_pct": lambda x: f"{x:.2f}%",
            "refund_amount_per_ticket_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)

# -------------------------------------------------------------------
# 7. Refund reasons by agent
# -------------------------------------------------------------------

reason_by_agent = (
    refunds
    .groupby(["agent_id", "refund_reason_code"])
    .agg(
        refund_count=("ticket_id", "nunique"),
        refund_amount_inr=("refund_amount_normalized", "sum")
    )
    .reset_index()
)

reason_by_agent["refund_amount_inr"] = reason_by_agent[
    "refund_amount_inr"
].round(2)

print("\n\nREFUND REASONS BY AGENT")
print("-" * 90)

print(
    reason_by_agent
    .sort_values(
        ["agent_id", "refund_amount_inr"],
        ascending=[True, False]
    )
    .to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)

# -------------------------------------------------------------------
# 8. Returns Desk separately
# -------------------------------------------------------------------

returns = agent_report[
    agent_report["team"] == "Returns Desk"
].copy()

print("\n\nRETURNS DESK")
print("-" * 90)

print(
    returns[
        display_columns
    ]
    .sort_values("refund_amount_inr", ascending=False)
    .to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}",
            "average_refund_inr": lambda x: f"₹{x:,.2f}",
            "refund_rate_pct": lambda x: f"{x:.2f}%",
            "refund_amount_per_ticket_inr": lambda x: f"₹{x:,.2f}"
        }
    )
)

# -------------------------------------------------------------------
# 9. Tier 1 vs Tier 2 — descriptive only
# -------------------------------------------------------------------

tier_summary = (
    agent_report
    .groupby("tier")
    .agg(
        agents=("agent_id", "nunique"),
        attended_tickets=("attended_tickets", "sum"),
        refund_count=("refund_count", "sum"),
        refund_amount_inr=("refund_amount_inr", "sum")
    )
    .reset_index()
)

tier_summary["refund_rate_pct"] = (
    tier_summary["refund_count"]
    / tier_summary["attended_tickets"]
    * 100
).fillna(0)

print("\n\nTIER SUMMARY — DESCRIPTIVE")
print("-" * 90)

print(
    tier_summary.to_string(
        index=False,
        formatters={
            "refund_amount_inr": lambda x: f"₹{x:,.2f}",
            "refund_rate_pct": lambda x: f"{x:.2f}%"
        }
    )
)

# -------------------------------------------------------------------
# 10. Save outputs
# -------------------------------------------------------------------

agent_report.to_csv("agent_refunds.csv", index=False)
team_summary.to_csv("team_refunds.csv", index=False)
reason_by_agent.to_csv("agent_reason_refunds.csv", index=False)

print("\n\nSaved:")
print("  agent_refunds.csv")
print("  team_refunds.csv")
print("  agent_reason_refunds.csv")

# -------------------------------------------------------------------
# 11. Reconciliation
# -------------------------------------------------------------------

canonical_total = refunds["refund_amount_normalized"].sum()
agent_total = agent_report["refund_amount_inr"].sum()

print("\n\nRECONCILIATION")
print("-" * 90)
print(f"Canonical refund total: ₹{canonical_total:,.2f}")
print(f"Agent report total:     ₹{agent_total:,.2f}")
print(f"Difference:             ₹{canonical_total - agent_total:,.2f}")

if abs(canonical_total - agent_total) < 0.01:
    print("STATUS: PASS")
else:
    print("STATUS: FAIL")