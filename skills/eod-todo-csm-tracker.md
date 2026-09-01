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
