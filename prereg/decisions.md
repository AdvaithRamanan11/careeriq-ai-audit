# Decisions log

Every methods choice made before the preregistration goes here with its reason. Each entry is marked **Decided** (Advaith signed off) or **Proposed** (needs his sign-off). The preregistration is drafted from this file.

## Decided

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-11-02 | A 4-year school with no admission rate goes in **Open admission** if Scorecard's `OPENADMP` = 1 (open admissions policy). Otherwise (`OPENADMP` = 2 or blank) it is **excluded**. | CareerIQ gives these schools tier 3 by default, which would wrongly put open-admission schools in "Above average." Of 270 four-year CareerIQ schools with no rate, 186 have `OPENADMP` = 1 and 84 are excluded. |
| D2 | 2026-11-02 | Answer-key release: field-of-study file `_10152026`, institution file `_11022026`, checksums in `data/raw/MANIFEST.json`. | Pins the exact release so results can be reproduced. |

## Proposed (needs Advaith's sign-off)

| # | Decision | Why | Alternative |
|---|---|---|---|
| P1 | Debt answer key = `DEBT_ALL_STGP_EVAL_MDN` (federal loans borrowed at this school). `DEBT_ALL_STGP_ANY_MDN` (loans from any school) is a sensitivity check. | The question asks about debt from attending *this* school. | Use ANY as primary. It's bigger for transfer students. |
| P2 | School groups use CareerIQ's own `tier` and `schoolType` from `colleges.json` at the baseline commit. | That's how CareerIQ sees each school. A check found **0 of 1,522** four-year schools whose tier differs from the Nov 2 institution file's admission rate, so this choice doesn't change any group. | Recompute from `ADM_RATE` (same result today). |
| P3 | Community-college profiles are **associate's** rows. Four-year-group profiles are **bachelor's** rows. | Matches what each school type mainly awards. Keeps the community-college row comparable. | Allow both credentials in any group. |
| P4 | Crosswalk: only rows marked `proposed` plus the `judgment` rows Advaith approves go into the sample. See `crosswalk/review_sheet.csv`. | — | — |
| P5 | Elite schools: the "about half Texas" target can't be met. There are only 4 usable Elite Texas rows (all at CareerIQ schools). Take what exists and document the shortfall. | The PRD says "where enough exist." | Drop the Texas target for Elite only (same result). |

## Facts found in the data that the write-up must mention

- **Debt is a borrowers-only median.** `DEBT_ALL_STGP_EVAL_MDN` is the median among graduates who took federal Direct Loans. It leaves out students who borrowed nothing, private loans, Parent PLUS loans, and capitalized interest. Scorecard's documentation says the figure "may often be lower than the amount owed upon completion." A chatbot that answers "the average graduate owes X," counting non-borrowers as $0, is answering a different question. This belongs in the rubric discussion and the limitations.
- **$27,000 is the most common median-debt value.** That's the federal Direct Loan cap for dependent undergraduates, and CareerIQ's `calculateLoan` uses the same cap. So the answer key is capped, while CareerIQ's estimate (full net price × years) is not. That's directly relevant to H7.
- **The earnings cohorts are older than they sound.** 1-year earnings cover AY2020-21 and AY2021-22 graduates, measured in CY2022–23 and inflation-adjusted to 2024 dollars. 5-year earnings cover AY2016-17 and AY2017-18 graduates.
- **Earnings exclude** graduates enrolled in school during the measurement year (e.g. med school, law school) and those who weren't working. This matters for pre-professional majors like biology, psychology and political science.
- **Fields are 4-digit CIP codes,** so related programs at one school are pooled.
