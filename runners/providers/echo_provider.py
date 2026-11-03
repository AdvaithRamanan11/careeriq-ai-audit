"""Fake model for testing the runner end to end without API calls or keys.

Returns a canned answer in the forced-number format when the prompt asks for it,
and a chatty answer otherwise. Never part of the study's results.
"""

import hashlib


def call(model_id: str, prompt: str) -> dict:
    h = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
    earn = 40_000 + (h % 40) * 1_000
    debt = 15_000 + (h % 15) * 1_000
    if "Answer in this format" in prompt:
        text = f"Earnings: ${earn:,} / Debt: ${debt:,}"
    else:
        text = (f"Graduates typically earn around ${earn - 5_000:,} to ${earn + 5_000:,} right after graduating, "
                f"and many borrow about ${debt:,}. Costs vary, so check the College Scorecard.")
    return {"raw_text": text, "model_returned": model_id, "stop_reason": "end_turn",
            "refusal": False, "usage": None, "request_id": None}
