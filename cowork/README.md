# 🧭 CSM Command Center (CoWork setup)

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

This is the **Claude CoWork** setup. If you're using Claude Code instead,
use the [main branch README](https://github.com/dylanbrightbill-ciq/csm-command-center/blob/main/README.md).

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
message in a **Claude CoWork** session.

**Step 1.** Open a CoWork session with Claude and paste this, filling in
your name:

> Hi Claude, I'd like to set up my own CSM Command Center. Fetch the setup
> files from the `cowork` branch of
> `https://raw.githubusercontent.com/dylanbrightbill-ciq/csm-command-center/cowork/`
> — specifically `skills/bob-sfdc-sync.md`, `skills/morning-meeting-prep.md`,
> `skills/eod-todo-csm-tracker.md`, `src/artifact/command-center.html`, and
> `scripts/empty-seed.json`. My name is **[Your Full Name, exactly as it
> appears in Salesforce]**. Please fill in my name on the three skill files,
> publish my personal dashboard artifact seeded with the empty seed data,
> then create three scheduled tasks — one per skill file, using its filled-in
> text as the task prompt — on these schedules: `bob-sfdc-sync` Mon/Wed/Fri
> 5am, `morning-meeting-prep` weekdays 7am, `eod-todo-csm-tracker` weekdays
> 3:30pm.

**Step 2.** Claude will publish your dashboard and give you a link.
**Bookmark it** — that's your Command Center from now on.

**Step 3.** Claude will also set up three scheduled tasks behind the scenes
(the Book of Business sync, the morning meeting prep, and the end-of-day
to-do list). You don't need to do anything else — they just start running
on schedule.

That's it. Your accounts will populate automatically the first time the
Book of Business sync runs, even if you're starting from nothing.

## Using it day to day

Open your bookmarked link each morning. Check your accounts, glance at
today's meeting prep, work your to-do list. If you want something refreshed
sooner than its schedule, just ask Claude — "refresh my book of business" or
"prep today's meetings now" both work.

## If your dashboard URL ever changes

If you republish the artifact and get a new URL, your three scheduled tasks
still point at the old one. Ask Claude to recreate them with the new URL —
there's no automatic way for a scheduled task to notice the change on its
own.

## Questions or something looks off?

Reach out to whoever set this up for your team, or open an issue on the
GitHub repo.

Full design details: [docs/specs/2026-09-01-csm-command-center-cowork-design.md](docs/specs/2026-09-01-csm-command-center-cowork-design.md).
