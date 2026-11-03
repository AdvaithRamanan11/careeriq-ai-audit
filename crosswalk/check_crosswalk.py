"""
Check crosswalk/cip_to_job.csv and build a review sheet for Advaith.

For every mapped field it checks:
  1. the job exists in CareerIQ's MAJORS list (at the pinned baseline) under the stated major
  2. whether the official NCES/BLS CIP-SOC crosswalk links any program in this
     4-digit field to the job's occupation code ("official_link")
  3. how many usable Scorecard rows the field has (associate's and bachelor's)

Output: crosswalk/review_sheet.csv (open in Excel; fill the 'advaith_decision' column)

Usage: python crosswalk/check_crosswalk.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import CIP_SOC_XLSX, REPO, load_colleges, load_jobs, usable_fos  # noqa: E402

CW = REPO / "crosswalk" / "cip_to_job.csv"
OUT = REPO / "crosswalk" / "review_sheet.csv"


def soc_matches(careeriq_soc: str, official_soc: str) -> bool:
    # Two CareerIQ jobs use BLS aggregate codes rather than detailed ones.
    if careeriq_soc == "25-1000":   # Postsecondary Teachers, All
        return official_soc.startswith("25-1")
    if careeriq_soc == "25-2050":   # Special Education Teachers (group)
        return official_soc.startswith("25-205")
    return careeriq_soc == official_soc


def main() -> int:
    cw = pd.read_csv(CW, dtype=str).fillna("")
    jobs = load_jobs()
    colleges = load_colleges()
    fos = usable_fos(colleges)

    problems = []
    if cw.cip4.duplicated().any():
        problems.append(f"Duplicate CIP codes: {cw.cip4[cw.cip4.duplicated()].tolist()}")
    # proposed = clear mapping; judgment = waiting on Advaith; approved = judgment row he accepted;
    # excluded = not sampled.
    valid = {"proposed", "judgment", "approved", "excluded"}
    if not cw.status.isin(valid).all():
        problems.append("Unknown status values: " + str(set(cw.status) - valid))
    if ((cw.status == "approved") & (cw.job_id == "")).any():
        problems.append("Approved rows with no job_id: " + str(cw.cip4[(cw.status == "approved") & (cw.job_id == "")].tolist()))

    official = pd.read_excel(CIP_SOC_XLSX, sheet_name="CIP-SOC", dtype=str)
    official["cip4"] = official.CIP2020Code.str.replace(".", "", regex=False).str[:4]

    job_lookup = jobs.set_index("job_id")
    rows = []
    for _, r in cw.iterrows():
        out = r.to_dict()
        if r.job_id:
            if r.job_id not in job_lookup.index:
                problems.append(f"{r.cip4}: job '{r.job_id}' is not in CareerIQ")
                continue
            j = job_lookup.loc[r.job_id]
            if j.major_id != r.major_id:
                problems.append(f"{r.cip4}: job '{r.job_id}' belongs to major '{j.major_id}', not '{r.major_id}'")
            socs = official.loc[official.cip4 == r.cip4, "SOC2018Code"]
            out.update(job_title=j.job_title, soc=j.socCode, soc_title=j.socTitle,
                       bls_mean_wage=j.blsBase, soc_is_proxy=j.isProxy,
                       official_link="yes" if any(soc_matches(j.socCode, s) for s in socs) else "no")
        sub = fos[fos.CIPCODE == r.cip4]
        name_in_data = sub.CIPDESC.iloc[0] if len(sub) else ""
        if name_in_data and name_in_data != r.cip_name:
            problems.append(f"{r.cip4}: name differs from Scorecard ('{name_in_data}')")
        out.update(usable_assoc=int((sub.CREDLEV == "2").sum()), usable_bach=int((sub.CREDLEV == "3").sum()))
        rows.append(out)

    sheet = pd.DataFrame(rows)
    sheet["advaith_decision"] = ""
    cols = ["cip4", "cip_name", "prompt_major", "status", "major_id", "job_id", "job_title", "official_link",
            "soc", "soc_title", "soc_is_proxy", "bls_mean_wage", "usable_assoc", "usable_bach",
            "notes", "advaith_decision"]
    sheet[cols].to_csv(OUT, index=False)

    # Coverage: how much of the usable data does the crosswalk reach?
    listed = set(cw.cip4)
    mapped = set(cw.loc[cw.job_id != "", "cip4"])
    unlisted = fos[~fos.CIPCODE.isin(listed)]
    print(f"Fields in crosswalk file: {len(cw)}  (proposed {sum(cw.status=='proposed')}, "
          f"judgment {sum(cw.status=='judgment')}, excluded {sum(cw.status=='excluded')})")
    print(f"Fields with a job mapped: {len(mapped)}")
    print(f"Usable rows covered by a mapping: {fos.CIPCODE.isin(mapped).sum():,} of {len(fos):,} "
          f"({fos.CIPCODE.isin(mapped).mean():.0%})")
    print(f"  ...if only 'proposed' rows are kept: "
          f"{fos.CIPCODE.isin(set(cw.loc[cw.status=='proposed','cip4'])).sum():,}")
    print(f"Usable rows in fields not listed at all (all small fields, treated as excluded): "
          f"{len(unlisted):,} across {unlisted.CIPCODE.nunique()} fields; "
          f"largest has {unlisted.CIPCODE.value_counts().max() if len(unlisted) else 0} rows")
    print(f"Mapped jobs with no official CIP-SOC link: "
          f"{sheet.loc[sheet.official_link=='no','cip4'].tolist()}")
    print(f"Wrote {OUT.relative_to(REPO)}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("No problems found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
