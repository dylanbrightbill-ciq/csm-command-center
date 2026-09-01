# T1 — Foundation: schema, migration, shared utilities

## Context

The CSM Command Center replaces the current CSM Tracker artifact with a clean
account schema, a proven task-merge pattern carried forward, and a new shared
protocol that every future refresh skill (T2, T3, T4) will follow. This ticket
has no independent user-facing behavior of its own — it is the foundation the
other three tickets build on. When it lands, opening the new artifact shows all
42 accounts (clean field names, no duplicate `*Fallback` fields) and every open
task from CSM Tracker, correctly migrated.

**Spec:** [docs/specs/2026-09-01-csm-command-center-spec.md](../specs/2026-09-01-csm-command-center-spec.md) — Data Model, Contracts & Interfaces, Migration & Rollback sections; ticket 1 of 4.

## Tangible Changes

- A new artifact exists, showing the same 42 accounts CSM Tracker shows today,
  under the clean 26-field schema instead of the current schema's duplicated
  fields.
- Every open task from CSM Tracker appears in the new artifact, linked to the
  correct account.
- Manually-entered fields (CSM Sentiment, Risk, Notes, Cap Research Status, CIQ
  Executive Sponsor, Last EBR) carry over exactly as they are in CSM Tracker
  today.
- No change yet to CSM Tracker itself — it stays live and untouched as the
  rollback target.
- The artifact shows the new 3-tab shell (Book of Business / Calendar / To
  Dos), using the visual design in
  [docs/design/command-center-mockup.html](../design/command-center-mockup.html)
  and [tokens.css](../design/tokens.css) — a custom theme, not CSM Tracker's
  look. Book of Business tab is populated; Calendar and To Dos tabs render
  their empty states (no meetings yet, no Kanban cards yet) until T3/T4 land.
- No live refresh pipeline yet — that comes in T2/T3/T4. This ticket ships the
  empty shell (`meetings: {}`, `syncLocks: {bob: null, meetings: null, todos:
  null}`) that those tickets fill in.

## Implementation Map

- **Migration script:** a one-time Python script that reads CSM Tracker's
  current published state, maps it to the clean schema, and flags anything it
  cannot map with confidence.
- **Shared protocol doc:** a new reference document describing the read-merge-
  write cycle, the sync-lock check, and the account-name matcher, written so
  T2/T3/T4 can each follow it without re-deriving the algorithm.
- **Artifact source:** the new artifact's initial HTML/JS, built from the
  visual design mockup (tab strip + status bar + Book of Business tab
  populated from the migration output; Calendar and To Dos tabs present but
  empty), using `tokens.css`'s custom theme. KPI row and column customization
  are new to this design pass — not carried forward from CSM Tracker's old
  UI, which this project is explicitly moving away from.

## Code Changes

### Migration script

**`scripts/migrate-csm-tracker.py`** — new file. Follows the same structure as
the prior build's `merge_seed.py` (in Dylan's separate `Documents/Claude/Code`
workspace, not this repo), which already solved account-name resolution for
this exact data. Reuse its approach directly rather than reinventing it:
normalize the name (strip punctuation and spaces, lowercase), check a
hand-maintained alias map for known nicknames or renamed accounts, then fall
back to substring containment. Extend the alias map with the current CSM
Tracker's actual nicknames as they're discovered during migration, the same
way the prior script accumulated
`{"coreweave": "Weights and Biases", "fivetran": "dbt Labs", ...}`.

Unlike the prior script, this one operates on CSM Tracker's live JSON directly
(read via the Artifact tool), not on a locally-cached HTML snapshot, so the
input-reading step differs even though the matching logic is identical.

```python
def map_account(old_account: dict) -> tuple[dict, list[str]]:
    """Map one CSM Tracker account to the clean schema.
    Returns (new_account, unmapped_field_warnings)."""
    # drop every *Fallback duplicate; keep the live value each duplicate pair
    # represents. Warn (do not guess) on any field with no clean single-value
    # equivalent in the old schema.
    ...
```

Output: `migration-output.json` (the new schema's `accounts` and `overrides`),
plus `migration-review.md` listing every account or field flagged for manual
review. Migration is not done until that review list is empty or explicitly
accepted by Dylan.

**Unknown:** the exact set of duplicate `*Fallback` fields in CSM Tracker's
current schema was sampled from one account (Feedzai) during the spec's
research, not exhaustively enumerated across all 42. Confirm the full set
before writing the field-mapping table.

### Shared protocol doc

**`docs/shared-refresh-protocol.md`** — new file, referenced by T2/T3/T4's
skill instructions instead of each restating it. Documents, as precise
followable steps (the same style CSM Tracker's existing `eod-todo-csm-tracker`
scheduled task already uses successfully):

1. Read the artifact's current published state.
2. Check `syncLocks.<section>`. If set, hold and poll until clear (manual
   refresh only — a cron never waits).
3. Set `syncLocks.<section>` to the current timestamp and publish that lock
   alone, atomically with the check in step 2, before doing any further work.
   ⚠️ Shortcut risk: if check-then-set is done as two separate publishes
   instead of one, a race is possible. Alternative: combine the check and the
   set into a single read-then-conditionally-publish call.
4. Do the section's own work (gather data, resolve accounts via the shared
   matcher below).
5. Read the artifact's current state again (it may have changed since step 1
   if this was a manual refresh that waited).
6. Merge: update only this section's owned fields, leave every other field
   untouched.
7. Publish the merged state, then clear `syncLocks.<section>`.

Also documents the shared account matcher as its own reusable procedure
(normalize, alias map, substring fallback — identical logic to the migration
script above), so T3 and T4 both point at one definition instead of two
copies drifting apart.

### Artifact source

**`src/artifact/command-center.html`** — new file. Implements the 3-tab shell
from the visual design (status bar, tab strip, Book of Business / Calendar /
To Dos tabs) using `tokens.css`'s custom theme. Book of Business tab
populated from migration output (KPI row + table); Calendar tab renders its
weekly-grid empty state pending T3; To Dos tab renders its Kanban empty state
pending T4. Seed-data script tag holds the new schema. This is a from-scratch
visual build per the design pass, not a port of CSM Tracker's old UI.

```html
<script type="application/json" id="seed-data">
{ "accounts": [...], "overrides": {...}, "meetings": {}, "tasks": [...],
  "archived": [...], "customTypes": [], "layout": {...}, "kpiVisible": {...},
  "columnSort": {}, "columnWidths": {...},
  "lastSynced": {"salesforce": "<migration timestamp>", "meetings": null, "eodTodo": "<carried from CSM Tracker>"},
  "syncLocks": {"bob": null, "meetings": null, "todos": null} }
</script>
```

### Tests

- Manual verification only, matching this project's testing strategy (no
  automated test suite exists for this tool). See Verification below.

## Key Files

| File | Change |
|------|--------|
| `scripts/migrate-csm-tracker.py` | New. One-time migration script. |
| `docs/shared-refresh-protocol.md` | New. Read-merge-write, lock, and matcher procedure shared by T2/T3/T4. |
| `src/artifact/command-center.html` | New. Initial artifact source, seeded from migration output. |

## Verification

1. Run the migration script against CSM Tracker's current published state.
   Confirm `migration-review.md` is empty, or every flagged item has been
   resolved with Dylan.
2. Spot-check five accounts by hand against CSM Tracker's current values,
   field by field, under the new names.
3. Publish `src/artifact/command-center.html` seeded with the migration
   output. Confirm all 42 accounts and every open task appear, with overrides
   intact.
4. Confirm CSM Tracker itself is untouched and still loads normally, as the
   rollback target.
