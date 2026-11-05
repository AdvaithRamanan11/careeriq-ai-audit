"""
Build the scored tables every analysis reads from.

Inputs
  runs/<contestant>.jsonl                 raw chatbot answers (final rows only)
  runs/<contestant>_needs_review.csv      hand-review fixes for F answers the extractor flagged
                                          (earnings_fixed, debt_fixed, format_refused)
  data/processed/careeriq_estimates.csv   CareerIQ at ba51be3
  data/processed/profiles.csv             the 150 profiles with Scorecard truth
  data/processed/sample_counts.csv        eligible rows per cell (weights for robustness 7f)
  data/raw/Most-Recent-Cohorts-Institution.csv   MD_EARN_WNE_P10 for exploratory 8b
  analysis/cpi_u.csv                      CPI-U factors (robustness 7e; H1b primary)

Outputs (in scoring/out/)
  truth.csv           one row per profile: Scorecard values, CPI-adjusted values, weight, school-level earnings
  f_answers.csv       one row per forced-number answer (chatbots) or estimate (CareerIQ), with errors
  profile_level.csv   one row per contestant x profile (mean over runs), the unit of analysis
  r_answers.csv       one row per real-student answer, ready to join with the coding sheets
  refusals.csv        per contestant: refusals, format refusals, empties, errors

Rules (preregistration sections in brackets)
  - A range is scored at its midpoint [4.1].
  - A hand-review fix overrides the extractor; format_refused = yes keeps the fixed figure and sets a flag [deviations 1].
  - Chatbot truth for the CPI check uses the month of each answer's timestamp; CareerIQ uses May 2025 [7e, D29].
  - Unit of analysis = profile; a chatbot's error per profile = mean over F runs that gave a number [4.2].
  - CV needs at least 2 numeric runs [5].
  - weight = cell's share of eligible rows / share of sample [7f].

Usage: python scoring/assemble.py [--runs-dir runs]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import INST_CSV, PROCESSED, REPO  # noqa: E402
from scoring.metrics import coefficient_of_variation, pct_error, covers  # noqa: E402

OUT = REPO / "scoring" / "out"
CAREERIQ_CPI_MONTH = (2025, 5)   # D29: CareerIQ's BLS wages are May 2025 OEWS dollars


def load_cpi() -> dict:
    c = pd.read_csv(REPO / "analysis" / "cpi_u.csv")
    return {(int(r.year), int(r.month)): float(r.factor_from_2024) for r in c.itertuples()}


def cpi_factor(cpi: dict, year: int, month: int) -> tuple[float, str]:
    """Factor for a month; if unpublished, fall back to the latest month and say so."""
    if (year, month) in cpi:
        return cpi[(year, month)], f"{year}-{month:02d}"
    latest = max(cpi)
    return cpi[latest], f"{latest[0]}-{latest[1]:02d} (latest published; {year}-{month:02d} not yet available)"


def build_truth(cpi: dict) -> pd.DataFrame:
    p = pd.read_csv(PROCESSED / "profiles.csv", dtype={"UNITID": str, "cip4": str})
    counts = pd.read_csv(PROCESSED / "sample_counts.csv")
    counts["weight"] = (counts.eligible_rows / counts.eligible_rows.sum()) / (counts.sampled / counts.sampled.sum())
    p = p.merge(counts[["school_group", "earnings_band", "eligible_rows", "weight"]],
                on=["school_group", "earnings_band"], how="left", validate="many_to_one")
    inst = pd.read_csv(INST_CSV, usecols=["UNITID", "MD_EARN_WNE_P10"], dtype=str)
    inst["sc_school_all_majors_earn"] = pd.to_numeric(inst.MD_EARN_WNE_P10, errors="coerce")
    # many_to_one: a school can appear in several profiles (different majors, different cells)
    p = p.merge(inst[["UNITID", "sc_school_all_majors_earn"]], on="UNITID", how="left", validate="many_to_one")
    f, label = cpi_factor(cpi, *CAREERIQ_CPI_MONTH)
    p["cpi_factor_careeriq"] = f
    p["cpi_month_careeriq"] = label
    p["sc_earn_1yr_adj_careeriq"] = p.sc_earn_1yr * f
    p["sc_earn_5yr_adj_careeriq"] = p.sc_earn_5yr * f
    return p


def load_fixes(path: Path) -> dict:
    fixes = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                fixes[(row["profile_id"], int(row["run"]))] = row
    return fixes


def to_num(s: str):
    s = (s or "").strip().replace("$", "").replace(",", "")
    return float(s) if s else None


def chatbot_rows(runs_dir: Path, cpi: dict) -> tuple[list, list, list]:
    f_rows, r_rows, tally = [], [], []
    for path in sorted(runs_dir.glob("*.jsonl")):
        c = path.stem
        fixes = load_fixes(runs_dir / f"{c}_needs_review.csv")
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        final = [r for r in rows if r.get("final")]
        t = {"contestant": c, "model_returned": ",".join(sorted({r.get("model_returned") or "" for r in final})),
             "calls_final": len(final), "errors_logged": sum(r["status"] == "error" for r in rows),
             "api_refusals": sum(r["status"] == "refusal" for r in final),
             "empty": sum(r["status"] == "empty" for r in final), "format_refused": 0, "no_number_after_review": 0,
             "fixed_by_hand": 0}
        for r in final:
            y, m = int(r["timestamp"][:4]), int(r["timestamp"][5:7])
            factor, label = cpi_factor(cpi, y, m)
            base = {"contestant": c, "profile_id": r["profile_id"], "run": r["run"], "prompt_type": r["prompt_type"],
                    "model_returned": r.get("model_returned"), "timestamp": r["timestamp"], "status": r["status"],
                    "cpi_factor": factor, "cpi_month": label, "raw_text": r["raw_text"]}
            if r["prompt_type"] == "R":
                r_rows.append(base)
                continue
            ex = r.get("extracted") or {}
            row = dict(base, earnings=ex.get("earnings"), debt=ex.get("debt"),
                       earnings_low=ex.get("earnings_low"), earnings_high=ex.get("earnings_high"),
                       debt_low=ex.get("debt_low"), debt_high=ex.get("debt_high"),
                       extract_status=ex.get("extract_status", r["status"]), format_refused=False, hand_fixed=False)
            fix = fixes.get((r["profile_id"], r["run"]))
            if fix is not None:
                ef, df_ = to_num(fix.get("earnings_fixed")), to_num(fix.get("debt_fixed"))
                if ef is not None or df_ is not None:
                    row.update(earnings=ef, debt=df_, hand_fixed=True)
                    t["fixed_by_hand"] += 1
                if (fix.get("format_refused") or "").strip().lower() == "yes":
                    row["format_refused"] = True
                    t["format_refused"] += 1
            if row["earnings"] is None and row["debt"] is None:
                t["no_number_after_review"] += 1
            f_rows.append(row)
        tally.append(t)
    return f_rows, r_rows, tally


def careeriq_rows(truth: pd.DataFrame) -> list:
    e = pd.read_csv(PROCESSED / "careeriq_estimates.csv", dtype={"UNITID": str})
    e = e.merge(truth[["profile_id", "cpi_factor_careeriq", "cpi_month_careeriq"]], on="profile_id")
    return [{"contestant": "careeriq", "profile_id": r.profile_id, "run": 1, "prompt_type": "F",
             "model_returned": f"careeriq@{r.careeriq_commit}", "timestamp": None, "status": "ok",
             "cpi_factor": r.cpi_factor_careeriq, "cpi_month": r.cpi_month_careeriq, "raw_text": None,
             "earnings": r.ciq_salary, "debt": r.ciq_debt, "debt_federal_portion": r.ciq_debt_federal_portion,
             "earnings_low": None, "earnings_high": None, "debt_low": None, "debt_high": None,
             "extract_status": "ok", "format_refused": False, "hand_fixed": False} for r in e.itertuples()]


def score(f: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    cols = ["profile_id", "school_group", "earnings_band", "state", "ownership_label", "cip4", "prompt_major",
            "major_id", "job_id", "weight", "sc_earn_1yr", "sc_earn_5yr", "sc_nat_earn_1yr", "sc_debt_eval",
            "sc_debt_any", "sc_school_all_majors_earn"]
    d = f.merge(truth[cols], on="profile_id", how="left", validate="many_to_one")
    d["sc_earn_1yr_adj"] = d.sc_earn_1yr * d.cpi_factor          # truth in the answer's own dollars
    d["sc_earn_5yr_adj"] = d.sc_earn_5yr * d.cpi_factor
    d["earn_signed"] = pct_error(d.earnings, d.sc_earn_1yr)
    d["earn_abs"] = np.abs(d.earn_signed)
    d["earn_signed_adj"] = pct_error(d.earnings, d.sc_earn_1yr_adj)
    d["earn_abs_adj"] = np.abs(d.earn_signed_adj)
    d["earn5_signed"] = pct_error(d.earnings, d.sc_earn_5yr)
    d["earn5_abs"] = np.abs(d.earn5_signed)
    d["earn5_signed_adj"] = pct_error(d.earnings, d.sc_earn_5yr_adj)
    d["debt_signed"] = pct_error(d.debt, d.sc_debt_eval)
    d["debt_abs"] = np.abs(d.debt_signed)
    d["debt_any_signed"] = pct_error(d.debt, d.sc_debt_any)
    if "debt_federal_portion" in d:
        d["debt_fed_signed"] = pct_error(d.debt_federal_portion, d.sc_debt_eval)
    d["badly_wrong"] = np.where(d.earn_abs.isna(), np.nan, (d.earn_abs > 0.25).astype(float))
    d["earn_range_covers"] = covers(d.earnings_low, d.earnings_high, d.sc_earn_1yr)
    d["debt_range_covers"] = covers(d.debt_low, d.debt_high, d.sc_debt_eval)
    # Exploratory 8b: which Scorecard value is the figure closest to, in percentage terms?
    cand = pd.DataFrame({"program": np.abs(pct_error(d.earnings, d.sc_earn_1yr)),
                         "national_field": np.abs(pct_error(d.earnings, d.sc_nat_earn_1yr)),
                         "school_all_majors": np.abs(pct_error(d.earnings, d.sc_school_all_majors_earn))})
    d["closest_to"] = np.where(d.earnings.isna(), None, cand.idxmin(axis=1))
    return d


def profile_level(scored: pd.DataFrame) -> pd.DataFrame:
    g = scored.groupby(["contestant", "profile_id"])
    out = g.agg(
        n_runs=("run", "size"), n_earn=("earnings", lambda s: int(s.notna().sum())),
        n_debt=("debt", lambda s: int(s.notna().sum())),
        earn_abs=("earn_abs", "mean"), earn_signed=("earn_signed", "mean"),
        earn_abs_adj=("earn_abs_adj", "mean"), earn_signed_adj=("earn_signed_adj", "mean"),
        earn5_abs=("earn5_abs", "mean"), earn5_signed=("earn5_signed", "mean"),
        debt_abs=("debt_abs", "mean"), debt_signed=("debt_signed", "mean"), debt_any_signed=("debt_any_signed", "mean"),
        badly_wrong_share=("badly_wrong", "mean"),
        earn_range_coverage=("earn_range_covers", "mean"), debt_range_coverage=("debt_range_covers", "mean"),
        earn_cv=("earnings", lambda s: coefficient_of_variation(s.tolist())),
        debt_cv=("debt", lambda s: coefficient_of_variation(s.tolist())),
        any_format_refused=("format_refused", "max"),
    ).reset_index()
    if "debt_fed_signed" in scored:
        out = out.merge(scored.groupby(["contestant", "profile_id"]).debt_fed_signed.mean().reset_index(),
                        on=["contestant", "profile_id"], how="left")
    keys = ["profile_id", "school_group", "earnings_band", "state", "ownership_label", "cip4", "prompt_major",
            "major_id", "weight", "sc_earn_1yr", "sc_debt_eval"]
    return out.merge(scored[keys].drop_duplicates("profile_id"), on="profile_id", how="left")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", type=Path, default=REPO / "runs")
    args = ap.parse_args()
    runs_dir = args.runs_dir.resolve()
    cpi = load_cpi()
    truth = build_truth(cpi)
    f_rows, r_rows, tally = chatbot_rows(runs_dir, cpi)
    f = pd.DataFrame(f_rows + careeriq_rows(truth))
    scored = score(f, truth)
    pl = profile_level(scored)
    OUT.mkdir(exist_ok=True)
    truth.to_csv(OUT / "truth.csv", index=False, lineterminator="\n")
    scored.drop(columns=["raw_text"]).to_csv(OUT / "f_answers.csv", index=False, lineterminator="\n")
    pl.to_csv(OUT / "profile_level.csv", index=False, lineterminator="\n")
    pd.DataFrame(r_rows).to_csv(OUT / "r_answers.csv", index=False, lineterminator="\n")
    pd.DataFrame(tally).to_csv(OUT / "refusals.csv", index=False, lineterminator="\n")
    print(f"truth: {len(truth)} profiles | F rows: {len(scored)} | profile-level: {len(pl)} | R rows: {len(r_rows)}")
    print(pd.DataFrame(tally).to_string(index=False))
    print("profiles per contestant:", pl.groupby("contestant").size().to_dict())
    print(f"wrote {OUT.relative_to(REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
