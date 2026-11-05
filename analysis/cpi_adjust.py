"""
Robustness check (D20): bring Scorecard earnings from "2024 dollars" to the month each
chatbot was asked, using CPI-U.

Scorecard's field-of-study earnings are inflation-adjusted to 2024 dollars (its
documentation: "earnings measured in calendar years 2022 and 2023 were adjusted to
2024 dollars"). A chatbot answering in late 2026 is presumably quoting 2026 dollars.
This script fetches the CPI-U index and writes a factor for each month, so that:

    earnings_in_query_month = EARN_MDN_1YR x CPI(query month) / CPI(2024 annual average)

Series: BLS CPI-U, All items, U.S. city average, not seasonally adjusted,
series ID CUUR0000SA0 (1982-84 = 100). Fetched from the BLS Public Data API v2.
No key is needed for a single series (BLS_API_KEY is used if set).
Debt is NOT adjusted: Scorecard reports debt as nominal dollars disbursed.

For CareerIQ the target is not a query month but May 2025, the OEWS reference period of
the BLS wages in salaries.json (D29: BLS series OEUN000000000000015125204 returns
CareerIQ's $148,100 for 2025 only). Use the 2025-05 row of cpi_u.csv for that.

Output: analysis/cpi_u.csv with columns year, month, cpi, factor_from_2024, fetched_at

Usage: python analysis/cpi_adjust.py
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SERIES = "CUUR0000SA0"
BASE_YEAR = 2024
OUT = Path(__file__).resolve().parent / "cpi_u.csv"


def fetch(start: int, end: int) -> pd.DataFrame:
    body = {"seriesid": [SERIES], "startyear": str(start), "endyear": str(end)}
    key = os.environ.get("BLS_API_KEY")
    if key:
        body["registrationkey"] = key
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS API: {payload.get('status')} {payload.get('message')}")
    rows = payload["Results"]["series"][0]["data"]
    df = pd.DataFrame(rows)
    df = df[df.period.str.startswith("M")]          # M01..M12; M13 is the annual average
    df = df[df.value != "-"]                        # BLS lists months it hasn't published yet as "-"
    df["year"] = df.year.astype(int)
    df["month"] = df.period.str[1:].astype(int)
    df["cpi"] = df.value.astype(float)
    return df[["year", "month", "cpi"]].sort_values(["year", "month"]).reset_index(drop=True)


def main() -> int:
    now = datetime.now(timezone.utc)
    df = fetch(BASE_YEAR, now.year)
    base = df[df.year == BASE_YEAR]
    if len(base) != 12:
        raise SystemExit(f"Expected 12 months of {BASE_YEAR} CPI, got {len(base)}")
    base_avg = base.cpi.mean()
    df["factor_from_2024"] = (df.cpi / base_avg).round(5)
    df["fetched_at"] = now.isoformat(timespec="seconds")
    df.to_csv(OUT, index=False, lineterminator="\n")
    latest = df.iloc[-1]
    print(f"{SERIES}: {BASE_YEAR} annual average = {base_avg:.3f}; "
          f"latest month {int(latest.year)}-{int(latest.month):02d} = {latest.cpi:.3f} "
          f"(factor {latest.factor_from_2024}). Wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
