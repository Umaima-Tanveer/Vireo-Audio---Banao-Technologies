import pandas as pd
from pathlib import Path

DATA = Path(".")

files = [
    "tickets.csv",
    "agents.csv",
    "orders.csv",
    "customers.csv",
    "products.csv",
]

for filename in files:
    path = DATA / filename

    print("\n" + "=" * 80)
    print(filename)
    print("=" * 80)

    df = pd.read_csv(path)

    print("Shape:", df.shape)
    print("\nColumns:")
    for col in df.columns:
        print("  -", col)

    print("\nMissing values:")
    print(df.isna().sum())

    print("\nDuplicate rows:", df.duplicated().sum())