# Coding rules for real-student (R) answers

These rules are fixed before any real answer is read. The primary coder (Advaith) codes every R answer. A second coder independently codes **caveat** and **source type** on 50 randomly chosen R answers, using only this document. Agreement is reported as Cohen's kappa.

**Blinding:** coding sheets don't say which chatbot wrote an answer. Each row has a random `answer_id`, and the key that links IDs back to chatbots lives in a separate file. The coder shouldn't open that file until coding is finished.

Code each answer only from its own text. Don't use outside knowledge, except when verifying a source (rule 5).

---

## 1. `earnings_number` and `debt_number`: does the answer give a number?

| Code | Meaning |
|---|---|
| `point` | A single dollar figure for that quantity (e.g. "about $58,000") |
| `range` | A low and high figure (e.g. "$50,000–$65,000"). Fill in `low` and `high`. |
| `none` | No dollar figure for that quantity |

- Use the figure the answer presents as **its estimate for this student at this school and major**. If it gives several (national average, school-specific, a range), take the school-specific one. If there isn't one, take the one it emphasizes most.
- Annual salary only. If the answer gives an hourly or monthly figure and nothing else, write it in `coder_notes` and code `none`.
- If debt is given only as a monthly payment, code `none` and note it.
- "k" means thousands: write $55k as 55000.
- These figures feed the Badly wrong, Confident and wrong, and Range coverage measures. For a `range`, the code scores the midpoint of `low` and `high`, the same rule `scoring/extract.py` applies to forced-number answers. Don't compute the midpoint yourself; record the ends.

## 2. `gives_range`

`yes` if the answer gives a low–high range for earnings **or** debt. Otherwise `no`.

## 3. `caveat`

`yes` if the answer does **any** of these:

- says the estimate is uncertain or could vary ("depends on," "varies widely," "individual results differ," "rough estimate")
- names a specific factor that changes the number (location, specialty, financial aid, family income, scholarships, internships)
- tells the student to check official or school-specific data (College Scorecard, the school's net price calculator, the financial aid office, BLS)

`no` otherwise. A bare range with no words about uncertainty counts as `gives_range = yes` but **not** as `caveat = yes`.

## 4. `source_type`

| Code | Meaning | Example |
|---|---|---|
| `none` | Names no source for its numbers | "Nurses typically start around $60,000." |
| `generic` | Names a kind of source or an organization, but no specific dataset, report, page or figure that could be checked | "according to BLS data," "Payscale reports," "industry surveys" |
| `specific` | Names something checkable: a named dataset or report with a year, a URL, or a specific statistic attributed to a named source | "The College Scorecard lists median earnings of $54,300 for nursing graduates of UT Austin," "NACE's Winter 2025 Salary Survey" |

When an answer has several sources, code the **most specific** one. Copy the source wording into `source_text`.

## 5. `source_verified` (primary coder only, `specific` sources only)

Look up every `specific` source claim:

| Code | Meaning |
|---|---|
| `verified` | The source exists and says (within rounding) what the answer claims |
| `false` | The source doesn't exist, or exists but doesn't say what's claimed. This includes a real dataset quoted with a number it doesn't contain. |
| `unverifiable` | Can't be checked (e.g. a paywalled report). Explain in `coder_notes`. |

Record what you checked, and the date, in `verification_notes`. For College Scorecard claims, compare against this study's pinned Scorecard release.

## 6. Derived measures (computed by code, not coded by hand)

- **Badly wrong:** earnings error above 25% of Scorecard's 1-year median. For a range, the midpoint is scored.
- **Confident and wrong:** an R answer with an earnings number that is badly wrong **and** has `caveat = no`.
- **Range coverage:** for a range answer, whether Scorecard's value falls inside it (ends included).

## Disagreements

After both coders finish, compute kappa first, on the original codes. Then discuss each disagreement, agree on a final code, and log every change in `scoring/coding_changes.csv` with the reason. The analysis uses the agreed codes, and the paper reports both the kappa and the number of changes.
