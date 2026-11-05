"""
Produce every preregistered result (preregistration.md section 5) from scoring/out/.

Outputs
  analysis/results.md          all tables, each hypothesis with its three-way decision
  analysis/figures/*.png       the figures
  analysis/results_tables/*.csv  every table as CSV, for the write-up

Nothing here is tuned to the data: the decision rules are copied from the
preregistration and applied mechanically. Sections the data can't support yet
(e.g. hand coding not done) are written as "not yet available", never skipped silently.

Usage: python analysis/results.py [--out-dir scoring/out] [--tag label]
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO  # noqa: E402
from scoring.metrics import bootstrap_median, bootstrap_median_diff, wilson_ci, N_BOOT, SEED  # noqa: E402

ANALYSIS = REPO / "analysis"
FIG = ANALYSIS / "figures"
TAB = ANALYSIS / "results_tables"

CONTESTANTS = ["chatgpt", "gemini", "claude", "careeriq"]
LABEL = {"chatgpt": "ChatGPT", "gemini": "Gemini", "claude": "Claude", "careeriq": "CareerIQ"}
COLOR = {"chatgpt": "#2a78d6", "gemini": "#eb6834", "claude": "#1baf7a", "careeriq": "#eda100"}  # validated palette
INK, INK2, MUTED, GRID, BASE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
GROUPS = ["Community college", "Open admission", "Above average", "Selective", "Elite"]
BANDS = ["Bottom", "Middle", "Top"]
SELECTIVITY_RANK = {"Elite": 1, "Selective": 2, "Above average": 3, "Open admission": 4}

# H5 field groups (preregistration 1.3)
HIGH_CEILING = lambda cip: cip.startswith("11") or cip == "1409" or cip == "5208"
COMPRESSED = lambda cip: cip == "5138" or cip.startswith("13")

H1_THRESHOLD, H3_THRESHOLD, H4_THRESHOLD = 0.20, 0.50, 0.05

plt.rcParams.update({"font.family": "sans-serif", "font.size": 10, "axes.edgecolor": BASE, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "axes.facecolor": "white", "grid.color": GRID, "grid.linewidth": 0.6})


class Report:
    def __init__(self):
        self.lines = []
        self.tables = {}

    def h(self, level, text):
        self.lines += ["", "#" * level + " " + text, ""]

    def p(self, text):
        self.lines += [text, ""]

    def table(self, name, df: pd.DataFrame, floatfmt=3):
        self.tables[name] = df
        d = df.copy()
        for c in d.columns:
            if d[c].dtype.kind == "f":
                d[c] = d[c].map(lambda v: "" if pd.isna(v) else f"{v:.{floatfmt}f}")
        cols = list(d.columns)
        self.lines.append("| " + " | ".join(str(c) for c in cols) + " |")
        self.lines.append("|" + "---|" * len(cols))
        for _, r in d.iterrows():
            self.lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
        self.lines.append("")

    def write(self, path: Path):
        path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")
        TAB.mkdir(exist_ok=True)
        for name, df in self.tables.items():
            df.to_csv(TAB / f"{name}.csv", index=False, lineterminator="\n")


def decide(lo, hi, threshold, direction="above"):
    """Three-way decision from a 95% CI."""
    if pd.isna(lo) or pd.isna(hi):
        return "inconclusive (no data)"
    if direction == "above":
        return "supported" if lo > threshold else ("not supported" if hi < threshold else "inconclusive")
    return "supported" if hi < threshold else ("not supported" if lo > threshold else "inconclusive")


def weighted_bootstrap_median(values, weights, n_boot=N_BOOT, seed=SEED):
    v = np.asarray(values, dtype=float); w = np.asarray(weights, dtype=float)
    ok = ~np.isnan(v); v, w = v[ok], w[ok]
    if len(v) == 0:
        return (np.nan, np.nan, np.nan, 0)
    p = w / w.sum()
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(v), size=(n_boot, len(v)), replace=True, p=p)
    boots = np.median(v[idx], axis=1)
    # point estimate: weighted median
    order = np.argsort(v); cw = np.cumsum(w[order]); wm = v[order][np.searchsorted(cw, cw[-1] / 2)]
    return (float(wm), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)), len(v))


def med_row(name, values, **extra):
    m, lo, hi, n = bootstrap_median(values)
    return dict(extra, measure=name, n=n, median=m, ci_low=lo, ci_high=hi)


def present(pl: pd.DataFrame) -> list:
    """Contestants in the data, known ones first in fixed order; unknown ones (e.g. the echo
    test model) appended so the pipeline can be exercised on fake data."""
    have = set(pl.contestant)
    extra = sorted(have - set(CONTESTANTS))
    for c in extra:
        LABEL.setdefault(c, c); COLOR.setdefault(c, "#898781")
    return [c for c in CONTESTANTS if c in have] + extra


# ────────────────────────────────────────────────────────────────── figures ──
def fig_accuracy(rows: pd.DataFrame, path: Path, title: str, xlabel: str, threshold=None):
    fig, ax = plt.subplots(figsize=(7, 0.6 * len(rows) + 1.4))
    y = np.arange(len(rows))[::-1]
    for yi, (_, r) in zip(y, rows.iterrows()):
        c = COLOR[r.contestant]
        ax.plot([r.ci_low, r.ci_high], [yi, yi], color=c, lw=2, solid_capstyle="round")
        ax.plot(r["median"], yi, "o", color=c, ms=8, mec="white", mew=1.5)
        ax.text(r.ci_high + 0.01, yi, f"{r['median']:.0%}  [{r.ci_low:.0%}, {r.ci_high:.0%}]", va="center", fontsize=9, color=INK2)
    if threshold is not None:
        ax.axvline(threshold, color=MUTED, lw=1, ls="--")
        ax.text(threshold, 0.98, f" {threshold:.0%} threshold", color=MUTED, fontsize=8, va="top",
                transform=matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes))
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_yticks(y); ax.set_yticklabels([LABEL[c] for c in rows.contestant], color=INK)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_xlabel(xlabel); ax.set_title(title, loc="left", color=INK, fontsize=11, pad=12)
    ax.grid(axis="x"); ax.set_axisbelow(True); ax.set_xlim(left=min(0, rows.ci_low.min() - 0.05))
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_by_group(tbl: pd.DataFrame, path: Path, title: str, value="median", xlabel="Median absolute earnings error",
                 groups=GROUPS, zero_line=False):
    """Small multiples: one panel per contestant, dot + CI per school group."""
    cs = present(tbl)
    fig, axes = plt.subplots(1, len(cs), figsize=(3.2 * len(cs), 3.6), sharey=True, sharex=True)
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, cs):
        sub = tbl[tbl.contestant == c].set_index("group").reindex(groups)
        y = np.arange(len(groups))[::-1]
        for yi, (g, r) in zip(y, sub.iterrows()):
            if pd.isna(r[value]):
                continue
            ax.plot([r.ci_low, r.ci_high], [yi, yi], color=COLOR[c], lw=2, solid_capstyle="round")
            ax.plot(r[value], yi, "o", color=COLOR[c], ms=7, mec="white", mew=1.2)
            ax.annotate(f"{r[value]:.0%}", (r.ci_high, yi), xytext=(4, 0), textcoords="offset points",
                        va="center", fontsize=8, color=INK2)
        if zero_line:
            ax.axvline(0, color=MUTED, lw=1)
        ax.set_ylim(-0.6, len(groups) - 0.4)
        ax.set_yticks(y); ax.set_yticklabels(groups, color=INK)
        ax.set_title(LABEL[c], loc="left", color=COLOR[c] if c != "careeriq" else INK, fontsize=10)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); ax.grid(axis="x"); ax.set_axisbelow(True)
    fig.supxlabel(xlabel, color=INK2, fontsize=9); fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_cv(pl: pd.DataFrame, path: Path):
    cs = [c for c in present(pl) if c != "careeriq"]
    fig, ax = plt.subplots(figsize=(7, 1.0 + 0.7 * len(cs)))
    rng = np.random.default_rng(SEED)
    for i, c in enumerate(cs[::-1]):
        v = pl.loc[pl.contestant == c, "earn_cv"].dropna().values
        ax.scatter(v, i + rng.uniform(-0.18, 0.18, len(v)), s=18, color=COLOR[c], alpha=0.7, edgecolors="white", linewidths=0.5)
        m = np.median(v) if len(v) else np.nan
        ax.plot([m, m], [i - 0.3, i + 0.3], color=INK, lw=2)
        ax.annotate(f"median {m:.1%}", (m, i - 0.3), xytext=(0, -3), textcoords="offset points",
                    ha="center", va="top", fontsize=8, color=INK2)
    ax.axvline(H4_THRESHOLD, color=MUTED, lw=1, ls="--")
    ax.text(H4_THRESHOLD, 0.98, " 5% threshold", color=MUTED, fontsize=8, va="top",
            transform=matplotlib.transforms.blended_transform_factory(ax.transData, ax.transAxes))
    ax.set_ylim(-0.75, len(cs) - 0.35)
    ax.set_yticks(range(len(cs))); ax.set_yticklabels([LABEL[c] for c in cs[::-1]], color=INK)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); ax.set_xlabel("Coefficient of variation of the earnings figure across 3 runs (one dot per profile)")
    ax.set_title("Consistency (H4)", loc="left", color=INK, fontsize=11, pad=10); ax.grid(axis="x"); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


# ────────────────────────────────────────────────────────────── sections ──
def section_accuracy(rep: Report, pl: pd.DataFrame):
    rep.h(2, "1. Accuracy (H1, H1b)")
    rows = []
    for c in present(pl):
        s = pl[pl.contestant == c]
        rows.append(med_row("earnings_abs", s.earn_abs, contestant=c))
        rows.append(med_row("earnings_abs_cpi_adjusted", s.earn_abs_adj, contestant=c))
        rows.append(med_row("earnings_signed", s.earn_signed, contestant=c))
        rows.append(med_row("earnings_signed_cpi_adjusted", s.earn_signed_adj, contestant=c))
        rows.append(med_row("debt_abs", s.debt_abs, contestant=c))
        rows.append(med_row("debt_signed", s.debt_signed, contestant=c))
    t = pd.DataFrame(rows)[["contestant", "measure", "n", "median", "ci_low", "ci_high"]]
    rep.p("Median error per contestant with 95% bootstrap CIs (2,000 resamples of profiles). Unit = profile; a chatbot's error per profile is the mean over its forced-number runs that gave a number.")
    rep.table("accuracy", t)
    h1 = t[t.measure == "earnings_abs"].copy()
    h1 = h1[h1.contestant != "careeriq"]
    h1["H1_decision (median abs error > 20%)"] = [decide(lo, hi, H1_THRESHOLD, "above") for lo, hi in zip(h1.ci_low, h1.ci_high)]
    rep.table("H1_decisions", h1[["contestant", "median", "ci_low", "ci_high", "H1_decision (median abs error > 20%)"]])
    h1b = t[t.measure == "earnings_signed_cpi_adjusted"].copy(); h1b = h1b[h1b.contestant != "careeriq"]
    h1b["H1b_decision (median signed error > 0, CPI-adjusted key)"] = [decide(lo, hi, 0.0, "above") for lo, hi in zip(h1b.ci_low, h1b.ci_high)]
    rep.table("H1b_decisions", h1b[["contestant", "median", "ci_low", "ci_high", "H1b_decision (median signed error > 0, CPI-adjusted key)"]])
    sec = t[t.measure == "earnings_signed"].copy(); sec = sec[sec.contestant != "careeriq"]
    rep.p("H1b secondary (unadjusted 2024-dollar key): " + "; ".join(f"{LABEL[r.contestant]} {r['median']:+.1%} [{r.ci_low:+.1%}, {r.ci_high:+.1%}]" for _, r in sec.iterrows()))
    FIG.mkdir(exist_ok=True)
    fig_accuracy(t[t.measure == "earnings_abs"], FIG / "fig1_accuracy_earnings.png", "Median absolute earnings error vs. College Scorecard (H1)", "Median absolute error, % of Scorecard 1-year median", H1_THRESHOLD)
    fig_accuracy(t[t.measure == "debt_abs"], FIG / "fig1b_accuracy_debt.png", "Median absolute debt error vs. College Scorecard", "Median absolute error, % of Scorecard median federal debt")
    return t


def group_table(pl: pd.DataFrame, col: str, by: str, groups: list) -> pd.DataFrame:
    rows = []
    for c in present(pl):
        for g in groups:
            s = pl[(pl.contestant == c) & (pl[by] == g)][col]
            m, lo, hi, n = bootstrap_median(s)
            rows.append({"contestant": c, "group": g, "n": n, "median": m, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def section_equity(rep: Report, pl: pd.DataFrame):
    rep.h(2, "2. Equity (H2): error by school group and earnings band")
    tg = group_table(pl, "earn_abs", "school_group", GROUPS)
    rep.p("Median absolute earnings error by school group (the headline equity table).")
    rep.table("equity_by_school_group", tg)
    tb = group_table(pl, "earn_abs", "earnings_band", BANDS)
    rep.table("equity_by_earnings_band", tb)
    fig_by_group(tg, FIG / "fig2_equity_by_school_group.png", "Median absolute earnings error by school group (H2)")
    # H2 decision per chatbot
    rows = []
    for c in [x for x in present(pl) if x != "careeriq"]:
        s = pl[(pl.contestant == c) & pl.school_group.isin(SELECTIVITY_RANK)].dropna(subset=["earn_abs"])
        rank = s.school_group.map(SELECTIVITY_RANK).values; err = s.earn_abs.values
        if len(s) < 8:
            rows.append({"contestant": c, "spearman_rho": np.nan, "ci_low": np.nan, "ci_high": np.nan, "cc_and_open_top2": None, "H2_decision": "inconclusive (no data)"}); continue
        rho = spearmanr(rank, err).correlation
        rng = np.random.default_rng(SEED); boots = []
        for _ in range(N_BOOT):
            i = rng.integers(0, len(s), len(s)); boots.append(spearmanr(rank[i], err[i]).correlation)
        lo, hi = np.nanpercentile(boots, 2.5), np.nanpercentile(boots, 97.5)
        meds = tg[tg.contestant == c].set_index("group")["median"]
        top2 = set(meds.sort_values(ascending=False).index[:2]) == {"Community college", "Open admission"}
        a = lo > 0; not_a = hi <= 0
        dec = "supported" if (a and top2) else ("not supported" if not_a else "inconclusive")
        rows.append({"contestant": c, "spearman_rho": rho, "ci_low": lo, "ci_high": hi, "cc_and_open_top2": top2, "H2_decision": dec})
    rep.p("H2 rule: (a) Spearman correlation between selectivity rank (Elite 1 … Open admission 4) and profile-level absolute error > 0 with the 95% CI excluding 0, and (b) Community college and Open admission have the two highest group medians. Supported if both; not supported if (a)'s CI lies entirely at or below 0; otherwise inconclusive.")
    rep.table("H2_decisions", pd.DataFrame(rows))


def section_direction(rep: Report, pl: pd.DataFrame):
    rep.h(2, "3. Direction: signed error")
    tg = group_table(pl, "earn_signed", "school_group", GROUPS)
    rep.p("Median signed earnings error by school group (+ = overestimate).")
    rep.table("signed_by_school_group", tg)
    fig_by_group(tg, FIG / "fig3_signed_by_school_group.png", "Median signed earnings error by school group", xlabel="Median signed error (+ = overestimate)", zero_line=True)
    tb = group_table(pl, "earn_signed", "earnings_band", BANDS)
    rep.table("signed_by_earnings_band", tb)
    td = group_table(pl, "debt_signed", "ownership_label", ["Public", "Private nonprofit"])
    rep.p("Median signed debt error by ownership.")
    rep.table("debt_signed_by_ownership", td)


def section_honesty(rep: Report, pl: pd.DataFrame, f: pd.DataFrame, coding: pd.DataFrame | None):
    rep.h(2, "4. Honesty (H3): caveats, sources, confident-and-wrong, range coverage")
    rows = []
    for c in [x for x in present(pl) if x != "careeriq"]:
        s = f[(f.contestant == c)]
        cov = s.earn_range_covers.dropna()
        rows.append({"contestant": c, "F_answers_with_earnings_range": int(s.earnings_low.notna().sum()),
                     "earnings_range_coverage": cov.mean() if len(cov) else np.nan,
                     "debt_range_coverage": s.debt_range_covers.dropna().mean() if s.debt_range_covers.notna().any() else np.nan})
    rep.p("Range coverage (forced-number answers that gave a range): share whose range contains the Scorecard value.")
    rep.table("range_coverage", pd.DataFrame(rows))
    if coding is None:
        rep.p("**Caveat, source type, confident-and-wrong: not yet available.** Hand coding of real-student answers (scoring/codebook.md) has not been completed. H3 decision: pending.")
        return
    rows = []
    for c in sorted(coding.contestant.unique()):
        s = coding[coding.contestant == c]
        n = len(s); k = int(((s.caveat == "yes") | (s.gives_range == "yes")).sum())
        p_, lo, hi = wilson_ci(k, n)
        rows.append({"contestant": c, "n_R": n, "share_caveat_or_range": p_, "ci_low": lo, "ci_high": hi,
                     "H3_decision (share < 50%)": decide(lo, hi, H3_THRESHOLD, "below"),
                     "caveat": (s.caveat == "yes").mean(), "caveat_uncertainty": (s.caveat_uncertainty == "yes").mean(),
                     "caveat_factor": (s.caveat_factor == "yes").mean(), "caveat_official": (s.caveat_official == "yes").mean(),
                     "source_none": (s.source_type == "none").mean(), "source_generic": (s.source_type == "generic").mean(),
                     "source_specific": (s.source_type == "specific").mean(),
                     "specific_false": (s.source_verified == "false").mean(),
                     "confident_and_wrong": s.confident_and_wrong.mean() if "confident_and_wrong" in s else np.nan})
    rep.table("H3_honesty", pd.DataFrame(rows))


def section_consistency(rep: Report, pl: pd.DataFrame):
    rep.h(2, "5. Consistency (H4): coefficient of variation across the 3 forced-number runs")
    rows = []
    for c in [x for x in present(pl) if x != "careeriq"]:
        s = pl[pl.contestant == c]
        m, lo, hi, n = bootstrap_median(s.earn_cv)
        rows.append({"contestant": c, "n_profiles": n, "median_cv": m, "ci_low": lo, "ci_high": hi,
                     "share_cv_over_5pct": (s.earn_cv > H4_THRESHOLD).mean() if n else np.nan,
                     "p90_cv": s.earn_cv.quantile(0.9) if n else np.nan,
                     "H4_decision (median CV > 5%)": decide(lo, hi, H4_THRESHOLD, "above"),
                     "median_debt_cv": s.debt_cv.median() if n else np.nan})
    rep.table("H4_consistency", pd.DataFrame(rows))
    if any(c != "careeriq" for c in present(pl)):
        fig_cv(pl, FIG / "fig4_consistency_cv.png")


def careeriq_block(rep: Report, pl: pd.DataFrame, f: pd.DataFrame, label: str):
    """H5-H7 on a CareerIQ-scored set (either the 150 profiles or all eligible training rows)."""
    s = pl[pl.contestant == "careeriq"].copy()
    s["cip4"] = s.cip4.astype(str).str.zfill(4)
    hc = s[s.cip4.map(HIGH_CEILING)]; cp = s[s.cip4.map(COMPRESSED)]
    m1, lo1, hi1, n1 = bootstrap_median(hc.earn_signed); m2, lo2, hi2, n2 = bootstrap_median(cp.earn_signed)
    h5 = "supported" if (lo1 > 0 and hi2 < 0) else ("not supported" if (hi1 < 0 or lo2 > 0) else "inconclusive")
    if n1 == 0 or n2 == 0: h5 = "inconclusive (no data)"
    rep.table(f"H5_{label}", pd.DataFrame([
        {"field_group": "high-ceiling (CIP 11.xx, 14.09, 52.08)", "n": n1, "median_signed_error": m1, "ci_low": lo1, "ci_high": hi1},
        {"field_group": "compressed-pay (CIP 51.38, 13.xx)", "n": n2, "median_signed_error": m2, "ci_low": lo2, "ci_high": hi2}]))
    rep.p(f"**H5 decision ({label}): {h5}.** Rule: median signed error > 0 for high-ceiling and < 0 for compressed-pay, both CIs excluding 0.")
    # H6: among multiplier > 1 rows, bottom band minus top band
    if "earnings_multiplier" in s:
        hi_sch = s[s.earnings_multiplier > 1.0]
        bot = hi_sch[hi_sch.earnings_band == "Bottom"].earn_signed; top = hi_sch[hi_sch.earnings_band == "Top"].earn_signed
        d, lo, hi = bootstrap_median_diff(bot, top)
        h6 = "supported" if lo > 0 else ("not supported" if hi <= 0 else "inconclusive")
        if len(bot) == 0 or len(top) == 0: h6 = "inconclusive (no data)"
        rep.table(f"H6_{label}", pd.DataFrame([{"rows_with_multiplier_gt_1": len(hi_sch), "n_bottom_band": len(bot), "n_top_band": len(top),
                                                "median_signed_bottom": bot.median(), "median_signed_top": top.median(),
                                                "difference": d, "ci_low": lo, "ci_high": hi}]))
        rep.p(f"**H6 decision ({label}): {h6}.** Rule: among schools with multiplier > 1, median signed error (bottom band) − (top band) > 0 with CI excluding 0.")
    m, lo, hi, n = bootstrap_median(s.debt_signed)
    h7 = decide(lo, hi, 0.0, "above")
    mf, lof, hif, nf = bootstrap_median(s.debt_fed_signed) if "debt_fed_signed" in s else (np.nan,) * 4
    rep.table(f"H7_{label}", pd.DataFrame([
        {"comparison": "full estimate (net price x years) vs Scorecard federal debt", "n": n, "median_signed": m, "ci_low": lo, "ci_high": hi, "decision": h7},
        {"comparison": "federal portion min(total, cap) vs Scorecard federal debt (secondary, descriptive)", "n": nf, "median_signed": mf, "ci_low": lof, "ci_high": hif, "decision": "—"}]))
    rep.p(f"**H7 decision ({label}): {h7}.**")
    # descriptive extras
    extra = [{"check": "overall median signed earnings error (BLS mean vs median question)", **dict(zip(["median", "ci_low", "ci_high", "n"], bootstrap_median(s.earn_signed)))}]
    if "earnings_multiplier" in s:
        capped = s[s.earnings_multiplier >= 1.6]; rest = s[s.earnings_multiplier < 1.6]
        extra.append({"check": "median abs error, schools capped at 1.60", **dict(zip(["median", "ci_low", "ci_high", "n"], bootstrap_median(capped.earn_abs)))})
        extra.append({"check": "median abs error, schools below the cap", **dict(zip(["median", "ci_low", "ci_high", "n"], bootstrap_median(rest.earn_abs)))})
    rep.table(f"careeriq_descriptive_{label}", pd.DataFrame(extra))


def section_careeriq(rep: Report, pl: pd.DataFrame, f: pd.DataFrame):
    rep.h(2, "6. CareerIQ assumptions (H5–H7)")
    est = pd.read_csv(PROCESSED / "careeriq_estimates.csv")[["profile_id", "earnings_multiplier"]]
    pl150 = pl.merge(est, on="profile_id", how="left")
    allrows = PROCESSED / "careeriq_all_eligible_scored.csv"
    if allrows.exists():
        rep.h(3, "6a. Primary test: all eligible rows at training schools (D19)")
        a = pd.read_csv(allrows); a["contestant"] = "careeriq"
        careeriq_block(rep, a, None, "all_training_rows")
    else:
        rep.h(3, "6a. Primary test: all eligible rows at training schools (D19)")
        rep.p("**Not yet available**: `data/processed/careeriq_all_eligible_scored.csv` has not been built (runners/run_careeriq_all.mjs).")
    rep.h(3, "6b. The 150 study profiles (for comparison)")
    careeriq_block(rep, pl150, f, "150_profiles")


def section_robustness(rep: Report, pl: pd.DataFrame, f: pd.DataFrame):
    rep.h(2, "7. Robustness")
    rows = []
    for c in present(pl):
        s = pl[pl.contestant == c]
        for name, col in [("abs error vs 5-yr earnings (a)", "earn5_abs"), ("signed error vs 5-yr earnings (a)", "earn5_signed"),
                          ("signed debt error vs debt at any school (b)", "debt_any_signed"),
                          ("abs earnings error, CPI-adjusted key (e)", "earn_abs_adj"), ("abs debt error (unchanged, nominal) (e)", "debt_abs")]:
            rows.append(med_row(name, s[col], contestant=c))
        wm, wlo, whi, wn = weighted_bootstrap_median(s.earn_abs, s.weight)
        rows.append({"contestant": c, "measure": "abs earnings error, reweighted by cell share of eligible rows (f)", "n": wn, "median": wm, "ci_low": wlo, "ci_high": whi})
        wm, wlo, whi, wn = weighted_bootstrap_median(s.debt_abs, s.weight)
        rows.append({"contestant": c, "measure": "abs debt error, reweighted (f)", "n": wn, "median": wm, "ci_low": wlo, "ci_high": whi})
    rep.table("robustness", pd.DataFrame(rows)[["contestant", "measure", "n", "median", "ci_low", "ci_high"]])
    rep.p("(c) App spot check vs API and (d) crosswalk sensitivity are reported in their own sections when those inputs exist (scoring/spot_check_template.csv; runners/run_careeriq.mjs with alternate crosswalks).")


def section_exploratory(rep: Report, pl: pd.DataFrame, f: pd.DataFrame):
    rep.h(2, "8. Exploratory (labeled as such)")
    rep.h(3, "8a. Regression of log(absolute earnings error + 0.01)")
    d = pl.dropna(subset=["earn_abs"]).copy()
    if d.contestant.nunique() >= 2 and len(d) >= 30:
        import statsmodels.formula.api as smf
        d["y"] = np.log(d.earn_abs + 0.01)
        d["school_group"] = pd.Categorical(d.school_group, GROUPS); d["earnings_band"] = pd.Categorical(d.earnings_band, BANDS)
        d["contestant"] = pd.Categorical(d.contestant, present(d))
        d = d.reset_index(drop=True)
        d["cluster"] = pd.factorize(d.profile_id)[0]
        m = smf.ols("y ~ C(school_group) + C(earnings_band) + C(contestant)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d.cluster.values})
        t = pd.DataFrame({"term": m.params.index, "coef": m.params.values, "se_cluster_profile": m.bse.values, "p": m.pvalues.values})
        rep.p(f"OLS, standard errors clustered by profile, n = {int(m.nobs)}, R² = {m.rsquared:.3f}. Baselines: {GROUPS[0]}, {BANDS[0]}, {LABEL[d.contestant.cat.categories[0]]}. Coefficients are differences in log error (0.69 ≈ 2×).")
        rep.table("exploratory_regression", t, floatfmt=3)
    else:
        rep.p("Not enough data for the regression yet.")
    rep.h(3, "8b. Scope substitution: which Scorecard value is each chatbot figure closest to?")
    s = f[f.contestant != "careeriq"].dropna(subset=["closest_to"])
    if len(s):
        ct = pd.crosstab([s.contestant, s.school_group], s.closest_to, normalize="index").reset_index()
        rep.p("Share of forced-number earnings figures closest (in % terms) to the program-level value, the field's national median, or the school's all-majors median (MD_EARN_WNE_P10). Descriptive only.")
        rep.table("scope_substitution", ct)
        overall = pd.crosstab(s.contestant, s.closest_to, normalize="index").reset_index()
        rep.table("scope_substitution_overall", overall)
    else:
        rep.p("No chatbot answers yet.")


def section_refusals(rep: Report, out: Path):
    rep.h(2, "0. Data collected")
    r = pd.read_csv(out / "refusals.csv")
    rep.table("data_collected", r)


def load_coding(out: Path):
    """Merge the hand-coding sheet with the key, if coding is complete."""
    d = REPO / "runs" / "coding"
    if not (d / "R_primary.csv").exists():
        return None
    a = pd.read_csv(d / "R_primary.csv", dtype=str).fillna("")
    if (a.caveat_uncertainty == "").all():
        return None
    key = pd.read_csv(d / "KEY_do_not_open.csv", dtype=str)
    a = a.merge(key, on="answer_id")
    for c in ["caveat_uncertainty", "caveat_factor", "caveat_official", "gives_range", "source_type", "source_verified"]:
        a[c] = a[c].str.strip().str.lower()
    a["caveat"] = np.where((a.caveat_uncertainty == "yes") | (a.caveat_factor == "yes") | (a.caveat_official == "yes"), "yes", "no")
    truth = pd.read_csv(out / "truth.csv")[["profile_id", "sc_earn_1yr"]]
    a = a.merge(truth, on="profile_id", how="left")
    ev = pd.to_numeric(a.earnings_value, errors="coerce"); lo = pd.to_numeric(a.earnings_low, errors="coerce"); hi = pd.to_numeric(a.earnings_high, errors="coerce")
    est = ev.where(ev.notna(), (lo + hi) / 2)
    err = np.abs((est - a.sc_earn_1yr) / a.sc_earn_1yr)
    a["confident_and_wrong"] = np.where(est.isna(), np.nan, ((err > 0.25) & (a.caveat == "no")).astype(float))
    return a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", type=Path, default=REPO / "scoring" / "out")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    out = args.out_dir.resolve()
    pl = pd.read_csv(out / "profile_level.csv", dtype={"cip4": str})
    f = pd.read_csv(out / "f_answers.csv", dtype={"cip4": str})
    rep = Report()
    rep.h(1, "Results" + (f" ({args.tag})" if args.tag else ""))
    rep.p(f"Generated by analysis/results.py from {out.relative_to(REPO) if out.is_relative_to(REPO) else out}. Every section follows preregistration.md section 5; decision rules are applied mechanically. Contestants present: {', '.join(LABEL[c] for c in present(pl))}.")
    section_refusals(rep, out)
    section_accuracy(rep, pl)
    section_equity(rep, pl)
    section_direction(rep, pl)
    section_honesty(rep, pl, f, load_coding(out))
    section_consistency(rep, pl)
    section_careeriq(rep, pl, f)
    section_robustness(rep, pl, f)
    section_exploratory(rep, pl, f)
    rep.write(ANALYSIS / "results.md")
    print(f"wrote analysis/results.md, {len(rep.tables)} tables in analysis/results_tables/, figures in analysis/figures/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
