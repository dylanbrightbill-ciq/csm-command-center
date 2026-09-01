# T3 — Calendar tab (weekly) and meeting-prep pipeline

## Context

Today's meeting prep currently produces a standalone document each morning and
saves it nowhere — Dylan has to find it in that morning's chat history. This
ticket adds the Calendar tab: the same prep work, linked to the right account,
persisted in the artifact so it is still there when he opens it before a call
later in the day.

**Spec:** [docs/specs/2026-09-01-csm-command-center-spec.md](../specs/2026-09-01-csm-command-center-spec.md) — Data Model (Meeting record), Contracts & Interfaces (meeting-prep write contract), ticket 3 of 4.

## Tangible Changes

- The Calendar tab shows a **weekly Mon–Fri grid**, not a single day. Each
  day's column shows a card per external customer meeting that day, with the
  same prep content the standalone document has today (agenda, risks,
  history), linked to the correct Book of Business account. The grid fills in
  incrementally — Monday's cron populates Monday's column, Tuesday's fills
  Tuesday's, and so on, so mid-week the grid shows every day run so far
  alongside empty columns for days not yet reached.
- Each card has a notes field Dylan can fill in during or after the meeting,
  which persists across refreshes.
- The scheduled prep run moves from 8am to 7am weekdays.
- Dylan can also trigger a fresh prep run by asking in chat, or by clicking the
  Calendar tab's refresh button.
- No change to which meetings count as "external customer meetings" or which
  sources meeting-prep searches (Calendar, Granola, Gong, Gmail, Salesforce,
  support tickets) — only where the output goes changes.

## Implementation Map

- **Skill update:** `morning-meeting-prep`'s existing SKILL.md gets a new output
  step, replacing "produce a standalone document" with "publish into the
  meetings entity, following the shared protocol."
- **Artifact:** the `meetings` entity and its weekly-grid tab UI (five day
  columns, each rendering that date's `meetings[date]` entries or an empty
  state), new in this ticket.
- **Shared matcher use:** this is the first real caller of T1's fuzzy account
  matcher, resolving each meeting's counterparty to an `accountId`.

## Code Changes

### Skill update

**`skills/morning-meeting-prep/SKILL.md`** — update the existing file (real
content already read: front-matter `description` names the 8am trigger, steps
1–4 check Calendar, identify external meetings, invoke `/meeting-prep` per
meeting, and output one document per meeting). Two changes:

1. Front-matter `description` and the schedule change from 8am to 7am weekdays.
2. Replace step 4 ("Output: Produce one meeting prep document per meeting")
   with:

```markdown
4. **Output**: for each external customer meeting found today, resolve its
   account using the shared fuzzy matcher (docs/shared-refresh-protocol.md) to
   get an accountId. Then follow the shared protocol's publish steps: check
   and set syncLocks.meetings, read the artifact's current state, write
   meetings[today][accountId] = { brief: <the prep content>, notes: "",
   notesOpen: false, sources: [...] }, publish, clear the lock, bump
   lastSynced.meetings.

   If no accountId resolves with confidence, still publish the brief under a
   null accountId rather than dropping it — surface it as unlinked in the
   panel instead of guessing wrong.

   If no external meetings are found today, skip the publish entirely rather
   than writing an empty meetings[today] entry.
```

Everything else in the skill (Calendar check, external-meeting filtering,
invoking `/meeting-prep` itself, tone/formatting preferences) stays unchanged.

### Artifact

**`src/artifact/command-center.html`** — add the Calendar tab: a five-column
weekly grid (Mon–Fri, computed from the current week's dates), each column
rendering that date's `meetings[date][*]` entries as cards (brief + editable
notes field bound to `meetings[date][accountId].notes`), or an empty state
("No meetings scheduled") when that date has no entries yet. Add the tab's
refresh button (same ask-Claude mechanism as T2's, same open question about
capability availability).

```html
<!-- inside seed-data, once T3 lands -->
"meetings": {
  "2026-09-01": {
    "0011I00000Zl3HaQAJ": { "brief": "...", "notes": "", "notesOpen": false, "sources": [] }
  },
  "2026-09-03": {
    "0011I00001Nt8dFQAR": { "brief": "...", "notes": "", "notesOpen": false, "sources": [] }
  }
```

### Tests

- Manual verification only, per this project's testing strategy.

## Key Files

| File | Change |
|------|--------|
| `skills/morning-meeting-prep/SKILL.md` | Update: 7am schedule, publish into `meetings` instead of a standalone doc. |
| `src/artifact/command-center.html` | Add Calendar tab UI and refresh button. |

## Verification

1. Run the updated skill on a real day with at least one external meeting.
   Confirm the brief appears in the Calendar tab, linked to the correct
   account.
2. Test the fuzzy matcher against a known tricky case (an abbreviation, an
   "Inc"/"Inc." suffix difference, or a minor misspelling already seen in the
   migrated account list) and confirm it still resolves correctly. Test a
   genuinely unrelated name and confirm it falls back to unlinked rather than
   a wrong match.
3. Run the skill twice in a row for the same day with no new meetings.
   Confirm no duplicate or overwritten entries.
4. Confirm the schedule actually fires at 7am, not 8am, on the next weekday.
5. Add a note to a meeting card, then trigger an unrelated refresh (Book of
   Business or Todos). Confirm the note is untouched.
