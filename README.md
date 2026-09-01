# csm-command-center

A personal CSM dashboard: Book of Business, weekly Calendar, To Dos Kanban —
one Claude Artifact, kept fresh by three scheduled skills. See
[docs/specs/2026-09-01-csm-command-center-spec.md](docs/specs/2026-09-01-csm-command-center-spec.md)
for the full design.

## Setup (new CSM)

1. Clone this repo.
2. Publish `src/artifact/command-center.html` as a Claude Artifact, seeded
   with `scripts/empty-seed.json` (see `scripts/build-artifact.py` for how to
   inject seed data into the template). Note the URL you get back.
3. Run:
   ```
   python3 scripts/setup.py --name "Your Full Name" --artifact-url <the URL from step 2>
   ```
   `--name` should match how you appear in Salesforce's CSM field. Pass
   `--sfdc-filter` separately if that's not the same string.
4. Personalized skill files land in `build/skills/<skill>/SKILL.md`
   (gitignored — these are yours, not template content, never commit them).
   Install each as a scheduled task in your own Claude session:
   - `bob-sfdc-sync` — Mon/Wed/Fri 5am
   - `morning-meeting-prep` — weekdays 7am
   - `eod-todo-csm-tracker` — weekdays 3:30pm
5. First `bob-sfdc-sync` run populates your accounts from Salesforce — you
   don't need any existing data to start.

To iterate on the design afterward, see
[docs/iterating-on-design.md](docs/iterating-on-design.md).
