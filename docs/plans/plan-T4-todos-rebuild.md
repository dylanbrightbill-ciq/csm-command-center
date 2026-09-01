# T4 — Todos rebuild

## Context

The existing end-of-day todo skill already does the hard part well: it
generates a prioritized todo list from the day's calendar, email, Slack, and
Salesforce activity, and merges it into a task list without ever duplicating
or resurrecting an old item. This ticket updates it in place: point it at the
new artifact, add today's meeting notes as a new input source, and replace its
case-insensitive-substring account matching with the shared fuzzy matcher.

**Spec:** [docs/specs/2026-09-01-csm-command-center-spec.md](../specs/2026-09-01-csm-command-center-spec.md) — Contracts & Interfaces (end-of-day-todo write contract), ticket 4 of 4 (last, depends on T3).

## Tangible Changes

- The Todos panel keeps working exactly as it does today in CSM Tracker: a
  prioritized list, generated at 3:30pm weekdays, merged in without ever
  duplicating or resurrecting an archived task.
- Todos can now reference things that came up in today's meeting notes (from
  the Today panel), not just calendar/email/Slack/Salesforce activity.
- Account matching gets more reliable — abbreviations, "Inc"/"Inc." suffix
  differences, and minor misspellings that used to fail the old
  substring-only match now resolve correctly, using the same matcher T3 uses.
- Dylan can also trigger a fresh todo run by asking in chat, or by clicking
  the Todos panel's refresh button.
- No change to the urgency buckets, badge logic, or the rule that meeting prep
  is out of scope for this list (that stays morning-meeting-prep's job).

## Implementation Map

- **Skill update:** `eod-todo-csm-tracker`'s existing SKILL.md (already proven:
  task-object shape, id/dedup/archive logic, publish steps) gets three
  changes: new input source (today's meeting notes), replace its own inline
  substring matcher with the shared one, and retarget the publish step from
  CSM Tracker to the new artifact.
- **No new entity.** The `tasks`/`archived` shape is unchanged from what CSM
  Tracker already proved works.

## Code Changes

### Skill update

**`skills/eod-todo-csm-tracker/SKILL.md`** — update the existing file (real
content already read: gathers from Calendar/Granola/Gmail/Slack/Salesforce,
synthesizes a prioritized list, then a detailed step 6 that parses tasks,
reads the artifact, resolves accountId, dedups against `tasks`+`archived`,
merges, and republishes). Changes:

1. Step 1 gains a new source: "today's meeting notes, read from
   `meetings[today][*].notes` in the artifact — treat these the same as an
   email or Slack thread, as a source of follow-up items."
2. The existing account-resolution logic ("case-insensitive substring, either
   direction") is replaced with a reference to the shared fuzzy matcher in
   `docs/shared-refresh-protocol.md`, instead of a second inline
   implementation. Fields captured per task stay exactly as they are today
   (id, text, badge, done, dueDate, createdAt, notes, sources, notesOpen) —
   only how `accountId` gets resolved changes.
3. Step 6's read/merge/publish target changes from CSM Tracker's URL to the
   new Command Center artifact's URL. The dedup logic itself (`seen` set built
   from both `tasks` and `archived`, never resurrecting archived) is proven
   and carries over unchanged.
4. Step 6 additionally follows T1's sync-lock protocol before publishing:
   check and set `syncLocks.todos`, and if a bob-sfdc-sync or meeting-prep
   cron currently holds a different lock, that is fine — todos only waits on
   its own lock, not the others.

Everything else (badge auto-assignment rules, "skip publish if nothing new"
behavior, tone/context preferences) stays unchanged from the real existing
skill.

### Tests

- Manual verification only, per this project's testing strategy.

## Key Files

| File | Change |
|------|--------|
| `skills/eod-todo-csm-tracker/SKILL.md` | Update: read meeting notes, use shared matcher, retarget publish to new artifact, use shared lock protocol. |

## Verification

1. Run on a day where the Today panel has at least one meeting with notes.
   Confirm the generated todos reference something from those notes, not just
   calendar/email/Slack/Salesforce activity.
2. Run twice in a row for the same day with no new activity. Confirm the
   second run is a true no-op — no duplicate tasks, no spurious publish
   (already the existing skill's proven behavior; confirm it still holds
   against the new artifact).
3. Test the shared matcher against the same known tricky and known-unrelated
   name cases used in T3's verification, confirming consistent behavior
   between the two skills.
4. Simulate a `syncLocks.bob` or `syncLocks.meetings` lock held during a
   manual Todos refresh. Confirm Todos proceeds anyway, since it only waits on
   its own lock.
5. Confirm every existing override and every prior task/archived entry
   (migrated in T1) survives this run unchanged.
