"""
Shared helpers: paths, the pinned CareerIQ baseline, and loading Scorecard data.

Every script imports from here, so the filters that define a "usable" row
live in exactly one place.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "raw"
PROCESSED = REPO / "data" / "processed"

# CareerIQ is tested at this exact commit ("data: annual data refresh 2026", Nov 1, 2026).
# Its CI re-fetches data on every push to main, so testing a later commit would test different data.
BASELINE_COMMIT = "ba51be37645409c929167b56d311d10902cbce98"

# Path to a local checkout of github.com/AdvaithRamanan11/CareerIQ at the baseline commit.
# Override with the CAREERIQ_DIR environment variable.
CAREERIQ_DIR = Path(os.environ.get("CAREERIQ_DIR", REPO.parent / "careeriq-baseline"))

FOS_CSV = RAW / "Most-Recent-Cohorts-Field-of-Study.csv"
INST_CSV = RAW / "Most-Recent-Cohorts-Institution.csv"
CIP_SOC_XLSX = RAW / "CIP2020_SOC2018_Crosswalk.xlsx"

# Column names below were checked against CollegeScorecardDataDictionary.xlsx
# (FieldOfStudy_Data_Dictionary sheet) on 2026-11-02.
FOS_COLS = [
    "UNITID", "INSTNM", "CONTROL", "CIPCODE", "CIPDESC", "CREDLEV", "CREDDESC",
    "EARN_MDN_1YR",            # primary answer key: median earnings 1 yr after completing
    "EARN_MDN_5YR",            # secondary: 5 yrs after completing
    "EARN_MDN_1YR_NAT",        # national median for the field x credential (earnings bands)
    "DEBT_ALL_STGP_EVAL_MDN",  # primary debt: median federal loans borrowed at this school
    "DEBT_ALL_STGP_ANY_MDN",   # sensitivity: loans borrowed at any school
]
NUMERIC_FOS = ["EARN_MDN_1YR", "EARN_MDN_5YR", "EARN_MDN_1YR_NAT",
               "DEBT_ALL_STGP_EVAL_MDN", "DEBT_ALL_STGP_ANY_MDN"]
CREDLEV_ASSOC, CREDLEV_BACH = "2", "3"


def check_baseline() -> None:
    """Stop with a clear error if the CareerIQ checkout is not at the pinned commit."""
    if not CAREERIQ_DIR.exists():
        raise SystemExit(
            f"CareerIQ checkout not found at {CAREERIQ_DIR}.\n"
            f"Clone it and pin it:\n"
            f"  git clone https://github.com/AdvaithRamanan11/CareerIQ.git {CAREERIQ_DIR}\n"
            f"  git -C {CAREERIQ_DIR} checkout {BASELINE_COMMIT}"
        )
    head = subprocess.run(["git", "-C", str(CAREERIQ_DIR), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if head != BASELINE_COMMIT:
        raise SystemExit(f"CareerIQ checkout is at {head[:7]}, but the study pins {BASELINE_COMMIT[:7]}.")


def load_colleges() -> pd.DataFrame:
    """CareerIQ's college list (colleges.json at the baseline commit)."""
    check_baseline()
    data = json.loads((CAREERIQ_DIR / "src" / "data" / "colleges.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(data["colleges"])
    return df.rename(columns={"id": "UNITID"})


def load_jobs() -> pd.DataFrame:
    """CareerIQ's 12 majors and 96 jobs, with each job's BLS base wage and SOC code.

    The major -> job structure lives in src/data/salaries.js (MAJORS). The wages and
    SOC codes live in src/data/salaries.json. We read the .js file as text rather
    than running it, which is enough to recover which job belongs to which major.
    """
    check_baseline()
    js = (CAREERIQ_DIR / "src" / "data" / "salaries.js").read_text(encoding="utf-8")
    block = js[js.index("export const MAJORS"):]
    block = block[:block.index("\n]\n") + 2]
    # Layout in the file: a major is "id: '...'," then "name: '...'," on their own lines;
    # each job is one line "{ id: '...', title: '...', blsBase: wage('...') },".
    rows, major_id, major_name = [], None, None
    for line in block.splitlines():
        j = re.search(r"\{\s*id:\s*'([a-z_]+)',\s*title:\s*'([^']+)'", line)
        if j:
            rows.append({"major_id": major_id, "major_name": major_name,
                         "job_id": j.group(1), "job_title": j.group(2)})
            continue
        m = re.fullmatch(r"\s*id:\s*'([a-z_]+)',\s*", line)
        if m:
            major_id = m.group(1)
            continue
        n = re.fullmatch(r"\s*name:\s*'([^']+)',\s*", line)
        if n:
            major_name = n.group(1)
    jobs = pd.DataFrame(rows)
    wages = json.loads((CAREERIQ_DIR / "src" / "data" / "salaries.json").read_text(encoding="utf-8"))["jobs"]
    wages = pd.DataFrame(wages).rename(columns={"jobId": "job_id"})[["job_id", "blsBase", "socCode", "socTitle", "isProxy"]]
    jobs = jobs.merge(wages, on="job_id", how="left", validate="one_to_one")
    assert len(jobs) == 96 and jobs.major_id.nunique() == 12, (len(jobs), jobs.major_id.nunique())
    return jobs


def load_fos() -> pd.DataFrame:
    """Field-of-study rows for associate's and bachelor's degrees, with 'PS' (privacy suppressed) -> NaN."""
    df = pd.read_csv(FOS_CSV, usecols=FOS_COLS, dtype=str)
    df = df[df.CREDLEV.isin([CREDLEV_ASSOC, CREDLEV_BACH])].copy()
    for c in NUMERIC_FOS:
        df[c] = pd.to_numeric(df[c].where(df[c] != "PS"), errors="coerce")
    return df


def usable_fos(colleges: pd.DataFrame | None = None) -> pd.DataFrame:
    """Rows that can be sampled: 1-yr earnings AND median debt present, school in CareerIQ's list."""
    df = load_fos()
    df = df[df.EARN_MDN_1YR.notna() & df.DEBT_ALL_STGP_EVAL_MDN.notna()]
    if colleges is None:
        colleges = load_colleges()
    return df[df.UNITID.isin(set(colleges.UNITID))].copy()
