# CoWork Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give CoWork users a working onboarding path — one pasted chat message produces a published Command Center artifact plus three scheduled automations — with no git clone, no GitHub connector dependency, and no local script execution.

**Architecture:** Three self-contained skill-instruction files (`cowork/skills/*.md`, no `{{REPO_PATH}}` pointer, fuzzy-matcher and lock protocol inlined) plus a CoWork-flavored `cowork/README.md` whose onboarding message tells Claude to `WebFetch` those files (and the existing `src/artifact/command-center.html` + `scripts/empty-seed.json`, unchanged from `main`), do the `{{TOKEN}}` substitution itself, publish the Artifact, and create three scheduled tasks from the resolved text.

**Tech Stack:** Markdown (skill/instruction content), no code, no build step. Verification is manual (matches this repo's existing personal-tool scale — see the Code-branch spec's own testing strategy).

**Spec:** [docs/specs/2026-09-01-csm-command-center-cowork-design.md](../specs/2026-09-01-csm-command-center-cowork-design.md)

## Global Constraints

- All work stays on the `cowork` branch; it is never merged back into `main` (design doc, Architecture section).
- No `{{REPO_PATH}}` token or path pointer to a local clone may remain anywhere in `cowork/skills/*.md` — every file must be resolvable standalone from its fetched text (design doc, Components table).
- Each skill file's write scope is unchanged from `main`: `bob-sfdc-sync` owns `accounts` + `lastSynced.salesforce` + `syncLocks.bob`; `morning-meeting-prep` owns `meetings[date][accountId]` + `lastSynced.meetings` + `syncLocks.meetings`; `eod-todo-csm-tracker` owns `tasks` (append-only) + `lastSynced.eodTodo` + `syncLocks.todos`. None of the three may touch another's fields (shared-refresh-protocol.md table).
- No automated tests. Verification is one real manual dry run before this ships to any CSM other than Dylan (design doc, Testing Strategy).
- The artifact published during the dry run must stay private — never shared or published for other viewers (Code-branch spec, Securability).

---

## File Structure

| File | Responsibility |
|---|---|
| `cowork/skills/bob-sfdc-sync.md` | Self-contained Salesforce sync instructions — Mon/Wed/Fri 5am cadence noted in the file, actual cron set at scheduled-task creation time. |
| `cowork/skills/morning-meeting-prep.md` | Self-contained meeting-prep instructions, with the fuzzy-matcher algorithm inlined (no external doc reference). |
| `cowork/skills/eod-todo-csm-tracker.md` | Self-contained end-of-day-todo instructions, with the same fuzzy-matcher algorithm inlined. |
| `cowork/README.md` | CoWork onboarding entry point: connector checklist, the exact paste-in-chat setup message, day-to-day usage notes, and the "URL changed" recreate-manually note. |

No changes to `scripts/setup.py`, `scripts/build-artifact.py`, `scripts/migrate-csm-tracker.py`, `src/artifact/command-center.html`, or `scripts/empty-seed.json` — the last two are fetched as-is by CoWork users; the scripts are simply unused on this branch (design doc, Components table).

---

### Task 1: `cowork/skills/bob-sfdc-sync.md`

**Files:**
- Create: `cowork/skills/bob-sfdc-sync.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a fetchable file whose raw URL is `https://raw.githubusercontent.com/dylanbrightbill-ciq/csm-command-center/cowork/skills/bob-sfdc-sync.md` once pushed. Task 4's README references this exact URL.

- [ ] **Step 1: Write the file**

```markdown
# bob-sfdc-sync

Cadence: Mon/Wed/Fri 5am + on-demand.

Refresh the Salesforce-owned account fields in {{CSM_NAME}}'s CSM Command
Center artifact ("Command Center", {{ARTIFACT_URL}}).

This is distinct from `bob-customer-intel-digest` — that skill produces a
separate news/leadership-change digest and is not touched by this task.

## Steps

1. Pull {{CSM_NAME}}'s active Salesforce accounts (`CSM__r.Name = '{{SFDC_CSM_FILTER}}'`)
   with their current values for: ARR (active subscription), ARR (sum of
   amount), renewal date, meeting cadence, churn score, risk records, expansion
   pipeline / open opportunities, active processing status, implementation
   projects, customer service start date, support level, fiscal year,
   processing frequency, previous tool, seats occupied, payees purchased, seat
   utilization, instance seat count, private/public, industry.

2. Follow this publish protocol exactly:
   - Check `syncLocks.bob` — this is a cron run, so proceed regardless of the
     lock (crons never wait).
   - Set `syncLocks.bob` to now, read the artifact's current state.
   - Match each Salesforce account to an existing `accounts[]` entry by
     `sfdcId` — a stable Salesforce identifier, so no fuzzy matching is
     needed here, unlike meeting-prep/eod-todo which resolve free-text
     account names.
   - Replace only the Salesforce-owned fields on each matched account. Leave
     `overrides`, `meetings`, `tasks`, and `archived` completely untouched.
   - Publish, clear `syncLocks.bob`, set `lastSynced.salesforce` to now.

3. If nothing changed since the last sync, skip the publish — don't write a
   no-op version.

4. If a new Salesforce account exists that isn't in `accounts[]` yet, add it
   with these Salesforce-owned fields populated and every CSM-judgment field
   (`csmSentiment`, `risk`, `notes`, `capResearchStatus`, `ciqExecutiveSponsor`,
   `lastEbr`) null — {{CSM_NAME}} fills those in by hand.

## Context

- {{CSM_NAME}} manages enterprise accounts (2,000+ employees) on CaptivateIQ.
- {{CSM_NAME}} is measured on NRR — surface anything tied to renewal risk or expansion,
  but this skill's job is the sync itself, not analysis or commentary.
- No em dashes; short paragraphs, clear next actions if anything needs
  attention (e.g. a brand-new account with no CSM judgment fields yet).
```

- [ ] **Step 2: Verify no leftover repo-path or frontmatter artifacts**

Run: `grep -n "REPO_PATH\|^---" cowork/skills/bob-sfdc-sync.md`
Expected: no output (empty). If it prints a match, remove the offending line before continuing.

- [ ] **Step 3: Verify every remaining token is one of the three expected placeholders**

Run: `grep -o "{{[A-Z_]*}}" cowork/skills/bob-sfdc-sync.md | sort -u`
Expected output exactly:
```
{{ARTIFACT_URL}}
{{CSM_NAME}}
{{SFDC_CSM_FILTER}}
```

- [ ] **Step 4: Commit**

```bash
git add cowork/skills/bob-sfdc-sync.md
git commit -m "Add self-contained bob-sfdc-sync template for CoWork"
```

---

### Task 2: `cowork/skills/morning-meeting-prep.md`

**Files:**
- Create: `cowork/skills/morning-meeting-prep.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a fetchable file at `https://raw.githubusercontent.com/dylanbrightbill-ciq/csm-command-center/cowork/skills/morning-meeting-prep.md`, referenced by Task 4's README.

- [ ] **Step 1: Write the file**

```markdown
# morning-meeting-prep

Cadence: weekdays 7am + on-demand.

You are a Senior Enterprise CSM at CaptivateIQ. Your job each morning is to
prepare for today's customer meetings and publish the briefs into the CSM
Command Center artifact ("Command Center", {{ARTIFACT_URL}})
— its Calendar tab shows a weekly grid, and this run fills in today's column.

## Steps

1. **Check Google Calendar** for today's events using the Google Calendar connector. Look for all events scheduled for today.

2. **Identify external customer meetings**: Filter for meetings that include external attendees (i.e., people not at @captivateiq.com). These are customer meetings. Skip internal-only meetings (all attendees are @captivateiq.com).

3. **For each external customer meeting**, invoke the `/meeting-prep` skill by running meeting prep for that account. The skill will search across Google Calendar, Granola, Gong, Gmail, Salesforce, and support tickets to build a call prep doc with a prioritized agenda and outstanding action items.

4. **Output**: for each external customer meeting found today, resolve its
   account to an `accountId` using the fuzzy matcher below, then follow the
   publish protocol below.

   **Fuzzy account matcher** — normalize, check the alias map, fall back to substring:
   ```python
   import re

   ALIASES = {
       # normalized nickname -> canonical account name, add entries as discovered
       "acme": "Acme Corporation",  # example — replace with your own real nicknames as discovered
   }

   def normalize(s):
       return re.sub(r"[/.\s]", "", s).lower()

   def resolve_account_id(name, accounts):
       """accounts: list of {"accountId": ..., "accountName": ...}. Returns
       accountId or None — never guess past this; unlinked-but-visible beats a
       wrong link."""
       if not name:
           return None
       needle = normalize(name)
       by_name = {normalize(a["accountName"]): a["accountId"] for a in accounts}

       if needle in ALIASES:
           target = normalize(ALIASES[needle])
           if target in by_name:
               return by_name[target]

       for norm_name, acct_id in by_name.items():
           if needle == norm_name or needle in norm_name or norm_name in needle:
               return acct_id
       return None
   ```
   Extend `ALIASES` as mismatches are discovered in real runs.

   **Publish protocol:**
   - Check `syncLocks.meetings` — this is a cron run, proceed regardless.
   - Set `syncLocks.meetings` to now, read the artifact's current state.
   - Write `meetings[<today's date>][accountId] = { brief: <the prep content>,
     notes: "", notesOpen: false, sources: [...] }`. If an entry already
     exists for that account today (a re-run), overwrite its `brief` and
     `sources` but never touch `notes` — that's {{CSM_NAME}}'s.
   - If no `accountId` resolves with confidence, still publish under a literal
     `"unlinked"` key rather than dropping the brief — visible and unlinked
     beats silently lost.
   - Publish, clear `syncLocks.meetings`, set `lastSynced.meetings` to now.
   - If no external meetings are found today, skip the publish entirely.

## Preferences
- Be concise — high signal, low friction.
- Reference account-specific context (health, stakeholders, risks, history) in every prep.
- Tie talking points to ROI, NRR, or customer health where relevant.
- Use plain language, short paragraphs, and bold key points.
- No em dashes.
```

- [ ] **Step 2: Verify no leftover repo-path or frontmatter artifacts**

Run: `grep -n "REPO_PATH\|^---" cowork/skills/morning-meeting-prep.md`
Expected: no output.

- [ ] **Step 3: Verify the fuzzy matcher is present and self-contained**

Run: `grep -c "def resolve_account_id" cowork/skills/morning-meeting-prep.md`
Expected: `1`

- [ ] **Step 4: Verify remaining tokens**

Run: `grep -o "{{[A-Z_]*}}" cowork/skills/morning-meeting-prep.md | sort -u`
Expected output exactly:
```
{{ARTIFACT_URL}}
{{CSM_NAME}}
```

- [ ] **Step 5: Commit**

```bash
git add cowork/skills/morning-meeting-prep.md
git commit -m "Add self-contained morning-meeting-prep template for CoWork"
```

---

### Task 3: `cowork/skills/eod-todo-csm-tracker.md`

**Files:**
- Create: `cowork/skills/eod-todo-csm-tracker.md`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a fetchable file at `https://raw.githubusercontent.com/dylanbrightbill-ciq/csm-command-center/cowork/skills/eod-todo-csm-tracker.md`, referenced by Task 4's README.

- [ ] **Step 1: Write the file**

```markdown
# eod-todo-csm-tracker

Cadence: weekdays 3:30pm + on-demand.

Run the end-of-day to-do skill for {{CSM_NAME}}, Senior Enterprise CSM at
CaptivateIQ, then push its output into the CSM Command Center artifact
("Command Center", {{ARTIFACT_URL}})
— its To Dos tab renders these as a Kanban board (Overdue / Today / This
Week / Done), computed automatically from each task's `dueDate` and `done`
fields, so nothing here needs to know about the board layout itself.

Objective: Generate a prioritized end-of-day to-do list and follow-up summary
by reviewing today's meetings, emails, Slack messages, this week's meeting
notes, and any open action items across accounts, then push new tasks into
the live Command Center artifact so they show up in its To Dos tab.

Steps 1-5 (gather + synthesize — invoke the `eod-todo` skill for this if it's
available in your skill list; otherwise follow these steps directly):

1. Pull from all available connectors: Google Calendar (today's meetings),
   Granola (meeting notes), Gmail (emails from today), Slack (mentions and DMs
   from today), Salesforce (any open tasks or opportunities with activity
   today), **and this week's `meetings[date][*].notes` already in the
   Command Center artifact** — treat these the same as an email or Slack
   thread, as a source of follow-up items. Read them from the artifact's
   current state (not a stale copy).
2. Synthesize a prioritized to-do list organized by urgency: (a) must do
   today/tonight, (b) this week. Do NOT include a "first thing tomorrow" or
   forward-looking bucket, and do NOT list preparing for upcoming meetings as
   a task — the morning-meeting-prep scheduled task already handles next-day
   meeting prep. Scope this list strictly to what came out of TODAY's
   meetings, emails, Slack, account activity, and this week's meeting notes.
3. Flag any account health risks, unanswered customer emails, or missed
   follow-ups from today.
4. Output the list in a clean, scannable format with bold headers and tight
   bullets.
5. (Nothing else to do here — step 6 below replaces the old "push" step.)

Step 6 — push tasks into the Command Center artifact:

a. Parse your step-2 output into task objects. For each bullet point, capture:
   - `"id"`: prefix `"eod-MMDD-"` + a 3-digit counter (e.g. `"eod-0901-001"`)
   - `"text"`: the task description (without account prefix)
   - `"accountName"`: account name if present before a colon (e.g. "Acme"
     from "Acme: send follow-up"), otherwise null — resolved to a real
     `accountId` in step (c) below using the fuzzy matcher, then discarded
   - `"badge"`: auto-assign — `"risk"` if text mentions churn/risk/escalation/
     overdue/invoice/blocker, `"exp"` if expand/upsell/renewal/growth/
     opportunity, `"follow"` if follow-up/reply/respond/email/slack, otherwise
     null
   - `"done"`: false
   - `"dueDate"`: today's date for today/tonight/urgent items, the Friday of
     the current week for this-week items — this is what the Kanban board
     buckets on, so get it right
   - `"createdAt"`: current ISO timestamp
   - `"notes"`: any parenthetical context, otherwise `""`
   - `"sources"`: []
   - `"notesOpen"`: false

b. Read the Command Center artifact's current HTML using the Artifact tool,
   action "read", with the URL above. If that fails to load for any reason,
   fall back to Artifact action "list" and find the artifact titled "Command
   Center" owned by the user, then read that URL instead — do not create a
   new artifact.

c. Parse its embedded `<script type="application/json" id="seed-data">` block
   into an object with `accounts`, `overrides`, `meetings`, `tasks`,
   `archived`, `customTypes`, `layout`, `kpiVisible`, `columnSort`,
   `columnWidths`, `lastSynced`, `syncLocks`. For each new task, resolve
   `accountId` using the fuzzy matcher below against `accounts[].accountName`;
   set `accountId: null` if nothing resolves with confidence — never guess.
   Drop `accountName` from the final object — only `accountId` is stored.

   **Fuzzy account matcher** — normalize, check the alias map, fall back to substring:
   ```python
   import re

   ALIASES = {
       # normalized nickname -> canonical account name, add entries as discovered
       "acme": "Acme Corporation",  # example — replace with your own real nicknames as discovered
   }

   def normalize(s):
       return re.sub(r"[/.\s]", "", s).lower()

   def resolve_account_id(name, accounts):
       """accounts: list of {"accountId": ..., "accountName": ...}. Returns
       accountId or None — never guess past this; unlinked-but-visible beats a
       wrong link."""
       if not name:
           return None
       needle = normalize(name)
       by_name = {normalize(a["accountName"]): a["accountId"] for a in accounts}

       if needle in ALIASES:
           target = normalize(ALIASES[needle])
           if target in by_name:
               return by_name[target]

       for norm_name, acct_id in by_name.items():
           if needle == norm_name or needle in norm_name or norm_name in needle:
               return acct_id
       return None
   ```
   Extend `ALIASES` as mismatches are discovered in real runs.

d. Build the `seen` Set from BOTH `tasks[]` and `archived[]` ids (unchanged,
   proven logic — never let it regress):
   ```
   const seen = new Set([...tasks, ...archived].map(t => t.id));
   const fresh = newTasks.filter(t => !seen.has(t.id));
   ```
   Only tasks whose id is not already in `seen` get appended to `tasks[]`.
   Never resurrect anything from `archived[]`.

e. Follow this lock protocol before publishing: check `syncLocks.todos` —
   this is a cron run, proceed regardless of the lock. Set `syncLocks.todos`
   to now, read the artifact's current state again (it may have changed
   since step b), do the merge in (d), publish, clear `syncLocks.todos`.

f. Set `lastSynced.eodTodo` to the current ISO timestamp. Leave `accounts`,
   `overrides`, `meetings`, `customTypes`, `layout`, `kpiVisible`, `sfBaseUrl`,
   `columnSort`, `columnWidths`, `lastSynced.salesforce`, and
   `lastSynced.meetings` untouched — this step never modifies them.

g. Regenerate the full HTML: replace the `#seed-data` script block's contents
   with `JSON.stringify(mergedPayload)`, keeping every other byte of the
   document unchanged. Do not touch anything outside that one script tag.

h. Publish the regenerated HTML once via the Artifact tool, passing `url` set
   to the Command Center artifact URL above so it updates the existing
   artifact rather than creating a new one, with an update summary like
   "Auto-pushed EOD tasks — <today's date>".

This is idempotent — running it twice with identical input is a no-op the
second time (every task id is already in `seen`). If step (b)/(c) finds zero
tasks worth adding (nothing came out of today), skip steps (d)-(h) entirely
rather than publishing a no-op update.

Context:
- {{CSM_NAME}} manages enterprise accounts (2,000+ employees) on CaptivateIQ, an incentive compensation platform.
- {{CSM_NAME}} is measured on NRR (net revenue retention) — surface anything tied to renewal risk or expansion.
- Tone: friendly, concise, high signal.
- No em dashes; use short paragraphs and clear next actions.
- Next-day meeting prep is handled by a separate morning-meeting-prep scheduled task; never duplicate that here.
```

- [ ] **Step 2: Verify no leftover repo-path or frontmatter artifacts**

Run: `grep -n "REPO_PATH\|^---" cowork/skills/eod-todo-csm-tracker.md`
Expected: no output.

- [ ] **Step 3: Verify the fuzzy matcher is present**

Run: `grep -c "def resolve_account_id" cowork/skills/eod-todo-csm-tracker.md`
Expected: `1`

- [ ] **Step 4: Verify remaining tokens**

Run: `grep -o "{{[A-Z_]*}}" cowork/skills/eod-todo-csm-tracker.md | sort -u`
Expected output exactly:
```
{{ARTIFACT_URL}}
{{CSM_NAME}}
```

- [ ] **Step 5: Commit**

```bash
git add cowork/skills/eod-todo-csm-tracker.md
git commit -m "Add self-contained eod-todo-csm-tracker template for CoWork"
```

---

### Task 4: `cowork/README.md`

**Files:**
- Create: `cowork/README.md`

**Interfaces:**
- Consumes: the three raw URLs produced by Tasks 1-3 (`.../cowork/skills/bob-sfdc-sync.md`, `.../morning-meeting-prep.md`, `.../eod-todo-csm-tracker.md`), plus `main`'s unchanged `src/artifact/command-center.html` and `scripts/empty-seed.json` (both already present on `cowork` since the branch point).
- Produces: the onboarding message a CSM pastes into a CoWork session. Task 5's dry run uses this message verbatim (substituting a real name).

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Verify the three skill URLs referenced in the setup message match the files created in Tasks 1-3**

Run: `grep -o "skills/[a-z-]*\.md" cowork/README.md | sort -u`
Expected output exactly:
```
skills/bob-sfdc-sync.md
skills/eod-todo-csm-tracker.md
skills/morning-meeting-prep.md
```

- [ ] **Step 3: Commit**

```bash
git add cowork/README.md
git commit -m "Add CoWork onboarding README"
```

---

### Task 5: End-to-end dry run (manual verification)

**Files:** none created or modified — this task exercises Tasks 1-4's output in a live CoWork session. This is the plan's only "test," matching the project's existing personal-tool-scale convention (manual verification, no automated tests — see Code-branch spec's Testing Strategy).

**Interfaces:**
- Consumes: the setup message from Task 4, the three files from Tasks 1-3, `src/artifact/command-center.html` and `scripts/empty-seed.json` from `main`.
- Produces: nothing shipped — a pass/fail signal on whether Tasks 1-4 actually work end-to-end before this goes to any other CSM.

- [ ] **Step 1: Push the branch**

```bash
git push origin cowork
```

- [ ] **Step 2: Start a fresh CoWork session with no prior Command Center artifact or scheduled tasks**

Confirm before proceeding: no existing "Command Center" artifact and no existing `bob-sfdc-sync` / `morning-meeting-prep` / `eod-todo-csm-tracker` scheduled tasks in this session. If any exist from earlier testing, remove them first so this run is a genuine clean-state test.

- [ ] **Step 3: Paste the exact setup message from Task 4's README, with your real name substituted**

Use the literal message text from `cowork/README.md`'s Step 1 block, replacing `[Your Full Name, exactly as it appears in Salesforce]` with your actual name.

- [ ] **Step 4: Verify the WebFetch succeeded and substitution has no leftover tokens**

Ask Claude to show the resolved text of all three skill files before it creates the scheduled tasks. Confirm none of them contain `{{CSM_NAME}}`, `{{ARTIFACT_URL}}`, or `{{SFDC_CSM_FILTER}}` — every token should be replaced with real values.

- [ ] **Step 5: Verify the artifact published successfully**

Open the returned artifact URL. Confirm it loads, shows the three tabs (Book of Business, Calendar, To Dos), and all three are empty (matching `scripts/empty-seed.json`'s empty arrays/objects) since this is a fresh account with no prior data.

- [ ] **Step 6: Verify all three scheduled tasks were created**

List the session's scheduled tasks. Confirm exactly three exist: `bob-sfdc-sync` (Mon/Wed/Fri 5am), `morning-meeting-prep` (weekdays 7am), `eod-todo-csm-tracker` (weekdays 3:30pm), each with the artifact URL from Step 5 baked into its prompt text.

- [ ] **Step 7: Trigger one automation manually to confirm the write-scope discipline holds**

Ask Claude to run the `bob-sfdc-sync` task's prompt right now (don't wait for the real cron). After it publishes, read the artifact's current state and confirm only `accounts`, `lastSynced.salesforce`, and `syncLocks.bob` changed — `overrides`, `meetings`, `tasks`, and `archived` must be byte-for-byte unchanged from Step 5's empty state.

- [ ] **Step 8: Record the outcome**

If every check in Steps 4-7 passed, this plan is verified — the CoWork onboarding flow is ready to hand to other CSMs. If any check failed, note exactly which step and what happened, fix the relevant file from Tasks 1-4, and re-run this task from Step 2 with a clean state.

---

## Self-Review Notes

- **Spec coverage:** all four Components-table items from the design doc (three skill templates + README) have a task; the design doc's Setup sequence steps 1-6 map onto Task 5's Steps 3-7; the design doc's required dry-run verification is Task 5 in full.
- **Placeholder scan:** no TBD/TODO in any task; every code/content block is the actual file content, not a description of it.
- **Type/token consistency:** `{{CSM_NAME}}`, `{{ARTIFACT_URL}}`, `{{SFDC_CSM_FILTER}}` are the only tokens used across all three skill files, matching the design doc and `main`'s existing `setup.py` token set exactly (`{{REPO_PATH}}` deliberately dropped per the design doc, since there is no local clone to resolve it against).
