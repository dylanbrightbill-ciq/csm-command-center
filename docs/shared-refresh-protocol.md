# Shared refresh protocol

Followed by every skill that writes into the Command Center artifact
(`bob-sfdc-sync`, `morning-meeting-prep`, `eod-todo-csm-tracker`). Each owns a
different top-level slice of the state and must never touch another's.

| Skill | Owns | Never touches |
|---|---|---|
| `bob-sfdc-sync` | `accounts` (SFDC-owned fields only — everything except the 7 manual fields below), `lastSynced.salesforce` | `overrides`, `meetings`, `tasks`, `archived`, and on `accounts`: `csmSentiment`, `risk`, `notes`, `capResearchStatus`, `ciqExecutiveSponsor`, `lastEbr`, `msaPriceIncreaseCap` — the CSM's manual judgment calls, never synced |
| `morning-meeting-prep` | `meetings[date][accountId]`, `lastSynced.meetings` | `accounts`, `overrides`, `tasks`, `archived` |
| `eod-todo-csm-tracker` | `tasks` (append-only), `lastSynced.eodTodo` | `accounts`, `overrides`, `meetings` |

## A fourth writer: the page itself

The artifact's own BoB table can self-publish too — inline-editing one of the
7 manual account fields calls the `artifact` capability's `publish()` directly
from the browser, no skill or cron involved. It follows a much simpler rule
than the lock protocol below: the platform does compare-and-set for it
(`publish` rejects `conflict` if a skill published in between, and every open
view — including the editor's — just reloads to the winner; no retry). It
only ever touches the one field a viewer edited, on one account, so it can
never step on a skill's owned keys. See `DOC_TEMPLATE_SRC` in
`src/artifact/command-center.html` for how the page reconstructs a full
document to publish without serializing the live DOM — re-run
`scripts/build-artifact.py` after any HTML/CSS/JS change to that file, since
it re-embeds that template.

## The publish cycle (every trigger — cron or manual — follows this)

1. Check `syncLocks.<yours>`.
   - **Cron**: ignore the lock, proceed straight to step 2. Crons never wait.
   - **Manual** (chat or button): if set, poll every ~5s until clear, then
     proceed. This is the only difference between the two trigger paths.
2. Read the artifact's *current* published state via the Artifact tool
   (`action: "read"`).
3. Set `syncLocks.<yours>` to the current ISO timestamp and publish that
   alone — read again immediately before this write so step 1's poll and this
   set happen against the same fresh read, not a stale one.
4. Do your actual work (gather data, resolve accounts via the fuzzy matcher
   below).
5. Read the artifact's current state again — it may have changed since step
   3 if another skill published in between.
6. Merge: replace only the field(s) in the "Owns" column above. Every other
   top-level key — untouched, byte-for-byte.
7. Publish the merged state, then clear `syncLocks.<yours>` (set to `null`)
   in a follow-up publish.

Skip the publish entirely if your work produced nothing new (no SFDC changes,
no external meetings today, no todos worth adding) — never publish a no-op.

## Fuzzy account matching

Used by `morning-meeting-prep` and `eod-todo-csm-tracker` to resolve a
free-text name (a calendar attendee's company, a Slack mention) to a real
`accountId`. Same algorithm as `scripts/migrate-csm-tracker.py`'s proven
precedent (normalize → alias map → substring fallback) — don't reimplement.

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

Extend `ALIASES` as mismatches are discovered in real runs — same discipline
the migration script already uses.
