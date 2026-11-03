"""
Check CareerIQ's estimates against the formula, independently of CareerIQ's code.

1. Recomputes every estimate in Python from colleges.json and salaries.json:
       salary = round(BLS mean wage x school multiplier x area multiplier x 0.62)
       debt   = net price (family income $48k-75k) x program years (2 or 4)
   and reports any profile where it disagrees with the Node run.
2. Prints a worked calculation for three profiles (a community college, an open-
   admission school and an elite school) for Advaith to check by hand.
3. Reproduces the PRD's own example (nursing at Austin Community College).

Usage: python scoring/verify_careeriq.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, load_colleges, load_jobs  # noqa: E402

ENTRY = 0.62          # EXPERIENCE_MULTIPLIERS['Entry'] in src/data/salaries.js
SUBURBAN_NATIONAL = 1.0


def js_round(x: float) -> int:
    # JavaScript Math.round rounds .5 up; Python's round() rounds .5 to even.
    import math
    return math.floor(x + 0.5)


def expected(college: pd.Series, job: pd.Series) -> tuple[int, float]:
    salary = js_round(job.blsBase * college.earningsMultiplier * SUBURBAN_NATIONAL * ENTRY)
    years = 2 if college.schoolType == "2-year" else 4
    debt = max(0, college.netPrice["mid2"] * years)
    return salary, debt


def main() -> int:
    draft = not (PROCESSED / "careeriq_estimates.csv").exists()
    suffix = "_DRAFT" if draft else ""
    est = pd.read_csv(PROCESSED / f"careeriq_estimates{suffix}.csv", dtype={"UNITID": str})
    prof = pd.read_csv(PROCESSED / f"profiles{suffix}.csv", dtype={"UNITID": str, "cip4": str})
    colleges = load_colleges().set_index("UNITID")
    jobs = load_jobs().set_index("job_id")

    bad = 0
    for _, e in est.iterrows():
        s, d = expected(colleges.loc[e.UNITID], jobs.loc[e.job_id])
        if s != e.ciq_salary or d != e.ciq_debt:
            bad += 1
            print(f"MISMATCH {e.profile_id}: Node salary {e.ciq_salary} vs {s}; debt {e.ciq_debt} vs {d}")
    print(f"Independent recomputation: {len(est) - bad} of {len(est)} profiles match exactly.\n")

    merged = prof.merge(est, on=["profile_id", "UNITID", "job_id"])
    picks = [merged[merged.school_group == g].iloc[0] for g in ["Community college", "Open admission", "Elite"]]
    for r in picks:
        c, j = colleges.loc[r.UNITID], jobs.loc[r.job_id]
        print(f"{r.profile_id}  {r.school} ({r.state}), {r.prompt_major}, {r.credential} -> CareerIQ job '{j.job_title}'")
        print(f"  salary = ${j.blsBase:,} (BLS mean, {j.socTitle}) x {c.earningsMultiplier} (school) "
              f"x 1.00 (Suburban, National) x 0.62 (Entry) = ${j.blsBase * c.earningsMultiplier * ENTRY:,.2f} "
              f"-> ${r.ciq_salary:,}")
        print(f"  debt   = ${c.netPrice['mid2']:,} net price/yr ($48k-75k) x {r.program_years} yrs = ${r.ciq_debt:,}")
        print(f"  Scorecard: 1-yr earnings ${r.sc_earn_1yr:,.0f}, median debt ${r.sc_debt_eval:,.0f}\n")

    acc = colleges[colleges.name == "Austin Community College District"]
    if len(acc):
        c = acc.iloc[0]
        s, _ = expected(c, jobs.loc["rn"])
        print(f"PRD example check: nursing at {c['name']}: $101,420 x {c.earningsMultiplier} x 1.00 x 0.62 = ${s:,} "
              f"(PRD says about $55,650)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
