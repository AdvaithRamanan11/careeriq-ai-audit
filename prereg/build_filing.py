"""
Build the two files that go to OSF with the preregistration:

  prereg/preregistration.pdf     the preregistration text, rendered to PDF
  prereg/supporting_files.zip    the files the text refers to, frozen at filing

PDF route: Markdown -> HTML (python-markdown, tables extension) -> PDF via
Microsoft Edge's headless print, which is on every Windows 11 machine. No LaTeX,
no pandoc. The HTML is kept next to the PDF so the rendering can be checked.

Usage: python prereg/build_filing.py
"""

import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

import markdown

REPO = Path(__file__).resolve().parent.parent
PREREG = REPO / "prereg"
MD = PREREG / "preregistration.md"
HTML = PREREG / "preregistration.html"
PDF = PREREG / "preregistration.pdf"
ZIP = PREREG / "supporting_files.zip"

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

SUPPORTING = [
    "prereg/decisions.md",
    "prereg/prior_work.md",
    "data/raw/MANIFEST.json",
    "crosswalk/cip_to_job.csv",
    "data/processed/profiles.csv",
    "data/processed/sample_counts.csv",
    "data/processed/holdout_schools.csv",
    "data/processed/pilot_profiles.csv",
    "data/processed/spot_check_profiles.csv",
    "prompts/v1.json",
    "runners/models.json",
    "scoring/codebook.md",
]

CSS = """
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt; line-height: 1.45;
       max-width: 7in; margin: 0 auto; color: #111; }
h1 { font-size: 20pt; margin-top: 0; } h2 { font-size: 15pt; margin-top: 1.6em; border-bottom: 1px solid #999; }
h3 { font-size: 12.5pt; margin-top: 1.3em; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 0.8em 0; page-break-inside: auto; }
th, td { border: 1px solid #bbb; padding: 4px 6px; vertical-align: top; text-align: left; }
th { background: #eee; } tr { page-break-inside: avoid; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f3f3f3; padding: 0 2px; }
blockquote { border-left: 3px solid #999; margin: 0; padding: 0.2em 0.9em; color: #333; background: #f7f7f7; }
@page { size: Letter; margin: 0.9in 0.8in; }
"""


def build_pdf() -> None:
    text = MD.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    html = (f"<!doctype html><html><head><meta charset='utf-8'><title>Preregistration</title>"
            f"<style>{CSS}</style></head><body>{body}"
            f"<p style='font-size:9pt;color:#555;margin-top:3em'>Rendered {date.today().isoformat()} "
            f"from prereg/preregistration.md by prereg/build_filing.py.</p></body></html>")
    HTML.write_text(html, encoding="utf-8")
    edge = next((p for p in EDGE_CANDIDATES if p.exists()), None)
    if edge is None:
        raise SystemExit("Microsoft Edge not found; open preregistration.html and print to PDF by hand.")
    if PDF.exists():
        PDF.unlink()
    subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-first-run",
                    f"--print-to-pdf={PDF}", "--no-pdf-header-footer", HTML.resolve().as_uri()],
                   check=True, timeout=120, capture_output=True)
    if not PDF.exists():
        raise SystemExit("Edge did not produce the PDF.")
    print(f"Wrote {PDF.relative_to(REPO)} ({PDF.stat().st_size // 1024} KB)")


def build_zip() -> None:
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in SUPPORTING:
            p = REPO / rel
            if not p.exists():
                raise SystemExit(f"Missing supporting file: {rel}")
            z.write(p, rel)
    print(f"Wrote {ZIP.relative_to(REPO)} with {len(SUPPORTING)} files")


if __name__ == "__main__":
    build_pdf()
    build_zip()
    sys.exit(0)
