"""
Step 3: draw the 150 school-and-major profiles.

Design (see prereg/decisions.md for the reason behind each rule):
  - 15 cells = 5 school groups x 3 earnings bands, 10 profiles per cell
  - School groups (D1, P2, P3):
        Community college  CareerIQ schoolType '2-year'               associate's rows
        Open admission     4-year, tier 4 (admit > 70%), OR no
                           admission rate and OPENADMP = 1           bachelor's rows
        Above average      4-year, tier 3 (40-70%), rate reported    bachelor's rows
        Selective          4-year, tier 2 (15-40%)                   bachelor's rows
        Elite              4-year, tier 1 (< 15%)                    bachelor's rows
    4-year schools with no admission rate and OPENADMP != 1 are excluded.
  - Earnings bands (P6): rank every field nationally at the same credential level by
    Scorecard's national median 1-year earnings (EARN_MDN_1YR_NAT) and split the
    ranked list into thirds: bottom, middle, top.
  - Only fields whose crosswalk status is 'proposed' or 'approved' are sampled (P4).
  - Within a cell (P5, P7): aim for 5 Texas + 5 non-Texas profiles, at most one
    profile per school. If one side is short, the other side fills the gap.
  - Randomness: each cell gets its own generator seeded from (2026, group #, band #),
    and candidates are sorted before shuffling, so reruns give an identical file.

If any crosswalk row is still 'judgment', the output is written as
profiles_DRAFT.csv instead of profiles.csv, because the eligible pool may change.

Usage: python data/sample_profiles.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import (CREDLEV_ASSOC, CREDLEV_BACH, INST_CSV, PROCESSED, REPO,  # noqa: E402
                        load_colleges, load_fos, usable_fos)

SEED = 2026
PER_CELL = 10
TX_TARGET = 5
# P8 (proposed): at most this many profiles from one field within a cell. None = no cap (pure random, as in the PRD).
MAX_PER_FIELD = None
GROUPS = ["Community college", "Open admission", "Above average", "Selective", "Elite"]
BANDS = ["Bottom", "Middle", "Top"]
CROSSWALK = REPO / "crosswalk" / "cip_to_job.csv"


def school_groups() -> pd.DataFrame:
    colleges = load_colleges()
    # ADM_RATE and OPENADMP checked against Institution_Data_Dictionary on 2026-11-02.
    inst = pd.read_csv(INST_CSV, usecols=["UNITID", "ADM_RATE", "OPENADMP"], dtype=str)
    inst["ADM_RATE"] = pd.to_numeric(inst.ADM_RATE, errors="coerce")
    c = colleges.merge(inst, on="UNITID", how="left", validate="one_to_one")

    def group(r):
        if r.schoolType == "2-year":
            return "Community college"
        if pd.isna(r.ADM_RATE):
            return "Open admission" if r.OPENADMP == "1" else None   # D1
        return {1: "Elite", 2: "Selective", 3: "Above average", 4: "Open admission"}[r.tier]

    c["school_group"] = c.apply(group, axis=1)
    c["open_adm_by_flag"] = (c.schoolType == "4-year") & c.ADM_RATE.isna() & (c.OPENADMP == "1")
    return c


def earnings_bands() -> pd.DataFrame:
    """Band each field (CIP x credential) by national 1-yr median earnings, thirds within credential."""
    fos = load_fos()
    nat = (fos.dropna(subset=["EARN_MDN_1YR_NAT"])
              .groupby(["CIPCODE", "CREDLEV"], as_index=False).EARN_MDN_1YR_NAT.first())
    out = []
    for cred, g in nat.groupby("CREDLEV"):
        g = g.sort_values(["EARN_MDN_1YR_NAT", "CIPCODE"]).reset_index(drop=True)
        g["earnings_band"] = pd.qcut(g.index, 3, labels=BANDS).astype(str)
        out.append(g)
    bands = pd.concat(out)
    return bands[["CIPCODE", "CREDLEV", "earnings_band"]]


def band_cutoffs(bands: pd.DataFrame, fos: pd.DataFrame) -> pd.DataFrame:
    nat = fos.groupby(["CIPCODE", "CREDLEV"]).EARN_MDN_1YR_NAT.first().reset_index()
    b = bands.merge(nat, on=["CIPCODE", "CREDLEV"])
    return b.groupby(["CREDLEV", "earnings_band"]).EARN_MDN_1YR_NAT.agg(["count", "min", "max"])


def draw_cell(cands: pd.DataFrame, rng: np.random.Generator, max_per_field=None) -> pd.DataFrame:
    cands = cands.sort_values(["UNITID", "CIPCODE"]).reset_index(drop=True)
    order = rng.permutation(len(cands))
    shuffled = cands.iloc[order]
    tx = shuffled[shuffled.state == "TX"]
    other = shuffled[shuffled.state != "TX"]

    picked, schools, per_field = [], set(), {}

    def take(pool, n):
        for _, r in pool.iterrows():
            if n == 0:
                break
            if r.UNITID in schools:
                continue
            if max_per_field and per_field.get(r.CIPCODE, 0) >= max_per_field:
                continue
            picked.append(r)
            schools.add(r.UNITID)
            per_field[r.CIPCODE] = per_field.get(r.CIPCODE, 0) + 1
            n -= 1

    take(tx, TX_TARGET)
    take(other, PER_CELL - len(picked))
    take(tx, PER_CELL - len(picked))      # fill from Texas if non-Texas ran short
    return pd.DataFrame(picked)


def main() -> int:
    global MAX_PER_FIELD
    if "--max-per-field" in sys.argv:
        MAX_PER_FIELD = int(sys.argv[sys.argv.index("--max-per-field") + 1])
    cw = pd.read_csv(CROSSWALK, dtype=str).fillna("")
    unresolved = cw[cw.status == "judgment"]
    draft = len(unresolved) > 0
    cw_ok = cw[cw.status.isin(["proposed", "approved"]) & (cw.job_id != "")]

    groups = school_groups()
    fos = usable_fos(groups)
    bands = earnings_bands()

    df = fos.merge(groups[["UNITID", "name", "city", "state", "schoolType", "tier", "ownership",
                           "school_group", "open_adm_by_flag", "ADM_RATE"]],
                   on="UNITID", how="inner", validate="many_to_one")
    df = df[df.school_group.notna()]
    df = df[((df.school_group == "Community college") & (df.CREDLEV == CREDLEV_ASSOC)) |
            ((df.school_group != "Community college") & (df.CREDLEV == CREDLEV_BACH))]   # P3
    df = df.merge(bands, on=["CIPCODE", "CREDLEV"], how="left", validate="many_to_one")
    df = df.merge(cw_ok[["cip4", "prompt_major", "major_id", "job_id", "status"]]
                  .rename(columns={"cip4": "CIPCODE", "status": "crosswalk_status"}),
                  on="CIPCODE", how="inner", validate="many_to_one")
    assert df.earnings_band.notna().all()

    profiles, counts = [], []
    for gi, g in enumerate(GROUPS):
        for bi, b in enumerate(BANDS):
            cands = df[(df.school_group == g) & (df.earnings_band == b)]
            rng = np.random.default_rng([SEED, gi, bi])
            drawn = draw_cell(cands, rng, MAX_PER_FIELD) if len(cands) else cands.head(0)
            profiles.append(drawn)
            counts.append({"school_group": g, "earnings_band": b,
                           "eligible_rows": len(cands), "eligible_schools": cands.UNITID.nunique(),
                           "eligible_tx_rows": int((cands.state == "TX").sum()),
                           "sampled": len(drawn), "sampled_tx": int((drawn.state == "TX").sum()) if len(drawn) else 0,
                           "distinct_fields_sampled": drawn.CIPCODE.nunique() if len(drawn) else 0})

    p = pd.concat(profiles, ignore_index=True)
    p.insert(0, "profile_id", [f"P{i + 1:03d}" for i in range(len(p))])
    p["ownership_label"] = p.ownership.map({1: "Public", 2: "Private nonprofit"})
    p = p.rename(columns={"name": "school", "CIPCODE": "cip4", "CIPDESC": "cip_name", "CREDDESC": "credential",
                          "EARN_MDN_1YR": "sc_earn_1yr", "EARN_MDN_5YR": "sc_earn_5yr",
                          "EARN_MDN_1YR_NAT": "sc_nat_earn_1yr",
                          "DEBT_ALL_STGP_EVAL_MDN": "sc_debt_eval", "DEBT_ALL_STGP_ANY_MDN": "sc_debt_any",
                          "ADM_RATE": "adm_rate"})
    cols = ["profile_id", "school_group", "earnings_band", "UNITID", "school", "INSTNM", "city", "state",
            "ownership_label", "adm_rate", "open_adm_by_flag", "tier", "cip4", "cip_name", "prompt_major",
            "credential", "major_id", "job_id", "crosswalk_status",
            "sc_earn_1yr", "sc_earn_5yr", "sc_nat_earn_1yr", "sc_debt_eval", "sc_debt_any"]
    p = p[cols]

    PROCESSED.mkdir(parents=True, exist_ok=True)
    name = "profiles_DRAFT.csv" if draft else "profiles.csv"
    p.to_csv(PROCESSED / name, index=False, lineterminator="\n")
    counts = pd.DataFrame(counts)
    counts.to_csv(PROCESSED / ("sample_counts_DRAFT.csv" if draft else "sample_counts.csv"),
                  index=False, lineterminator="\n")

    pd.set_option("display.width", 200)
    print(counts.to_string(index=False))
    print(f"\nTotal profiles: {len(p)}  (Texas: {(p.state == 'TX').sum()})")
    print("\nEarnings-band cutoffs (national 1-yr median, all fields at that credential):")
    print(band_cutoffs(bands, load_fos()).to_string())
    print("\nMost common fields in the sample:")
    print(p.prompt_major.value_counts().head(10).to_string())
    print(f"\nWrote data/processed/{name}")
    if draft:
        print(f"DRAFT: {len(unresolved)} crosswalk rows are still 'judgment'. Resolve them, then rerun.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
