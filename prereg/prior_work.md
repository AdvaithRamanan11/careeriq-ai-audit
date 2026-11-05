# Prior work: search log and reading notes

**Question:** Has anyone already scored chatbot earnings or debt estimates for specific college programs against federal outcome data?

**Short answer:** Not with a numeric answer key. The Urban Institute's 2026 evaluation is the closest work and is the study we position against (see the preregistration, §1.1). It used expert ratings on curated prompts and explicitly disclaims being a quantitative benchmark. An OpenAI blog post evaluated wage answers at the occupation level, by the model's maker. Everything else found is about general financial advice, bias, or college advising without ground truth.

## Search log

| Date | Where | Terms | Scope |
|---|---|---|---|
| 2026-11-02 | Web search (Claude) | chatbot accuracy college earnings/debt; LLM financial advice audit | First pass |
| 2026-11-04 | Google Scholar, "Since 2023" filter, by Advaith | `ChatGPT "College Scorecard"` (pages 1–2); `"large language model" college earnings accuracy`; `chatbot "student debt" advice accuracy`; `LLM "college choice" OR "college major" advice evaluation`; `"ChatGPT" "financial advice" accuracy benchmark`; `"generative AI" "return on investment" college students`; `LLM wage estimates OEWS` (page 1 each) | Main pass |
| pending | SSRN, by hand | `ChatGPT financial advice` | **Still to do** |

## Reading status

- **Read in full (by Claude, 2026-11-04):** the two Urban Institute reports.
- **Read (by Advaith, 2026-11-04):** the OpenAI post and the Bahrami, Cookson & Moss SSRN paper. Both block automated fetching, so the notes below are Advaith's.
- **Snippets only:** everything under "Relevant to specific hypotheses" and "Background." Read the abstract before citing any of them.

## Closest work

### Tyagi, Blagg & Gutierrez (May 2026). *Evaluating How LLMs Handle Education and Workforce Pathway Data.* Urban Institute. [PDF](https://www.urban.org/sites/default/files/2026-05/Evaluating-How-LLMs-Handle-Education-and-Workforce-Pathway-Data-final.pdf)

Read in full. Facts with page numbers:

- **Design (pp. 3–4):** 100 curated prompts across 10 topics (including "institution-level earnings" and "student loans") and 6 personas (including "career or education advisor"). Sent to GPT-5.2, Claude Sonnet 4.5 and Gemini 3 Flash, "the models a user would likely encounter when interacting with the free versions … as of early 2026," programmatically, "as a standalone query with no custom system prompt, conversation history, or tool access beyond what each model provides by default." Evaluators blinded to model. 300 responses.
- **Scoring (p. 4):** subject-matter experts, six dimensions (accuracy, clarity, completeness, confidence, reference, responsibility), four-point scale (no / minor / significant / critical issues), plus diagnostic tags. No numeric comparison to a ground-truth dataset.
- **Self-description (p. 5):** "not to rank specific models, serve as a quantitative benchmark, or make broad claims about LLM capabilities"; prompts "deliberately constructed"; figures "should be read as patterns, rather than generalizable performance metrics."
- **Findings:** only 16% of responses had no accuracy issues; 34% critical (p. 7). Specific-retrieval prompts (a particular school, district or institution): 58% critical (p. 5). References: significant or critical issues in >60% of responses; "the presence of a citation in a response was also not associated with higher accuracy" (p. 7). "Inaccurate statistics were typically presented in the same tone, precision, and level of apparent certainty as accurate ones" (p. 7). Scope substitution: models "defaulting to national trends when asked about specific schools or institutions" (p. 2, p. 8). Caveats "frequently missing" (p. 2, p. 8). Example: "a response provided Purdue engineering graduate earnings figures that were tens of thousands of dollars below the actual values reported in the College Scorecard" (p. 7). GPT-5.2 asked clarifying questions more often, "making direct cross-model comparisons difficult to interpret" (p. 5).
- **Relevance to this study:** same three vendors, same "default experience" query setup, overlapping topics. Differs in: expert ratings vs numeric error; curated vs sampled prompts; institution-level vs program-level; no selectivity breakdown; one response per prompt; no preregistration mentioned.

### Tyagi, Blagg & Gutierrez (Oct 2026). *Improving How LLMs Handle Education and Workforce Pathway Data.* Urban Institute. [PDF](https://www.urban.org/sites/default/files/2026-10/Improving-How-LLMs-Handle-Education-and-Workforce-Pathway-Data.pdf)

Read in full.

- **Design (pp. 2, 5):** same 100 prompts, Claude Sonnet 4.5 only (same version as baseline), August 2026, with Urban's two MCP servers connected and expanded documentation. Evaluators were *not* blinded this round. "Extended thinking disabled, as in the baseline" (note 4).
- **Findings:** no-accuracy-issue responses rose from 16% to 61%; critical from 35% to 7% (p. 2). Institution-specific prompts: critical issues 42% → 11% (p. 7). References no-issues 11% → 84%; confidence no-issues 26% → 71% (p. 2). Cost ~12× per response, median 37 seconds (p. 9).
- **Remaining errors were judgment calls (p. 8):** e.g. one response "returned institution-level earnings data for undergraduates and described its figures as graduates' earnings, even though they also include students who did not complete a degree." Urban's portal has program-level earnings only from PSEO; the Education-to-Workforce tool names College Scorecard as a source.
- **Free-tier access (note 8):** "As of September 2026, ChatGPT supported custom MCP servers only through developer mode, which was not available on its free plan"; Claude's free plan allowed one custom connector; Gemini's custom connections limited to adults in the US.
- **Relevance:** shows that anchoring on data works, but through a route most students can't use. Motivates CareerIQ v2's approach (federal data inside a free tool, no setup).

### OpenAI (Mar 17, 2026). *Equipping workers with insights about compensation.* [Post](https://openai.com/index/equipping-workers-with-insights-about-compensation/)

Read by Advaith, 2026-11-04. The post says Americans send nearly 3 million messages a day to ChatGPT about wages, compensation or earnings (from a privacy-preserving classifier analysis), and that GPT-5.4, tested against 2024 OEWS median wages at national and metro levels, was "highly accurate" in the observed sample. It does not give a percent-error figure and the evaluation was run by OpenAI. Relevant as (a) evidence of the scale of demand, (b) an occupation-level, maker-run accuracy claim that this study's program-level, independent design can be contrasted with. Cite no more than this.

### Bahrami, Cookson & Moss (2026). *Judge for Yourself: Confidence Beats Accuracy in AI Financial Advice.* SSRN 7602338, posted Oct 12, 2026.

Read by Advaith, 2026-11-04. **Correction:** an earlier note described this as an app-vs-API comparison. It is not. It analyzes 3,060 Chatbot Arena votes on financial questions. Users prefer confident, actionable advice; the more accurate answer wins only 52.2% of decisive votes; when one answer has a serious error and the other is correct, users choose the flawed one 47.8% of the time. Bears on H3 and the confident-and-wrong measure, not on the app spot check.

## Relevant to specific hypotheses (abstracts not yet read)

| Source | From Advaith's notes | Bears on |
|---|---|---|
| Wang & Wang (2025). "Assessing consistency and reproducibility in the outputs of large language models: Evidence across diverse finance and accounting tasks." arXiv:2503.16974. | Consistency of LLM outputs on finance tasks. | H4 |
| Geiger, O'Sullivan, Wang & Lo (2025). PLOS ONE. | Salary-negotiation advice bias audit varying gender, university and major; no ground truth. | H2 (school-type differences) |
| Smith (2024). "'I'm Sorry, but I Can't Assist': Bias in Generative AI." RESPECT conference. | Uses College Scorecard institution naming; check relevance to refusals. | Refusal rate; H2 |

## Background (snippets only)

- Hean, Saha & Saha (2024/2025). "Can AI Help with Your Personal Finances?" arXiv:2412.19784.
- Sorokovikova et al. (2025). "Surface Fairness, Deep Bias." arXiv:2506.10491.
- Lekan & Pardos (2025). "AI-Augmented Advising." *Journal of Learning Analytics* 12(1).
- Zheng (2025). "Dissecting bias of ChatGPT in college major recommendations." *Information Technology and Management*.
- Fletcher (2024). "ChatGPT, Finances, and Degree Attainment." IEEE Frontiers in Education.
- Ngangoue, Schotter & Wang (2026). "Life's Big Decisions in the Age of AI." SSRN.
- Choukhmane, de Silva, Lin et al. (2026). "AI financial advice: Supply, demand, and life cycle implications." SSRN.
- Lo & Ross (2024). "Can ChatGPT plan your retirement?" *Harvard Data Science Review*.
- Takayanagi et al. (2025). "Are Generative AI Agents Effective Personalized Financial Advisors?" arXiv:2504.05862.
- Gray literature, cite with caution: Figures (Feb 2026), company blog, ~10,000 ChatGPT salary benchmarks, ~17% average error.

## Background on the answer key

- [College Scorecard field of study documentation](https://collegescorecard.ed.gov/files/FieldOfStudyDataDocumentation.pdf) (Version: October 2026): definitions and limitations used throughout.
