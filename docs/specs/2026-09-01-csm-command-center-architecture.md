# CSM Command Center — Architecture

**Status:** Draft for review
**Author:** Claude (with Dylan Brightbill)
**Date:** 2026-09-01
**Supersedes:** [2026-08-31-csm-tracker-merge-design.md](2026-08-31-csm-tracker-merge-design.md) and the artifacts/scheduled tasks it produced (see "Replaces" below)

## Problem

Dylan (Senior Enterprise CSM) wants one place — a persistent Claude Artifact — that covers his daily workflow: book of business status, today's meeting prep/notes, and end-of-day todos. This already exists in partial, organically-grown form:

- **CSM Tracker** (artifact `b71a4081-07fb-4a52-87bf-30f7db6eaf02`) — 42 accounts synced from Salesforce, a proven `overrides` map for manually-maintained fields, and a proven idempotent `tasks[]`/`archived[]` merge — but its account schema has accumulated duplicate `*Fallback` fields from earlier iterations, there's no "today's meetings" section, and its Salesforce refresh happens **live client-side on every page open** rather than through a controlled, auditable publish step.
- Several earlier/abandoned iterations (Book of Business Tracker ×2, CSM Signal Deck, CSM Ops Console, CSM Terminal, CSM Signal Room, Daily Task Tracker) that this work replaces outright — they simply go stale once the new artifact is live; nothing needs active deletion.
- Three scheduled tasks already run against pieces of this: `morning-meeting-prep` (8am weekdays, outputs a standalone prep doc, never pushed anywhere), `eod-todo-csm-tracker` (3:30pm weekdays, pushes into CSM Tracker's `tasks[]`), `bob-customer-intel-digest-weekly` (Mondays 8:30am, produces a digest, not pushed into any artifact).

This document designs the single artifact and refresh pipeline that replaces all of the above.

## Goals

- One artifact, one dataset, three sections: **Book of Business**, **Today**, **Todos**.
- Personal instance per CSM (not a shared multi-user artifact) — Dylan first, replicable for other CSMs later.
- Manually-maintained fields (CSM Sentiment, Risk, Notes, Cap Research Status, CIQ Exec Sponsor, Last EBR, etc.) persist across every automated refresh, never clobbered.
- Reuse what already works: the `overrides` merge pattern and the `tasks[]`/`archived[]` idempotent-merge pattern, carried forward as-is.
- Clean up what doesn't: drop the `*Fallback` duplicate account fields; move Salesforce refresh from live-client-side-on-open to a controlled cron/manual publish step (see "Behavior change" below).
- Add the missing piece: a **Today** section fed by `/meeting-prep`, linked to Book of Business by `accountId`.
- Rebuild `/eod-todo` to also read today's meeting notes (not just calendar/email/Slack/SFDC activity) and to resolve accounts by fuzzy name match, not exact/substring.
- Cron-vs-manual write safety: scheduled refreshes always win a race; manual (chat or in-page button) refreshes hold and retry rather than colliding.

## Non-goals (this version)

- Not a shared/team-wide dashboard — no cross-CSM view.
- Not building live in-browser data fetching — deliberately moving away from that model (see below).
- No new account/task creation UI beyond what already exists (inline edit, Add Task modal) unless it breaks in migration.
- Not rolling this out to other CSMs yet — this design covers Dylan's instance; replication is a follow-up.

## Behavior change from today

The current CSM Tracker calls Salesforce directly from the browser every time the page opens, via a client-side capability call. The new design **removes this** in favor of: scheduled cron publishes (weekly BoB sync, daily meeting sync) + on-demand chat or button-triggered publishes. This trades "always maximally fresh on open" for "predictable, auditable refresh points with no live dependency on Salesforce reachability from the viewer's browser." Flagging explicitly since it's a real capability removal, not just refactoring.

## Data model

Single JSON blob (artifact self-saved state), evolving today's seed-data shape:

```
{
  accounts: [ { <26 clean fields from Dylan's list, no *Fallback dupes>, accountId, sfdcId } ],
  overrides: { [accountName]: { <manual field edits> } },   // unchanged pattern
  meetings: {
    [date]: { [accountId]: { brief, notes, notesOpen, sources } }
  },                                                          // NEW
  tasks: [ <unchanged task shape: id, done, dueDate, text, badge, sources, createdAt, notes, accountId, notesOpen> ],
  archived: [ ... ],                                          // unchanged
  customTypes: [], layout: {...}, kpiVisible: {...},
  columnSort: {}, columnWidths: {},                           // unchanged UX customization
  lastSynced: { salesforce, meetings, eodTodo },               // add `meetings`
  syncLocks: { bob: null, meetings: null, todos: null }        // NEW — cron-priority locking
}
```

## Components

- **Book of Business panel** — account table, same main/details/hidden configurable column groups as today. SFDC-owned fields come from `/bob-customer-intel-digest`; CSM-judgment fields live in `overrides`, untouched by any sync.
- **Today panel** — one card per external meeting today, keyed by `accountId` + date under `meetings`. Populated by `/meeting-prep`'s brief; notes field is yours, preserved across refreshes.
- **Todos panel** — unchanged task list UI/schema, populated by the rebuilt `/eod-todo`.
- **Refresh buttons** — one per panel, using the artifact runtime's ask-Claude capability to trigger that panel's specific refresh flow without a full-page regen. Falls back to asking in chat if that capability isn't available on this account (to be confirmed during implementation).

## Data flow

Three triggers per section, all following **read → merge → write** against current published state (never a blind overwrite):

1. **`/bob-customer-intel-digest`** — weekly cron (Mon 8:30am) + on-demand (chat or BoB button). Refreshes SFDC-owned account fields only; leaves `overrides`/`notes` untouched; bumps `lastSynced.salesforce`.
2. **`/meeting-prep`** — daily cron **7am weekdays** (moved earlier from 8am) + on-demand (chat or Today button). Writes `meetings[today][accountId]`; never touches `accounts`, `overrides`, or `tasks`.
3. **Rebuilt `/eod-todo`** — daily cron 3:30pm weekdays + on-demand (chat or Todos button). Gathers calendar/email/Slack/SFDC activity **plus today's `meetings[today][*].notes`**; merges into `tasks[]` via the existing id-dedup-against-`tasks`+`archived` logic; skips publish if nothing new; bumps `lastSynced.eodTodo`.

**One-time migration**: import CSM Tracker's 42 accounts + `overrides` + open `tasks`, dropping `*Fallback` duplicates and renaming to the clean 26-field schema. One-shot script, not part of ongoing refresh logic; anything that can't be cleanly mapped is flagged for manual review rather than dropped or guessed.

## Cron-priority locking

Each section has a `syncLocks.<section>` timestamp. A cron sets its lock, does its read-merge-write, clears the lock — crons never wait. A manual refresh (chat or button) checks the lock first: if clear, proceeds immediately; if set, holds and polls until clear, then runs against the now-current state. Guarantees cron writes always land first; manual refreshes never race them, at the cost of an occasional few-second wait if triggered at the same moment a cron fires.

## Error handling

- **Merge conflicts**: handled by the locking scheme above. If a publish is rejected due to a genuine conflict (something else published mid-write), re-read and retry once rather than forcing an overwrite.
- **Account matching**: fuzzy/similarity match (not exact/substring) for resolving free-text account names to `accountId`, in both `/eod-todo` and `/meeting-prep`. Below-confidence matches fall back to `accountId: null` (visible/unlinked) rather than guessing wrong.
- **Connector/skill failure mid-refresh**: fail loudly for that section, leave existing artifact data untouched — never publish partial/empty state over good data.
- **Zero new items**: skip publish entirely (already `/eod-todo`'s behavior; extend to `/meeting-prep` for e.g. weekends or no-external-meeting days).
- **Re-run safety**: every refresh is idempotent — running twice with unchanged input is a no-op the second time.
- **Migration-time mapping issues**: flag for manual review rather than silently dropping or guessing.

## Testing

- Migration: spot-check accounts against the old artifact post-import; resolve every flagged review case before calling migration done.
- Idempotency: run each of the three refreshes twice back-to-back with no real-world change; confirm true no-op second time.
- Locking: simulate a cron in-flight, trigger a manual refresh, confirm it holds and only writes once the lock clears.
- Fuzzy matching: known tricky cases (abbreviations, "Inc"/"Inc." suffixes, minor misspellings) link correctly; unrelated names still fall back to `null`.
- Refresh buttons: confirm each triggers only its own section, and confirm the ask-Claude runtime capability is actually available before relying on it (chat remains the tested fallback).
- Manual field survival: after a full refresh cycle across all three sections, confirm every override/note is exactly as left.

## Open items for implementation planning

- Confirm the artifact runtime's ask-Claude capability is available on this account before building the refresh buttons; design the chat-fallback path regardless.
- Decide exact fuzzy-match algorithm/threshold (e.g. normalized-string edit distance) during implementation, not architecture.
- This working directory is not a git repository — no commit made; confirm with Dylan whether to init one or leave this doc as an uncommitted file for now.
