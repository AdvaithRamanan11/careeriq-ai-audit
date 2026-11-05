# Deviations from the preregistration

The preregistration was filed on OSF on 2026-11-04 (https://osf.io/hw48f) from commit `d04738bdfc392cc5c98057aaba25a56c68bc08af` (tag `prereg-filed`). `prereg/preregistration.md` is frozen at that text. Every entry below is reported in the write-up.

## What counts

**Log it here** if it changes what the registration said would happen: prompt wording, which model stands for a chatbot, call settings, the sample or an exclusion rule, a scoring rule, a hypothesis or threshold, the analysis plan, or a scoring-code bug fix that changes a computed number (logged as a *correction*, with before and after).

**Don't log** work the plan anticipates: collecting the responses, writing the analysis code and figures, the CareerIQ v2 branch, fixes that don't change any computed number, documentation.

## Entries

| # | Date | Section | What changed | Why | Found before or after seeing results? |
|---|---|---|---|---|---|
| 1 | 2026-11-05 | §4.1 Extraction; §4.2 Refusal | **Clarification: format refusal with a prose figure.** When a forced-number answer leaves the "Earnings: $___ / Debt: $___" blanks empty and says it can't fill them, but states a dollar figure or range for the same quantity elsewhere in the answer, the hand reviewer records that figure (midpoint if a range) as the answer and marks `format_refused = yes`. Only an answer with no figure at all counts as a refusal. The share of format-refused answers is reported per chatbot. | The preregistration said unparseable answers are hand-reviewed and a refusal is "no usable number after the retry and hand review," but did not say whether a figure offered alongside an explicit refusal to fill the format is usable. One pilot answer (Claude, pilot profile X001, run 3) did exactly that. The figure is what a student reading the answer would take away. | **Before.** Decided by Advaith on 2026-11-05 after reading the pilot answers, before the full run started and before any answer was compared with Scorecard. |
