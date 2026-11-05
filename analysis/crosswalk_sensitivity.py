"""
Robustness 7(d): does CareerIQ's result depend on which job stands in for a major?

For each alternative mapping named in the preregistration, swap the job for the
affected fields, re-run CareerIQ's own code on the 150 profiles, and compare the
median absolute and signed earnings error with the baseline crosswalk, overall and
on the affected profiles only. Debt is unaffected (it doesn't depend on the job).

Alternatives (preregistration section 5, item 7d; decisions D15):
  psychology (CIP 42.01, 42.27, 42.28): psychologist -> market_researcher, and -> hr_specialist
  economics (45.06):                     economist   -> financial_analyst
  business (52.01, 52.02):               operations_manager -> management_consultant

Output: data/processed/careeriq_crosswalk_sensitivity.csv (read by analysis/results.py)

Usage: python analysis/crosswalk_sensitivity.py
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO, load_jobs  # noqa: E402
from scoring.metrics import bootstrap_median, pct_error  # noqa: E402

NODE = Path(r"C:\Program Files\nodejs\node.exe")
ALTERNATIVES = [
    ("psychology -> market_researcher", {"4201", "4227", "4228"}, "market_researcher"),
    ("psychology -> hr_specialist", {"4201", "4227", "4228"}, "hr_specialist"),
    ("economics -> financial_analyst", {"4506"}, "financial_analyst"),
    ("business -> management_consultant", {"5201", "5202"}, "management_consultant"),
]
TMP = PROCESSED / "sensitivity"


def run_careeriq(inp: Path, out: Path) -> None:
    node = NODE if NODE.exists() else "node"
    r = subprocess.run([str(node), str(REPO / "runners" / "run_careeriq.mjs"), str(inp), str(out)],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(r.stderr)


def summarize(label: str, est: pd.DataFrame, profiles: pd.DataFrame, affected: set) -> list:
    d = profiles.merge(est[["profile_id", "ciq_salary", "job_id"]].rename(columns={"job_id": "job_used"}), on="profile_id")
    d["signed"] = pct_error(d.ciq_salary, d.sc_earn_1yr); d["abs"] = np.abs(d.signed)
    rows = []
    for scope, sub in [("all 150", d), ("affected profiles", d[d.cip4.isin(affected)])]:
        m, lo, hi, n = bootstrap_median(sub["abs"]); ms, los, his, _ = bootstrap_median(sub["signed"])
        rows.append({"mapping": label, "scope": scope, "n": n, "median_abs_error": m, "abs_ci_low": lo, "abs_ci_high": hi,
                     "median_signed_error": ms, "signed_ci_low": los, "signed_ci_high": his})
    return rows


def main() -> int:
    jobs = load_jobs().set_index("job_id")
    profiles = pd.read_csv(PROCESSED / "profiles.csv", dtype={"UNITID": str, "cip4": str})
    base = pd.read_csv(PROCESSED / "careeriq_estimates.csv", dtype={"UNITID": str})
    TMP.mkdir(exist_ok=True)
    rows = []
    all_affected = set().union(*(a[1] for a in ALTERNATIVES))
    rows += summarize("baseline crosswalk", base, profiles, all_affected)
    for label, cips, new_job in ALTERNATIVES:
        assert new_job in jobs.index, new_job
        alt = profiles.copy()
        alt.loc[alt.cip4.isin(cips), "job_id"] = new_job
        n_changed = int(alt.cip4.isin(cips).sum())
        inp = TMP / f"input_{new_job}.csv"; out = TMP / f"estimates_{new_job}.csv"
        alt.to_csv(inp, index=False, lineterminator="\n")
        run_careeriq(inp, out)
        est = pd.read_csv(out, dtype={"UNITID": str})
        for r in summarize(label, est, profiles, cips):
            r["profiles_remapped"] = n_changed
            rows.append(r)
        print(f"{label}: {n_changed} profiles remapped ({jobs.loc[new_job, 'job_title']}, BLS ${jobs.loc[new_job, 'blsBase']:,})")
    res = pd.DataFrame(rows)
    res.to_csv(PROCESSED / "careeriq_crosswalk_sensitivity.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 200)
    print(res[["mapping", "scope", "n", "median_abs_error", "median_signed_error"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
