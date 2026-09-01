# CSM Command Center — CoWork Adaptation Design

> **Status:** Draft
> **Author:** Claude (with Dylan Brightbill)
> **Date:** 2026-09-01
> **Branch:** `cowork` (diverges permanently from `main`, not intended to merge back)
> **Jira:** Not applicable. Personal CSM tooling, not a CaptivateIQ product ticket.

## Context

The `main` branch's CSM Command Center (see
[2026-09-01-csm-command-center-spec.md](2026-09-01-csm-command-center-spec.md))
targets Claude Code: a CSM clones the repo, runs `scripts/setup.py` to
generate personalized skill files, and installs those as scheduled tasks
in their own Claude Code session.

Most CSMs work in Claude Chat or Claude CoWork, not Claude Code. CoWork
shares Claude Code's core toolkit — sandboxed Bash, Read/Write/Edit,
the Artifact tool, the same MCP connectors, the same scheduled-tasks
mechanism — but differs in ways that break the `main` branch's onboarding
flow:

- File paths are sandboxed/mapped, not a raw persistent filesystem tied to
  a git working directory.
- CoWork has "no git/dev environment framing" — it's built for document
  and workflow output, not shipping code. There's no natural place for a
  cloned repo to live session-to-session.
- The GitHub MCP connector (API/repo operations) is unreliable — confirmed
  failing to connect in at least one CoWork session (auth server issue),
  independent of repo visibility.
- Plain `WebFetch` of `raw.githubusercontent.com` **is** confirmed reachable
  from a CoWork session, unauthenticated, with no proxy/allowlist block —
  verified directly by fetching a live file. This is the one dependency the
  design below relies on.

This document defines a `cowork`-branch-only variant that gets a CSM to
the same end state (a personal Command Center artifact plus three
scheduled automations) without git, without the GitHub connector, and
without any script execution outside a single chat turn.

### References
- **Code-branch spec:** [2026-09-01-csm-command-center-spec.md](2026-09-01-csm-command-center-spec.md) — data model, write-lock protocol, and fuzzy-matcher algorithm are unchanged and inherited verbatim from this doc.
- **Shared protocol:** [../shared-refresh-protocol.md](../shared-refresh-protocol.md) — still the source of truth for the read-merge-write discipline; this design changes *where* that content lives at run time, not what it says.

## Scope

**In scope:** a CoWork-native onboarding flow (one pasted chat message →
published artifact + three scheduled automations), new `cowork/skills/*.md`
templates that are self-contained (no `{{REPO_PATH}}` pointer), and a
CoWork-specific README section with the paste-in-chat instructions.

**Out of scope:** CSM Tracker migration (CoWork onboarding is fresh-start
only — no predecessor artifact to migrate from), a shared/multi-CSM view,
resolving whether the artifact's refresh-button (ask-Claude) capability is
available — this was already an open question on `main` and stays open
here; the chat-triggered manual refresh is the tested fallback regardless.

**Constraints:** same as the Code-branch spec — personal tool, no SLA, no
alerting, stale `lastSynced` is an acceptable failure signal, artifact must
stay private.

## Technical Design

### Architecture

```
raw.githubusercontent.com/.../cowork/skills/*.md  ──WebFetch──┐
                                                                 ├──> Claude resolves {{TOKENS}} inline
CSM's pasted setup message (name; URL/filter only if re-running)┘         │
                                                                          ▼
                                                    Artifact tool (publish dashboard)
                                                          │
                                                          ▼
                                        3x scheduled tasks, each created with the
                                        fully-resolved skill text as its prompt body
                                        (bob-sfdc-sync, morning-meeting-prep, eod-todo)
```

Everything `scripts/setup.py` and `scripts/build-artifact.py` do on disk in
the Code version, Claude does live in one conversation turn on this
branch: fetch → substitute → publish → schedule. Nothing is written back
to the repo from a CSM's session — the fetched templates are read-only
content.

**Scheduled tasks are snapshots, not live references.** A task's prompt
has the CSM's name, artifact URL, and SFDC filter already baked in as
plain text — there is no indirection to "look up the current artifact URL"
at run time. If a CSM's artifact URL ever changes (e.g. a republish issues
a new URL), the three scheduled tasks must be recreated manually. This is
a deliberate simplicity choice, not an oversight — confirmed acceptable
given the rarity of that event at this scale.

### Components — changes needed on the `cowork` branch

| Path | Change |
|---|---|
| `cowork/skills/bob-sfdc-sync.md`, `morning-meeting-prep.md`, `eod-todo-csm-tracker.md` (new) | Same three skills, same `{{CSM_NAME}}` / `{{ARTIFACT_URL}}` / `{{SFDC_CSM_FILTER}}` tokens as `main`'s `skills/*/SKILL.md`, but with the shared-refresh-protocol's read-merge-write steps and the fuzzy-matcher algorithm **inlined directly** — no `{{REPO_PATH}}` pointer, since there's no local clone at cron-run time to resolve one against. |
| `cowork/README.md` (new) | CoWork-flavored onboarding message: fetch instructions instead of `git clone`, no mention of `setup.py` or local scheduled-task installation steps. |
| `scripts/setup.py`, `scripts/build-artifact.py` | Not used on this branch. Their jobs (token substitution, artifact publish) happen live in the setup conversation instead of via script execution. Left absent from `cowork/`, not deleted from the branch's copy of `scripts/` — no need to actively remove them, they're simply not part of the CoWork flow. |
| `scripts/migrate-csm-tracker.py` | Not applicable — no CSM Tracker predecessor exists for a fresh CoWork user. Out of scope, not solved here. |
| Data model, write-lock protocol, fuzzy-matcher algorithm | Unchanged from `main`. Already artifact-tool-based, not filesystem-based — nothing about the protocol assumed Claude Code specifically. |

### Setup sequence

1. Parse the CSM's full name from the pasted message (required). Parse an
   existing artifact URL / SFDC filter only if they are re-running setup,
   not a fresh install.
2. `WebFetch` the three raw skill templates from the `cowork` branch, plus
   `src/artifact/command-center.html` and `scripts/empty-seed.json` (both
   already present on `cowork`, inherited from `main` at the branch point —
   no need to recreate them).
3. Substitute `{{TOKENS}}` inline on the fetched text — plain string
   replacement on content already in context; no script invocation.
4. Publish the seeded HTML as an Artifact via the Artifact tool. Capture
   the returned URL.
5. Create three scheduled tasks (via the `schedule` skill /
   `scheduled-tasks` MCP tool), one per automation, each with its
   fully-resolved skill text as the prompt body and the original cadence:
   `bob-sfdc-sync` Mon/Wed/Fri 5am, `morning-meeting-prep` weekdays 7am,
   `eod-todo-csm-tracker` weekdays 3:30pm.
6. Report back to the CSM: the artifact URL to bookmark, and confirmation
   that three automations are scheduled.

### Error handling

- **WebFetch failure** (branch renamed, GitHub unreachable, rate-limited)
  → surface directly to the CSM; never silently fall back to stale or
  guessed content.
- **Scheduled-task creation failure** → surface per-task, naming which
  automation failed and why; never silently skip one of the three.
- **Artifact refresh-button capability** → same open question already
  flagged on `main`; unresolved here too. Chat-triggered manual refresh is
  the tested fallback path regardless of button availability.
- **SFDC name/filter mismatch** → same override mechanism as `main`
  (`--sfdc-filter` equivalent, passed as `{{SFDC_CSM_FILTER}}`), unchanged.

### Testing Strategy

No automated tests, consistent with the Code-branch spec's own scale
(personal tool, manual verification throughout). Before this ships to any
CSM other than Dylan: one full dry run from a clean state — no existing
artifact, no existing scheduled tasks — running the actual onboarding
message in a real CoWork session, confirming all three scheduled tasks
fire correctly on their first real run and that read-merge-write locking
holds under that execution model. This mirrors the per-ticket manual
verification the Code-branch spec already used.

## Risks & Open Questions

- ⚠️ **Scheduled-task snapshot staleness** — carried forward from the
  architecture section above: an artifact URL change requires manually
  recreating all three scheduled tasks. Accepted risk, not mitigated
  further, per explicit decision above.
- ❓ **Artifact ask-Claude capability availability** — unresolved, inherited
  unchanged from the Code-branch spec.
- ❓ **GitHub connector recovery** — if/when the GitHub MCP connector
  starts working reliably in CoWork, it could replace `WebFetch` for
  fetching templates with no functional change to this design. Not a
  blocker either way since `WebFetch` is already confirmed working.

---

*This is a living document. Update as implementation reveals new information.*
