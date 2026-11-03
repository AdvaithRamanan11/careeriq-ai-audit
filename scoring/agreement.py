"""
Step 8: inter-coder agreement (Cohen's kappa) on the 50 double-coded R answers.

Compares the primary coder's ORIGINAL codes with the second coder's, for:
  caveat       (yes / no)
  source_type  (none / generic / specific)
Run this before discussing disagreements (codebook: "Disagreements").

Usage: python scoring/agreement.py [--runs-dir runs]
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import REPO  # noqa: E402
from scoring.metrics import cohens_kappa  # noqa: E402

VALID = {"caveat": {"yes", "no"}, "source_type": {"none", "generic", "specific"}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", type=Path, default=REPO / "runs")
    args = ap.parse_args()
    args.runs_dir = args.runs_dir.resolve()
    d = args.runs_dir / "coding"
    a = pd.read_csv(d / "R_primary.csv", dtype=str).fillna("")
    b = pd.read_csv(d / "R_second_coder.csv", dtype=str).fillna("")
    m = b.merge(a, on="answer_id", suffixes=("_2", "_1"))
    print(f"Double-coded answers: {len(m)}")
    ok = True
    for var, allowed in VALID.items():
        x = m[f"{var}_1"].str.strip().str.lower()
        y = m[f"{var}_2"].str.strip().str.lower()
        bad = m.answer_id[~x.isin(allowed) | ~y.isin(allowed)].tolist()
        if bad:
            print(f"  {var}: missing or invalid codes for {bad[:10]}{'...' if len(bad) > 10 else ''}")
            ok = False
            continue
        k = cohens_kappa(x.tolist(), y.tolist())
        agree = (x == y).mean()
        print(f"  {var}: kappa = {k:.2f}, raw agreement = {agree:.0%}, disagreements = {(x != y).sum()}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
