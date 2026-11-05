"""
H5-H7 primary test input (preregistration 1.3, D19): CareerIQ scored on EVERY eligible
school-and-major row at the 80% training schools, not only the 150 profiles.

Steps
  1. Rebuild the eligible pool exactly as the sampler did (data/sample_profiles.eligible_rows).
  2. Keep rows at training schools only (holdout schools are reserved for CareerIQ v2).
  3. Write the input CSV and run CareerIQ's own code on it (runners/run_careeriq.mjs).
  4. Score each row against Scorecard with the same rules as the 150 (scoring/assemble.py).

Outputs
  data/processed/careeriq_all_eligible_input.csv    one row per eligible training row
  data/processed/careeriq_all_eligible_estimates.csv CareerIQ's estimates for them
  data/processed/careeriq_all_eligible_scored.csv   errors; read by analysis/results.py section 6a

Usage: python analysis/careeriq_all_rows.py
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO  # noqa: E402
from data.sample_profiles import eligible_rows  # noqa: E402
from scoring.assemble import CAREERIQ_CPI_MONTH, cpi_factor, load_cpi  # noqa: E402
from scoring.metrics import pct_error  # noqa: E402

NODE = Path(r"C:\Program Files\nodejs\node.exe")
INPUT = PROCESSED / "careeriq_all_eligible_input.csv"
EST = PROCESSED / "careeriq_all_eligible_estimates.csv"
SCORED = PROCESSED / "careeriq_all_eligible_scored.csv"


def main() -> int:
    rows, draft, _ = eligible_rows()
    assert not draft
    hold = pd.read_csv(PROCESSED / "holdout_schools.csv", dtype={"UNITID": str})
    train = set(hold.loc[hold.split == "train", "UNITID"])
    rows = rows[rows.UNITID.isin(train)].copy()
    rows = rows.sort_values(["UNITID", "CIPCODE", "CREDLEV"]).reset_index(drop=True)
    rows.insert(0, "profile_id", [f"E{i + 1:05d}" for i in range(len(rows))])
    cols = ["profile_id", "UNITID", "INSTNM", "state", "school_group", "earnings_band", "ownership",
            "CIPCODE", "CIPDESC", "CREDLEV", "prompt_major", "major_id", "job_id",
            "EARN_MDN_1YR", "EARN_MDN_5YR", "EARN_MDN_1YR_NAT", "DEBT_ALL_STGP_EVAL_MDN", "DEBT_ALL_STGP_ANY_MDN"]
    inp = rows[cols].rename(columns={"CIPCODE": "cip4", "EARN_MDN_1YR": "sc_earn_1yr", "EARN_MDN_5YR": "sc_earn_5yr",
                                     "EARN_MDN_1YR_NAT": "sc_nat_earn_1yr", "DEBT_ALL_STGP_EVAL_MDN": "sc_debt_eval",
                                     "DEBT_ALL_STGP_ANY_MDN": "sc_debt_any"})
    inp.to_csv(INPUT, index=False, lineterminator="\n")
    print(f"Eligible rows at training schools: {len(inp):,} ({inp.UNITID.nunique():,} schools, {inp.cip4.nunique()} fields)")
    print(inp.groupby("school_group").size().to_string())

    node = NODE if NODE.exists() else "node"
    r = subprocess.run([str(node), str(REPO / "runners" / "run_careeriq.mjs"), str(INPUT), str(EST)],
                       capture_output=True, text=True, cwd=REPO)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr); return 1

    est = pd.read_csv(EST, dtype={"UNITID": str})
    d = inp.merge(est[["profile_id", "ciq_salary", "ciq_debt", "ciq_debt_federal_portion", "earnings_multiplier",
                       "bls_base", "program_years"]], on="profile_id", validate="one_to_one")
    f, label = cpi_factor(load_cpi(), *CAREERIQ_CPI_MONTH)
    d["cpi_factor"] = f; d["cpi_month"] = label
    d["earn_signed"] = pct_error(d.ciq_salary, d.sc_earn_1yr)
    d["earn_abs"] = np.abs(d.earn_signed)
    d["earn_signed_adj"] = pct_error(d.ciq_salary, d.sc_earn_1yr * f)
    d["earn_abs_adj"] = np.abs(d.earn_signed_adj)
    d["earn5_signed"] = pct_error(d.ciq_salary, d.sc_earn_5yr)
    d["debt_signed"] = pct_error(d.ciq_debt, d.sc_debt_eval)
    d["debt_abs"] = np.abs(d.debt_signed)
    d["debt_any_signed"] = pct_error(d.ciq_debt, d.sc_debt_any)
    d["debt_fed_signed"] = pct_error(d.ciq_debt_federal_portion, d.sc_debt_eval)
    d["badly_wrong"] = (d.earn_abs > 0.25).astype(float)
    d["ownership_label"] = d.ownership.map({1: "Public", 2: "Private nonprofit"})
    d.to_csv(SCORED, index=False, lineterminator="\n")
    print(f"Scored {len(d):,} rows -> {SCORED.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
