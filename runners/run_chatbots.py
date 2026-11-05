"""
Step 5 / Step 7: ask the chatbots every profile's questions and log every answer.

For each profile and each chatbot:
  R (real-student prompt)  asked 1 time
  F (forced-number prompt) asked 3 times
Each call is a brand-new conversation with no system prompt (prompts/v1.json).

Logging: one JSON line per call in <out-dir>/<contestant>.jsonl, holding the profile
ID, model requested and returned, timestamp, prompt version and text, run number,
raw answer, stop reason, token usage, and (for F) the extracted numbers.

Refusals (an API-level refusal or safety block) are retried once with the same
prompt, and both attempts are logged (PRD risk table).

Resume: rerunning skips every (profile, prompt, run) that already has a final
logged answer, and retries calls that failed with an error. So a crash or a
Ctrl+C loses at most the calls in flight.

Usage:
  python runners/run_chatbots.py --contestants echo --limit 10 --out-dir runs/test
  python runners/run_chatbots.py --contestants chatgpt,gemini,claude --pilot --out-dir runs/pilot
  python runners/run_chatbots.py --contestants chatgpt,gemini,claude            # full run -> runs/

API keys come from environment variables only (see runners/models.json).
"""

import argparse
import csv
import hashlib
import importlib
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.common import PROCESSED, REPO, prompt_school  # noqa: E402
from scoring.extract import extract  # noqa: E402

MODELS = json.loads((REPO / "runners" / "models.json").read_text(encoding="utf-8"))


def load_profiles(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def done_keys(path: Path) -> set:
    keys = set()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("final"):
                    keys.add((r["profile_id"], r["prompt_type"], r["run"]))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contestants", required=True, help="comma list from runners/models.json, e.g. chatgpt,gemini,claude")
    ap.add_argument("--profiles", type=Path, default=None)
    ap.add_argument("--prompt-version", default="v1")
    ap.add_argument("--out-dir", type=Path, default=REPO / "runs")
    ap.add_argument("--limit", type=int, default=None, help="only the first N profiles")
    ap.add_argument("--pilot", action="store_true",
                    help="use the 10 pilot profiles (outside the study sample) and write to runs/pilot")
    ap.add_argument("--workers", type=int, default=4, help="parallel calls per chatbot")
    args = ap.parse_args()
    args.out_dir = args.out_dir.resolve()

    if args.pilot:
        # Pilot profiles are drawn outside the 150 (data/make_splits.py) and carry no
        # Scorecard values, so nothing from the pilot can be scored. Pilot output never
        # lands in runs/ itself.
        args.profiles = args.profiles or PROCESSED / "pilot_profiles.csv"
        if args.out_dir == (REPO / "runs").resolve():
            args.out_dir = REPO / "runs" / "pilot"
    elif args.profiles is None:
        final = PROCESSED / "profiles.csv"
        args.profiles = final if final.exists() else PROCESSED / "profiles_DRAFT.csv"
    profiles = load_profiles(args.profiles)
    if args.limit:
        profiles = profiles[: args.limit]

    prompts = json.loads((REPO / "prompts" / f"{args.prompt_version}.json").read_text(encoding="utf-8"))
    contestants = [c.strip() for c in args.contestants.split(",")]
    for c in contestants:
        if c not in MODELS or c.startswith("_"):
            raise SystemExit(f"Unknown contestant '{c}'. Options: {[k for k in MODELS if not k.startswith('_')]}")
        env = MODELS[c]["api_key_env"]
        if env and not os.environ.get(env):
            raise SystemExit(f"{c}: environment variable {env} is not set. (Keys never go in files or git.)")
    if "echo" in contestants and len(contestants) > 1:
        raise SystemExit("Don't mix the echo test model with real chatbots in one run.")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Profiles: {len(profiles)} from {args.profiles.name}; prompt {args.prompt_version}; out {args.out_dir}")

    for c in contestants:
        spec = MODELS[c]
        provider = importlib.import_module(f"runners.providers.{spec['provider']}_provider")
        out_path = args.out_dir / f"{c}.jsonl"
        skip = done_keys(out_path)
        jobs = []
        for p in profiles:
            for ptype in ("R", "F"):
                for run in range(1, prompts["runs"][ptype] + 1):
                    if (p["profile_id"], ptype, run) not in skip:
                        jobs.append((p, ptype, run))
        print(f"\n[{c}] {spec['model_id']}: {len(jobs)} calls to make ({len(skip)} already logged)")
        lock = threading.Lock()

        def log(rec):
            with lock, open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        def work(job):
            p, ptype, run = job
            prompt = prompts["templates"][ptype].format(major=p["prompt_major"], school=prompt_school(p["INSTNM"]))
            base = {
                "contestant": c, "provider": spec["provider"], "model_requested": spec["model_id"],
                "profile_id": p["profile_id"], "prompt_version": args.prompt_version, "prompt_type": ptype,
                "run": run, "prompt_text": prompt,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
            }
            for attempt in (1, 2):
                t0 = time.time()
                rec = dict(base, attempt=attempt, timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                try:
                    out = provider.call(spec["model_id"], prompt)
                except Exception as e:  # SDKs already retried transient errors; log and move on
                    rec.update(status="error", final=False, error=f"{type(e).__name__}: {e}"[:2000],
                               latency_s=round(time.time() - t0, 2))
                    log(rec)
                    return "error"
                rec.update(out, latency_s=round(time.time() - t0, 2))
                if out["refusal"]:
                    rec.update(status="refusal", final=(attempt == 2))
                    log(rec)
                    if attempt == 1:
                        continue          # retry once with the same prompt
                    return "refusal"
                if not out["raw_text"].strip():
                    rec.update(status="empty", final=True)
                else:
                    rec.update(status="ok", final=True)
                if ptype == "F":
                    rec["extracted"] = extract(out["raw_text"])
                log(rec)
                return rec["status"]

        tally = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(work, j) for j in jobs]
            for i, fut in enumerate(as_completed(futures), 1):
                s = fut.result()
                tally[s] = tally.get(s, 0) + 1
                if i % 25 == 0 or i == len(jobs):
                    print(f"  {i}/{len(jobs)}  {tally}")
        summarize(out_path)
    return 0


def summarize(path: Path) -> None:
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    final = [r for r in rows if r.get("final")]
    models = sorted({r.get("model_returned") for r in final if r.get("model_returned")})
    need = [r for r in final if r["prompt_type"] == "F" and r.get("extracted", {}).get("extract_status") != "ok"]
    errors = [r for r in rows if r["status"] == "error"]
    print(f"  {path.name}: {len(final)} final answers; models returned: {models}")
    if len(models) > 1:
        print("  !! More than one model version answered. Check whether the provider changed models mid-run.")
    print(f"  F answers needing hand review: {len(need)}; error lines (will retry on rerun): {len(errors)}")
    if need:
        review = path.with_name(path.stem + "_needs_review.csv")
        with open(review, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["profile_id", "run", "extract_notes", "raw_text", "earnings_fixed", "debt_fixed", "reviewer_note"])
            for r in need:
                w.writerow([r["profile_id"], r["run"], r.get("extracted", {}).get("extract_notes", r["status"]),
                            r["raw_text"], "", "", ""])
        print(f"  Wrote {review.relative_to(REPO)} for hand review")


if __name__ == "__main__":
    sys.exit(main())
