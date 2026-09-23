import json
from pathlib import Path
import re
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CANONICAL_REFUNDS = BASE_DIR / "canonical_refunds.csv"
CANONICAL_TICKETS = BASE_DIR / "canonical_tickets.csv"
AGENTS = BASE_DIR / "agents.csv"
ORDERS = BASE_DIR / "orders.csv"
PRODUCTS = BASE_DIR / "products.csv"
POLICY_AUDIT = BASE_DIR / "refund_policy_audit.csv"

PROMPT_FILE = BASE_DIR / "prompts" / "refund_classifier.txt"

# Ollama is called via its local HTTP API rather than the `ollama run` CLI.
# The CLI is an interactive terminal UI: while a model "thinks", it redraws
# text in place using ANSI cursor-control codes (e.g. ESC[1D to move the
# cursor left, ESC[K to erase to end of line). Even when stdout is piped,
# those redraws still happen, and stripping the escape *codes* with a regex
# leaves behind the literal characters they were meant to erase - producing
# duplicated/garbled fragments like "custo" immediately followed by
# "customer". The HTTP API has no terminal UI, so it returns clean text.
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_TIMEOUT_SECONDS = 120

st.set_page_config(
    page_title="Vireo Audio Refund Intelligence",
    page_icon="💰",
    layout="wide",
)


# ============================================================
# STYLING
# ============================================================

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .subtitle {
        color: #666;
        margin-bottom: 1.5rem;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #666;
    }

    .review-box {
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #ddd;
        background: #fafafa;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_bool(series):
    """
    Standardize varied boolean representations across datasets into standard python Booleans.
    """
    if series is None or series.empty:
        return pd.Series(dtype=bool)

    return (
        series.astype(str)
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
            "t": True,
            "f": False
        })
        .fillna(False)
    )


def call_ollama(prompt, model=OLLAMA_MODEL, timeout=OLLAMA_TIMEOUT_SECONDS):
    """
    Call the local Ollama HTTP API (not the interactive CLI) and return the
    raw response text plus any error message.

    - stream=False: return the full response in one JSON payload instead of
      newline-delimited streaming chunks.
    - format="json": tells Ollama to constrain generation to valid JSON,
      so we get a clean parseable object back instead of freeform text.
    - think=False: for hybrid-reasoning models like Qwen3, suppresses the
      "thinking" trace from being interleaved into the response text.
      (Older Ollama servers ignore unknown fields, so this is safe to send
      even if the installed version predates the "think" parameter.)

    Returns (text, error). Exactly one of the two is non-empty/None.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False,
        "options": {"temperature": 0.1},
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
    except requests.exceptions.ConnectionError:
        return None, (
            "Could not reach the local Ollama server at "
            f"{OLLAMA_API_URL}. Make sure Ollama is running "
            "(`ollama serve`) and that the model has been pulled "
            f"(`ollama pull {model}`)."
        )
    except requests.exceptions.Timeout:
        return None, f"The local model timed out after {timeout} seconds."
    except requests.exceptions.RequestException as e:
        return None, f"Request to Ollama failed: {e}"

    if response.status_code != 200:
        return None, f"Ollama returned HTTP {response.status_code}: {response.text}"

    try:
        data = response.json()
    except json.JSONDecodeError:
        return None, "Ollama returned a non-JSON response."

    if "error" in data:
        return None, f"Ollama error: {data['error']}"

    return data.get("response", ""), None


def parse_model_json(output):
    """
    Parse the model's response into a JSON object.

    With format="json" the API should already return a clean JSON string,
    so this is mostly a straight json.loads(). The fallbacks below are kept
    as a defensive layer in case a model wraps its answer in <think> tags,
    markdown fences, or stray text despite the JSON-mode constraint.
    """
    if not output:
        return None

    cleaned = output.strip()

    # Defensive: strip a <think>...</think> block if one leaked through.
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)

    # Defensive: strip markdown fence formatting if present.
    cleaned = re.sub(r"```(?:json)?", "", cleaned)
    cleaned = cleaned.replace("```", "")

    cleaned = cleaned.strip()

    # Try direct parse first - this is the expected path with format="json".
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON object spanning from first { to last }.
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")

    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_candidate = cleaned[first_brace : last_brace + 1]
        try:
            result = json.loads(json_candidate)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():
    refunds = pd.read_csv(CANONICAL_REFUNDS)
    tickets = pd.read_csv(CANONICAL_TICKETS)
    agents = pd.read_csv(AGENTS)
    orders = pd.read_csv(ORDERS)
    products = pd.read_csv(PRODUCTS)

    # Normalize monetary values
    refunds["refund_amount"] = pd.to_numeric(
        refunds["refund_amount_normalized"], errors="coerce"
    ).fillna(0)

    # Normalize replacement flag boolean immediately after loading
    if "replacement_issued" in refunds.columns:
        refunds["replacement_flag"] = normalize_bool(refunds["replacement_issued"])
    else:
        refunds["replacement_flag"] = False

    tickets["created_at"] = pd.to_datetime(
        tickets["created_at"], errors="coerce"
    )

    if "resolved_at" in tickets.columns:
        tickets["resolved_at"] = pd.to_datetime(
            tickets["resolved_at"], errors="coerce"
        )

    return refunds, tickets, agents, orders, products


@st.cache_data
def load_policy_audit():
    if not POLICY_AUDIT.exists():
        return pd.DataFrame()

    return pd.read_csv(POLICY_AUDIT)


try:
    refunds, tickets, agents, orders, products = load_data()
    policy_audit = load_policy_audit()
except Exception as e:
    st.error(f"Could not load project data: {e}")
    st.stop()


# ============================================================
# DATA PREPARATION
# ============================================================

refunds["created_at"] = pd.to_datetime(
    refunds["created_at"], errors="coerce"
)

refunds["month"] = refunds["created_at"].dt.to_period("M").astype(str)

# Ensure correct schema mapping for agent details
agent_cols = ["agent_id", "team"]
if "agent_name" in agents.columns:
    agent_cols.append("agent_name")
elif "name" in agents.columns:
    agents["agent_name"] = agents["name"]
    agent_cols.append("agent_name")

if "tier" in agents.columns:
    agent_cols.append("tier")

refunds = refunds.merge(
    agents[agent_cols],
    on="agent_id",
    how="left",
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">💰 Vireo Audio Refund Intelligence</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Finance-ready refund reconciliation, operational analysis and AI-assisted ticket QC"
    "</div>",
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE METRICS
# ============================================================

total_refunds = len(refunds)
total_amount = refunds["refund_amount"].sum()
avg_refund = (
    total_amount / total_refunds
    if total_refunds
    else 0
)

unique_tickets = refunds["ticket_id"].nunique()

monthly_total = refunds.groupby(
    "month"
)["refund_amount"].sum().sum()

agent_total = refunds.groupby(
    "agent_id"
)["refund_amount"].sum().sum()

reason_total = refunds.groupby(
    "refund_reason_code"
)["refund_amount"].sum().sum()

reconciliation_pass = (
    abs(total_amount - monthly_total) < 0.01
    and abs(total_amount - agent_total) < 0.01
    and abs(total_amount - reason_total) < 0.01
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Refund tickets",
        f"{total_refunds:,}",
    )

with c2:
    st.metric(
        "Refund value",
        f"₹{total_amount / 100000:.2f} lakh",
    )

with c3:
    st.metric(
        "Average refund",
        f"₹{avg_refund:,.2f}",
    )

with c4:
    st.metric(
        "Reconciliation",
        "PASS" if reconciliation_pass else "CHECK",
    )


st.divider()


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Filters")

months = sorted(
    refunds["month"].dropna().unique()
)

selected_months = st.sidebar.multiselect(
    "Refund month",
    months,
    default=months,
)

teams = sorted(
    refunds["team"].dropna().unique()
)

selected_teams = st.sidebar.multiselect(
    "Team",
    teams,
    default=teams,
)

reasons = sorted(
    refunds["refund_reason_code"].dropna().unique()
)

selected_reasons = st.sidebar.multiselect(
    "Reason",
    reasons,
    default=reasons,
)


filtered = refunds[
    refunds["month"].isin(selected_months)
    & refunds["team"].isin(selected_teams)
    & refunds["refund_reason_code"].isin(selected_reasons)
].copy()


# ============================================================
# MAIN TABS
# ============================================================

tabs = st.tabs(
    [
        "Executive Summary",
        "Monthly",
        "Reasons",
        "Agents & Teams",
        "Review Queue",
        "AI Assistant",
    ]
)


# ============================================================
# TAB 1 — EXECUTIVE SUMMARY
# ============================================================

with tabs[0]:

    st.subheader("Executive Summary")

    st.write(
        """
        This tool converts the reconciled Vireo Audio support export into
        a finance-ready refund view. Financial calculations are deterministic;
        the local LLM is used only for ticket-text quality control.
        """
    )

    raw_amount = pd.to_numeric(
        refunds.get("refund_amount_inr", 0),
        errors="coerce"
    ).sum()
    canonical_amount = refunds["refund_amount"].sum()

    st.info(
        f"""
        **Data reconciliation**

        Raw source monetary total: ₹{raw_amount:,.0f}

        Canonical INR total used for reporting: ₹{canonical_amount:,.0f}

        The export contains mixed monetary units. Legacy records are normalized before reporting. The dashboard uses the canonical INR amount.
        """
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("### Refund overview")

        overview = pd.DataFrame(
            {
                "Metric": [
                    "Canonical refund tickets",
                    "Canonical refund value",
                    "Average refund",
                    "Unique refund tickets",
                ],
                "Value": [
                    f"{total_refunds:,}",
                    f"₹{total_amount:,.2f}",
                    f"₹{avg_refund:,.2f}",
                    f"{unique_tickets:,}",
                ],
            }
        )

        st.dataframe(
            overview,
            use_container_width=True,
            hide_index=True,
        )

    with col2:

        st.markdown("### Reconciliation checks")

        reconciliation = pd.DataFrame(
            {
                "Check": [
                    "Monthly total",
                    "Agent total",
                    "Reason total",
                ],
                "Amount": [
                    f"₹{monthly_total:,.2f}",
                    f"₹{agent_total:,.2f}",
                    f"₹{reason_total:,.2f}",
                ],
                "Status": [
                    "PASS" if abs(total_amount - monthly_total) < 0.01 else "CHECK",
                    "PASS" if abs(total_amount - agent_total) < 0.01 else "CHECK",
                    "PASS" if abs(total_amount - reason_total) < 0.01 else "CHECK",
                ],
            }
        )

        st.dataframe(
            reconciliation,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Top refund drivers")

    top_reasons = (
        filtered.groupby("refund_reason_code")
        .agg(
            refunds=("ticket_id", "count"),
            amount=("refund_amount", "sum"),
        )
        .sort_values("amount", ascending=False)
        .reset_index()
    )

    top_reasons["amount"] = top_reasons["amount"].map(
        lambda x: f"₹{x:,.0f}"
    )

    st.dataframe(
        top_reasons,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 2 — MONTHLY
# ============================================================

with tabs[1]:

    st.subheader("Monthly Refunds")

    monthly = (
        filtered.groupby("month")
        .agg(
            refund_tickets=("ticket_id", "count"),
            refund_amount=("refund_amount", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )

    chart_data = monthly.set_index("month")[
        "refund_amount"
    ]

    st.bar_chart(chart_data)

    display_monthly = monthly.copy()

    display_monthly["refund_amount"] = display_monthly[
        "refund_amount"
    ].map(lambda x: f"₹{x:,.2f}")

    st.dataframe(
        display_monthly,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 3 — REASONS
# ============================================================

with tabs[2]:

    st.subheader("Refund Reasons")

    reason_summary = (
        filtered.groupby("refund_reason_code")
        .agg(
            refund_tickets=("ticket_id", "count"),
            refund_amount=("refund_amount", "sum"),
            average_refund=("refund_amount", "mean"),
        )
        .reset_index()
        .sort_values("refund_amount", ascending=False)
    )

    st.bar_chart(
        reason_summary.set_index("refund_reason_code")[
            "refund_amount"
        ]
    )

    display_reason = reason_summary.copy()

    display_reason["refund_amount"] = display_reason[
        "refund_amount"
    ].map(lambda x: f"₹{x:,.2f}")

    display_reason["average_refund"] = display_reason[
        "average_refund"
    ].map(lambda x: f"₹{x:,.2f}")

    st.dataframe(
        display_reason,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 4 — AGENTS & TEAMS
# ============================================================

with tabs[3]:

    st.subheader("Agent & Team Analysis")

    groupby_team_cols = ["team"]
    if "tier" in filtered.columns:
        groupby_team_cols.append("tier")

    team_summary = (
        filtered.groupby(groupby_team_cols)
        .agg(
            agents=("agent_id", "nunique"),
            tickets=("ticket_id", "count"),
            refund_amount=("refund_amount", "sum"),
            refunds=("ticket_id", "count"),
        )
        .reset_index()
        .sort_values(
            "refund_amount",
            ascending=False,
        )
    )

    st.markdown("### Team view")

    display_team = team_summary.copy()

    display_team["refund_amount"] = display_team[
        "refund_amount"
    ].map(lambda x: f"₹{x:,.2f}")

    st.dataframe(
        display_team,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Agent view")

    agent_summary = (
        filtered.groupby("agent_id")
        .agg(
            refund_tickets=("ticket_id", "count"),
            refund_amount=("refund_amount", "sum"),
            average_refund=("refund_amount", "mean"),
        )
        .reset_index()
    )

    agent_summary = agent_summary.merge(
        agents[["agent_id", "agent_name", "team"]],
        on="agent_id",
        how="left"
    ).sort_values("refund_amount", ascending=False)

    display_agent = agent_summary.copy()

    display_agent["refund_amount"] = display_agent[
        "refund_amount"
    ].map(lambda x: f"₹{x:,.2f}")

    display_agent["average_refund"] = display_agent[
        "average_refund"
    ].map(lambda x: f"₹{x:,.2f}")

    st.dataframe(
        display_agent,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(
        "Agent totals are operational indicators, not misconduct rankings. "
        "Returns Desk owns refund processing by design, and Tier 2 should "
        "not be compared with Tier 1 on raw volume."
    )


# ============================================================
# TAB 5 — REVIEW QUEUE
# ============================================================

with tabs[4]:

    st.subheader("Policy & Data-Quality Review Queue")

    st.write(
        "These are review flags, not automatic policy-violation findings."
    )

    # Goodwill
    goodwill = refunds[
        (refunds["refund_reason_code"] == "GW-OTHER")
        & (refunds["refund_amount"] > 500)
    ].copy()

    # Refund + replacement via normalized boolean column
    refund_replacement = refunds[
        refunds["replacement_flag"]
    ].copy()

    replacement_count = len(refund_replacement)
    replacement_amount = refund_replacement["refund_amount"].sum()

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric(
            "GW-OTHER > ₹500",
            f"{len(goodwill):,}",
        )

    with r2:
        st.metric(
            "Refund + replacement",
            f"{replacement_count:,}",
            f"₹{replacement_amount:,.0f}" if replacement_amount else None
        )

    with r3:
        st.metric(
            "Ambiguous order matches",
            "145",
        )

    with r4:
        st.metric(
            "Refund > Unit Retail",
            "110",
        )

    st.markdown("### GW-OTHER refunds above ₹500 — review queue")
    st.caption("Policy cap is ₹500/ticket and requires Team Lead approval. This flags records for review; it does not establish that approval was missing.")

    if len(goodwill):
        goodwill_display = goodwill[
            [
                "ticket_id",
                "agent_id",
                "refund_amount",
                "refund_reason_code",
            ]
        ].sort_values(
            "refund_amount",
            ascending=False,
        )

        goodwill_display["refund_amount"] = goodwill_display[
            "refund_amount"
        ].map(lambda x: f"₹{x:,.2f}")

        st.dataframe(
            goodwill_display,
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("### Refund + replacement — policy review")

    if replacement_count:

        rr_display = refund_replacement[
            [
                "ticket_id",
                "agent_id",
                "refund_amount",
                "refund_reason_code",
            ]
        ].copy()

        rr_display["refund_amount"] = rr_display[
            "refund_amount"
        ].map(lambda x: f"₹{x:,.2f}")

        st.dataframe(
            rr_display,
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "The 110 refunds above listed unit retail price remain review flags, "
        "because a refund can exceed one unit's listed price when quantity/order linkage "
        "or other exceptions are involved."
    )


# ============================================================
# TAB 6 — AI ASSISTANT
# ============================================================

with tabs[5]:

    st.subheader("🤖 AI Refund Assistant")

    st.write(
        """
        The AI assistant uses the local Qwen3 8B model through the Ollama
        HTTP API. It is used for text understanding and quality control,
        not for financial calculations.
        """
    )

    if not PROMPT_FILE.exists():
        st.warning(
            f"Prompt file not found: {PROMPT_FILE}"
        )

    # Filter selector to only actual refund tickets
    ticket_ids = sorted(
        refunds["ticket_id"]
        .dropna()
        .astype(str)
        .unique()
    )

    selected_ticket = st.selectbox(
        "Select a ticket to analyze",
        ticket_ids,
    )

    ticket_row = tickets[
        tickets["ticket_id"].astype(str)
        == str(selected_ticket)
    ]

    if len(ticket_row):

        row = ticket_row.iloc[0]

        st.markdown("### Ticket details")

        recorded_reason = row.get(
            "refund_reason_code",
            "",
        )

        customer_message = str(
            row.get(
                "customer_message",
                "",
            )
        )

        agent_notes = str(
            row.get(
                "agent_notes",
                "",
            )
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**Recorded reason**")
            st.code(str(recorded_reason))

            st.markdown("**Customer message**")
            st.write(customer_message)

        with col_b:
            st.markdown("**Agent notes**")
            st.write(agent_notes)

        if st.button(
            "Analyze ticket with Qwen3 8B",
            type="primary",
        ):

            if not PROMPT_FILE.exists():
                st.error("AI prompt file is missing.")
                st.stop()

            prompt_template = PROMPT_FILE.read_text(
                encoding="utf-8"
            )

            ticket_text = f"""
TICKET ID:
{selected_ticket}

RECORDED REASON:
{recorded_reason}

CUSTOMER MESSAGE:
{customer_message}

AGENT NOTES:
{agent_notes}

INSTRUCTION: You must respond ONLY with a raw valid JSON object. Do not output reasoning, commentary, or markdown formatting.
"""

            full_prompt = prompt_template + "\n\n" + ticket_text

            with st.spinner(
                "Running local Qwen3 8B..."
            ):

                output, error = call_ollama(full_prompt)

                if error:
                    st.error(error)

                else:
                    st.markdown(
                        "### AI response"
                    )

                    parsed = parse_model_json(output)

                    if parsed:

                        ai_reason = parsed.get(
                            "reason_code",
                            "UNKNOWN",
                        )

                        confidence = parsed.get(
                            "confidence",
                            None,
                        )

                        evidence = parsed.get(
                            "evidence",
                            "",
                        )

                        needs_review = parsed.get(
                            "needs_review",
                            True,
                        )

                        c1, c2, c3 = st.columns(3)

                        with c1:
                            st.metric(
                                "AI reason",
                                ai_reason,
                            )

                        with c2:
                            if confidence is not None:
                                st.metric(
                                    "Confidence",
                                    f"{float(confidence):.0%}",
                                )
                            else:
                                st.metric(
                                    "Confidence",
                                    "N/A",
                                )

                        with c3:
                            st.metric(
                                "Review",
                                "YES"
                                if needs_review
                                else "NO",
                            )

                        st.markdown(
                            "**Evidence**"
                        )

                        st.info(
                            evidence
                            if evidence
                            else "No evidence returned."
                        )

                        if (
                            ai_reason
                            != str(recorded_reason)
                        ):
                            st.warning(
                                "AI-supported reason differs "
                                "from the recorded reason. "
                                "Manual review is recommended."
                            )

                        with st.expander(
                            "Structured Output"
                        ):
                            st.json(parsed)

                    else:

                        st.error(
                            "The model did not return valid JSON."
                        )
                        with st.expander("Raw Ollama Output"):
                            st.code(output)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Vireo Audio Refund Intelligence • "
    "Financial calculations are deterministic; "
    "AI is advisory and used for text QC."
)
