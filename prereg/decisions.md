# Decisions log

Every methods choice made before the preregistration goes here with its reason. Each entry is marked **Decided** (Advaith signed off) or **Open** (still needs a decision). The preregistration is drafted from this file. Former proposal numbers (P#) are kept in brackets so earlier notes still make sense.

## Decided

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-11-02 | A 4-year school with no admission rate goes in **Open admission** if Scorecard's `OPENADMP` = 1 (open admissions policy). Otherwise (`OPENADMP` = 2 or blank) it is **excluded**. | CareerIQ gives these schools tier 3 by default, which would wrongly put open-admission schools in "Above average." Of 270 four-year CareerIQ schools with no rate, 186 have `OPENADMP` = 1 and 84 are excluded. |
| D2 | 2026-11-02 | Answer-key release: field-of-study file `_10152026`, institution file `_11022026`, checksums in `data/raw/MANIFEST.json`. | Pins the exact release so results can be reproduced. |
| D3 | 2026-11-02 | Each chatbot is represented by the API model closest to its **free consumer app's default**: what a student actually gets. | The study is about the advice students get. Most students use the free apps. |
| D4 [P1] | 2026-11-02 | **Debt answer key** = `DEBT_ALL_STGP_EVAL_MDN` (median federal loans borrowed at this school). `DEBT_ALL_STGP_ANY_MDN` (loans from any school) is a sensitivity check. | The question asks about debt from attending *this* school. |
| D5 [P2] | 2026-11-02 | **School groups** use CareerIQ's own `tier` and `schoolType` from `colleges.json` at the baseline commit. | That's how CareerIQ sees each school. **0 of 1,522** four-year schools have a tier that differs from the Nov 2 admission rate, so this changes no group. |
| D6 [P3] | 2026-11-02 | **Community-college profiles are associate's rows. Four-year-group profiles are bachelor's rows.** | Matches what each school type mainly awards. |
| D7 [P4] | 2026-11-02 | **Crosswalk:** only rows marked `proposed`, plus the `judgment` rows Advaith approves, go into the sample (`crosswalk/review_sheet.csv`). | Every mapping is reviewed before sampling (PRD step 2). |
| D8 [P5] | 2026-11-02 | **Elite Texas shortfall:** only 4 usable Elite Texas rows exist. Take what exists and document the shortfall. | The PRD says "where enough exist." |
| D9 [P6] | 2026-11-02 | **Earnings bands:** rank every field nationally (all 4-digit CIPs at that credential level) by `EARN_MDN_1YR_NAT` and split into thirds, separately for associate's and bachelor's. Bachelor's: bottom ≤ $40,871 < middle ≤ $55,930 < top. Associate's: bottom ≤ $34,704 < middle ≤ $44,660 < top. | Doesn't depend on crosswalk choices. Gives community colleges all three bands. |
| D10 [P7] | 2026-11-02 | **At most one profile per school within a cell.** Aim for 5 Texas + 5 non-Texas per cell, and fill a short side from the other. | Keeps one big school from supplying several profiles in a cell. |
| D11 [P9] | 2026-11-02 | **Models:** ChatGPT = `gpt-5.6-luna`, Gemini = `gemini-3.5-flash-lite`, Claude = `claude-sonnet-5-5` (sources in `runners/models.json`). **Condition: before the full run, Advaith confirms in each free app which model it shows.** If an app shows something different, this entry gets updated before any data is collected. | Follows D3. Limitations to report: Gemini's free "Auto" mode sometimes routes to bigger models, which the API can't copy. OpenAI's own pages disagree (one release note says "GPT-6 Luna"). |
| D12 [P10] | 2026-11-02 | **Call settings:** one user message, no system prompt, no tools (so no web search), provider defaults for sampling and reasoning. Claude's API requires `max_tokens`, set to 16,000. **Claude's automatic refusal fallback is off.** | PRD "Settings." Refusals are a result, not something to paper over with another model. |
| D14 [P8, O1] | 2026-11-02 | **No field cap.** The sample is a pure random draw within each cell, as in the PRD. | With the final crosswalk, the uncapped sample has 42 fields across 11 of CareerIQ's 12 majors, and no field is over 10% of profiles. A cap of 3 would cut nursing from 11 profiles to 4, weakening H5, which tests nursing as a compressed-pay field. Trade-off to report: the Community college × Top cell is all nursing, which reflects the data, since nursing is the top-earning associate's field. |
| D15 [O2] | 2026-11-02 | **Crosswalk rule:** map a field only to a CareerIQ job that the official NCES/BLS CIP-to-SOC crosswalk links to it, in a CareerIQ major that fits the field. If several are linked, use the one most typical for new graduates. If none is linked, exclude the field. Applied to all 29 judgment rows (26 approved, 3 excluded), and Advaith accepted every recommendation. Result: 59 mapped fields, all officially linked. Planned crosswalk sensitivity checks: psychology (4201/4227/4228) with market_researcher and hr_specialist, economics (4506) with financial_analyst, and business (5201/5202) with management_consultant. | Keeps the mapping from resting on anyone's taste, and every mapping can be checked against a federal source. |
| D13 [P11] | 2026-11-02 | **Pilot set:** the first profile from 10 of the 15 cells, picked with seed 2026. Pilot answers go to `runs/pilot/` and are **not** used in the analysis. | Tests the pipeline across school types and bands without using pilot answers as data. |

## Open

| # | Question | Status |
|---|---|---|
| O3 | **Final hypothesis thresholds (H1–H4)** for the preregistration. | Draft in step 6, before filing on OSF. |
| O4 | **Second coder:** who codes 50 R answers independently? | Advaith to find someone (PRD open question). |

## API cost estimate (checked 2026-11-02, to confirm after the pilot)

Each chatbot gets 640 calls: 150 profiles × 4, plus the 40 pilot calls. Each prompt is about 60 input tokens. As a **cautious guess**, assume 2,000 output tokens per call, counting any hidden reasoning tokens. That's roughly double a typical answer.

| Chatbot | Model | Output price / 1M | Estimated cost |
|---|---|---|---|
| ChatGPT | gpt-5.6-luna | $1.20 | ~$1.50 |
| Gemini | gemini-3.5-flash-lite | $2.50 | ~$3.20 |
| Claude | claude-sonnet-5-5 | $10.00 | ~$12.80 |
| **Total** | | | **~$17.50**. Suggested budget: **$30**, to cover retries |

Input costs are under $0.10 total. The pilot logs real token counts, so the estimate gets redone from those before the full run. Price sources: OpenAI's [GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna), [Gemini API pricing](https://aistudio.google.com/docs/pricing), and Anthropic's published API pricing for Sonnet 5.5.

## Facts found in the data that the write-up must mention

- **Debt is a borrowers-only median.** `DEBT_ALL_STGP_EVAL_MDN` is the median among graduates who took federal Direct Loans. It leaves out students who borrowed nothing, private loans, Parent PLUS loans, and capitalized interest. Scorecard's documentation says the figure "may often be lower than the amount owed upon completion." A chatbot that answers "the average graduate owes X," counting non-borrowers as $0, is answering a different question. This belongs in the rubric discussion and the limitations.
- **$27,000 is the most common median-debt value.** That's the federal Direct Loan cap for dependent undergraduates, so the answer key tends to top out there. CareerIQ's estimate (full net price × years) has no such cap. That's directly relevant to H7.
- **The earnings cohorts are older than they sound.** 1-year earnings cover AY2020-21 and AY2021-22 graduates, measured in CY2022–23 and inflation-adjusted to 2024 dollars. 5-year earnings cover AY2016-17 and AY2017-18 graduates.
- **Earnings exclude** graduates enrolled in school during the measurement year (e.g. med school, law school) and those who weren't working. This matters for pre-professional majors like biology, psychology and political science.
- **Fields are 4-digit CIP codes,** so related programs at one school are pooled.
