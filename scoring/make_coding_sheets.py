"""
Step 8: build the hand-coding sheets for real-student (R) answers (rules: scoring/codebook.md).

Outputs (in <runs-dir>/coding/):
  R_primary.csv          every R answer, shuffled, chatbot names hidden; primary coder fills all columns
  R_second_coder.csv     50 random answers from the same pool; second coder fills caveat + source_type only
  KEY_do_not_open.csv    answer_id -> chatbot, profile; open only after coding is finished

Shuffling and the 50-answer draw use seed 2026, so the sheets can be rebuilt identically.
This script refuses to overwrite sheets that already exist, so coding work can't be lost.

Usage: python scoring/make_coding_sheets.py [--runs-dir runs]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import REPO  # noqa: E402

SEED = 2026
N_SECOND = 50
PRIMARY_COLS = ["earnings_number", "earnings_value", "earnings_low", "earnings_high",
                "debt_number", "debt_value", "debt_low", "debt_high",
                "gives_range", "caveat_uncertainty", "caveat_factor", "caveat_official", "source_type", "source_text",
                "source_verified", "verification_notes", "coder_notes"]
SECOND_COLS = ["caveat", "source_type", "coder_notes"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", type=Path, default=REPO / "runs")
    args = ap.parse_args()
    args.runs_dir = args.runs_dir.resolve()
    out_dir = args.runs_dir / "coding"
    if (out_dir / "R_primary.csv").exists():
        raise SystemExit(f"{out_dir / 'R_primary.csv'} already exists. Not overwriting coding work.")

    rows = []
    for f in sorted(args.runs_dir.glob("*.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            if r["prompt_type"] == "R" and r.get("final"):
                rows.append(r)
    if not rows:
        raise SystemExit(f"No final R answers found in {args.runs_dir}")
    df = pd.DataFrame(rows).sort_values(["contestant", "profile_id"]).reset_index(drop=True)
    rng = np.random.default_rng(SEED)
    df = df.iloc[rng.permutation(len(df))].reset_index(drop=True)
    df["answer_id"] = [f"A{i + 1:04d}" for i in range(len(df))]

    out_dir.mkdir(parents=True, exist_ok=True)
    df[["answer_id", "contestant", "model_returned", "profile_id", "status"]].to_csv(
        out_dir / "KEY_do_not_open.csv", index=False, lineterminator="\n")

    sheet = df[["answer_id", "prompt_text", "raw_text"]].rename(columns={"raw_text": "answer_text"})
    for c in PRIMARY_COLS:
        sheet[c] = ""
    sheet.to_csv(out_dir / "R_primary.csv", index=False, lineterminator="\n")

    second_ids = sorted(rng.choice(sheet.answer_id, size=min(N_SECOND, len(sheet)), replace=False))
    second = sheet[sheet.answer_id.isin(second_ids)][["answer_id", "prompt_text", "answer_text"]].copy()
    for c in SECOND_COLS:
        second[c] = ""
    second.to_csv(out_dir / "R_second_coder.csv", index=False, lineterminator="\n")
    print(f"{len(sheet)} R answers -> {out_dir.relative_to(REPO)}/R_primary.csv; "
          f"{len(second)} -> R_second_coder.csv; key in KEY_do_not_open.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
