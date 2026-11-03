# Decisions log

Every methods choice made before the preregistration goes here with its reason. Each entry is marked **Decided** (Advaith signed off) or **Proposed** (needs his sign-off). The preregistration is drafted from this file.

## Decided

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-11-02 | A 4-year school with no admission rate goes in **Open admission** if Scorecard's `OPENADMP` = 1 (open admissions policy). Otherwise (`OPENADMP` = 2 or blank) it is **excluded**. | CareerIQ gives these schools tier 3 by default, which would wrongly put open-admission schools in "Above average." Of 270 four-year CareerIQ schools with no rate, 186 have `OPENADMP` = 1 and 84 are excluded. |
| D3 | 2026-11-02 | Each chatbot is represented by the API model closest to its **free consumer app's default**: what a student actually gets. Proposed IDs and sources are in `runners/models.json` (see P9). | The study is about the advice students get. Most students use the free apps. |
| D2 | 2026-11-02 | Answer-key release: field-of-study file `_10152026`, institution file `_11022026`, checksums in `data/raw/MANIFEST.json`. | Pins the exact release so results can be reproduced. |

## Proposed (needs Advaith's sign-off)

| # | Decision | Why | Alternative |
|---|---|---|---|
| P1 | Debt answer key = `DEBT_ALL_STGP_EVAL_MDN` (federal loans borrowed at this school). `DEBT_ALL_STGP_ANY_MDN` (loans from any school) is a sensitivity check. | The question asks about debt from attending *this* school. | Use ANY as primary. It's bigger for transfer students. |
| P2 | School groups use CareerIQ's own `tier` and `schoolType` from `colleges.json` at the baseline commit. | That's how CareerIQ sees each school. A check found **0 of 1,522** four-year schools whose tier differs from the Nov 2 institution file's admission rate, so this choice doesn't change any group. | Recompute from `ADM_RATE` (same result today). |
| P3 | Community-college profiles are **associate's** rows. Four-year-group profiles are **bachelor's** rows. | Matches what each school type mainly awards. Keeps the community-college row comparable. | Allow both credentials in any group. |
| P4 | Crosswalk: only rows marked `proposed` plus the `judgment` rows Advaith approves go into the sample. See `crosswalk/review_sheet.csv`. | — | — |
| P6 | **Earnings bands:** rank every field nationally (all 4-digit CIPs at that credential level, not just mapped ones) by `EARN_MDN_1YR_NAT` and split into thirds, done separately for associate's and bachelor's. Bachelor's cutoffs: bottom ≤ $40,871 < middle ≤ $55,930 < top. Associate's: bottom ≤ $34,704 < middle ≤ $44,660 < top. | Doesn't depend on crosswalk choices. Banding within credential gives community colleges all three bands, instead of putting almost every associate's field in "bottom." | Weight fields by number of graduates. Or compute thirds only over mapped fields. |
| P7 | **At most one profile per school within a cell.** Within a cell: 5 Texas + 5 non-Texas when possible, and the short side gets filled from the other. | Keeps one big school from supplying several profiles in a cell. | No school limit. |
| P8 | **Field cap per cell: undecided.** A pure random draw (the PRD default) lets big fields dominate: in the draft, biology is 34 of 150 profiles and Community college × Top is 10 nursing programs. A cap of 3 per field per cell spreads the sample out, but some cells may not fill. Re-run both ways after the crosswalk is final, then decide. | H5 compares error *by field*, which needs several fields. | Keep pure random and report the field mix. |
| P9 | **Models:** ChatGPT = `gpt-5.6-luna`, Gemini = `gemini-3.5-flash-lite`, Claude = `claude-sonnet-5-5` (sources in `runners/models.json`, checked 2026-11-02). **Before the full run, Advaith confirms in each free app** which model it shows. | Follows D3. Caveats: OpenAI's pages disagree (one Oct 7 release note says "GPT-6 Luna"). Gemini's free app uses "Auto," which sends most prompts to Flash-Lite but some to Flash or Pro; the API can't copy that routing, so this is a limitation. No Anthropic page says "Sonnet 5.5 is the Free default" in those words. | — |
| P10 | **Call settings:** one user message, no system prompt, no tools (so no web search), provider defaults for sampling and reasoning. Claude's API requires `max_tokens`, set to 16,000 so answers aren't cut off. **Claude's automatic refusal fallback is off,** because it would quietly answer with a different model; refusals are a result. | PRD "Settings." | — |
| P11 | **Pilot set:** the first profile from 10 of the 15 cells, picked with seed 2026 (`run_chatbots.py --pilot`). Pilot answers go to `runs/pilot/` and are **not** used in the analysis. The full run asks every profile fresh. | Tests the pipeline across school types and bands without using pilot answers as data. | — |
| P5 | Elite schools: the "about half Texas" target can't be met. There are only 4 usable Elite Texas rows (all at CareerIQ schools). Take what exists and document the shortfall. | The PRD says "where enough exist." | Drop the Texas target for Elite only (same result). |

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
- **$27,000 is the most common median-debt value.** That's the federal Direct Loan cap for dependent undergraduates, and CareerIQ's `calculateLoan` uses the same cap. So the answer key is capped, while CareerIQ's estimate (full net price × years) is not. That's directly relevant to H7.
- **The earnings cohorts are older than they sound.** 1-year earnings cover AY2020-21 and AY2021-22 graduates, measured in CY2022–23 and inflation-adjusted to 2024 dollars. 5-year earnings cover AY2016-17 and AY2017-18 graduates.
- **Earnings exclude** graduates enrolled in school during the measurement year (e.g. med school, law school) and those who weren't working. This matters for pre-professional majors like biology, psychology and political science.
- **Fields are 4-digit CIP codes,** so related programs at one school are pooled.
