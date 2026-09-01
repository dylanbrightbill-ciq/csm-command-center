# CSM Command Center — Tech Spec

> **Status:** Draft
> **Author:** Claude (with Dylan Brightbill)
> **Date:** 2026-09-01
> **Jira:** Not applicable. This is personal CSM tooling, not a CaptivateIQ product ticket.

## Context

Dylan is a Senior Enterprise CSM at CaptivateIQ. He wants one place to see his book of
business, prepare for today's meetings, and track end-of-day todos. He wants that place
to be a Claude Artifact he opens each day, not a mix of documents and one-off chat replies.

This need is already partly met, in an organically grown form. A live artifact called
CSM Tracker holds 42 accounts synced from Salesforce and a task list fed by a scheduled
task. It works, but it has three problems. Its account schema carries duplicate fields
left over from earlier iterations. It has no section for today's meetings. It refreshes
Salesforce data live, in the browser, on every page open, instead of through a
controlled and auditable step.

Three scheduled tasks already run against pieces of this workflow. One prepares a
meeting document each morning but never saves it anywhere. One pushes end-of-day
todos into CSM Tracker's task list and already does this well: it merges new tasks in
without ever duplicating or resurrecting an old one. One produces a weekly account
intelligence digest (news, leadership changes) but does not update any artifact and
does not sync core Salesforce fields — that stays a separate, independent tool and is
not touched by this project.

CSM Tracker's core Salesforce fields (ARR, renewal date, seats, risk records, and so
on) refresh today through a live client-side call to Salesforce on every page open,
a different mechanism entirely from the intel digest. This spec removes that live
call and replaces it with a new dedicated scheduled skill, described below.

This spec defines a single new artifact and refresh pipeline that replaces CSM Tracker
and the other partial or abandoned iterations that preceded it. It reuses what already
works, in particular the proven task-merge logic, and fixes what does not.

### References
- **Architecture doc:** [2026-09-01-csm-command-center-architecture.md](2026-09-01-csm-command-center-architecture.md) — the brainstorming-stage design this spec formalizes.
- **Superseded spec:** the prior merge design (referenced in the architecture doc, held in Dylan's separate Claude Code workspace) — the design that produced the current CSM Tracker artifact.
- **PRD/BRD:** None. This work originated directly from a brainstorming session with Dylan, with no separate product document.

### User Flows / Use Cases

**Use case 1: Monday morning check-in**
1. Dylan opens the Command Center artifact at his desk.
2. He sees the Book of Business panel, refreshed earlier that morning (or, worst
   case, two days prior) by the Monday/Wednesday/Friday 5am sync. Renewal dates,
   ARR, and risk records are current as of the last sync timestamp shown at the
   top of the panel.
3. He sees the Today panel already populated. A 7am scheduled task ran before he sat
   down and prepared a brief for his 10am call with a customer.
4. He reads the brief, which includes that account's book-of-business snapshot and
   his notes from the last touchpoint.

**Use case 2: End of a busy day**
1. Dylan finishes a day full of calls and slack threads.
2. At 3:30pm, a scheduled task reads today's calendar, email, Slack activity, and the
   notes he left in the Today panel during his meetings.
3. It writes a short prioritized todo list into the Todos panel. Items already in the
   list, including ones he already checked off, are untouched.
4. Dylan glances at the new items, adjusts one due date, and moves on.

**Use case 3: Mid-afternoon manual refresh**
1. Dylan just got off a call that changed his read on an account's risk.
2. He wants an updated brief before his next call with a different account, without
   waiting for the 7am cron.
3. He clicks the refresh button on the Today panel.
4. The panel updates with a fresh brief for his next meeting, without touching the
   Book of Business or Todos panels.

## Scope

**In scope:** a single new artifact with three panels (Book of Business, Today,
Todos), a clean account schema, a one-time migration from CSM Tracker, a
cron-priority write-locking mechanism, fuzzy account-name matching shared across
panels, per-panel manual refresh (chat and in-page button), and a rebuilt end-of-day
todo skill that also reads today's meeting notes.

**Out of scope:** a shared or multi-CSM view of this artifact, live in-browser
Salesforce calls (removed by design, see Technical Design), the weekly account
intelligence digest skill (stays fully separate, not touched by this project),
any change to how the meeting prep skill gathers its source data (only where its
output is published changes), and any new account or task creation flows beyond
what CSM Tracker already has.

**Constraints:** this is a personal productivity tool, not a customer-facing
product. It carries no cross-team contract review, no service-level objective, and
no requirement for automated alerting on failure. Dylan has said that noticing a
stale sync timestamp is an acceptable failure signal. The artifact must stay
private. It caches real Salesforce customer data and must never be shared or
published for others to view.

## Technical Design

### Architecture

One artifact holds the full state as a single saved JSON document, edited only
through a read-merge-write cycle. Three independent skills write into different
parts of that document. No skill overwrites another skill's part of the state.

```
Salesforce  ──> bob-sfdc-sync skill ─────────┐
Calendar,   ──> meeting-prep skill ──────────┼──> read-merge-write ──> artifact state
Gong, Gmail,                                 │        (locked per section)
Slack       ──> end-of-day-todo skill ───────┘             │
                    ^                                       │
                    └────────── reads today's meeting notes ┘
```

The weekly account intelligence digest (news, leadership changes) is a separate,
independent skill, unrelated to this diagram. It is out of scope for this project.

Each of the three skills runs on its own schedule and can also run on demand, either
by chat request or by a refresh button embedded in its panel. Every run, scheduled
or manual, follows the same read-merge-write discipline: read the artifact's current
state, update only the fields that skill owns, and republish. Fields another skill
owns, or that Dylan edits by hand, are carried forward untouched.

### Data Model

The artifact state is one JSON document with these top-level entities.

- **Entity:** Account record
  - **Change:** replaces CSM Tracker's account object. Carries the 26 fields Dylan
    specified (ARR active and ARR sum, renewal date, meeting cadence, churn score,
    CSM sentiment, risk, risk records, expansion pipeline, active processing,
    implementation, customer service start date, support level, fiscal year,
    processing frequency, previous tool, seats occupied, payees purchased, seat
    utilization, instance seat count, MSA price increase cap, cap research status,
    CIQ executive sponsor, last EBR, notes, private or public, industry), plus an
    account identifier and a Salesforce identifier. Drops every duplicate
    "fallback" field the current schema has accumulated.
  - **Migration concern:** one-time import from the current 42 accounts. Fields
    that split into an automated and a manual version today (for example risk,
    which has both a computed churn score and a CSM-judgment risk rating) must map
    to exactly one field each in the new schema, not both a live and a fallback
    copy.

- **Entity:** Override record
  - **Change:** unchanged from CSM Tracker's proven pattern. A map keyed by account
    name, holding only the fields Dylan edits by hand: CSM sentiment, risk, notes,
    cap research status, CIQ executive sponsor, last EBR. No automated sync ever
    writes to this map.
  - **Migration concern:** carry forward as is from CSM Tracker.

- **Entity:** Meeting record (new)
  - **Change:** a map from date to account identifier to a record holding the
    meeting brief text, Dylan's notes, and a note-panel open or closed flag. This
    entity does not exist in CSM Tracker today.
  - **Migration concern:** none. Starts empty.

- **Entity:** Task record
  - **Change:** unchanged from CSM Tracker's proven schema: identifier, done flag,
    due date, text, badge, sources, created timestamp, notes, account identifier,
    notes-panel open flag. The merge logic that prevents duplicates and never
    resurrects an archived task is also unchanged.
  - **Migration concern:** carry forward open tasks from CSM Tracker as is.

- **Entity:** Sync lock record (new)
  - **Change:** one timestamp per panel (book of business, meetings, todos),
    null when no sync is in progress. Read by every write path before it publishes.
  - **Migration concern:** none. Starts empty.

### Contracts & Interfaces

There is no network API in the traditional sense. The contract between the three
skills and the artifact is the shape of the JSON state document itself, since every
skill reads and writes that same document directly.

- **Type:** shared document state, read and republished by each skill
- **Direction:** bidirectional, one skill at a time per panel, enforced by the sync
  lock
- **Write contract, bob-sfdc-sync skill (new dedicated skill, not the intel digest):**
  ```json
  {
    "accounts": ["<full replacement of Salesforce-owned fields, keyed by accountId>"],
    "syncLocks": { "bob": "<ISO timestamp, cleared on completion>" },
    "lastSynced": { "salesforce": "<ISO timestamp>" }
  }
  ```
  Must never write to `overrides`, `meetings`, `tasks`, or `archived`.
- **Write contract, meeting-prep skill:**
  ```json
  {
    "meetings": { "<date>": { "<accountId>": { "brief": "string", "notes": "string", "notesOpen": "boolean" } } },
    "syncLocks": { "meetings": "<ISO timestamp, cleared on completion>" },
    "lastSynced": { "meetings": "<ISO timestamp>" }
  }
  ```
  Must never write to `accounts`, `overrides`, `tasks`, or `archived`.
- **Write contract, end-of-day-todo skill:**
  ```json
  {
    "tasks": ["<new task records appended, existing ones untouched>"],
    "syncLocks": { "todos": "<ISO timestamp, cleared on completion>" },
    "lastSynced": { "eodTodo": "<ISO timestamp>" }
  }
  ```
  Reads `meetings[today][*].notes` as an input source. Resolves a free-text account
  name to an `accountId` using the shared fuzzy matcher. Never guesses past the
  matcher's confidence threshold. Must never write to `accounts`, `overrides`, or
  `meetings`.
- **Breaking change risk:** none outside this system. Nothing else in Dylan's
  workflow reads this document today. The only consumer is the artifact page
  itself and the three skills defined here.

### Migration & Rollback

- **Migration steps:**
  1. Read CSM Tracker's current published state in full.
  2. For each of the 42 accounts, map its fields to the new clean schema. Drop
     every duplicate fallback field. Flag any field that cannot be mapped
     unambiguously for Dylan's manual review, rather than guessing.
  3. Carry the `overrides` map forward unchanged, renaming keys where the
     underlying field was renamed in step 2.
  4. Carry forward every open (non-archived) task unchanged.
  5. Publish the new artifact with these three entities populated, `meetings` and
     `syncLocks` empty, and `lastSynced` set to the migration timestamp.
  6. Point all three scheduled tasks at the new artifact's identifier.
- **Feature flag:** not applicable. This is a single-user tool with one deployment
  target, the artifact itself.
- **Rollback plan:** CSM Tracker is not deleted or modified by this migration. If
  the new artifact has a problem, Dylan keeps using CSM Tracker and its existing
  scheduled tasks until the issue is fixed, then re-runs the migration.
- **Data backfill:** none needed beyond the one-time account and task import
  described above.

## Proposed Tickets

These are blocking edges, not an execution order. Any ticket whose blockers are
done can start.

| # | Title | Description | Blocked by | Estimate |
|---|-------|-------------|------------|----------|
| 1 | Foundation: schema, migration, shared utilities | Define the clean account schema. Write the one-time migration script from CSM Tracker, including the manual-review flag for unmappable fields. Build the shared sync-lock read-merge-write utility and the shared fuzzy account-name matcher. Publish the new artifact with Book of Business and Todos populated from migrated data. Testable when done: the new artifact shows all 42 accounts and every open task, matching CSM Tracker field for field under the new names. | None | M |
| 2 | Book of Business refresh pipeline | Build a new dedicated bob-sfdc-sync skill (separate from the out-of-scope intel digest) that pulls core Salesforce fields and publishes through the shared read-merge-write utility. Add the Monday/Wednesday/Friday 5am EST cron, the on-demand chat path, and the panel's refresh button. Testable when done: triggering a refresh updates Salesforce-owned fields and leaves every override untouched. | 1 | M |
| 3 | Today panel and meeting-prep pipeline | Add the `meetings` entity and its panel UI. Wire the meeting-prep skill to publish through the shared utilities, using the fuzzy matcher to resolve accounts. Add the 7am weekday cron, the on-demand chat path, and the panel's refresh button. Testable when done: a real meeting today produces a brief in the panel, linked to the correct account. | 1 | M/L |
| 4 | Todos rebuild | Rebuild the end-of-day-todo skill to also read today's meeting notes as an input source, alongside calendar, email, Slack, and Salesforce activity. Use the fuzzy matcher for account resolution. Merge into `tasks` through the shared utility. Add the 3:30pm weekday cron, the on-demand chat path, and the panel's refresh button. Testable when done: a day with meeting notes produces todos that reference them, and re-running the same day twice produces no duplicates. | 1, 3 | M |

### Dependency Graph & Parallelism

```
1 (Foundation)
 ├──> 2 (Book of Business pipeline)          — can run in parallel with 3
 └──> 3 (Today panel + meeting-prep) ──> 4 (Todos rebuild)
```

Tickets 2 and 3 can both start as soon as 1 lands. Ticket 4 needs 3 finished first,
since it reads meeting notes that 3 introduces.

## Testing Strategy

- **Test gaps identified:** none of this today runs under any automated test. All
  verification below is manual, matching the scale of a personal tool.
- **Per-ticket testing:**
  | Ticket | Test type | What to test |
  |--------|-----------|-------------|
  | 1 | manual verification | Spot-check a sample of migrated accounts against CSM Tracker's current values. Confirm every flagged unmappable field is resolved before calling migration done. |
  | 2 | manual verification, idempotency check | Run the refresh twice with no real-world change in between and confirm the second run is a true no-op. Confirm overrides survive a full refresh unchanged. |
  | 3 | manual verification, idempotency check | Run meeting-prep on a real day with external meetings. Confirm the brief links to the correct account, including for a known tricky name case (abbreviation, suffix, or minor misspelling). Confirm a genuinely unrelated name still falls back to unlinked rather than a wrong match. |
  | 4 | manual verification, idempotency check | Confirm todos generated after a day with meeting notes reference those notes. Run twice with unchanged input and confirm no duplicate tasks appear. Confirm the lock-holding behavior: trigger a manual refresh while a cron's lock is simulated as held, and confirm the manual call waits rather than writing concurrently. |
- **Integration test requirements:** none across services in the traditional
  sense. The only true integration point worth checking by hand is the sync lock
  itself, tested in ticket 4 above, since it is the one piece of logic three
  independent skills all depend on.
- **Feature flag testing:** not applicable, no feature flag in this design.

## Operational Plan

### Observability
- **Metrics:** none. Not warranted at this scale.
- **Logging:** none beyond what each skill already emits in its own run output.
- **Alerting:** none. Dylan confirmed that a stale `lastSynced` timestamp, noticed
  on next use, is an acceptable failure signal for a personal tool. This is a
  deliberate, confirmed decision, not an oversight.
- **Dashboards:** none. The artifact's own panels serve as the only dashboard
  needed.

### Reliability
- **Failure modes:** a connector failure mid-refresh (Salesforce, Calendar, or any
  other source unreachable) must fail that panel's refresh loudly and leave the
  artifact's existing data untouched. A publish must never overwrite good data
  with a partial or empty result. A scheduled task that never runs at all (for
  example, a broken skill or an authentication failure) has no automated
  detection under this design, consistent with the constraint above.
- **Circuit breakers / retries:** a publish rejected due to a genuine write
  conflict is re-read and retried once against the now-current state, rather than
  forced through.
- **Graceful degradation:** if the artifact runtime's ask-Claude capability, which
  the refresh buttons depend on, is unavailable, the fallback is Dylan asking in
  chat. This fallback path must work regardless of button availability, and must
  be the one actually tested during implementation.

### Securability
- **Auth / access control:** the artifact must remain private to Dylan. It must
  never be shared or published for other viewers.
- **Data handling:** the artifact caches real Salesforce customer data, including
  account financials and risk assessments. This data already exists in Salesforce
  under normal access controls. This design does not widen who can see it, since
  the artifact stays private to the one CSM who already has that Salesforce
  access.
- **Input validation:** not applicable in the traditional sense. The closest
  analog is the fuzzy account matcher's confidence threshold, which must fail
  closed to an unlinked record rather than guess a wrong account.

### Rollback Plan
CSM Tracker is left untouched by this work. If a problem appears in the new
artifact after cutover, Dylan reverts to using CSM Tracker and its existing three
scheduled tasks, then fixes the issue and re-runs the migration when ready.

## Risks & Open Questions

- ⚠️ **Cron-versus-manual write race** — a manual refresh triggered at the exact
  moment a scheduled task is mid-write could, in principle, still see a stale lock
  state under a bad implementation of the lock check. Mitigation: the sync lock
  must be checked and set as one atomic step within the shared utility, not two
  separate reads, and this must be verified explicitly in ticket 1's testing.
- ⚠️ **Fuzzy matcher over-matching** — too loose a similarity threshold risks
  silently linking a task or meeting to the wrong account, which is worse than
  leaving it unlinked. Mitigation: fail closed to unlinked below a conservative
  confidence threshold, and test explicitly against known tricky and known
  unrelated name pairs in ticket 1.
- ❓ **Artifact ask-Claude capability availability** — the refresh buttons depend
  on a runtime capability whose availability on Dylan's account has not been
  confirmed. Needs resolving during ticket 2 or 3's implementation, before the
  button feature is built. The chat fallback must not depend on this answer.
- ❓ **Exact fuzzy-match algorithm and threshold** — left as an implementation
  decision for ticket 1, not fixed at the architecture level.

## Systems Touched

| System | Why it's involved |
|--------|-------------------|
| CSM Command Center artifact | The new artifact itself: schema, panels, and the read-merge-write and sync-lock utilities that every skill writes through. |
| New bob-sfdc-sync skill | New dedicated skill for the Book of Business panel's Salesforce-owned fields. Not the intel digest skill, which stays separate and untouched. |
| Meeting-prep skill (`/meeting-prep`) | Its publish target changes from a standalone document to the new Today panel, and its schedule moves to 7am weekdays. |
| End-of-day-todo skill (`/eod-todo`) | Rebuilt to read today's meeting notes as a new input source and to use the shared fuzzy matcher for account resolution. |
| CSM Tracker artifact (prior) | Source of the one-time migration. Left untouched, serves as the rollback target until cutover is confirmed stable. |
| Salesforce connector | Source of all account-level data synced into the Book of Business panel. |
| Calendar, Gong, Gmail, Slack connectors | Sources for meeting-prep and end-of-day-todo, unchanged from their current use. |

---

*This is a living document. Update as implementation reveals new information.*
