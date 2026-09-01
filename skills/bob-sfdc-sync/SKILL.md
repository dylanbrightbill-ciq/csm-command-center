---
name: bob-sfdc-sync
description: Refresh core Salesforce fields into the CSM Command Center's Book of Business tab, Mon/Wed/Fri 5am EST + on-demand
---

Refresh the Salesforce-owned account fields in Dylan Brightbill's CSM Command
Center artifact ("Command Center", https://claude.ai/code/artifact/ee70267c-1131-41e6-af8d-41a3ec95a649).

This is distinct from `bob-customer-intel-digest` — that skill produces a
separate news/leadership-change digest and is not touched by this task.

## Steps

1. Pull Dylan's active Salesforce accounts (`CSM__r.Name = 'Dylan Brightbill'`)
   with their current values for: ARR (active subscription), ARR (sum of
   amount), renewal date, meeting cadence, churn score, risk records, expansion
   pipeline / open opportunities, active processing status, implementation
   projects, customer service start date, support level, fiscal year,
   processing frequency, previous tool, seats occupied, payees purchased, seat
   utilization, instance seat count, private/public, industry.

2. Follow `docs/shared-refresh-protocol.md` in the `csm-command-center` repo
   exactly for the publish step:
   - Check `syncLocks.bob` — this is a cron run, so proceed regardless of the
     lock (crons never wait).
   - Set `syncLocks.bob` to now, read the artifact's current state.
   - Match each Salesforce account to an existing `accounts[]` entry by
     `sfdcId` (already a stable identifier from the T1 migration — no fuzzy
     matching needed here, unlike meeting-prep/eod-todo).
   - Replace only the Salesforce-owned fields on each matched account. Leave
     `overrides`, `meetings`, `tasks`, and `archived` completely untouched.
   - Publish, clear `syncLocks.bob`, set `lastSynced.salesforce` to now.

3. If nothing changed since the last sync, skip the publish — don't write a
   no-op version.

4. If a new Salesforce account exists that isn't in `accounts[]` yet, add it
   with these Salesforce-owned fields populated and every CSM-judgment field
   (`csmSentiment`, `risk`, `notes`, `capResearchStatus`, `ciqExecutiveSponsor`,
   `lastEbr`) null — Dylan fills those in by hand.

## Context

- Dylan manages enterprise accounts (2,000+ employees) on CaptivateIQ.
- He is measured on NRR — surface anything tied to renewal risk or expansion,
  but this skill's job is the sync itself, not analysis or commentary.
- No em dashes; short paragraphs, clear next actions if anything needs his
  attention (e.g. a brand-new account with no CSM judgment fields yet).
