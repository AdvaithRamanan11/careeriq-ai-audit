"""
Download the College Scorecard files this study uses into data/raw/.

What it downloads (all public, no API key needed):
  1. Field-of-study file  -> the answer key (earnings and debt by school + major)
  2. Institution file     -> admission rate and open-admission flag for each school
  3. Data dictionary      -> official column names, used to check every column we touch
  4. Field-of-study technical documentation (PDF) -> methods and limitations

Why pinned URLs: Scorecard puts the release date in each file name
(e.g. ..._10152026.zip = Oct 15, 2026). Pinning the exact names means a rerun
gets the same release instead of whatever is newest. The dictionary and PDF
have no date in their names, so their SHA-256 fingerprints are recorded in
data/raw/MANIFEST.json and checked on every rerun.

Usage:
  python data/download_data.py           # download anything missing, verify checksums
  python data/download_data.py --force   # re-download everything
"""

import argparse
import hashlib
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / "raw"
MANIFEST = RAW_DIR / "MANIFEST.json"

# Release recorded from https://collegescorecard.ed.gov/data/ on 2026-11-02.
# The page said: "This data was last updated November 2, 2026."
FILES = {
    "field_of_study_zip": {
        "url": "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_10152026.zip",
        "filename": "Most-Recent-Cohorts-Field-of-Study_10152026.zip",
        "unzip": True,
    },
    "institution_zip": {
        "url": "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_11022026.zip",
        "filename": "Most-Recent-Cohorts-Institution_11022026.zip",
        "unzip": True,
    },
    "data_dictionary": {
        "url": "https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx",
        "filename": "CollegeScorecardDataDictionary.xlsx",
        "unzip": False,
    },
    "field_of_study_documentation": {
        "url": "https://collegescorecard.ed.gov/files/FieldOfStudyDataDocumentation.pdf",
        "filename": "FieldOfStudyDataDocumentation.pdf",
        "unzip": False,
    },
    # Official NCES + BLS crosswalk from field of study (CIP 2020) to occupation (SOC 2018).
    # Used to check each major-to-job mapping in crosswalk/cip_to_job.csv.
    # Source page: https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56
    "cip_soc_crosswalk": {
        "url": "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx",
        "filename": "CIP2020_SOC2018_Crosswalk.xlsx",
        "unzip": False,
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "careeriq-ai-audit/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(tmp, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
    tmp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"files": {}}
    new = {"recorded_from": "https://collegescorecard.ed.gov/data/", "files": {}}
    ok = True

    for key, spec in FILES.items():
        dest = RAW_DIR / spec["filename"]
        if args.force or not dest.exists():
            print(f"Downloading {spec['filename']} ...")
            download(spec["url"], dest)
            downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        else:
            downloaded_at = old["files"].get(key, {}).get("downloaded_at")
            print(f"Already have {spec['filename']}")

        digest = sha256(dest)
        expected = old["files"].get(key, {}).get("sha256")
        if expected and expected != digest:
            print(f"  !! CHECKSUM CHANGED for {spec['filename']}: the file differs from the recorded release.")
            ok = False

        entry = {
            "url": spec["url"],
            "filename": spec["filename"],
            "bytes": dest.stat().st_size,
            "sha256": digest,
            "downloaded_at": downloaded_at,
        }
        if spec["unzip"]:
            with zipfile.ZipFile(dest) as z:
                entry["contents"] = [i.filename for i in z.infolist()]
                z.extractall(RAW_DIR)
        new["files"][key] = entry

    if ok:
        MANIFEST.write_text(json.dumps(new, indent=2) + "\n")
        print(f"Wrote {MANIFEST.relative_to(RAW_DIR.parent.parent)}")
    else:
        print("Manifest NOT updated because a checksum changed. Investigate before continuing.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
