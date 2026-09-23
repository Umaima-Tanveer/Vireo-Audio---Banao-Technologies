import pandas as pd

agents = pd.read_csv("agents.csv")

print("=" * 80)
print("AGENT ROSTER INSPECTION")
print("=" * 80)

print("\nShape:")
print(agents.shape)

print("\nColumns:")
print(list(agents.columns))

print("\nFirst rows:")
print(agents.head(10).to_string(index=False))

print("\nAgent IDs:")
print("Total rows:", len(agents))
print("Unique agent IDs:", agents["agent_id"].nunique())

print("\nDuplicate agent IDs:")
counts = agents["agent_id"].value_counts()
print(counts[counts > 1].to_string())

print("\nTeam distribution:")
print(agents["team"].value_counts(dropna=False).to_string())

if "tier" in agents.columns:
    print("\nTier distribution:")
    print(agents["tier"].value_counts(dropna=False).to_string())

if "from_date" in agents.columns:
    print("\nFrom-date range:")
    print(agents["from_date"].min(), "to", agents["from_date"].max())

if "to_date" in agents.columns:
    print("\nTo-date missing:")
    print(agents["to_date"].isna().sum(), "/", len(agents))

print("\nFull roster:")
print(agents.to_string(index=False))