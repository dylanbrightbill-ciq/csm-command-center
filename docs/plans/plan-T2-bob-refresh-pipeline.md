# T2 — Book of Business refresh pipeline

## Context

The Book of Business tab needs a way to keep its Salesforce-owned fields
(ARR, renewal date, seats, support level, pipeline, risk records, and so on)
current, now that CSM Tracker's old live-in-browser sync is being removed and
the weekly intel digest skill is staying fully separate. This ticket builds a
new, dedicated skill for exactly that: pull the core fields, publish them
through T1's shared protocol, on a schedule plus on demand.

**Spec:** [docs/specs/2026-09-01-csm-command-center-spec.md](../specs/2026-09-01-csm-command-center-spec.md) — Contracts & Interfaces (bob-sfdc-sync write contract), ticket 2 of 4.

## Tangible Changes

- A new scheduled task runs Monday, Wednesday, and Friday at 5am EST, refreshing
  every account's Salesforce-owned fields in the Book of Business tab.
- Dylan can also trigger the same refresh by asking in chat, or by clicking the
  Book of Business tab's refresh button.
- Manually-entered fields (CSM Sentiment, Risk, Notes, Cap Research Status, CIQ
  Executive Sponsor, Last EBR) are never touched by this refresh, on any
  trigger path.
- No change to the weekly intel digest skill — it keeps running exactly as it
  does today, fully independent of this pipeline.
- No change to the Calendar or To Dos tabs.

## Implementation Map

- **New skill:** `bob-sfdc-sync`, a new scheduled-task skill file following the
  same shape as the existing `eod-todo-csm-tracker` and
  `bob-customer-intel-digest-weekly` scheduled tasks, but pulling core account
  fields instead of news signals.
- **Artifact wiring:** a refresh button on the Book of Business tab, using
  the runtime capability that lets the page ask Claude a question directly.

## Code Changes

### New skill

**`skills/bob-sfdc-sync/SKILL.md`** — new file. Modeled directly on the real,
existing `bob-customer-intel-digest-weekly/SKILL.md` structure (front-matter
name/description, a plain-language instruction body), but the body follows
T1's shared protocol instead of producing a chat-only digest:

```markdown
---
name: bob-sfdc-sync
description: Refresh core Salesforce fields into the CSM Command Center's Book of Business tab, Mon/Wed/Fri 5am EST + on-demand
---

Pull Dylan's active Salesforce accounts (CSM__r.Name = 'Dylan Brightbill') —
ARR (active subscription and sum of amount), renewal date, seats occupied,
payees purchased, seat utilization, instance seat count, support level,
processing frequency, active processing status, implementation projects, risk
records, and open pipeline.

Follow docs/shared-refresh-protocol.md exactly for the publish step: check and
set syncLocks.bob, read the artifact's current state, merge only the
Salesforce-owned account fields, publish, clear the lock, bump
lastSynced.salesforce.

Never write to overrides, meetings, tasks, or archived.
```

**Deploy location:** this file gets installed as an actual scheduled task the
same way the three existing ones are (`~/Documents/Claude/Scheduled/` or
`~/.claude/scheduled-tasks/`, per Dylan's existing convention) — that step
happens at implementation/deploy time, not by writing to this repo alone. Keep
the repo copy as the versioned source of truth per the earlier decision to
version skill sources here.

**Unknown:** exact field-to-Salesforce-object mapping (which fields come from
the Account object directly versus related Opportunity/Implementation_Project
records) was sampled from one account (Feedzai) during the spec's research,
not confirmed against Salesforce's actual schema. Confirm the full mapping
before this skill's first real run.

### Artifact wiring

**`src/artifact/command-center.html`** — add a refresh button to the Book of
Business tab header. On click, it should ask Claude to run the bob-sfdc-sync
skill, using the runtime's ask-Claude capability.

⚠️ Shortcut risk: this button depends on a runtime capability whose
availability on Dylan's account is still unconfirmed (open question from the
spec). Alternative if unavailable: ship the tab without the button for now,
and rely on the cron plus "ask in chat" as the only two trigger paths — this
does not block the rest of the ticket, since the skill and its cron/chat paths
work independently of the button.

### Tests

- Manual verification only, per this project's testing strategy.

## Key Files

| File | Change |
|------|--------|
| `skills/bob-sfdc-sync/SKILL.md` | New. Scheduled-task skill, Mon/Wed/Fri 5am EST. |
| `src/artifact/command-center.html` | Add Book of Business tab refresh button. |

## Verification

1. Trigger `bob-sfdc-sync` manually (chat) once T1's artifact is live. Confirm
   Salesforce-owned fields update and every override survives unchanged.
2. Run it twice in a row with no real-world Salesforce change in between.
   Confirm the second run produces the same data, not a spurious duplicate
   publish.
3. Confirm the actual scheduled task fires at the next Mon/Wed/Fri 5am EST
   window once deployed.
4. If the refresh button ships: click it, confirm it triggers only the Book
   of Business refresh, not a full-page regeneration. If it does not ship
   (capability unavailable): confirm chat-triggered refresh still works as
   the tested fallback.
