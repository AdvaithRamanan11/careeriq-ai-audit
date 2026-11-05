# Preregistration: Do AI chatbots give students accurate earnings and debt numbers for a specific college and major?

> **DRAFT, revised 2026-11-04. For Advaith to review before filing on OSF.** Items marked **[CONFIRM]** need his decision. Once filed, this document is frozen. Any later change is logged as a deviation in `prereg/deviations.md` and reported in the write-up.

**Author:** Advaith Ramanan (independent researcher)
**Planned filing:** OSF Registries, by Nov 15, 2026, before the full chatbot data collection. Kept private (embargoed) until the study is complete.
**Code and data:** github.com/AdvaithRamanan11/careeriq-ai-audit, at the commit hash recorded at filing.

---

## 1. Study information

### 1.1 Background

High school students can ask a chatbot what a specific college and major will pay and cost, and get back a confident dollar figure. This study checks those figures against federal data on what graduates of that exact program actually earned and borrowed. It also checks CareerIQ, a free college-ROI tool built by the author in 2025. CareerIQ is included so its errors can be found and fixed, not to promote it. A loss for CareerIQ is a reportable result.

**Prior work and what this study adds.** The closest prior work is the Urban Institute's two-part evaluation (Tyagi, Blagg & Gutierrez, May and October 2026). Urban had subject-matter experts rate 300 responses from GPT-5.2, Claude Sonnet 4.5 and Gemini 3 Flash to 100 curated prompts about education and workforce data, including institution-level earnings and student loans, on a four-point scale. They found that only 16% of responses had no accuracy issues; that 58% of responses to questions about a specific school or institution had critical errors; that more than 60% had significant or critical citation problems, and that citations were not associated with higher accuracy; that models often answered a different question than asked, "defaulting to national trends when asked about specific schools or institutions"; and that caveats were frequently missing. In one example, "a response provided Purdue engineering graduate earnings figures that were tens of thousands of dollars below the actual values reported in the College Scorecard." In the follow-up, connecting Claude Sonnet 4.5 to Urban's data through MCP servers raised the share of responses with no accuracy issues from 16% to 61%, at roughly 12 times the cost per response; Urban also notes that free ChatGPT accounts cannot use custom MCP servers at all.

Urban's authors describe their evaluation as "not a quantitative benchmark": prompts were "deliberately constructed" to surface failure types, scoring was qualitative, and the authors advise against reading the figures as generalizable performance metrics. This study is designed to answer the question Urban's evaluation raises but does not measure:

1. **A single numeric answer key.** Every estimate is scored as a percentage error against College Scorecard's program-level earnings and debt, with bootstrap confidence intervals, rather than rated by experts.
2. **A sampled, program-level test set.** 150 school-and-major profiles are drawn by seeded stratified random sampling from every eligible Scorecard row, not curated. Urban's prompts asked for institution-level figures; this study asks about a specific major at a specific school, which is what a student choosing a program needs.
3. **Equity.** Errors are compared across five school groups ordered by selectivity, plus community colleges, and across three earnings bands (H2). Urban's published results are broken down by task type and by persona (May 2026, pp. 5–7, Figure 1); neither brief reports results by institution type.
4. **Consistency.** Each forced-number prompt is asked three times (H4). Urban scored one response per prompt.
5. **Honesty, quantified.** Caveat rate, source type with every specific source verified, range coverage, and "confident and wrong" are coded with written rules and a second coder (H3), turning Urban's qualitative observations about confidence and citations into rates.
6. **A non-chatbot comparison and a rebuild.** CareerIQ, a formula-based tool, is scored on the same profiles (H5–H7) and then rebuilt to anchor on federal program-level data. Urban showed that direct data access sharply improves chatbot answers but requires MCP connections most students can't use; this study tests whether a free web tool can deliver the same anchoring without any configuration by the student.
7. **Preregistration.** Hypotheses and decision rules are fixed before data collection. Neither Urban brief mentions a preregistration (full-text search of both PDFs, 2026-11-04).

Urban's models "reflect the models a user would likely encounter when interacting with the free versions of ChatGPT, Claude, and Gemini, respectively, as of early 2026" (May 2026, p. 4); this study uses the free-tier defaults of November 2026 (§1.2). Two other sources frame the stakes. OpenAI (March 2026) reports that Americans send nearly 3 million messages a day to ChatGPT about wages, compensation or earnings, and that GPT-5.4, tested against 2024 BLS OEWS median wages at the national and metro level, was "highly accurate" in the observed sample. That evaluation was conducted by the model's maker at the occupation level; this study is independent and at the program level. Bahrami, Cookson & Moss (2026), analyzing 3,060 Chatbot Arena votes on financial questions, find that users prefer confident, actionable advice: the more accurate answer wins only 52.2% of decisive votes, and when one answer contains a serious error and the other is correct, users choose the flawed one 47.8% of the time. If users can't tell a confident wrong answer from a right one, the share of confident-and-wrong answers (§4.2) matters as much as the error rate. Searches of Google Scholar (seven term sets, "since 2023") and SSRN on 2026-11-04 found no study that systematically scores chatbot earnings or debt figures for specific college programs against federal outcome data. The closest are Urban (2026), whose expert-rated evaluation includes individual comparisons with College Scorecard, and OpenAI (2026), which compared occupation-level wages with BLS OEWS. Other related work is listed in `prereg/prior_work.md`, with search terms and dates.

### 1.2 Contestants

| Contestant | How it is queried | Model |
|---|---|---|
| ChatGPT | OpenAI API | `gpt-6-luna` (reasoning effort at the API default, medium) |
| Gemini | Google Gemini API | `gemini-3.5-flash-lite` |
| Claude | Anthropic API | `claude-sonnet-5-5`, effort set to medium (the API default is high) |
| CareerIQ | Its own code at commit `ba51be3` (Nov 1, 2026), run by script | — |

Each chatbot is represented by the API model closest to its **free consumer app's default**. On 2026-11-04 the author opened each free app in a new chat: ChatGPT identified itself as GPT-6 (OpenAI's release notes say Free and Go accounts use GPT-6 Luna), Gemini showed "Gemini Auto (Gemini 3 models)," and Claude showed "Sonnet 5.5" at effort "medium." The ChatGPT entry was changed from `gpt-5.6-luna` to `gpt-6-luna` that day, before any chatbot data was collected (D25). For Gemini, the free app's "Auto" setting routes most prompts to Flash-Lite and some to Flash or Pro (Google's Gemini Apps help page), and the app labels these as "Gemini 3 models," meaning the Gemini 3 generation; `gemini-3.5-flash-lite` is the current Flash-Lite model of that generation in the Gemini API documentation. Google does not state which Flash-Lite version the app runs, so the match is an inference (§7). Sources and the full app-check notes are in `runners/models.json`.

### 1.3 Hypotheses

H1–H4 concern the three chatbots. H5–H7 concern CareerIQ. Each hypothesis gets a pre-set decision rule with three possible outcomes: **supported**, **not supported**, or **inconclusive**. All are tested separately for each relevant contestant. "Error" means percentage error relative to the Scorecard value (§4.2).

| ID | Prediction | Decision rule |
|---|---|---|
| **H1** | Each chatbot's median absolute earnings error is **above 20%**. | Supported if the 95% bootstrap CI of the median lies entirely above 20%. Not supported if it lies entirely below 20%. Otherwise inconclusive. Debt error is reported the same way, with no threshold. |
| **H1b** | Each chatbot's median **signed** earnings error is **above 0**: chatbots overestimate first-year pay. | Supported if the 95% bootstrap CI of the median signed error lies entirely above 0. Not supported if it lies entirely below 0. Otherwise inconclusive. Also reported after the inflation adjustment in 7(e), since the 2024-dollar answer key biases this test toward overestimation by roughly 7%. |
| **H2** | Chatbot error **rises as schools get less selective**, and is **largest for community colleges and open-admission schools**. | (a) Among four-year groups, the Spearman correlation between selectivity rank (Elite 1, Selective 2, Above average 3, Open admission 4) and profile-level absolute earnings error is above 0, with the 95% bootstrap CI excluding 0. (b) Community college and Open admission have the two highest group medians of the five groups. Supported if both (a) and (b) hold. Not supported if (a)'s CI lies entirely at or below 0. Otherwise inconclusive. |
| **H3** | **Fewer than half** of real-student (R) answers give a range or a caveat. | Share of R answers with `gives_range = yes` OR `caveat = yes`. Supported if the 95% Wilson CI upper bound is below 50%. Not supported if the lower bound is above 50%. Otherwise inconclusive. |
| **H4** | The same forced-number prompt asked 3 times **varies by more than 5%**. | Coefficient of variation (CV) of the earnings figure across the 3 runs, per profile. Supported if the 95% bootstrap CI of the median CV across profiles lies entirely above 5%. Not supported if it lies entirely below. Otherwise inconclusive. |
| **H5** | CareerIQ's flat entry discount (0.62 × BLS mean wage) **overestimates high-ceiling fields** (tech: CIP 11.xx and 14.09; finance: 52.08) and **underestimates compressed-pay fields** (nursing: 51.38; education: 13.xx). | Supported if CareerIQ's median signed earnings error is above 0 for high-ceiling fields and below 0 for compressed-pay fields, with both 95% bootstrap CIs excluding 0. Not supported if either CI lies entirely on the wrong side of 0. Otherwise inconclusive. |
| **H6** | CareerIQ's all-majors school multiplier **inflates low-earning majors at high-earning schools**. | Among rows at schools with CareerIQ `earningsMultiplier` > 1.0: the median signed earnings error for the bottom earnings band minus that for the top band is above 0, with the 95% bootstrap CI excluding 0. Not supported if the CI lies entirely at or below 0. Otherwise inconclusive. |
| **H7** | CareerIQ's debt estimate (full net price × program years) **overestimates debt**. | **Primary:** CareerIQ's full estimate (`ciq_debt`) vs. Scorecard's median federal debt. Supported if the median signed debt error is above 0 with the 95% bootstrap CI excluding 0. Not supported if the CI lies entirely at or below 0. Otherwise inconclusive. **Secondary (descriptive, no decision rule):** the part of that estimate CareerIQ treats as federal Direct Loans, min(total loan, $27,000; $12,000 at 2-year schools), vs. the same Scorecard value. This asks whether the overestimate comes only from CareerIQ assuming money is borrowed beyond the federal caps. |

Thresholds (20%, 50%, 5%) are the PRD's starting values, confirmed on 2026-11-04 (D16).

**What prior work suggests about each prediction.** Urban (May 2026) found critical errors in 58% of expert-rated responses about specific institutions, which points in the direction of H1 but does not give a percentage error, so the 20% threshold remains a judgment. H1b (added 2026-11-04, before data collection) rests on a mechanism: OpenAI (2026) reports accurate occupation-level wages, and a chatbot that answers a first-year-pay question with occupation-wide wages across all experience levels should overestimate. The evidence is not one-sided: Urban's one quoted Scorecard comparison (Purdue engineering) was an underestimate, and Scorecard's 2024-dollar earnings make any late-2026 answer look high, which is why H1b is reported both before and after the inflation adjustment. Urban's "scope substitution" finding, that models default to national or aggregate figures when asked about a specific institution, is the mechanism behind H2: a chatbot that falls back on national or well-known-school figures should be further off for less-selective and less-documented schools. Urban found caveats "frequently missing" and only 26% of baseline Claude responses with no issues on its confidence dimension, consistent with H3. Bahrami, Cookson & Moss (2026) show why H3 and the confident-and-wrong measure matter: in their Chatbot Arena data, users favored confident, actionable advice, and when one answer contained a serious error and the other was correct, they chose the flawed answer 47.8% of the time. A chatbot that omits caveats is therefore unlikely to be corrected by its users. H4 has no direct precedent in Urban's work, which scored one response per prompt. Wang & Wang (2025), across 50 repeated runs of three OpenAI models on five finance and accounting tasks, find substantial but task-dependent consistency: near-perfect on simple classification, more variable on complex tasks, and much better when 3–5 runs are aggregated. A program-specific dollar estimate is an open-ended task, so H4 predicts noticeable variation; their aggregation result also supports using the mean of the 3 F runs as each profile's estimate (§4.2). H5–H7 concern CareerIQ's own formula and have no external precedent. The thresholds were set before this literature was read in full and were not changed afterwards.

**Where H5–H7 are tested (D19; a departure from the PRD).** CareerIQ is deterministic and costs nothing to run, so the **primary** test of H5–H7 uses **every eligible school-and-major row at the 80% training schools** (§2.4), not only the 150 profiles. H5–H7 are also reported on the 150 profiles for comparison. Held-out schools are not used for H5–H7, because they're reserved for scoring the rebuilt CareerIQ. Rationale: the 150 profiles contain only 11 high-ceiling and 19 compressed-pay profiles, which is too few for a reliable test. **None of these comparisons will be run before this document is filed.**

---

## 2. Design

### 2.1 Study type

Observational audit of model outputs against administrative data. No human subjects and no real student data.

### 2.2 Ground truth: College Scorecard field-of-study data

U.S. Department of Education, "Most Recent Data by Field of Study," release `Most-Recent-Cohorts-Field-of-Study_10152026.zip`, plus the institution file `_11022026` and the data dictionary downloaded 2026-11-02. SHA-256 checksums are in `data/raw/MANIFEST.json`. Every column name was checked against the official data dictionary.

| Quantity | Column | Definition |
|---|---|---|
| Earnings (primary) | `EARN_MDN_1YR` | Median earnings 1 year after completing, among graduates working and not enrolled. Covers AY2020-21 and AY2021-22 completers, measured CY2022–23, in 2024 dollars. |
| Earnings (robustness) | `EARN_MDN_5YR` | The same median 5 years after completing |
| Debt (primary) | `DEBT_ALL_STGP_EVAL_MDN` | Median federal Direct Loan debt borrowed at this institution, among graduates who borrowed (AY2022-23 and AY2023-24 completers) |
| Debt (robustness) | `DEBT_ALL_STGP_ANY_MDN` | The same median, counting loans from any institution |

Rows with privacy-suppressed (`PS`) earnings or debt are excluded.

### 2.3 Sample: 150 school-and-major profiles

**Eligible rows** are Scorecard rows (school × 4-digit CIP × credential) that meet all of these:
- 1-year earnings and median debt are both reported
- the credential is an associate's degree (`CREDLEV` 2) or a bachelor's degree (`CREDLEV` 3)
- the school is in CareerIQ's college list (2,581 schools)
- the field maps to a CareerIQ job in `crosswalk/cip_to_job.csv`

**Crosswalk rule (D15).** A field is mapped only to a CareerIQ job that the official NCES/BLS CIP 2020–SOC 2018 crosswalk links to it, in a CareerIQ major that fits the field. If several jobs are linked, the one most typical for new graduates is used. Fields with no linked job are excluded. The result is 59 mapped fields.

**School groups (D1, D5, D6).** Groups use CareerIQ's own `schoolType` and `tier` fields:
- **Community college:** a 2-year school; associate's rows only.
- **Open admission:** a 4-year school with tier 4 (admits more than 70%), or with no admission rate and Scorecard `OPENADMP` = 1.
- **Above average:** tier 3 (admits 40–70%), with a reported rate.
- **Selective:** tier 2 (admits 15–40%).
- **Elite:** tier 1 (admits under 15%).
- Four-year groups use bachelor's rows only. Four-year schools with no rate and `OPENADMP` ≠ 1 are excluded.

**Earnings bands (D9).** All fields nationally at each credential level are ranked by `EARN_MDN_1YR_NAT` and split into thirds, separately for associate's and bachelor's. Bachelor's cutoffs are $40,871 and $55,930. Associate's cutoffs are $34,704 and $44,660.

**Draw (D10, D14).** 10 profiles per cell (5 groups × 3 bands = 15 cells, 150 profiles). Within each cell the draw is random with seed (2026, group index, band index). It aims for 5 Texas and 5 non-Texas profiles, takes at most one profile per school, and applies no field cap. Elite cells have too few Texas rows to reach the target (D8).

**The sample is already drawn:** `data/processed/profiles.csv`, SHA-256 `2e3a9d2f…c9e4`. It has 150 profiles, 56 in Texas, 42 fields, and 76 public and 74 private nonprofit schools.

**Weighting.** Every cell has 10 profiles regardless of its size, so pooled results are unweighted and over-represent elite schools and community colleges relative to all eligible programs (eligible rows per cell range from 28 to 2,331; `data/processed/sample_counts.csv`). The primary results are the unweighted ones, because the study's question is about students at each kind of school, not the average eligible program. Robustness check 7(f) reports the pooled results reweighted by each cell's share of eligible rows.

### 2.4 Holdout schools for the CareerIQ rebuild

20% of CareerIQ's schools within each school group are held out, chosen by seeded shuffle: `data/processed/holdout_schools.csv`, SHA-256 `f137df45…1331`. 33 of the 150 profiles are at held-out schools. Any recalibration of CareerIQ is fit on training schools only, and the rebuilt model's fallback error is reported on held-out schools only.

### 2.5 Blinding

R answers are hand-coded on sheets with the chatbot's name removed and the order shuffled (`scoring/make_coding_sheets.py`). Number extraction from F answers is automatic.

---

## 3. Data collection

### 3.1 Prompts (`prompts/v1.json`)

- **R (real-student), asked once:** "I'm a high school senior thinking about majoring in {major} at {school}. How much would I make right after graduating, and how much student debt would I probably have?"
- **F (forced-number), asked 3 times:** the same text followed by "Answer in this format: Earnings: $___ / Debt: $___."

`{major}` is the plain-English field name in the crosswalk (`prompt_major`). `{school}` is the Scorecard institution name.

### 3.2 Call settings (D12)

Every call is a fresh conversation with one user message: no system prompt, no tools (so no web search), and provider defaults for sampling and reasoning, with one exception: Claude's effort is set to "medium" to match the free app (D24). Claude requires `max_tokens`, which is set to 16,000. Claude's server-side refusal fallback is off. An API-level refusal or safety block is retried once with the same prompt, and both attempts are logged.

Each model's full set of 600 calls (150 profiles × 4) runs within one 7-day window. Every call logs the requested and returned model ID, a timestamp, the prompt version and text, the raw response, the stop reason and token usage (`runners/run_chatbots.py`, one JSONL file per chatbot).

### 3.3 CareerIQ

`runners/run_careeriq.mjs` imports CareerIQ's own `calculations.js` from a clean checkout at `ba51be3`. It calls `calculateSalary` (Entry, Suburban, National) and `calculateLoan` (income bracket $48,001–$75,000, key `mid2`). The debt estimate is `totalLoan4Year`: net price × 2 or 4 years. An independent Python recomputation reproduces all 150 estimates exactly.

### 3.4 Pilot (D17)

Before the full run, a pilot of 10 profiles runs through the full pipeline (R once, F three times, per chatbot: 120 calls). **The pilot profiles are not among the 150 study profiles.** They were drawn from the same eligible pool minus the 150 sampled rows: 10 of the 15 cells were chosen by a seeded shuffle (seed 2026), and one row was drawn at random from each chosen cell, with at most one row per school (`data/make_splits.py`; `data/processed/pilot_profiles.csv`, SHA-256 `85461cef…addf`). The pilot file carries no Scorecard values, so no error can be computed from it. The pilot is used only to check number extraction, refusal handling, and cost. Pilot answers are stored in `runs/pilot/` and are never analyzed. They are read by the author and by Claude (the analysis assistant used to build the pipeline) to check number extraction and refusal handling; neither compares any pilot answer with Scorecard. If the pilot leads to any prompt or code change, the change is versioned and recorded here as an amendment before the full run.

### 3.5 Consumer-app spot check (D18)

30 profiles (2 per cell, seed 2026; `data/processed/spot_check_profiles.csv`). Each profile gets the **R prompt once** in each chatbot's free app, with default settings and a fresh chat, logged by hand in `scoring/spot_check_template.csv`: 90 responses. It records whether the app used web search and which model the app displays.

### 3.6 Stopping rule

The sample is fixed at 150 profiles. There's no optional stopping.

---

## 4. Variables and scoring (`scoring/metrics.py`, `scoring/codebook.md`)

### 4.1 Extraction

F answers are parsed by `scoring/extract.py`. Every answer it can't parse cleanly (no labelled number, several labelled numbers, or a value outside $5k–$500k) is reviewed by hand, and the fix is logged. A range is scored at its midpoint.

R answers are not parsed automatically. Their earnings and debt figures, needed for Badly wrong, Confident and wrong, and Range coverage, are recorded during hand coding under codebook rule 1: a single value for a point estimate, or the low and high values for a range, from which the midpoint is computed by code; `none` if the answer gives no figure. This mirrors `extract.py`'s rules, so F and R figures are treated the same way.

### 4.2 Measures

| Measure | Definition | Applies to |
|---|---|---|
| Signed error | (estimate − Scorecard) / Scorecard | F answers, CareerIQ |
| Absolute error | \|signed error\| | F answers, CareerIQ |
| Badly wrong | absolute earnings error > 25% | all numeric answers |
| Range coverage | Scorecard value lies within the stated range (ends included) | answers giving a range |
| Caveat | yes/no per codebook rule 3 | R answers |
| Source type | none / generic / specific, per codebook rule 4. Every specific source is checked and coded verified / false / unverifiable. | R answers |
| Confident and wrong | badly wrong and caveat = no | R answers containing an earnings number |
| Consistency | CV = sample SD / mean of the 3 F earnings figures | chatbots |
| Refusal | no usable number after the retry and hand review | all |

**Unit of analysis.** The unit is the profile. A chatbot's error on a profile is the mean of its absolute (or signed) errors over the F runs that gave a number. CareerIQ has one estimate per profile.

### 4.3 Second coder

The second coder is **Safiullah Baig**, who had no role in the study design. They code `caveat` and `source_type` for 50 randomly drawn R answers (seed 2026) using only the codebook, with no discussion with the author until finished. Cohen's kappa is computed on the original codes before any discussion. Disagreements are then resolved by discussion, and every change is logged. The second coder is named in public materials only with their permission; otherwise they are described as "a second coder with no role in the study design."

---

## 5. Analysis plan

All intervals are 95% percentile bootstrap intervals with 2,000 resamples of profiles (seed 2026), except H3, which uses Wilson intervals. The tools are Python, pandas and matplotlib.

1. **Accuracy (H1).** Median absolute earnings error and debt error for each contestant, with CIs.
2. **Equity (H2).** Median absolute earnings error by school group and by earnings band, for each contestant. The main figure is a contestant × group chart.
3. **Direction.** Median signed error by group and band. Debt signed error is also split by public vs. private.
4. **Honesty (H3).** Share of R answers with a caveat, a range, any source, a false specific source, and confident-and-wrong numbers. Also range coverage.
5. **Consistency (H4).** Distribution of CV across profiles, for each chatbot.
6. **CareerIQ assumptions (H5–H7).** Tested per §1.3, plus two descriptive checks: signed error among capped schools (multiplier = 1.60) vs. the rest, and overall signed error (the BLS mean-vs-median question).
7. **Robustness.**
   - (a) All accuracy results rerun against 5-year earnings, to see whether chatbots answer with later-career numbers.
   - (b) Debt rerun against `DEBT_ALL_STGP_ANY_MDN`.
   - (c) App spot check vs. API answers for the same 30 profiles (descriptive).
   - (d) CareerIQ crosswalk sensitivity: psychology (CIP 42.01, 42.27, 42.28) re-mapped to market_researcher and hr_specialist, economics (45.06) to financial_analyst, and business (52.01, 52.02) to management_consultant.
   - (e) **Inflation (D20).** Scorecard earnings are stated in 2024 dollars. Each chatbot answer is presumably in the dollars of the month it was asked. All earnings accuracy results are rerun with Scorecard earnings brought forward to the month of each query: value × CPI(query month) / CPI(2024 annual average), using BLS CPI-U, All items, U.S. city average, not seasonally adjusted, series `CUUR0000SA0` (`analysis/cpi_adjust.py`, which records the fetch date). If the query month's CPI isn't published yet at analysis time, the latest published month is used and this is noted. For CareerIQ, Scorecard earnings are brought forward to the reference period of the BLS OEWS wages in `salaries.json`, not to a query month. That file does not record the OEWS year, so it was determined on 2026-11-04 by querying the BLS series CareerIQ uses for Software Developers (`OEUN000000000000015125204`): the $148,100 value in `salaries.json` is the annual 2025 value and no other year is available in that series, so CareerIQ's wages are May 2025 OEWS dollars, and the factor is CPI(May 2025) / CPI(2024 annual average). Debt is not adjusted, because Scorecard reports debt as the nominal dollars disbursed.
   - (f) **Reweighting (added 2026-11-04).** Pooled accuracy results (item 1) are recomputed with each profile weighted by its cell's share of eligible rows (`data/processed/sample_counts.csv`), so the pooled medians describe the eligible-program population rather than the equal-cells design. Weighted medians use the same 2,000-resample bootstrap, resampling profiles with probability proportional to weight.
8. **Exploratory.**
   - (a) Regression of log(absolute earnings error + 0.01) on school group, earnings band and contestant, with standard errors clustered by profile.
   - (b) **Scope substitution** (added 2026-11-04 after reading Urban 2026, before any data collection). For each F earnings figure, which of three Scorecard values it is closest to in percentage terms: the program-level median (the answer key), the field's national median for that credential (`EARN_MDN_1YR_NAT`), or the school's all-majors median earnings 10 years after entry from the institution file (`MD_EARN_WNE_P10`, checked against the data dictionary; the same measure CareerIQ's school multiplier uses). The share of answers closest to a non-program value, by contestant and school group, is reported as a description of *how* chatbots are wrong, not as a hypothesis test.

**Multiple comparisons.** Results are reported with CIs and the three-way decision rules above. No p-value correction is applied, and the write-up says so.

**Missing data.**
- An F run with no usable number is excluded from error measures and counted in the refusal rate.
- A profile enters a chatbot's error measures if at least one of its F runs gave a number.
- CV needs at least 2 numeric runs.
- Refusal rates are reported per chatbot.

**Everything here gets reported,** including null results. Anything not listed here is labeled exploratory.

**Minimum version.** If the study is behind schedule at the Nov 29, 2026 checkpoint, it may be cut to accuracy and equity only (§5 items 1–2). Any such cut is reported as a deviation, and none of the analyses above will be dropped because of their results.

### 5.1 CareerIQ rebuild validation (not a hypothesis test)

The rebuilt CareerIQ (v2) does three things:
- uses Scorecard 1-year earnings and debt where they exist ("anchor")
- falls back to the formula with field-specific entry ratios fit on training schools only
- shows the full-net-price debt as a worst case

Reported:
- the fallback's error on held-out schools only
- the anchor's coverage: the share of eligible rows that Scorecard can answer

The v1 and v2 code are tagged `v1-baseline` and `v2-hybrid`.

---

## 6. Data already seen at filing (disclosure)

- Scorecard field-of-study and institution files were explored for feasibility: column checks, row counts per cell, and the distribution of median debt values (e.g. that $27,000 is the most common median debt value).
- CareerIQ estimates for all 150 profiles were computed and checked for correctness against an independent recomputation. **Only the number of matches was viewed.** During checking on 2026-11-02, CareerIQ and Scorecard values were displayed for 3 profiles of an earlier draft sample: biology at the University of North Texas, biology at Rice University, and teacher education at San Jacinto College. No other CareerIQ error was computed or viewed.
- CareerIQ's "federal portion" of debt (§1.3, H7 secondary) was computed for the 150 profiles. Only CareerIQ-side facts were viewed (e.g. how many profiles sit at the federal cap); nothing was compared with Scorecard.
- **No chatbot answers to any study prompt have been collected.** The pipeline was tested only with a fake "echo" model. **[Update at filing: state whether the pilot (§3.4) has run, and confirm that no pilot answer was compared with Scorecard.]**

---

## 7. Limitations known in advance

- Scorecard covers only graduates who received federal aid, and its earnings exclude graduates who were still enrolled or not working.
- One year after graduating is not exactly "starting salary."
- Scorecard's debt is a median among federal borrowers. It excludes non-borrowers, private loans and interest, and tends to top out at the $27,000 federal cap. A chatbot or tool that counts non-borrowers, or assumes everything is borrowed, is answering a somewhat different question.
- CareerIQ maps each major to one job. The crosswalk sensitivity check (§5, 7d) tests that assumption.
- The API models stand in for the free apps but are not identical to them. Gemini's free app routes some prompts to larger models, and Google does not say which Flash-Lite version it runs, so `gemini-3.5-flash-lite` is an inference. The spot check measures the gap.
- 150 profiles is a sample. Findings are stated as "in this sample of 150 profiles."
- Results are a snapshot of specific model versions on specific dates. Urban (2026) showed that giving a model direct access to the data changes its answers substantially, so these results describe the default experience, not what the same models can do with tools attached.
