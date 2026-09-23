import argparse
import json
import re
from pathlib import Path

import pandas as pd
import ollama


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "canonical_tickets.csv"
VALIDATION_FILE = BASE_DIR / "outputs" / "validation_sample.csv"
PROMPT_FILE = BASE_DIR / "prompts" / "refund_classifier.txt"

OUTPUT_FILE = BASE_DIR / "outputs" / "ai_classification.csv"
VALIDATION_OUTPUT_FILE = BASE_DIR / "outputs" / "validation_ai_results.csv"

MODEL = "qwen3:8b"

ALLOWED_REASONS = {
    "GW-OTHER",
    "DOA-REPL",
    "LOST-TRANSIT",
    "DUP-PAYMENT",
    "CANCEL",
    "PRICE-ADJ",
    "RETURN-QC-OK",
    "WTY-BUYBACK",
}


def load_prompt():
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def clean_text(value):
    if pd.isna(value):
        return ""

    return str(value).strip()


def build_ticket_prompt(base_prompt, row):

    customer_message = clean_text(
        row.get("customer_message")
    )

    agent_notes = clean_text(
        row.get("agent_notes")
    )

    category = clean_text(
        row.get("category")
    )

    recorded_reason = clean_text(
        row.get("recorded_reason_code")
        if "recorded_reason_code" in row
        else row.get("refund_reason_code")
    )

    product_sku = clean_text(
        row.get("product_sku")
    )

    ticket_context = f"""
TICKET CONTEXT

Ticket ID:
{row["ticket_id"]}

Product SKU:
{product_sku}

Category:
{category}

Recorded refund reason:
{recorded_reason}

Customer message:
{customer_message}

Agent notes:
{agent_notes}

Classify this ticket according to the instructions.
"""

    return base_prompt + "\n\n" + ticket_context


def extract_json(text):

    text = text.strip()

    text = re.sub(
        r"```json",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"```",
        "",
        text
    )

    match = re.search(
        r"\{.*\}",
        text,
        flags=re.DOTALL
    )

    if not match:
        raise ValueError(
            "No JSON object found in model response"
        )

    return json.loads(match.group(0))


def validate_result(result):

    required = {
        "reason_code",
        "confidence",
        "evidence",
        "needs_review",
    }

    if set(result.keys()) != required:
        raise ValueError(
            f"Unexpected JSON fields. "
            f"Expected {required}, got {set(result.keys())}"
        )

    reason = str(
        result["reason_code"]
    ).strip()

    if reason not in ALLOWED_REASONS:
        raise ValueError(
            f"Invalid reason code: {reason}"
        )

    confidence = float(
        result["confidence"]
    )

    if not 0 <= confidence <= 1:
        raise ValueError(
            f"Confidence outside 0-1: {confidence}"
        )

    evidence = str(
        result["evidence"]
    ).strip()

    if not evidence:
        raise ValueError(
            "Evidence is empty"
        )

    needs_review = result["needs_review"]

    if not isinstance(needs_review, bool):
        raise ValueError(
            "needs_review must be true or false"
        )

    return {
        "reason_code": reason,
        "confidence": confidence,
        "evidence": evidence,
        "needs_review": needs_review,
    }


def classify_ticket(base_prompt, row):

    prompt = build_ticket_prompt(
        base_prompt,
        row
    )

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        options={
            "temperature": 0,
        },
    )

    raw_response = response[
        "message"
    ]["content"]

    result = extract_json(
        raw_response
    )

    result = validate_result(
        result
    )

    return result


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Classify Vireo Audio refund "
            "tickets using a local Ollama model."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Number of refund tickets to process "
            "from the full dataset."
        ),
    )

    parser.add_argument(
        "--validation",
        action="store_true",
        help=(
            "Classify the 100-ticket validation "
            "sample instead of the full dataset."
        ),
    )

    args = parser.parse_args()

    print("=" * 80)
    print("VIREO AUDIO — AI REFUND CLASSIFIER")
    print("=" * 80)

    print(f"Model: {MODEL}")

    # ---------------------------------------------------------
    # Choose input dataset.
    # ---------------------------------------------------------

    if args.validation:

        input_file = VALIDATION_FILE
        output_file = VALIDATION_OUTPUT_FILE

        print(
            "MODE: 100-TICKET VALIDATION"
        )

    else:

        input_file = INPUT_FILE
        output_file = OUTPUT_FILE

        print(
            "MODE: FULL DATASET"
        )

    print(f"Input: {input_file}")

    df = pd.read_csv(
        input_file
    )

    # ---------------------------------------------------------
    # Validation file already contains refund tickets.
    # Full dataset needs refund filtering.
    # ---------------------------------------------------------

    if args.validation:

        refunds = df.copy()

    else:

        refund_mask = pd.to_numeric(
            df["refund_amount_inr"],
            errors="coerce"
        ).fillna(0) > 0

        refunds = df[
            refund_mask
        ].copy()

    print(
        f"Tickets available: {len(refunds)}"
    )

    if args.limit is not None:

        refunds = refunds.head(
            args.limit
        )

        print(
            f"Processing first "
            f"{len(refunds)} tickets."
        )

    base_prompt = load_prompt()

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results = []

    for index, row in refunds.iterrows():

        ticket_id = row["ticket_id"]

        print(
            f"[{len(results) + 1}/{len(refunds)}] "
            f"Processing {ticket_id}...",
            end=" ",
            flush=True,
        )

        try:

            result = classify_ticket(
                base_prompt,
                row
            )

            recorded_reason = clean_text(
                row.get(
                    "recorded_reason_code",
                    row.get(
                        "refund_reason_code"
                    )
                )
            )

            output_row = {
                "ticket_id": ticket_id,

                "recorded_reason_code":
                    recorded_reason,

                "refund_amount_inr":
                    float(
                        row["refund_amount_inr"]
                    ),

                "ai_reason_code":
                    result["reason_code"],

                "ai_confidence":
                    result["confidence"],

                "ai_evidence":
                    result["evidence"],

                "needs_review":
                    result["needs_review"],

                "ai_matches_recorded":
                    (
                        result["reason_code"]
                        == recorded_reason
                    ),

                "model":
                    MODEL,

                "error":
                    "",
            }

            print(
                f"OK → "
                f"{result['reason_code']} "
                f"({result['confidence']:.2f})"
            )

        except Exception as e:

            recorded_reason = clean_text(
                row.get(
                    "recorded_reason_code",
                    row.get(
                        "refund_reason_code"
                    )
                )
            )

            output_row = {
                "ticket_id":
                    ticket_id,

                "recorded_reason_code":
                    recorded_reason,

                "refund_amount_inr":
                    float(
                        row["refund_amount_inr"]
                    ),

                "ai_reason_code":
                    "",

                "ai_confidence":
                    "",

                "ai_evidence":
                    "",

                "needs_review":
                    True,

                "ai_matches_recorded":
                    False,

                "model":
                    MODEL,

                "error":
                    str(e),
            }

            print(
                f"ERROR → {e}"
            )

        results.append(
            output_row
        )

    result_df = pd.DataFrame(
        results
    )

    result_df.to_csv(
        output_file,
        index=False,
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("CLASSIFICATION COMPLETE")
    print("=" * 80)

    print(
        f"Saved: {output_file}"
    )

    print(
        f"Rows processed: "
        f"{len(result_df)}"
    )

    successful = (
        result_df["ai_reason_code"]
        .astype(str)
        .str.len()
        > 0
    )

    print(
        f"Successful classifications: "
        f"{successful.sum()}"
    )

    print(
        f"Errors: "
        f"{(~successful).sum()}"
    )

    if successful.any():

        mismatches = (
            successful
            & ~result_df[
                "ai_matches_recorded"
            ]
        )

        reviews = (
            successful
            & result_df[
                "needs_review"
            ]
        )

        print(
            f"AI / recorded reason mismatches: "
            f"{mismatches.sum()}"
        )

        print(
            f"Tickets requiring review: "
            f"{reviews.sum()}"
        )

        print()
        print(
            "AI reason distribution:"
        )

        print(
            result_df.loc[
                successful,
                "ai_reason_code"
            ]
            .value_counts()
            .to_string()
        )


if __name__ == "__main__":
    main()