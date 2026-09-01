# 🧭 CSM Command Center

Your own personal dashboard for the day-to-day of being a CSM. One page,
three tabs, kept up to date automatically:

- **Book of Business** — every account you own, with ARR, renewal date,
  sentiment, and risk, refreshed straight from Salesforce a few times a week.
- **Calendar** — a week-at-a-glance view of your customer meetings. Every
  morning, Claude preps notes for that day's calls before you even sit down —
  account history, risks, talking points — right there waiting for you. Add
  your own notes during or after each call, and they stay put.
- **To Dos** — a simple board (Overdue / Today / This Week / Done) that fills
  itself in at the end of every day, pulled from your meetings, emails, and
  Slack — so nothing falls through the cracks.

No spreadsheets, no manual updates. You open it, it's current.

## What you'll need

This runs through Claude, using a few connectors turned on in your Claude
settings. Make sure these are connected before setup:

- **Salesforce** — for your book of business data
- **Google Calendar** — to know about your meetings
- **Gmail** — for email context in meeting prep and end-of-day todos
- **Slack** — for mentions and DMs in your end-of-day todos
- **Granola** and **Gong** — for meeting notes and call context

If any of these aren't turned on yet, turn them on first — everything below
assumes they're ready to go.

## Setup — takes about 5 minutes, no coding required

Everything technical is done *for* you. All you do is send Claude one
message.

**Step 1.** Get access to the project. Ask whoever shared this with you to
add you to the GitHub repository (`csm-command-center`) — you'll get an
email invite. Accept it.

**Step 2.** Open a chat with Claude and paste this, filling in your name:

> Hi Claude, I'd like to set up my own CSM Command Center from
> `https://github.com/dylanbrightbill-ciq/csm-command-center`. My name is
> **[Your Full Name, exactly as it appears in Salesforce]**. Please set up
> my personal dashboard and the automations that keep it updated.

**Step 3.** Claude will publish your dashboard and give you a link.
**Bookmark it** — that's your Command Center from now on.

**Step 4.** Claude will also set up three automations behind the scenes (the
Book of Business sync, the morning meeting prep, and the end-of-day to-do
list). You don't need to do anything else — they just start running on
schedule.

That's it. Your accounts will populate automatically the first time the
Book of Business sync runs, even if you're starting from nothing.

## Using it day to day

Open your bookmarked link each morning. Check your accounts, glance at
today's meeting prep, work your to-do list. If you want something refreshed
sooner than its schedule, just ask Claude — "refresh my book of business" or
"prep today's meetings now" both work.

## Questions or something looks off?

Reach out to whoever set this up for your team, or open an issue on the
GitHub repo.

---

## Advanced / manual setup

The above is what most people need. If you're comfortable with git and the
command line and want to do it by hand instead of asking Claude:

1. Clone this repo.
2. Publish `src/artifact/command-center.html` as a Claude Artifact, seeded
   with `scripts/empty-seed.json` (see `scripts/build-artifact.py`). Note
   the URL you get back.
3. Run:
   ```
   python3 scripts/setup.py --name "Your Full Name" --artifact-url <the URL from step 2>
   ```
   `--name` should match how you appear in Salesforce's CSM field. Pass
   `--sfdc-filter` separately if that's not the same string.
4. Personalized skill files land in `build/skills/<skill>/SKILL.md`
   (gitignored — these are yours, don't commit them). Install each as a
   scheduled task in your own Claude session:
   - `bob-sfdc-sync` — Mon/Wed/Fri 5am
   - `morning-meeting-prep` — weekdays 7am
   - `eod-todo-csm-tracker` — weekdays 3:30pm

Full design details: [docs/specs/2026-09-01-csm-command-center-spec.md](docs/specs/2026-09-01-csm-command-center-spec.md).
To iterate on the visual design afterward: [docs/iterating-on-design.md](docs/iterating-on-design.md).
