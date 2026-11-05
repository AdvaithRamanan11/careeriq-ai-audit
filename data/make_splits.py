"""
Fix two random selections before any results are seen, so neither can be tuned later.

1. Holdout schools for the CareerIQ rebuild (PRD "Validation"):
   20% of CareerIQ's schools are held out entirely. Any recalibration (for example,
   field-specific entry ratios) is fit only on the other 80%, and the rebuilt
   model's fallback is scored only on held-out schools. The split is stratified by
   school group so each group loses the same share, and it uses a seeded shuffle
   of the sorted school IDs, so it can be reproduced.
   -> data/processed/holdout_schools.csv

2. Consumer-app spot check (PRD "Query protocol"; D18):
   30 profiles, 2 from each of the 15 cells, picked with seed 2026. Advaith runs
   the real-student (R) prompt once per profile in each chatbot's free app.
   -> data/processed/spot_check_profiles.csv
   -> scoring/spot_check_template.csv  (one row per profile x chatbot = 90 rows, to fill in)

3. Pilot profiles (D17): 10 school-and-major rows that are NOT among the 150 study
   profiles, used only to test parsing, refusals and cost. Drawn from the same
   eligible pool as the study sample, minus the 150 sampled rows: 10 of the 15
   cells are chosen by a seeded shuffle, and one random row is taken from each
   (at most one per school). Scorecard values are deliberately left out of the
   file, so no error can be computed from the pilot.
   -> data/processed/pilot_profiles.csv

Usage: python data/make_splits.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO, prompt_school  # noqa: E402
from data.sample_profiles import BANDS, GROUPS, eligible_rows, school_groups  # noqa: E402

SEED = 2026
HOLDOUT_SHARE = 0.20
SPOT_PER_CELL = 2
SPOT_CHATBOTS = ["chatgpt", "gemini", "claude"]
PILOT_N = 10
PILOT_COLS = ["profile_id", "school_group", "earnings_band", "UNITID", "INSTNM", "state",
              "cip4", "CIPDESC", "prompt_major", "job_id"]


def pilot(profiles: pd.DataFrame) -> pd.DataFrame:
    rows, draft, _ = eligible_rows()
    assert not draft, "crosswalk still has judgment rows"
    sampled = set(zip(profiles.UNITID, profiles.cip4, profiles.credential_level))
    rows = rows[[(u, c, l) not in sampled for u, c, l in zip(rows.UNITID, rows.CIPCODE, rows.CREDLEV)]]
    cells = [(g, b) for g in GROUPS for b in BANDS]
    rng = np.random.default_rng([SEED, 11])
    chosen = [cells[i] for i in sorted(rng.permutation(len(cells))[:PILOT_N])]
    picks, schools = [], set()
    for gi, bi in [(GROUPS.index(g), BANDS.index(b)) for g, b in chosen]:
        cands = rows[(rows.school_group == GROUPS[gi]) & (rows.earnings_band == BANDS[bi])]
        cands = cands.sort_values(["UNITID", "CIPCODE"]).reset_index(drop=True)
        order = np.random.default_rng([SEED, 11, gi, bi]).permutation(len(cands))
        for k in order:
            if cands.UNITID[k] not in schools:
                picks.append(cands.iloc[k])
                schools.add(cands.UNITID[k])
                break
    p = pd.DataFrame(picks).rename(columns={"CIPCODE": "cip4"})
    p.insert(0, "profile_id", [f"X{i + 1:03d}" for i in range(len(p))])
    return p[PILOT_COLS]


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
            rows.append({
                "profile_id": p.profile_id, "chatbot": bot, "prompt_type": "R",
                "prompt_text": prompts["R"].format(major=p.prompt_major, school=prompt_school(p.INSTNM)),
                "date": "", "model_shown_in_app": "", "logged_in": "", "web_search_used": "",
                "response_text": "", "notes": "",
            })
    pd.DataFrame(rows).to_csv(REPO / "scoring" / "spot_check_template.csv", index=False, lineterminator="\n")
    print(f"Spot check: {len(s)} profiles -> {len(rows)} rows in scoring/spot_check_template.csv")

    profiles["credential_level"] = profiles.credential.map({"Associate's Degree": "2", "Bachelor's Degree": "3"})
    assert profiles.credential_level.notna().all()
    x = pilot(profiles)
    x.to_csv(PROCESSED / "pilot_profiles.csv", index=False, lineterminator="\n")
    overlap = set(zip(x.UNITID, x.cip4)) & set(zip(profiles.UNITID, profiles.cip4))
    assert not overlap, overlap
    print(f"Pilot: {len(x)} profiles outside the study sample -> data/processed/pilot_profiles.csv "
          f"(cells: {sorted(set(zip(x.school_group, x.earnings_band)))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
