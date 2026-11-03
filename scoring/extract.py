"""
Pull the earnings and debt numbers out of a forced-number (F) answer.

The F prompt asks for "Earnings: $___ / Debt: $___". Models don't always obey, so
this handles the common variants and says when it is unsure:

  "Earnings: $58,000 / Debt: $27,000"      -> 58000, 27000
  "Earnings: $55k-$65k / Debt: $20,000"    -> range 55000-65000 (midpoint 60000), 20000
  "Earnings: $55,000 to $65,000"           -> range, midpoint scored (PRD rubric)
  "Earnings: $1.2 million"                 -> 1200000
  "Debt: $0"                               -> 0
  no labelled number                       -> None, status 'needs_review'

Anything that isn't a clean match gets status 'needs_review' so a person checks
it by hand (PRD step 5: every answer the regex can't parse is reviewed).

Usage as a module: extract(text) -> dict
Self-test: python scoring/extract.py
"""

import re

MONEY = r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k|K|thousand|million|M)?"
RANGE_SEP = r"\s*(?:-|–|—|to)\s*"


def _to_number(num: str, unit: str | None) -> float:
    value = float(num.replace(",", ""))
    if unit in ("k", "K", "thousand"):
        value *= 1_000
    elif unit in ("million", "M"):
        value *= 1_000_000
    return value


def _find(label: str, text: str) -> dict:
    """Find the number (or range) right after 'Earnings:' / 'Debt:'."""
    pat = re.compile(
        rf"\**{label}\**\s*[:：]\s*\**\s*(?:about|around|approximately|~|roughly)?\s*"
        rf"{MONEY}(?:{RANGE_SEP}{MONEY})?",
        re.IGNORECASE,
    )
    matches = list(pat.finditer(text))
    if not matches:
        return {"value": None, "low": None, "high": None, "is_range": False, "n_matches": 0}
    m = matches[0]
    low_unit, high_unit = m.group(2), m.group(4)
    if m.group(3):  # a range
        # "$55-65k": the unit after the second number applies to both
        low = _to_number(m.group(1), low_unit or high_unit)
        high = _to_number(m.group(3), high_unit or low_unit)
        if high < low:
            low, high = high, low
        return {"value": (low + high) / 2, "low": low, "high": high, "is_range": True, "n_matches": len(matches)}
    v = _to_number(m.group(1), low_unit)
    return {"value": v, "low": None, "high": None, "is_range": False, "n_matches": len(matches)}


def extract(text: str) -> dict:
    e = _find("Earnings", text or "")
    d = _find("Debt", text or "")
    reasons = []
    if e["value"] is None:
        reasons.append("no earnings number")
    if d["value"] is None:
        reasons.append("no debt number")
    if e["n_matches"] > 1 or d["n_matches"] > 1:
        reasons.append("more than one labelled number")
    if e["value"] is not None and not 5_000 <= e["value"] <= 500_000:
        reasons.append("earnings outside $5k-$500k")
    if d["value"] is not None and not 0 <= d["value"] <= 500_000:
        reasons.append("debt outside $0-$500k")
    return {
        "earnings": e["value"], "earnings_low": e["low"], "earnings_high": e["high"], "earnings_is_range": e["is_range"],
        "debt": d["value"], "debt_low": d["low"], "debt_high": d["high"], "debt_is_range": d["is_range"],
        "extract_status": "needs_review" if reasons else "ok",
        "extract_notes": "; ".join(reasons),
    }


if __name__ == "__main__":
    cases = [
        ("Earnings: $58,000 / Debt: $27,000", 58000, 27000, "ok"),
        ("**Earnings:** $55,000 / **Debt:** $24,500", 55000, 24500, "ok"),
        ("Earnings: $55k-$65k / Debt: $20,000", 60000, 20000, "ok"),
        ("Earnings: $55,000 to $65,000 / Debt: $25,000 – $30,000", 60000, 27500, "ok"),
        ("Earnings: $55-65k / Debt: $0", 60000, 0, "ok"),
        ("Earnings: about $70,000 / Debt: approximately $30,000", 70000, 30000, "ok"),
        ("Earnings: $ 61,500 / Debt: $ 19,750.", 61500, 19750, "ok"),
        ("I can't give exact figures, but nurses typically earn around $60,000.", None, None, "needs_review"),
        ("Earnings: $60,000 / Debt: varies", 60000, None, "needs_review"),
        ("Earnings: $1.2 million / Debt: $30,000", 1_200_000, 30000, "needs_review"),
    ]
    failed = 0
    for text, e, d, status in cases:
        r = extract(text)
        ok = r["earnings"] == e and r["debt"] == d and r["extract_status"] == status
        failed += not ok
        print(("PASS" if ok else "FAIL"), "|", text, "->", r["earnings"], r["debt"], r["extract_status"], r["extract_notes"])
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    raise SystemExit(1 if failed else 0)
