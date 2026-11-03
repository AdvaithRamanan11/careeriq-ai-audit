# CareerIQ AI-Advice Audit

Do AI chatbots give students accurate earnings and debt numbers for a specific college and major?

This study asks ChatGPT, Gemini, Claude, and [CareerIQ](https://github.com/AdvaithRamanan11/CareerIQ) the same questions about 150 school-and-major profiles. It then scores every answer against the U.S. Department of Education's College Scorecard field-of-study data, which reports what graduates of that exact program actually earned and borrowed.

The point is an honest test. If CareerIQ loses, that result gets reported and the tool gets fixed.

**Status:** in progress (Nov 2026). Methods will be preregistered on OSF before the full data collection run.

## Repo layout

```
lib/common.py           shared paths, the pinned CareerIQ commit, Scorecard loaders
data/download_data.py   downloads the Scorecard files (step 1)
data/raw/               the downloaded files (not in git, except MANIFEST.json)
data/processed/         profiles.csv, careeriq_estimates.csv
crosswalk/              cip_to_job.csv: Scorecard field codes -> CareerIQ jobs
prompts/                prompt templates, versioned (v1, v2, ...)
runs/                   raw chatbot responses, one JSONL file per model
scoring/                number extraction, rubric, manual coding sheets
analysis/               notebook and figures
prereg/                 preregistration text and the decisions log
paper/                  write-up drafts
```

## Setup

Requires Python 3.12 or later.

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows (Git Bash). On Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python data/download_data.py
```

The download is about 60 MB zipped and 360 MB unzipped. No API key is needed for the bulk files.

CareerIQ is tested at commit `ba51be3`. The scripts expect a checkout of it next to this repo, or wherever `CAREERIQ_DIR` points:

```bash
git clone https://github.com/AdvaithRamanan11/CareerIQ.git ../careeriq-baseline
git -C ../careeriq-baseline checkout ba51be37645409c929167b56d311d10902cbce98
```

The scripts refuse to run if that checkout is at any other commit.

## Data: the answer key

**Source:** [College Scorecard](https://collegescorecard.ed.gov/data/), U.S. Department of Education.

| File | Release | Notes |
|---|---|---|
| Most Recent Data by Field of Study | `Most-Recent-Cohorts-Field-of-Study_10152026.zip` (Oct 15, 2026) | The answer key |
| Most Recent Institution-Level Data | `Most-Recent-Cohorts-Institution_11022026.zip` (Nov 2, 2026) | Admission rate, open-admission flag |
| Data dictionary | `CollegeScorecardDataDictionary.xlsx`, downloaded Nov 2, 2026 | Column names checked against this |
| Field of study technical documentation | `FieldOfStudyDataDocumentation.pdf`, "Version: October 2026" | Methods and limitations |
| NCES/BLS CIP 2020 to SOC 2018 crosswalk | `CIP2020_SOC2018_Crosswalk.xlsx` ([source](https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56)) | Checks each major-to-job mapping |

The download page said "This data was last updated November 2, 2026" on the day of download. [`data/raw/MANIFEST.json`](data/raw/MANIFEST.json) records each file's exact URL, size, and SHA-256 checksum. Rerunning the script verifies the files still match. If Scorecard ever replaces a file, the script stops with a warning instead of quietly switching releases.

### Columns used (all checked against the official data dictionary)

| Purpose | Column | What it means |
|---|---|---|
| Primary earnings | `EARN_MDN_1YR` | Median earnings 1 year after completing, for graduates working and not enrolled. Covers graduates from AY2020-21 and AY2021-22, measured in CY2022 and CY2023, in 2024 dollars. |
| Secondary earnings | `EARN_MDN_5YR` | The same median 5 years after completing (AY2016-17 and AY2017-18 graduates, 2024 dollars) |
| Earnings bands | `EARN_MDN_1YR_NAT` | National median 1-year earnings for that field and credential |
| Debt (primary) | `DEBT_ALL_STGP_EVAL_MDN` | Median federal Direct Loan debt (Stafford, plus Grad PLUS, which is zero for undergraduates) borrowed at this institution, among graduates who borrowed. Covers AY2022-23 and AY2023-24 completers. |
| Debt (sensitivity) | `DEBT_ALL_STGP_ANY_MDN` | The same median, counting loans from any institution the student attended |
| Keys | `UNITID`, `CIPCODE` (4-digit), `CREDLEV` (2 = associate's, 3 = bachelor's) | One row per school x field x credential |

Suppressed cells are coded `PS` (privacy suppressed) and are excluded.

### Known limits of the answer key

These come from Scorecard's own documentation:

- **Federal-aid students only.** Earnings and debt cover only graduates who received Title IV federal aid, so they may not represent every graduate.
- **Working graduates only.** Earnings leave out graduates who were enrolled in school or not working during the measurement year.
- **Borrowers only, federal loans only.** The debt median covers graduates who took out federal loans. It excludes private and state loans and capitalized interest. Scorecard itself says its debt figures "may often be lower than the amount owed upon completion."
- **One year after graduation is not exactly a "starting salary."**
- **Fields are 4-digit CIP codes.** For example, all of "Computer Science" (11.07) is one field, so different programs at the same school can be pooled together.
