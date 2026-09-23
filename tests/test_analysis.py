import pandas as pd


# ---------------------------------------------------------
# Test 1: Canonical refund dataset
# ---------------------------------------------------------

def test_canonical_refunds():
    df = pd.read_csv("canonical_refunds.csv")

    assert len(df) == 2340
    assert df["ticket_id"].nunique() == 2340

    total = pd.to_numeric(
        df["refund_amount_normalized"],
        errors="coerce"
    ).sum()

    assert total == 6_709_932

    assert df["refund_reason_code"].notna().all()


# ---------------------------------------------------------
# Test 2: Reason totals
# ---------------------------------------------------------

def test_refund_reason_counts():
    df = pd.read_csv("canonical_refunds.csv")

    counts = (
        df["refund_reason_code"]
        .value_counts()
        .to_dict()
    )

    expected = {
        "GW-OTHER": 991,
        "RETURN-QC-OK": 452,
        "DUP-PAYMENT": 321,
        "CANCEL": 222,
        "DOA-REPL": 147,
        "WTY-BUYBACK": 89,
        "PRICE-ADJ": 71,
        "LOST-TRANSIT": 47,
    }

    assert counts == expected


# ---------------------------------------------------------
# Test 3: No invalid refund amounts
# ---------------------------------------------------------

def test_refund_amounts_are_valid():
    df = pd.read_csv("canonical_refunds.csv")

    amounts = pd.to_numeric(
        df["refund_amount_normalized"],
        errors="coerce"
    )

    assert amounts.notna().all()
    assert (amounts > 0).all()


# ---------------------------------------------------------
# Test 4: GW-OTHER policy review queue
# ---------------------------------------------------------

def test_goodwill_review_queue():
    df = pd.read_csv("canonical_refunds.csv")

    amounts = pd.to_numeric(
        df["refund_amount_normalized"],
        errors="coerce"
    )

    mask = (
        (df["refund_reason_code"] == "GW-OTHER")
        & (amounts > 500)
    )

    assert mask.sum() == 879

    assert amounts[mask].sum() == 2_871_632


# ---------------------------------------------------------
# Test 5: Refund + replacement review queue
# ---------------------------------------------------------

def test_refund_plus_replacement():
    df = pd.read_csv("canonical_refunds.csv")

    replacement = (
        df["replacement_issued"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
            "yes": True,
            "no": False,
            "y": True,
            "n": False,
        })
        .fillna(False)
    )

    flagged = df[replacement]

    assert len(flagged) == 166

    amounts = pd.to_numeric(
        flagged["refund_amount_normalized"],
        errors="coerce"
    )

    assert amounts.sum() == 574_191


# ---------------------------------------------------------
# Test 6: Monthly totals reconcile
# ---------------------------------------------------------

def test_monthly_refunds_reconcile():
    df = pd.read_csv("canonical_refunds.csv")

    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce"
    )

    df["month"] = df["created_at"].dt.to_period("M")

    amounts = pd.to_numeric(
        df["refund_amount_normalized"],
        errors="coerce"
    )

    monthly_total = (
        df.assign(amount=amounts)
        .groupby("month")["amount"]
        .sum()
        .sum()
    )

    overall_total = amounts.sum()

    assert monthly_total == overall_total
    assert monthly_total == 6_709_932


# ---------------------------------------------------------
# Test 7: Agent-level totals reconcile
# ---------------------------------------------------------

def test_agent_totals_reconcile():
    refunds = pd.read_csv("canonical_refunds.csv")

    agents = pd.read_csv("agents.csv")

    refunds["amount"] = pd.to_numeric(
        refunds["refund_amount_normalized"],
        errors="coerce"
    )

    agent_summary = (
        refunds.groupby("agent_id")["amount"]
        .sum()
    )

    assert agent_summary.sum() == 6_709_932

    # Every refund should have a known agent
    known_agents = set(
        agents["agent_id"].dropna().astype(str)
    )

    refund_agents = set(
        refunds["agent_id"].dropna().astype(str)
    )

    assert refund_agents.issubset(known_agents)


# ---------------------------------------------------------
# Test 8: Refund ticket IDs are unique
# ---------------------------------------------------------

def test_refund_ticket_ids_unique():
    df = pd.read_csv("canonical_refunds.csv")

    assert df["ticket_id"].is_unique


# ---------------------------------------------------------
# Test 9: Required columns exist
# ---------------------------------------------------------

def test_required_columns():
    df = pd.read_csv("canonical_refunds.csv")

    required = {
        "ticket_id",
        "created_at",
        "agent_id",
        "assigned_team",
        "refund_amount_inr",
        "refund_amount_normalized",
        "refund_reason_code",
        "replacement_issued",
    }

    assert required.issubset(df.columns)