"""
The scoring rubric as code. Every measure in the PRD's rubric is defined here once.

All percentage errors are relative to the Scorecard value:
    signed error   = (estimate - truth) / truth          (+ = overestimate)
    absolute error = |estimate - truth| / truth
For a range answer, the midpoint is the estimate.

Unit of analysis = profile. A chatbot's error for a profile is the mean of its
absolute errors over the forced-number runs that produced a number. Confidence
intervals come from resampling profiles (2,000 resamples, seed 2026, percentile method).
"""

import numpy as np
import pandas as pd

BADLY_WRONG = 0.25
N_BOOT = 2000
SEED = 2026


def pct_error(estimate, truth):
    estimate = np.asarray(estimate, dtype=float)
    truth = np.asarray(truth, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(truth > 0, (estimate - truth) / truth, np.nan)


def covers(low, high, truth):
    low, high, truth = (np.asarray(x, dtype=float) for x in (low, high, truth))
    out = (low <= truth) & (truth <= high)
    return np.where(np.isnan(low) | np.isnan(high), np.nan, out.astype(float))


def coefficient_of_variation(values) -> float:
    """Sample SD / mean of one profile's F-run estimates. Needs at least 2 numbers."""
    v = np.asarray([x for x in values if x is not None and not np.isnan(x)], dtype=float)
    if len(v) < 2 or v.mean() == 0:
        return np.nan
    return float(v.std(ddof=1) / v.mean())


def score_runs(runs: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    """runs: one row per F answer with columns contestant, profile_id, run, earnings, debt,
    earnings_low, earnings_high, debt_low, debt_high. truth: profiles.csv."""
    t = truth[["profile_id", "sc_earn_1yr", "sc_earn_5yr", "sc_debt_eval", "sc_debt_any"]].copy()
    for c in t.columns[1:]:
        t[c] = pd.to_numeric(t[c])
    df = runs.merge(t, on="profile_id", how="left", validate="many_to_one")
    df["earn_signed"] = pct_error(df.earnings, df.sc_earn_1yr)
    df["earn_abs"] = np.abs(df.earn_signed)
    df["earn5_signed"] = pct_error(df.earnings, df.sc_earn_5yr)
    df["earn5_abs"] = np.abs(df.earn5_signed)
    df["debt_signed"] = pct_error(df.debt, df.sc_debt_eval)
    df["debt_abs"] = np.abs(df.debt_signed)
    df["debt_any_signed"] = pct_error(df.debt, df.sc_debt_any)
    df["badly_wrong"] = np.where(df.earn_abs.isna(), np.nan, (df.earn_abs > BADLY_WRONG).astype(float))
    df["earn_range_covers"] = covers(df.earnings_low, df.earnings_high, df.sc_earn_1yr)
    df["debt_range_covers"] = covers(df.debt_low, df.debt_high, df.sc_debt_eval)
    return df


def profile_level(scored: pd.DataFrame) -> pd.DataFrame:
    """Collapse runs to one row per contestant x profile."""
    agg = scored.groupby(["contestant", "profile_id"]).agg(
        n_runs=("run", "size"),
        n_earn=("earnings", lambda s: s.notna().sum()),
        earn_abs=("earn_abs", "mean"), earn_signed=("earn_signed", "mean"),
        earn5_abs=("earn5_abs", "mean"), earn5_signed=("earn5_signed", "mean"),
        debt_abs=("debt_abs", "mean"), debt_signed=("debt_signed", "mean"),
        debt_any_signed=("debt_any_signed", "mean"),
        badly_wrong_share=("badly_wrong", "mean"),
        earn_cv=("earnings", lambda s: coefficient_of_variation(s.tolist())),
        debt_cv=("debt", lambda s: coefficient_of_variation(s.tolist())),
    ).reset_index()
    return agg


def bootstrap_median(values, n_boot: int = N_BOOT, seed: int = SEED):
    """Median with a 95% percentile bootstrap CI. NaNs dropped. Returns (median, lo, hi, n)."""
    v = np.asarray([x for x in values if not pd.isna(x)], dtype=float)
    if len(v) == 0:
        return (np.nan, np.nan, np.nan, 0)
    rng = np.random.default_rng(seed)
    boots = np.median(rng.choice(v, size=(n_boot, len(v)), replace=True), axis=1)
    return (float(np.median(v)), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)), len(v))


def bootstrap_median_diff(a, b, n_boot: int = N_BOOT, seed: int = SEED):
    """Median(a) - median(b) with a 95% bootstrap CI, resampling each group separately."""
    a = np.asarray([x for x in a if not pd.isna(x)], dtype=float)
    b = np.asarray([x for x in b if not pd.isna(x)], dtype=float)
    if len(a) == 0 or len(b) == 0:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    da = np.median(rng.choice(a, size=(n_boot, len(a))), axis=1)
    db = np.median(rng.choice(b, size=(n_boot, len(b))), axis=1)
    d = da - db
    return (float(np.median(a) - np.median(b)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))


def wilson_ci(successes: int, n: int, z: float = 1.959964):
    """Share with a 95% Wilson score interval (for H3 caveat/range shares)."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (p, centre - half, centre + half)


def cohens_kappa(a, b) -> float:
    """Cohen's kappa for two coders' labels on the same items (any number of categories)."""
    a, b = list(a), list(b)
    assert len(a) == len(b) and len(a) > 0
    cats = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


if __name__ == "__main__":
    # Self-tests on made-up numbers only (no study data).
    assert np.isclose(pct_error(55_000, 50_000), 0.10)
    assert np.isclose(pct_error(45_000, 50_000), -0.10)
    assert covers(40_000, 60_000, 50_000) == 1.0 and covers(40_000, 45_000, 50_000) == 0.0
    assert np.isclose(coefficient_of_variation([100, 100, 100]), 0.0)
    assert np.isclose(coefficient_of_variation([90, 100, 110]), 10 / 100)
    assert np.isnan(coefficient_of_variation([100]))
    m, lo, hi, n = bootstrap_median([0.1, 0.2, 0.3, 0.4, 0.5])
    assert m == 0.3 and lo <= m <= hi and n == 5
    p, lo, hi = wilson_ci(40, 100)
    assert np.isclose(p, 0.4) and np.isclose(lo, 0.3094, atol=1e-3) and np.isclose(hi, 0.4980, atol=1e-3)
    # Kappa: textbook example (Cohen 1960 style): 20 yes/yes, 15 no/no, 5 + 10 disagreements -> 0.40
    a = ["y"] * 20 + ["y"] * 5 + ["n"] * 10 + ["n"] * 15
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert np.isclose(cohens_kappa(a, b), 0.40), cohens_kappa(a, b)
    assert cohens_kappa(["a", "b", "c"], ["a", "b", "c"]) == 1.0

    runs = pd.DataFrame({"contestant": "x", "profile_id": ["P1"] * 3, "run": [1, 2, 3],
                         "earnings": [60_000, 50_000, 55_000], "debt": [20_000, 20_000, 20_000],
                         "earnings_low": [np.nan, 45_000, np.nan], "earnings_high": [np.nan, 55_000, np.nan],
                         "debt_low": np.nan, "debt_high": np.nan})
    truth = pd.DataFrame({"profile_id": ["P1"], "sc_earn_1yr": [50_000], "sc_earn_5yr": [60_000],
                          "sc_debt_eval": [25_000], "sc_debt_any": [26_000]})
    s = score_runs(runs, truth)
    assert np.allclose(s.earn_abs, [0.2, 0.0, 0.1]) and s.earn_range_covers.iloc[1] == 1.0
    pl = profile_level(s)
    assert np.isclose(pl.earn_abs.iloc[0], 0.1) and np.isclose(pl.debt_signed.iloc[0], -0.2)
    assert np.isclose(pl.badly_wrong_share.iloc[0], 0.0)
    print("All metric self-tests passed.")
