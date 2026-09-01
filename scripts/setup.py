#!/usr/bin/env python3
"""Personalize the skill templates for one CSM. Run once per person.

Usage:
  python3 setup.py --name "Jane Doe" --artifact-url https://claude.ai/code/artifact/xxxx

--artifact-url is optional on the first run (you don't have one yet — publish
src/artifact/command-center.html seeded with scripts/empty-seed.json first,
then re-run this with the URL you get back).

Writes personalized SKILL.md files to build/skills/<name>/ (gitignored —
these are yours, not template content). Copy them into your own scheduled
tasks; don't commit them.
"""
import argparse
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ["bob-sfdc-sync", "morning-meeting-prep", "eod-todo-csm-tracker"]

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True, help="Your full name, as it appears in Salesforce's CSM field")
ap.add_argument("--artifact-url", default="{{ARTIFACT_URL}}", help="Your published Command Center artifact URL (omit on first run)")
ap.add_argument("--sfdc-filter", default=None, help="Value for CSM__r.Name if different from --name")
args = ap.parse_args()

out_dir = REPO_ROOT / "build" / "skills"
for skill in SKILLS:
    src = REPO_ROOT / "skills" / skill / "SKILL.md"
    text = src.read_text()
    text = text.replace("{{CSM_NAME}}", args.name)
    text = text.replace("{{SFDC_CSM_FILTER}}", args.sfdc_filter or args.name)
    text = text.replace("{{ARTIFACT_URL}}", args.artifact_url)
    text = text.replace("{{REPO_PATH}}", str(REPO_ROOT))

    dst_dir = out_dir / skill
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "SKILL.md").write_text(text)
    print(f"wrote {dst_dir / 'SKILL.md'}")

if args.artifact_url == "{{ARTIFACT_URL}}":
    print("\nNo --artifact-url given — that placeholder is still in the output.")
    print("Publish src/artifact/command-center.html seeded with scripts/empty-seed.json")
    print("first, then re-run this script with --artifact-url set to what you get back.")
