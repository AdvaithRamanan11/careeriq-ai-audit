"""
Fix two random selections before any results are seen, so neither can be tuned later.

1. Holdout schools for the CareerIQ rebuild (PRD "Validation"):
   20% of CareerIQ's schools are held out entirely. Any recalibration (for example,
   field-specific entry ratios) is fit only on the other 80%, and the rebuilt
   model's fallback is scored only on held-out schools. The split is stratified by
   school group so each group loses the same share, and it uses a seeded shuffle
   of the sorted school IDs, so it can be reproduced.
   -> data/processed/holdout_schools.csv

2. Consumer-app spot check (PRD "Query protocol"):
   30 profiles, 2 from each of the 15 cells, picked with seed 2026. Advaith runs
   these by hand in each chatbot's free app.
   -> data/processed/spot_check_profiles.csv
   -> scoring/spot_check_template.csv  (one row per profile x chatbot x prompt, to fill in)

Usage: python data/make_splits.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO  # noqa: E402
from data.sample_profiles import GROUPS, school_groups  # noqa: E402

SEED = 2026
HOLDOUT_SHARE = 0.20
SPOT_PER_CELL = 2
SPOT_CHATBOTS = ["chatgpt", "gemini", "claude"]


def holdout() -> pd.DataFrame:
    g = school_groups()
    g["school_group"] = g.school_group.fillna("Excluded (no admission rate, not open-admission)")
    out = []
    for i, (grp, sub) in enumerate(sorted(g.groupby("school_group"), key=lambda x: x[0])):
        ids = sorted(sub.UNITID)
        rng = np.random.default_rng([SEED, 99, i])
        order = rng.permutation(len(ids))
        n_hold = round(len(ids) * HOLDOUT_SHARE)
        hold = {ids[k] for k in order[:n_hold]}
        out += [{"UNITID": u, "school_group": grp, "split": "holdout" if u in hold else "train"} for u in ids]
    return pd.DataFrame(out).sort_values("UNITID")


def spot_check(profiles: pd.DataFrame) -> pd.DataFrame:
    picks = []
    for gi, grp in enumerate(GROUPS):
        for bi, band in enumerate(["Bottom", "Middle", "Top"]):
            cell = profiles[(profiles.school_group == grp) & (profiles.earnings_band == band)].sort_values("profile_id")
            rng = np.random.default_rng([SEED, 7, gi, bi])
            idx = sorted(rng.choice(len(cell), size=min(SPOT_PER_CELL, len(cell)), replace=False))
            picks.append(cell.iloc[idx])
    return pd.concat(picks)


def main() -> int:
    h = holdout()
    h.to_csv(PROCESSED / "holdout_schools.csv", index=False, lineterminator="\n")
    print("Holdout split by school group:")
    print(h.groupby(["school_group", "split"]).size().unstack(fill_value=0).to_string())

    profiles = pd.read_csv(PROCESSED / "profiles.csv", dtype=str)
    in_hold = profiles.UNITID.isin(set(h.loc[h.split == "holdout", "UNITID"]))
    print(f"\nSample profiles at held-out schools: {in_hold.sum()} of {len(profiles)}")

    s = spot_check(profiles)
    s[["profile_id", "school_group", "earnings_band", "school", "INSTNM", "state", "prompt_major"]].to_csv(
        PROCESSED / "spot_check_profiles.csv", index=False, lineterminator="\n")

    prompts = json.loads((REPO / "prompts" / "v1.json").read_text(encoding="utf-8"))["templates"]
    rows = []
    for _, p in s.iterrows():
        for bot in SPOT_CHATBOTS:
            for ptype in ("R", "F"):
                rows.append({
                    "profile_id": p.profile_id, "chatbot": bot, "prompt_type": ptype,
                    "prompt_text": prompts[ptype].format(major=p.prompt_major, school=p.INSTNM),
                    "date": "", "model_shown_in_app": "", "logged_in": "", "web_search_used": "",
                    "response_text": "", "notes": "",
                })
    pd.DataFrame(rows).to_csv(REPO / "scoring" / "spot_check_template.csv", index=False, lineterminator="\n")
    print(f"Spot check: {len(s)} profiles -> {len(rows)} rows in scoring/spot_check_template.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
